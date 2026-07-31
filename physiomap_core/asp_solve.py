"""ASP-based qualitative sign-solver for large feedback SCCs (scales past the exact cap).

The exact comparative-statics engine in :mod:`physiomap_core.qualitative` is `O(2^m)` and capped
at ``SCC_EXACT_MAX = 16``; above it the conservative loop-fixpoint engine abstains on *every*
negative-feedback conflict, so the large whole-body SCC abstains on the clinically
important feedback paradoxes (E6). This module solves the same SCCs with Answer Set Programming
(clingo), which performs *global* constraint satisfaction rather than local $\\oplus$-propagation and
so resolves loops the fixpoint engine cannot, while scaling to the whole-body component.

**Semantics and soundness.** We encode qualitative *sign-consistency*: a within-SCC node's
steady-state change is admissible iff its sign is supported by at least one incoming influence
(edge sign $\\otimes$ source sign, or external forcing), with the negative self-regulation/dissipation
(D3) absorbed into the per-row balance. Every *achievable* comparative-static sign pattern
$\\sign(-J^{-1}b)$ satisfies these (necessary) constraints, so the set of answer sets is a
**superset** of the achievable sign patterns. Hence a sign that is a *cautious consequence* (holds in
**all** answer sets) holds for the true solution too: **ASP-determinate $\\Rightarrow$ sound**. The
engine never invents a sign; like the exact engine it abstains (``?``) when the sign is not fixed.
It is no less conservative than the exact engine on small SCCs (verified) and strictly less
conservative than the loop-fixpoint engine on feedback loops.

This is the route named in the paper's future work (an answer-set encoding of sign-solvability that
determines a coordinate's sign iff all answer sets agree).
"""

from __future__ import annotations

import networkx as nx

from physiomap_core.model import PhysioMap, Sign
from physiomap_core.qualitative import (
    Intervention,
    SolveResult,
    _solve_singleton,
    _times,
)

__all__ = ["solve_signs_asp", "asp_scc_signs", "ASP_SCC_MIN"]

#: Non-trivial SCCs at least this big are sent to ASP; smaller ones keep the exact engine
#: (which is cheap and at least as informative). Set to 2 to use ASP for every loop.
ASP_SCC_MIN = 2

_ASP_PROGRAM = """
{ sign(V,p); sign(V,m); sign(V,z) } = 1 :- node(V).
sign(V,S) :- clamp(V,S).
influence(V,p) :- edge(U,V,plus),  sign(U,p).
influence(V,p) :- edge(U,V,minus), sign(U,m).
influence(V,m) :- edge(U,V,plus),  sign(U,m).
influence(V,m) :- edge(U,V,minus), sign(U,p).
pos(V) :- influence(V,p).
pos(V) :- ext(V,p).
neg(V) :- influence(V,m).
neg(V) :- ext(V,m).
:- sign(V,p), not pos(V).
:- sign(V,m), not neg(V).
:- sign(V,z), pos(V), not neg(V).
:- sign(V,z), neg(V), not pos(V).
#show sign/2.
"""


