"""Tests for sigma-separation (physiomap_core.sigma).

Correctness anchors (design decision D1):
  1. On any ACYCLIC input, sigma-separation agrees with networkx d-separation.
  2. The acyclify-based and direct sigma-walk implementations agree (differential test
     over random graphs, cyclic and acyclic).
  3. Known small CYCLIC examples with hand-derived expected (in)dependence.
"""

from __future__ import annotations

import itertools
import random

import networkx as nx
import pytest

from physiomap_core.sigma import (
    acyclify,
    sigma_separated_acyclify,
    sigma_separated_oracle,
)


def _nx_dsep(g, x, y, z):
    if hasattr(nx, "is_d_separator"):
        return nx.is_d_separator(g, set(x), set(y), set(z))
    return nx.d_separated(g, set(x), set(y), set(z))


def _random_dag(n, p, seed):
    rng = random.Random(seed)
    g = nx.DiGraph()
    g.add_nodes_from(range(n))
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < p:
                g.add_edge(i, j)  # i<j keeps it acyclic
    return g


def _random_digraph(n, p, seed):
    rng = random.Random(seed)
    g = nx.DiGraph()
    g.add_nodes_from(range(n))
    for i in range(n):
        for j in range(n):
            if i != j and rng.random() < p:
                g.add_edge(i, j)
    return g


def _all_triples(nodes):
    """Yield disjoint (X, Y, Z) with X, Y singletons and Z a small subset."""
    for a, b in itertools.combinations(nodes, 2):
        rest = [n for n in nodes if n not in (a, b)]
        for r in range(0, min(2, len(rest)) + 1):
            for z in itertools.combinations(rest, r):
                yield {a}, {b}, set(z)


# --- Anchor 1: acyclic input matches networkx d-separation --------------------


@pytest.mark.parametrize("seed", range(12))
def test_agrees_with_d_separation_on_dags(seed):
    g = _random_dag(6, 0.35, seed)
    for x, y, z in _all_triples(list(g.nodes)):
        assert sigma_separated_acyclify(g, x, y, z) == _nx_dsep(g, x, y, z)
        assert sigma_separated_oracle(g, x, y, z) == _nx_dsep(g, x, y, z)


def test_acyclification_is_identity_on_dag():
    g = _random_dag(5, 0.4, 0)
    dag, latents = acyclify(g)
    assert latents == set()
    assert set(dag.edges) == set(g.edges)


# --- Anchor 2: differential test of the two implementations -------------------


@pytest.mark.parametrize("seed", range(40))
def test_acyclify_and_walk_agree_random(seed):
    g = _random_digraph(5, 0.3, seed)
    for x, y, z in _all_triples(list(g.nodes)):
        a = sigma_separated_acyclify(g, x, y, z)
        w = sigma_separated_oracle(g, x, y, z)
        assert a == w, f"disagreement seed={seed} x={x} y={y} z={z}: acyclify={a} walk={w}"


# --- Anchor 3: hand-derived cyclic examples -----------------------------------


def test_two_cycle_members_not_separable():
    """A <-> B feedback loop: members of an SCC are never sigma-separated (no latents
    cut), unlike a plain DAG. Conditioning on the cycle does not separate them."""
    g = nx.DiGraph([("A", "B"), ("B", "A")])
    g.add_node("C")
    assert not sigma_separated_acyclify(g, {"A"}, {"B"}, set())
    assert not sigma_separated_oracle(g, {"A"}, {"B"}, set())


def test_collider_into_a_cycle():
    """X -> S1, Y -> S1, with S1<->S2 a 2-cycle (S1,S2 one SCC). X and Y are sigma-
    separated given {} (collider S1 closed) but NOT given S2 (a member of the collider's
    SCC), since conditioning on the SCC opens the collider."""
    g = nx.DiGraph([("X", "S1"), ("Y", "S1"), ("S1", "S2"), ("S2", "S1")])
    assert sigma_separated_acyclify(g, {"X"}, {"Y"}, set())
    assert sigma_separated_oracle(g, {"X"}, {"Y"}, set())
    assert not sigma_separated_acyclify(g, {"X"}, {"Y"}, {"S2"})
    assert not sigma_separated_oracle(g, {"X"}, {"Y"}, {"S2"})


def test_chain_blocked_by_conditioning():
    """Simple chain X -> M -> Y: conditioning on M separates X and Y (acyclic sanity)."""
    g = nx.DiGraph([("X", "M"), ("M", "Y")])
    assert not sigma_separated_acyclify(g, {"X"}, {"Y"}, set())
    assert sigma_separated_acyclify(g, {"X"}, {"Y"}, {"M"})
    assert sigma_separated_oracle(g, {"X"}, {"Y"}, {"M"})


# --------------------------------------------------------------------------- #
# Deterministic (definitional / algebraic-identity) nodes — Geiger-Verma-Pearl
# --------------------------------------------------------------------------- #

from physiomap_core.model import CausalEdge, Node, PhysioMap, Scale, Sign  # noqa: E402
from physiomap_core.sigma import deterministic_closure, sigma_separated  # noqa: E402


def _nodes(*ids):
    return [Node(id=i, label=i, scale=Scale.ORGAN_SYSTEM) for i in ids]


def _identity_map(extra_stochastic_parent: bool):
    """y = f(a, b) (definitional), y -> c, y -> d. Optionally add a stochastic k -> y."""
    ids = ["a", "b", "y", "c", "d"] + (["k"] if extra_stochastic_parent else [])
    edges = [
        CausalEdge(source="a", target="y", sign=Sign.PLUS, definitional=True),
        CausalEdge(source="b", target="y", sign=Sign.PLUS, definitional=True),
        CausalEdge(source="y", target="c", sign=Sign.PLUS),
        CausalEdge(source="y", target="d", sign=Sign.PLUS),
    ]
    if extra_stochastic_parent:
        edges.append(CausalEdge(source="k", target="y", sign=Sign.PLUS))  # NOT definitional
    return PhysioMap(name="t", nodes=_nodes(*ids), causal_edges=edges)


def test_deterministic_closure_adds_determined_node():
    pm = _identity_map(extra_stochastic_parent=False)
    assert deterministic_closure(pm, {"a", "b"}) == {"a", "b", "y"}  # y is fixed by {a,b}
    assert deterministic_closure(pm, {"a"}) == {"a"}  # one parent missing -> not determined


def test_conditioning_on_identity_parents_blocks_path_through_the_identity():
    pm = _identity_map(extra_stochastic_parent=False)
    g = pm.causal_subgraph()
    # common cause y makes c, d dependent unconditionally
    assert sigma_separated(pm, {"c"}, {"d"}, set()) is False
    # conditioning on y's parents fixes y -> c _||_ d | {a,b}  (determinism-aware)
    assert sigma_separated(pm, {"c"}, {"d"}, {"a", "b"}) is True
    # plain d-separation (no determinism) does NOT block it: y not in Z -> path open
    assert sigma_separated_acyclify(g, {"c"}, {"d"}, {"a", "b"}) is False


def test_node_with_a_stochastic_parent_is_not_treated_as_deterministic():
    pm = _identity_map(extra_stochastic_parent=True)  # y also has stochastic parent k
    assert deterministic_closure(pm, {"a", "b"}) == {"a", "b"}  # y NOT determined (k free)
    # so conditioning on {a,b} leaves the y-path open -> c, d still dependent
    assert sigma_separated(pm, {"c"}, {"d"}, {"a", "b"}) is False
