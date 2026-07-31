"""Dynamic *synthetic knockout* — clamp any node and derive the phenotypes, on demand.

This is the **dynamic** counterpart to the precomputed rare-disease traces
(:mod:`physiomap_core.trace`): instead of a fixed catalogue of curated disorders, you pick
*any* node, impose a ``do()`` of either direction (a synthetic knockout / overexpression), and
the comparative-statics solver derives the steady-state sign of every reachable node. The
HPO-mapped nodes among them are reported as **derived phenotypes** (PATO direction → HPO term),
exactly as the forward HPO benchmark scores them — but driven live, for an arbitrary lesion.

A single solve over the full composed map is ~0.1 s, so this runs interactively (CLI and the
web service in :mod:`web.api`). The signs are the **comparative static at the stable fixed point**
(``sign(dx*/dθ)``), not naive forward propagation — a node inside the whole-body homeostatic SCC
honestly resolves to ``?`` (abstains) rather than reporting a magnitude-dependent guess.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from physiomap_core.model import PhysioMap, Sign
from physiomap_core.modulation import GainChange, Synergy, gain_changes, synergies
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from physiomap_core.trace import combined_do_graph

__all__ = [
    "PhenotypeHit",
    "KnockoutResult",
    "phenotype_index",
    "abnormality_index",
    "knockout",
    "knockout_multi",
    "trace_to",
    "trace_many",
    "trace_many_multi",
]

ARROW = {Sign.PLUS: "↑", Sign.MINUS: "↓", Sign.UNKNOWN: "?"}

_TERM_MAP = Path(__file__).resolve().parent.parent / "benchmarks/hpo/hpo_term_map.yaml"
_ABN_MAP = Path(__file__).resolve().parent.parent / "benchmarks/hpo/hpo_abnormality_terms.yaml"


@lru_cache(maxsize=1)
def phenotype_index(term_map_path: str | None = None) -> dict[str, dict[str, dict[str, str]]]:
    """node id -> {"+": {"hpo", "label"}, "-": {...}} from the HPO term map.

    An HPO abnormal-quantity term is a (node, PATO direction) pair; this inverts the map so a
    predicted node+sign can be named as a phenotype. Cached (the file is static per process).
    """
    path = Path(term_map_path) if term_map_path else _TERM_MAP
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    idx: dict[str, dict[str, dict[str, str]]] = {}
    for hpo, spec in (data.get("terms") or {}).items():
        node, sign = spec.get("node"), spec.get("sign")
        if not node or sign not in ("+", "-"):
            continue
        # several HPO terms can map to one (node, sign); keep the first (most canonical) seen
        idx.setdefault(node, {}).setdefault(sign, {"hpo": hpo, "label": spec.get("label", hpo)})
    return idx


@lru_cache(maxsize=1)
def abnormality_index(abn_map_path: str | None = None) -> dict[str, dict[str, str]]:
    """node id -> {"hpo", "label"} for the neutral *"Abnormality of X"* HPO term.

    Built by ``scripts/build_abnormality_terms.py`` from the directional term map + hp.obo. Lets a
    *reachable-but-direction-undetermined* (``?``) trait be reported as **"X affected"** and linked
    to HPO's direction-neutral term. Cached (static per process); ``{}`` if the file is absent.
    """
    path = Path(abn_map_path) if abn_map_path else _ABN_MAP
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    out: dict[str, dict[str, str]] = {}
    for node, spec in (data.get("abnormality_terms") or {}).items():
        if spec.get("hpo"):
            out[node] = {"hpo": spec["hpo"], "label": spec.get("label", spec["hpo"])}
    return out


class PhenotypeHit(BaseModel):
    """A derived phenotype on an HPO-mapped node.

    ``effect="directional"`` (the default) is a determinate ``+``/``-`` sign. ``effect="affected"``
    is the neutral case — the trait is *reachable* from the intervention (so it **is** affected) but
    its comparative-statics sign is ``?`` (e.g. a feedback-core node); ``sign`` is then ``"?"`` and
    ``hpo``/``hpo_label`` point at HPO's direction-neutral *"Abnormality of X"* term.
    """

    node: str
    label: str            # node label
    sign: str             # "+" / "-" / "?"
    effect: str = "directional"    # "directional" | "affected"
    hpo: str | None = None
    hpo_label: str | None = None   # the HPO term name for this node+direction (or the neutral term)
    in_big_scc: bool = False


class KnockoutResult(BaseModel):
    """Result of a synthetic knockout: full predicted field + the HPO phenotypes among it.

    Supports clamping one *or several* nodes at once: ``do`` is the full ``node -> "+"/"-"``
    clamp set. For a single-node knockout the legacy ``node``/``node_label``/``sign`` fields
    mirror the one clamped node (back-compat); for a multi-node clamp they hold the *first*
    target and the full set lives in ``do``/``do_labels``.
    """

    node: str
    node_label: str
    sign: str
    do: dict[str, str] = Field(default_factory=dict)         # every clamped node -> "+"/"-"
    do_labels: dict[str, str] = Field(default_factory=dict)  # clamped node -> label
    predicted: dict[str, str] = Field(default_factory=dict)   # node -> "+"/"-"/"?"
    phenotypes: list[PhenotypeHit] = Field(default_factory=list)   # determinate (↑/↓)
    affected: list[PhenotypeHit] = Field(
        default_factory=list,
        description="Reachable HPO traits whose direction is undetermined (?): 'X affected'.",
    )
    gain_changes: list[GainChange] = Field(
        default_factory=list,
        description="Multiplicative edges whose gain this intervention strengthens/weakens (2nd order).",
    )
    synergies: list[Synergy] = Field(
        default_factory=list,
        description="Modulated targets where source & modulator both move: super-/sub-additive verdict.",
    )
    n_predicted: int = 0
    n_determinate: int = 0
    constitutive_notes: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(
        default_factory=list,
        description="Explicit steady-state influence contexts selected for this solve.",
    )
    error: str | None = None


def knockout(
    pmap: PhysioMap,
    node: str,
    sign: Sign | str,
    contexts: Iterable[str] | None = None,
) -> KnockoutResult:
    """Clamp a single ``node`` to ``sign`` (synthetic knockout/overexpression), derive phenotypes.

    Thin wrapper over :func:`knockout_multi` for the common one-node case.
    """
    sign = Sign(sign) if not isinstance(sign, Sign) else sign
    return knockout_multi(pmap, {node: sign}, contexts=contexts)


def knockout_multi(
    pmap: PhysioMap,
    targets: dict[str, Sign | str],
    contexts: Iterable[str] | None = None,
) -> KnockoutResult:
    """Clamp **several** nodes at once (each ``+``/``-``) and derive the joint phenotypes.

    A multi-node ``do()`` — the comparative-statics solver already accepts a multi-target
    :class:`~physiomap_core.qualitative.Intervention`, so this is the same single solve over the
    composed map with more than one node clamped. Returns the steady-state sign of every reachable
    node plus the HPO-mapped phenotypes among the *determinate* predictions, ranked SCC-out.
    """
    selected_contexts = list(contexts) if contexts is not None else []
    active_map = pmap.context_slice(selected_contexts) if contexts is not None else pmap
    do = {n: (Sign(s) if not isinstance(s, Sign) else s) for n, s in targets.items()}
    if not do:
        return KnockoutResult(node="", node_label="", sign="", error="no targets given")
    first = next(iter(do))
    unknown = [n for n in do if n not in set(active_map.node_ids)]
    if unknown:
        return KnockoutResult(node=first, node_label=first, sign=do[first].value,
                              do={n: s.value for n, s in do.items()},
                              error=f"unknown node(s): {', '.join(unknown)}")

    label = "knockout " + ", ".join(f"{n}={s.value}" for n, s in do.items())
    iv = Intervention(targets=do, label=label)
    res = solve_multiscale(active_map, iv)
    predicted = {n: s.value for n, s in res.predicted.items()}

    def _lbl(n: str) -> str:
        try:
            return active_map.node(n).label
        except KeyError:
            return n

    big_scc = _big_scc(active_map)
    idx = phenotype_index()
    abn = abnormality_index()
    hits: list[PhenotypeHit] = []      # determinate (↑/↓)
    affected: list[PhenotypeHit] = []  # reachable but direction-undetermined (?): "X affected"
    for n, s in res.predicted.items():
        if n in do:
            continue
        if s in (Sign.PLUS, Sign.MINUS):
            ph = idx.get(n, {}).get(s.value)
            if ph:
                hits.append(PhenotypeHit(node=n, label=_lbl(n), sign=s.value, effect="directional",
                                         hpo=ph["hpo"], hpo_label=ph["label"], in_big_scc=n in big_scc))
        elif s == Sign.UNKNOWN and n in idx:
            # reachable HPO-recognized trait with an ambiguous net sign -> "affected" (neutral).
            a = abn.get(n)
            affected.append(PhenotypeHit(node=n, label=_lbl(n), sign="?", effect="affected",
                                         hpo=(a or {}).get("hpo"), hpo_label=(a or {}).get("label"),
                                         in_big_scc=n in big_scc))
    # core (non-SCC) traits first, then alphabetical
    hits.sort(key=lambda h: (h.in_big_scc, h.label.lower()))
    affected.sort(key=lambda h: (h.in_big_scc, h.label.lower()))

    # second-order modulation layer (pure post-processing of the solved field — no extra solve)
    gc = gain_changes(active_map, do, res.predicted)
    sy = synergies(active_map, do, res.predicted)

    n_det = sum(1 for v in predicted.values() if v in ("+", "-"))
    return KnockoutResult(
        node=first, node_label=_lbl(first), sign=do[first].value,
        do={n: s.value for n, s in do.items()},
        do_labels={n: _lbl(n) for n in do},
        predicted=predicted, phenotypes=hits, affected=affected,
        gain_changes=gc, synergies=sy,
        n_predicted=len(predicted), n_determinate=n_det,
        constitutive_notes=res.constitutive_notes,
        contexts=selected_contexts,
    )


def _sign_path(g, nodes: list[str], sign: Sign) -> list[dict]:
    s = sign
    steps: list[dict] = []
    for a, b in zip(nodes, nodes[1:]):
        es = Sign(g.edges[a, b]["sign"])
        s = s * es
        steps.append({"src": a, "dst": b, "sign": es.value,
                      "kind": g.edges[a, b].get("kind", "causal"), "running": s.value})
    return steps


def trace_to(
    pmap: PhysioMap,
    node: str,
    sign: Sign | str,
    target: str,
    max_paths: int = 1,
    contexts: Iterable[str] | None = None,
) -> list[list[dict]]:
    """One illustrative signed path from the knockout clamp to a derived phenotype (for the UI).

    Uses a BFS **shortest path** (O(V+E)) rather than enumerating simple paths — the latter is
    combinatorially explosive when the target sits in the whole-body SCC. The path is purely
    illustrative (the *net* sign is the solver's comparative static, not this path product).
    """
    import networkx as nx

    sign = Sign(sign) if not isinstance(sign, Sign) else sign
    active_map = pmap.context_slice(contexts) if contexts is not None else pmap
    g = combined_do_graph(active_map, {node: sign})
    if not (g.has_node(node) and g.has_node(target)) or not nx.has_path(g, node, target):
        return []
    return [_sign_path(g, nx.shortest_path(g, node, target), sign)]


def trace_many(
    pmap: PhysioMap,
    node: str,
    sign: Sign | str,
    targets: list[str],
    contexts: Iterable[str] | None = None,
) -> dict[str, list[dict]]:
    """Shortest signed path to each of ``targets`` — builds the do-graph **once** (UI fast path)."""
    sign = Sign(sign) if not isinstance(sign, Sign) else sign
    return trace_many_multi(pmap, {node: sign}, targets, contexts=contexts)


def trace_many_multi(
    pmap: PhysioMap,
    do: dict[str, Sign | str],
    targets: list[str],
    contexts: Iterable[str] | None = None,
) -> dict[str, list[dict]]:
    """Shortest signed path from **any** clamped node to each of ``targets`` (multi-clamp UI path).

    Builds the combined do-graph once and runs a single multi-source BFS: each target's path
    starts at whichever clamped node is nearest, and the running sign is seeded from that
    clamp's direction. Purely illustrative — the *net* sign is the solver's comparative static.
    """
    import networkx as nx

    do = {n: (Sign(s) if not isinstance(s, Sign) else s) for n, s in do.items()}
    active_map = pmap.context_slice(contexts) if contexts is not None else pmap
    g = combined_do_graph(active_map, do)
    sources = [n for n in do if g.has_node(n)]
    if not sources:
        return {}
    # multi-source shortest paths via a virtual super-source feeding every clamped node, then a
    # single BFS (networkx has no multi_source_shortest_path in all versions).
    super_src = "__do__"
    for s in sources:
        g.add_edge(super_src, s, sign=do[s].value, kind="causal")
    paths = nx.single_source_shortest_path(g, super_src)
    out: dict[str, list[dict]] = {}
    for t in targets:
        p = paths.get(t)
        if p and len(p) > 2:  # [super_src, clamped_source, ..., t]
            real = p[1:]
            seed = do[real[0]]  # sign of the nearest clamped source on this path
            out[t] = _sign_path(g, real, seed)
    return out


def _big_scc(pmap: PhysioMap) -> set[str]:
    """The largest strongly-connected component of the causal graph (the whole-body homeostat)."""
    import networkx as nx

    g = pmap.causal_subgraph()
    sccs = list(nx.strongly_connected_components(g))
    return max(sccs, key=len) if sccs else set()


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    import sys
    from physiomap_core.hpo import build_map

    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2 or args[1] not in ("+", "-"):
        print("usage: python -m physiomap_core.knockout <node> <+|-> [target]")
        print("  e.g. python -m physiomap_core.knockout hepcidin -")
        return 2
    node, sgn = args[0], args[1]
    pmap = build_map()
    r = knockout(pmap, node, sgn)
    if r.error:
        print(r.error)
        return 2
    print(f"=== intervention: do({r.node_label} = {sgn}) ===")
    print(f"predicted {r.n_predicted} nodes, {r.n_determinate} determinate; "
          f"{len(r.phenotypes)} directional + {len(r.affected)} affected HPO trait(s)\n")
    if len(args) >= 3:  # also show the trace to one named target
        from physiomap_core.trace import render
        iv = Intervention(targets={node: Sign(sgn)}, label="intervention")
        print(render(pmap, iv, args[2]))
        print()
    if not r.phenotypes and not r.affected:
        print("(no HPO trait reached — clamp may sit upstream of only the SCC,")
        print(" or its targets are leaf analytes that honestly abstain)")
        return 0
    if r.phenotypes:
        print("Derived phenotypes (determinate):")
        for h in r.phenotypes:
            scc = "  [whole-body SCC]" if h.in_big_scc else ""
            print(f"  {ARROW[Sign(h.sign)]} {h.label}  —  {h.hpo_label} ({h.hpo}){scc}")
    if r.affected:
        print("\nAffected (direction undetermined — \"X affected\"):")
        for h in r.affected:
            scc = "  [whole-body SCC]" if h.in_big_scc else ""
            link = f"  —  {h.hpo_label} ({h.hpo})" if h.hpo else ""
            print(f"  ~ {h.label} affected{link}{scc}")
    if r.gain_changes:
        print("\nGain changes (2nd-order sensitization):")
        for g in r.gain_changes:
            w = "strengthened" if g.direction == "+" else "weakened"
            print(f"  {g.direction} {g.edge_source} -> {g.edge_target} coupling {w}  (via {g.modulator})")
    if r.synergies:
        print("\nSynergies (joint do on a modulated target):")
        for s in r.synergies:
            print(f"  {s.verdict:13s} on {s.edge_target}  "
                  f"({s.edge_source} x {s.modulator}; cross={s.cross_sign}, net={s.target_direction})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