def asp_scc_signs(
    members: set[str],
    g: nx.DiGraph,
    sign: dict[str, str],
    fixed: dict[str, str],
    observed: dict[str, str] | None = None,
) -> dict[str, str]:
    """Determinate signs (``+``/``-``/``0``) for SCC members via ASP cautious consequences.

    ``sign`` holds already-solved signs (used for external forcing from outside the SCC);
    ``fixed`` are do-clamped nodes. Members absent from the returned map are ambiguous (``?``).

    ``observed`` (optional) *conditions* the solve on factually-observed member signs by
    integrity constraints (it filters answer sets without do-surgery) -- this is the
    abduction step of a counterfactual query. Conditioning can only shrink the answer-set
    family, so it never makes a determinate sign wrong, and may resolve members the marginal
    intervention leaves ``?``.
    """
    import clingo

    observed = observed or {}

    nodes = sorted(members)
    idx = {n: i for i, n in enumerate(nodes)}
    facts: list[str] = []
    for n in nodes:
        i = idx[n]
        if n in fixed:
            s = fixed[n]
            if s in ("+", "-"):
                facts.append(f"clamp({i},{'p' if s == '+' else 'm'}).")
            # a clamped-to-0 node simply exerts no influence; emit nothing
        else:
            facts.append(f"node({i}).")
        # within-SCC edges + external forcing
        for p in g.predecessors(n):
            es = g.edges[p, n]["sign"]
            if p in members and p != n:
                facts.append(f"edge({idx[p]},{i},{'plus' if es == '+' else 'minus'}).")
            elif p not in members:
                contrib = _times(sign.get(p, "0"), es)  # solved-parent sign x edge sign
                if contrib == "+":
                    facts.append(f"ext({i},p).")
                elif contrib == "-":
                    facts.append(f"ext({i},m).")
                elif contrib == "?":  # ambiguous external input: could push either way
                    facts.append(f"ext({i},p).")
                    facts.append(f"ext({i},m).")
    # abduction: condition on factually-observed member signs (filter answer sets, no surgery)
    for n, s in observed.items():
        if n in idx and s in ("+", "-"):
            facts.append(f":- not sign({idx[n]},{'p' if s == '+' else 'm'}).")

    ctl = clingo.Control(
        ["--enum-mode=cautious", "--models=0", "--warn=no-atom-undefined"]
    )
    ctl.add("base", [], _ASP_PROGRAM + "\n".join(facts))
    ctl.ground([("base", [])])
    cautious: list = []  # symbols of the last (intersection) model
    ctl.solve(on_model=lambda m: (cautious.clear(), cautious.extend(m.symbols(shown=True))))

    out: dict[str, str] = {}
    for sym in cautious:
        if sym.name == "sign" and len(sym.arguments) == 2:
            v = int(sym.arguments[0].number)
            s = sym.arguments[1].name
            out[nodes[v]] = {"p": "+", "m": "-", "z": "0"}[s]
    return out


def solve_signs_asp(
    pmap: PhysioMap, intervention: Intervention, asp_scc_min: int = ASP_SCC_MIN
) -> SolveResult:
    """Like :func:`physiomap_core.qualitative.solve_signs` but solving SCCs with ASP."""
    g = pmap.causal_subgraph()
    fixed = {t: s.value for t, s in intervention.targets.items()}

    gi = g.copy()
    for t in fixed:
        gi.remove_edges_from([(p, t) for p in list(gi.predecessors(t))])

    reach: set[str] = set(fixed)
    for t in fixed:
        reach |= nx.descendants(gi, t)

    sign: dict[str, str] = dict(fixed)
    ambig: list[str] = []
    cond = nx.condensation(gi)
    for comp in nx.topological_sort(cond):
        members: set[str] = set(cond.nodes[comp]["members"])
        if members.isdisjoint(reach):
            continue
        if len(members) == 1:
            (node,) = tuple(members)
            if node in fixed:
                continue
            _solve_singleton(node, gi, sign, ambig)
        elif len(members) >= asp_scc_min:
            det = asp_scc_signs(members, gi, sign, fixed)
            for n in members:
                if n in fixed:
                    sign[n] = fixed[n]
                else:
                    sign[n] = det.get(n, "?")
                    if sign[n] == "?":
                        ambig.append(f"{n}: ASP sign-consistency undetermined (loop conflict)")

    predicted: dict[str, Sign] = {}
    for node in reach:
        s = sign.get(node, "0")
        if s in ("+", "-"):
            predicted[node] = Sign(s)
        elif s == "?":
            predicted[node] = Sign.UNKNOWN
    return SolveResult(predicted=predicted, ambiguities=ambig)


def main() -> int:  # pragma: no cover - manual CLI
    import sys

    from physiomap_core.hpo import build_map

    node, direction = sys.argv[1], sys.argv[2]
    pmap = build_map()
    res = solve_signs_asp(
        pmap, Intervention(targets={node: Sign(direction)}, label=f"do({node}{direction})")
    )
    for n in sorted(res.predicted):
        print(f"  {n:34s} {res.predicted[n].value}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
