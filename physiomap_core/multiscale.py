"""Multi-scale (cross-scale) reasoning over constitutive edges.

PhysioMap keeps typed dependence layers separate (see ``README.md`` and
``docs/MULTISCALE.md``):

* **CAUSAL influences** — interventionist, signed, may cycle; reasoned over by
  :mod:`physiomap_core.sigma` (sigma-separation) and :mod:`physiomap_core.qualitative`
  (comparative statics). Typed production and quantitative records may contribute explicitly
  tagged compatibility shadows to that operational graph; they remain distinct authored records.
* **CONSTITUTIVE** edges — ``part_of`` + *determination*: the micro
  configuration *fixes* (supervenes) the macro quality. This is **not** causation, so it
  is handled here, in a separate pass.

This module provides the **upward determination sign-transfer**: once the causal solver
has produced signs at each scale, a change in a constituting (micro) quality determines a
change in the constituted (macro) quality, with the edge's determination sign. Downward
transfer (macro change -> which micro changed?) is multiply realizable and intentionally
**not** inferred here (see the design doc).
"""

from __future__ import annotations

from collections.abc import Iterable

import networkx as nx
from pydantic import BaseModel, Field

from physiomap_core.model import PhysioMap, Sign, combine_parallel
from physiomap_core.qualitative import (
    SCC_EXACT_MAX,
    Intervention,
    _plus,
    _solve_scc_exact,
    _solve_scc_loop,
    _solve_singleton,
    _times,
    _ZERO,
    solve_signs,
)

__all__ = [
    "constitutive_graph",
    "propagate_constitutive",
    "MultiscaleResult",
    "solve_multiscale",
]


def constitutive_graph(pmap: PhysioMap) -> nx.DiGraph:
    """The constitutive DiGraph (``micro -> macro``; edges carry the determination ``sign``).

    Must be acyclic (scales are strictly nested), so determination can be propagated in
    topological order.
    """
    from physiomap_core.quantity import effective_determination_sign

    g: nx.DiGraph = nx.DiGraph()
    g.add_nodes_from(pmap.node_ids)
    for e in pmap.constitutive_edges:
        # quality-typed determination: use the sign DERIVED from the macro quality's measurement
        # type where it fixes one (extensive/rate summand +, ratio numerator +, denominator −),
        # falling back to the asserted sign for hard-intensive macros.
        g.add_edge(e.micro, e.macro, sign=effective_determination_sign(pmap, e).value)
    if not nx.is_directed_acyclic_graph(g):
        raise ValueError("constitutive graph must be acyclic (micro -> macro)")
    return g


def propagate_constitutive(
    pmap: PhysioMap, signs: dict[str, Sign]
) -> tuple[dict[str, Sign], list[str]]:
    """Transfer signs **upward** across constitutive edges by determination.

    Given causal signs ``signs`` (node id -> Sign), walk the constitutive DAG micro->macro
    in topological order; each constituted node receives ``⊕`` of ``sign(micro) ⊗
    determination_sign`` over its constituents. If a macro node already has a *causal*
    sign, the two are combined with ``⊕`` (a disagreement yields ``Sign.UNKNOWN`` and is
    logged). Returns ``(updated_signs, notes)``.
    """
    cg = constitutive_graph(pmap)
    out = dict(signs)
    notes: list[str] = []
    for node in nx.topological_sort(cg):
        constituents = list(cg.predecessors(node))
        contribs = [
            out[m] * Sign(cg.edges[m, node]["sign"])  # micro sign ⊗ determination sign
            for m in constituents
            if m in out
        ]
        if not contribs:
            continue
        determined = combine_parallel(contribs)
        if node in out:
            combined = combine_parallel([out[node], determined])
            if combined is not out[node]:
                notes.append(
                    f"{node}: causal={out[node].value} vs determination="
                    f"{determined.value} -> {combined.value}"
                )
            out[node] = combined
        else:
            out[node] = determined
            notes.append(
                f"{node}: determined from {len(contribs)} constituent(s) -> "
                f"{determined.value}"
            )
    return out, notes


