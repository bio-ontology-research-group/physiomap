"""Tests for the qualitative comparative-statics sign solver (physiomap_core.qualitative)."""

from __future__ import annotations

from physiomap_core.model import CausalEdge, Node, PhysioMap, Scale, Sign
from physiomap_core.qualitative import (
    Intervention,
    _signed_det,
    solve_signs,
)


def _chain(n):
    nodes = [f"n{i}" for i in range(n)]
    edges = [(f"n{i}", f"n{i+1}", "+") for i in range(n - 1)]
    return _mk(nodes, edges)


def _mk(nodes, edges):
    ns = [Node(id=n, label=n, scale=Scale.ORGAN_SYSTEM) for n in nodes]
    es = [CausalEdge(source=s, target=t, sign=Sign(sg)) for s, t, sg in edges]
    return PhysioMap(nodes=ns, causal_edges=es)


# --- signed determinant -------------------------------------------------------


def test_signed_det_basic():
    assert _signed_det((("+",),)) == "+"
    assert _signed_det((("-", "0"), ("0", "-"))) == "+"  # (-)(-) = +
    assert _signed_det((("+", "+"), ("+", "+"))) == "?"  # +*+ - +*+ : cancellation
    assert _signed_det((("-", "-"), ("+", "-"))) == "+"  # (-)(-) - (-)(+) = + ⊕ + = +


# --- acyclic propagation ------------------------------------------------------


def test_acyclic_chain_propagation():
    pm = _mk(["a", "b", "c"], [("a", "b", "+"), ("b", "c", "-")])
    r = solve_signs(pm, Intervention(targets={"a": Sign.PLUS}))
    assert r.predicted["b"] is Sign.PLUS
    assert r.predicted["c"] is Sign.MINUS
    assert r.ambiguities == []


def test_parallel_paths_cancel_to_unknown():
    # a -> b (+), a -> c (-), b -> d (+), c -> d (+): d gets + and - -> '?'
    pm = _mk(
        ["a", "b", "c", "d"],
        [("a", "b", "+"), ("a", "c", "-"), ("b", "d", "+"), ("c", "d", "+")],
    )
    r = solve_signs(pm, Intervention(targets={"a": Sign.PLUS}))
    assert r.predicted["d"] is Sign.UNKNOWN
    assert any("d" in msg for msg in r.ambiguities)


# --- comparative statics through feedback (not forward propagation) -----------


def test_negative_feedback_buffers_but_keeps_sign():
    # External theta -> X (+); X -> Y (+), Y -> X (-) is a negative feedback loop.
    # do(theta=+) leaves {X,Y} an intact SCC. Comparative statics: both X and Y rise
    # (the loop attenuates but does not flip the sign). Naive propagation would loop.
    pm = _mk(
        ["theta", "X", "Y"],
        [("theta", "X", "+"), ("X", "Y", "+"), ("Y", "X", "-")],
    )
    r = solve_signs(pm, Intervention(targets={"theta": Sign.PLUS}))
    assert r.predicted["X"] is Sign.PLUS
    assert r.predicted["Y"] is Sign.PLUS


def test_intervention_breaks_cycle_via_surgery():
    # do(X=+) inside the X<->Y loop cuts Y->X; Y is then a clean descendant of X.
    pm = _mk(["X", "Y"], [("X", "Y", "+"), ("Y", "X", "-")])
    r = solve_signs(pm, Intervention(targets={"X": Sign.PLUS}))
    assert r.predicted["X"] is Sign.PLUS
    assert r.predicted["Y"] is Sign.PLUS


def test_hybrid_forces_loop_engine_on_large_scc():
    # A big bidirectional ring forms one large SCC; with a low exact cap the loop-aware
    # engine handles it (scalably) and a single forcing arm stays determinate.
    n = 30
    nodes = [f"r{i}" for i in range(n)] + ["theta"]
    edges = [(f"r{i}", f"r{(i + 1) % n}", "+") for i in range(n)]  # directed ring (one SCC)
    edges += [("theta", "r0", "+")]
    pm = _mk(nodes, edges)
    # do(theta=+) cuts nothing into theta; ring r0..r29 stays a 30-node SCC (> cap 16)
    r = solve_signs(pm, Intervention(targets={"theta": Sign.PLUS}), scc_exact_max=16)
    # forcing enters at r0 (+); around an all-'+' ring every node rises (no sign conflict)
    assert r.predicted["r0"] is Sign.PLUS
    assert r.predicted["r15"] is Sign.PLUS


def test_exact_and_loop_agree_on_acyclic_when_no_conflict():
    pm = _chain(6)
    exact = solve_signs(pm, Intervention(targets={"n0": Sign.PLUS}), scc_exact_max=99)
    loopy = solve_signs(pm, Intervention(targets={"n0": Sign.PLUS}), scc_exact_max=0)
    assert exact.predicted == loopy.predicted  # no SCCs here; both use singleton path


def test_positive_then_negative_loop_sign():
    # theta -> X (+); X -> Y (-), Y -> X (-): loop is positive feedback (-,- => +).
    # Forcing X up: Y = sign of X-effect = -, and X stays + (stable assumption).
    pm = _mk(
        ["theta", "X", "Y"],
        [("theta", "X", "+"), ("X", "Y", "-"), ("Y", "X", "-")],
    )
    r = solve_signs(pm, Intervention(targets={"theta": Sign.PLUS}))
    assert r.predicted["X"] is Sign.PLUS
    assert r.predicted["Y"] is Sign.MINUS
