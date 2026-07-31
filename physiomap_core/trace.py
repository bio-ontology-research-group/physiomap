"""Trace a Mendelian variant from the gene lesion to the endophenotype through PhysioMap.

A monogenic loss/gain-of-function is a ``do()`` that clamps the *direction* (↑/↓) of a primary
node. This module renders the **signed mechanistic path(s)** from that primary node to a target
phenotype — each step annotated with its typed relation, edge sign, and running ↑/↓ state. It
distinguishes authored causal influences, production shadows, quantitative-identity shadows,
and cross-scale **constitutive lifts** (micro ▷ macro). It then reconciles the
forward path product against the **comparative-statics** net sign from
:func:`physiomap_core.multiscale.solve_multiscale`.

The two can differ, and that difference is the whole point of PhysioMap: a forward path through a
homeostatic **feedback loop** (SCC) gives a naive sign, but the steady-state (compensated) sign is
the comparative static — which is honestly ``?`` when the loop makes it magnitude-dependent.
Endophenotypes are increased/decreased qualities (PATO directions), so each node renders as ↑/↓/?.
"""

from __future__ import annotations

import networkx as nx
from pydantic import BaseModel, Field

from physiomap_core.model import PhysioMap, Sign
from physiomap_core.multiscale import constitutive_graph, solve_multiscale
from physiomap_core.qualitative import Intervention

__all__ = ["combined_do_graph", "signed_paths", "trace", "render", "TraceStep", "PathTrace"]

ARROW = {Sign.PLUS: "↑", Sign.MINUS: "↓", Sign.UNKNOWN: "?"}


def combined_do_graph(pmap: PhysioMap, targets: dict[str, Sign]) -> nx.DiGraph:
    """Operational DiGraph after do-surgery plus constitutive lifts.

    Authored influences and typed compatibility shadows retain distinct ``kind`` values.
    Constitutive edges are then added as non-causal determination links.
    """
    g = pmap.causal_subgraph()
    for u, v in g.edges:
        g.edges[u, v]["kind"] = {
            "causal-influence": "causal",
            "production-derived": "production",
            "quantitative-derived": "quantitative",
        }.get(g.edges[u, v].get("edge_kind"), "causal")
    for t in targets:  # do-surgery: the variant overrides the clamped node's own inputs
        g.remove_edges_from([(p, t) for p in list(g.predecessors(t))])
    for u, v in constitutive_graph(pmap).edges:
        g.add_edge(u, v, sign=constitutive_graph(pmap).edges[u, v]["sign"], kind="constitutive")
    return g


class TraceStep(BaseModel):
    src: str
    dst: str
    edge_sign: Sign
    kind: str            # causal | production | quantitative | constitutive
    running: Sign        # ↑/↓/? state at dst along this path


class PathTrace(BaseModel):
    nodes: list[str]
    steps: list[TraceStep]
    net: Sign            # forward path-product sign at the target


def signed_paths(
    g: nx.DiGraph, source: str, target: str, source_sign: Sign,
    max_len: int = 12, max_paths: int = 24,
) -> list[PathTrace]:
    """Enumerate simple paths source→target, carrying the ↑/↓ state (sign product) along each."""
    if source == target or not g.has_node(source) or not g.has_node(target):
        return []
    if not nx.has_path(g, source, target):
        return []
    out: list[PathTrace] = []
    for nodes in nx.all_simple_paths(g, source, target, cutoff=max_len):
        s = source_sign
        steps: list[TraceStep] = []
        for a, b in zip(nodes, nodes[1:]):
            es = Sign(g.edges[a, b]["sign"])
            s = s * es
            steps.append(TraceStep(src=a, dst=b, edge_sign=es, kind=g.edges[a, b]["kind"], running=s))
        out.append(PathTrace(nodes=nodes, steps=steps, net=s))
        if len(out) >= max_paths:
            break
    out.sort(key=lambda p: len(p.nodes))
    return out