class MultiscaleResult(BaseModel):
    """Result of a multi-scale solve: causal signs plus constitutive determination."""

    predicted: dict[str, Sign] = Field(default_factory=dict)
    causal_only: dict[str, Sign] = Field(default_factory=dict)
    ambiguities: list[str] = Field(default_factory=list)
    constitutive_notes: list[str] = Field(default_factory=list)


def solve_multiscale(
    pmap: PhysioMap,
    intervention: Intervention,
    scc_exact_max: int = SCC_EXACT_MAX,
    contexts: Iterable[str] | None = None,
) -> MultiscaleResult:
    """Unified multi-scale solve: causal comparative statics + constitutive determination,
    interleaved over a meta-DAG of causal SCCs linked **upward** by constitutive edges.

    A change therefore flows through the signed operational graph; up across scales by
    determination; and then onward through another operational component (so e.g. a molecular drug reaches
    organ-system physiology). Causal SCCs are solved exactly (≤ ``scc_exact_max``) or by the
    loop-aware engine; cross-scale determination enters as additional forcing into the
    constituted node. Constitutive edges are never treated as causal (no σ-traversal).
    """
    gcausal = pmap.causal_subgraph(contexts)
    cg = constitutive_graph(pmap)  # micro -> macro, determination sign
    fixed: dict[str, str] = {t: s.value for t, s in intervention.targets.items()}

    gi = gcausal.copy()
    for t in fixed:  # do-surgery on the causal graph only
        gi.remove_edges_from([(p, t) for p in list(gi.predecessors(t))])

    # reachable over BOTH causal and constitutive edges
    union: nx.DiGraph = nx.DiGraph()
    union.add_nodes_from(gi.nodes)
    union.add_edges_from(gi.edges)
    union.add_edges_from(cg.edges)
    reach: set[str] = set(fixed)
    for t in fixed:
        reach |= nx.descendants(union, t)

    sign: dict[str, str] = dict(fixed)
    ambig: list[str] = []
    notes: list[str] = []

    # condense causal SCCs, then build a meta-DAG adding constitutive edges (component level)
    cond = nx.condensation(gi)
    comp_of = {n: c for c in cond.nodes for n in cond.nodes[c]["members"]}
    meta: nx.DiGraph = nx.DiGraph()
    meta.add_nodes_from(cond.nodes)
    meta.add_edges_from(cond.edges)
    for micro, macro in cg.edges:
        cm, cM = comp_of[micro], comp_of[macro]
        if cm != cM:
            meta.add_edge(cm, cM)
    if not nx.is_directed_acyclic_graph(meta):
        raise ValueError("combined causal+constitutive meta-graph has a cross-scale cycle")

    for comp in nx.topological_sort(meta):
        members = set(cond.nodes[comp]["members"])
        if members.isdisjoint(reach):
            continue
        # determination forcing into each member from already-solved constituents (micro)
        extra: dict[str, str] = {}
        for n in members:
            acc = _ZERO
            seen = False
            for micro in cg.predecessors(n):
                if micro in sign:
                    acc = _plus(acc, _times(sign[micro], cg.edges[micro, n]["sign"]))
                    seen = True
            if seen and acc != _ZERO:
                extra[n] = acc
                notes.append(f"{n}: determination forcing {acc} from constituents")
        if len(members) == 1:
            (n,) = tuple(members)
            if n in fixed:
                continue
            _solve_singleton(n, gi, sign, ambig, extra=extra)
        elif len(members) <= scc_exact_max:
            _solve_scc_exact(members, gi, sign, fixed, ambig, extra=extra)
        else:
            _solve_scc_loop(members, gi, sign, fixed, ambig, extra=extra)

    predicted: dict[str, Sign] = {}
    for node in reach:
        s = sign.get(node, _ZERO)
        if s in ("+", "-"):
            predicted[node] = Sign(s)
        elif s == "?":
            predicted[node] = Sign.UNKNOWN
    causal_only = solve_signs(pmap, intervention, scc_exact_max=scc_exact_max).predicted
    return MultiscaleResult(
        predicted=predicted,
        causal_only=causal_only,
        ambiguities=ambig,
        constitutive_notes=notes,
    )
