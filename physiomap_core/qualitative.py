"""Qualitative comparative-statics sign solver (feedback-loop aware).

Predicts ``sign(d x*/d theta)`` — the sign of each variable's change at the **stable
steady state** of the cyclic SCM implied by a PhysioMap, under a do-intervention that
fixes the sign of one or more nodes. This is NOT naive forward sign propagation: through a
feedback loop the net sign generally differs from the open-loop product.

Method (design decisions **D2/D3**; see ``README.md`` and
``resources/qualitative-reasoning/NOTES.md`` / ``resources/ode-causality/NOTES.md``):

1. Apply the intervention by **do-surgery**: remove every in-edge of an intervened node
   and fix its sign. (This is what breaks cycles passing through the intervened node.)
2. Condense the surgered causal graph into its DAG of SCCs; walk it in topological order.
3. A singleton component (no feedback) gets ordinary QPN **sign propagation**:
   ``sign(i) = ⊕_p ( sign(p) ⊗ sign(p->i) )`` with ``+ ⊕ - = ?`` (Wellman 1990;
   Druzdzel & Henrion 1993); ``?`` is absorbing.
4. A non-trivial SCC is solved by **comparative statics via sign-solvability**
   (Quirk–Maybee / Lancaster): at a stable equilibrium ``F(x*,theta)=0`` the implicit
   function theorem gives ``J dx = -b`` with ``J = ∂F/∂x`` (sign pattern: edge sign for a
   within-SCC parent, a **negative diagonal** from the assumed dissipation/stability, D3)
   and ``b`` the forcing from already-solved nodes outside the SCC. By Cramer,
   ``dx_i = det(J_i)/det(J)`` where ``J_i`` is ``J`` with column ``i`` replaced by ``-b``.
   Stability (Hurwitz) fixes ``sign(det J) = (-1)^{|SCC|}`` for free. ``sign(det J_i)`` is
   computed by a **sign-only** Laplace expansion: it is determined iff its signed
   expansion has no term-cancellation, otherwise the result is ``?`` (logged) — never
   guessed.
"""

from __future__ import annotations

import functools
from collections.abc import Iterable, Mapping

import networkx as nx
from pydantic import BaseModel, Field

from physiomap_core.model import PhysioMap, Sign

__all__ = ["Intervention", "SolveResult", "solve_signs", "SCC_EXACT_MAX"]

#: SCCs up to this size are solved exactly (signed-determinant / sign-solvability);
#: larger SCCs fall back to the polynomial loop-aware fixpoint engine. Sign-nonsingularity
#: is NP-hard, and the exact engine is O(2^|SCC|) (cheap for the sparse, modest SCCs that
#: survive do-surgery), so we cap it and stay scalable + sound on whole-body maps.
SCC_EXACT_MAX = 16

# Internal sign domain includes "0" (no change); '?' is qualitative ambiguity.
_PLUS, _MINUS, _ZERO, _Q = "+", "-", "0", "?"


def _times(a: str, b: str) -> str:
    """Sign composition along a chain (⊗)."""
    if a == _ZERO or b == _ZERO:
        return _ZERO
    if a == _Q or b == _Q:
        return _Q
    return _PLUS if a == b else _MINUS


def _plus(a: str, b: str) -> str:
    """Sign combination across parallel contributions (⊕); ``+ ⊕ - = ?``."""
    if a == _ZERO:
        return b
    if b == _ZERO:
        return a
    if a == _Q or b == _Q:
        return _Q
    return a if a == b else _Q


def _neg(a: str) -> str:
    if a == _PLUS:
        return _MINUS
    if a == _MINUS:
        return _PLUS
    return a  # 0 / ?


def _signed_det(matrix: tuple[tuple[str, ...], ...]) -> str:
    """Sign of the determinant of a sign matrix (entries in {+,-,0,?}).

    Returns ``+``/``-``/``0``/``?``; ``?`` means the sign is not determined by the sign
    pattern alone (term cancellation, or a ``?`` entry in a non-zero term). Laplace
    expansion with memoisation over the set of remaining columns; ``?`` is absorbing.
    """
    n = len(matrix)
    full_cols = tuple(range(n))

    @functools.lru_cache(maxsize=None)
    def det(cols: tuple[int, ...]) -> str:
        if not cols:
            return _PLUS  # determinant of the empty matrix is 1
        row = n - len(cols)
        acc = _ZERO
        for idx, c in enumerate(cols):
            entry = matrix[row][c]
            if entry == _ZERO:
                continue
            sub = det(cols[:idx] + cols[idx + 1 :])
            if sub == _ZERO:
                continue
            perm = _PLUS if idx % 2 == 0 else _MINUS
            acc = _plus(acc, _times(_times(entry, sub), perm))
            if acc == _Q:
                break  # absorbing
        return acc

    result = det(full_cols)
    det.cache_clear()
    return result