def trace(pmap: PhysioMap, intervention: Intervention, target: str,
          max_len: int = 12, max_paths: int = 24) -> dict:
    """Trace every primary clamp to ``target``: signed paths + comparative-statics net sign."""
    g = combined_do_graph(pmap, intervention.targets)
    paths: list[PathTrace] = []
    for src, sgn in intervention.targets.items():
        paths += signed_paths(g, src, target, sgn, max_len=max_len, max_paths=max_paths)
    net_cs = solve_multiscale(pmap, intervention).predicted.get(target)
    path_signs = {p.net for p in paths}
    forward = next(iter(path_signs)) if len(path_signs) == 1 else Sign.UNKNOWN
    return {"target": target, "paths": paths, "net_comparative_statics": net_cs, "net_forward": forward}


def render(pmap: PhysioMap, intervention: Intervention, target: str,
           label: str | None = None, **kw) -> str:
    """Human-readable end-to-end trace for one endophenotype."""
    def lab(n: str) -> str:
        try:
            return pmap.node(n).label
        except KeyError:
            return n

    r = trace(pmap, intervention, target, **kw)
    L = []
    src = ", ".join(f"{n} {ARROW[s]}" for n, s in intervention.targets.items())
    head = f"variant ⇒ do({src})  ──▶  {target} {ARROW.get(r['net_comparative_statics'], '·')}"
    if label:
        head += f"   [{label}]"
    L.append(head)
    if not r["paths"]:
        L.append("    (no path found from the clamp to this node)")
        return "\n".join(L)
    for i, p in enumerate(r["paths"][:6], 1):
        chain = []
        s0 = intervention.targets[p.nodes[0]]
        chain.append(f"{p.nodes[0]}{ARROW[s0]}")
        for st in p.steps:
            sep = {"constitutive": "▷", "production": "↠", "quantitative": "="}.get(
                st.kind, "→"
            )
            tag = {
                "constitutive": "(determination)",
                "production": f"(production {st.edge_sign.value})",
                "quantitative": f"(identity {st.edge_sign.value})",
            }.get(st.kind, f"({st.edge_sign.value})")
            chain.append(f" {sep}{tag} {st.dst}{ARROW[st.running]}")
        L.append(f"  path{i}: " + "".join(chain))
    cs, fwd = r["net_comparative_statics"], r["net_forward"]
    if cs is Sign.UNKNOWN and fwd in (Sign.PLUS, Sign.MINUS):
        L.append(f"    NB forward mechanism says {ARROW[fwd]}, but the steady-state (comparative "
                 f"statics) net is ? — {target} sits in a homeostatic feedback loop (SCC); the "
                 f"compensated sign is magnitude-dependent.")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    import sys
    from physiomap_core.hpo import build_map, load_disorders
    from pathlib import Path

    args = sys.argv[1:] if argv is None else argv
    pmap = build_map()
    if len(args) == 3:  # ad-hoc: <node> <+|-> <target>
        node, sgn, target = args
        iv = Intervention(targets={node: Sign(sgn)}, label="ad-hoc")
        print(render(pmap, iv, target))
        return 0
    # disorder mode: <disorder name substring> — trace to each phenotype
    name = args[0] if args else "hemochromatosis"
    ds = [d for d in load_disorders(Path(__file__).resolve().parent.parent / "benchmarks/hpo/disorders.yaml")
          if name.lower() in d.name.lower()]
    if not ds:
        print(f"no disorder matching {name!r}"); return 2
    d = ds[0]
    iv = Intervention(targets=d.primary, label=f"{d.name} ({d.gene}, OMIM {d.omim})")
    print(f"=== {d.name} — {d.gene} (OMIM {d.omim}) ===")
    print(f"mechanism: {d.mechanism}\n")
    for ph in d.phenotypes:
        print(render(pmap, iv, ph.node, label=ph.label))
        print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