class Intervention(BaseModel):
    """A do()-intervention: fix the sign (direction of change) of one or more nodes."""

    targets: dict[str, Sign] = Field(
        ..., description="Map of node id -> imposed sign of change."
    )
    label: str | None = None


class SolveResult(BaseModel):
    """Result of a qualitative solve."""

    predicted: dict[str, Sign] = Field(
        default_factory=dict, description="Predicted sign per reachable node (no '0's)."
    )
    ambiguities: list[str] = Field(
        default_factory=list,
        description="Nodes whose sign was undetermined ('?'), with a logged reason.",
    )


def solve_signs(
    pmap: PhysioMap,
    intervention: Intervention,
    scc_exact_max: int = SCC_EXACT_MAX,
    contexts: Iterable[str] | None = None,
) -> SolveResult:
    """Predict ``sign(d x*/d theta)`` for every node reachable from the intervention.

    ``scc_exact_max`` is the largest SCC solved by exact sign-solvability; larger SCCs use
    the polynomial loop-aware fixpoint engine (more conservative — '?' on loop conflict).
    ``contexts`` selects a fixed steady-state regime. If it is omitted, context-only influences
    and conflicting parallel alternatives force an honest ``?`` rather than assuming a regime or
    accepting an arbitrary insertion-order choice.
    """
    g = pmap.causal_subgraph(contexts)
    fixed: dict[str, str] = {t: s.value for t, s in intervention.targets.items()}

    # 1. do-surgery: cut in-edges of intervened nodes
    gi = g.copy()
    for t in fixed:
        gi.remove_edges_from([(p, t) for p in list(gi.predecessors(t))])

    # reachable set from the intervened nodes (where a prediction is meaningful)
    reach: set[str] = set(fixed)
    for t in fixed:
        reach |= nx.descendants(gi, t)

    sign: dict[str, str] = dict(fixed)
    ambig: list[str] = []

    cond = nx.condensation(gi)  # DAG of SCCs; node attr 'members'
    for comp in nx.topological_sort(cond):
        members: set[str] = set(cond.nodes[comp]["members"])
        if members.isdisjoint(reach):
            continue
        if len(members) == 1:
            (node,) = tuple(members)
            if node in fixed:
                continue
            _solve_singleton(node, gi, sign, ambig)
        elif len(members) <= scc_exact_max:
            _solve_scc_exact(members, gi, sign, fixed, ambig)
        else:
            _solve_scc_loop(members, gi, sign, fixed, ambig)

    predicted: dict[str, Sign] = {}
    for node in reach:
        s = sign.get(node, _ZERO)
        if s in (_PLUS, _MINUS):
            predicted[node] = Sign(s)
        elif s == _Q:
            predicted[node] = Sign.UNKNOWN
        # s == '0' -> no change predicted; omit
    return SolveResult(predicted=predicted, ambiguities=ambig)


def _solve_singleton(
    node: str,
    g: nx.DiGraph,
    sign: dict[str, str],
    ambig: list[str],
    extra: Mapping[str, str] | None = None,
) -> None:
    """QPN sign propagation into a feedback-free node.

    ``extra`` supplies optional additional forcing (e.g. cross-scale determination),
    combined (``⊕``) with signed contributions from the operational graph.
    """
    acc = (extra or {}).get(node, _ZERO)
    for p in g.predecessors(node):
        if p == node:
            continue  # self-loop: pure dissipation, no comparative-static effect
        acc = _plus(acc, _times(sign.get(p, _ZERO), g.edges[p, node]["sign"]))
    sign[node] = acc
    if acc == _Q:
        ambig.append(f"{node}: ambiguous net sign (opposing parallel paths)")


def _scc_jacobian_and_forcing(
    members: set[str],
    g: nx.DiGraph,
    sign: dict[str, str],
    extra: Mapping[str, str] | None = None,
) -> tuple[list[str], dict[str, int], list[list[str]], list[str]]:
    """Shared setup: ordered nodes, index, signed Jacobian (negative diagonal), forcing.

    ``extra`` adds cross-scale determination forcing into ``b`` (``⊕``).
    """
    extra = extra or {}
    nodes = sorted(members)
    idx = {n: k for k, n in enumerate(nodes)}
    m = len(nodes)
    jac = [[_ZERO] * m for _ in range(m)]
    b = [_ZERO] * m
    for n in nodes:
        i = idx[n]
        jac[i][i] = _MINUS  # implicit dissipation / stability (D3)
        acc = extra.get(n, _ZERO)
        for p in g.predecessors(n):
            es = g.edges[p, n]["sign"]
            if p in members and p != n:
                jac[i][idx[p]] = es
            elif p not in members:
                acc = _plus(acc, _times(sign.get(p, _ZERO), es))
        b[i] = acc
    return nodes, idx, jac, b


def _solve_scc_exact(
    members: set[str],
    g: nx.DiGraph,
    sign: dict[str, str],
    fixed: Mapping[str, str],
    ambig: list[str],
    extra: Mapping[str, str] | None = None,
) -> None:
    """Exact comparative-statics sign-solve (Cramer + sign-only determinant) for an SCC."""
    nodes, idx, jac, b = _scc_jacobian_and_forcing(members, g, sign, extra)
    m = len(nodes)
    sign_det_j = _PLUS if m % 2 == 0 else _MINUS  # Hurwitz: sign(det J) = (-1)^m
    neg_b = [_neg(x) for x in b]
    for n in nodes:
        i = idx[n]
        if n in fixed:
            sign[n] = fixed[n]
            continue
        ji = tuple(
            tuple(neg_b[r] if c == i else jac[r][c] for c in range(m)) for r in range(m)
        )
        num = _signed_det(ji)
        if num == _ZERO:
            sign[n] = _ZERO
        elif num == _Q:
            sign[n] = _Q
            ambig.append(
                f"{n}: SCC comparative static not sign-determined (loop magnitudes matter)"
            )
        else:
            sign[n] = _times(num, sign_det_j)


def _solve_scc_loop(
    members: set[str],
    g: nx.DiGraph,
    sign: dict[str, str],
    fixed: Mapping[str, str],
    ambig: list[str],
    extra: Mapping[str, str] | None = None,
) -> None:
    """Scalable loop-aware sign-solve for a large SCC.

    Computes the sign of the Neumann series ``dx = b ⊕ A⊗dx`` (= ``(I-A)^{-1}b`` with the
    negative diagonal normalised out), iterated to a fixpoint. ``?`` is absorbing, so this
    converges in ``≤ 2|SCC|`` sweeps. Polynomial and sound, but more conservative than the
    exact engine — a negative-feedback loop yields alternating-sign path contributions and
    therefore ``?`` (where the exact determinant, using ``sign(det J)=(-1)^m``, may resolve).
    """
    extra = extra or {}
    nodes = sorted(members)
    forcing: dict[str, str] = {}
    incoming: dict[str, list[tuple[str, str]]] = {n: [] for n in nodes}
    for n in nodes:
        acc = extra.get(n, _ZERO)
        for p in g.predecessors(n):
            es = g.edges[p, n]["sign"]
            if p in members and p != n:
                incoming[n].append((p, es))
            elif p not in members:
                acc = _plus(acc, _times(sign.get(p, _ZERO), es))
        forcing[n] = acc

    dx = {n: _ZERO for n in nodes}
    for _ in range(2 * len(nodes) + 2):
        changed = False
        for n in nodes:
            val = forcing[n]
            for p, es in incoming[n]:
                val = _plus(val, _times(dx[p], es))
            if val != dx[n]:
                dx[n] = val
                changed = True
        if not changed:
            break

    for n in nodes:
        if n in fixed:
            sign[n] = fixed[n]
            continue
        sign[n] = dx[n]
        if dx[n] == _Q:
            ambig.append(
                f"{n}: large-SCC loop-aware sign undetermined "
                f"(|SCC|={len(nodes)} > exact cap; loop conflict)"
            )
