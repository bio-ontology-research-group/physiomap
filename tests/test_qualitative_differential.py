"""Randomized differential checks for the exact and large-SCC qualitative engines."""

from __future__ import annotations

import random

import networkx as nx

from physiomap_core.model import CausalEdge, Node, PhysioMap, Scale, Sign
from physiomap_core.qualitative import Intervention, SCC_EXACT_MAX, solve_signs


RANDOM_SEED = 20260721
RANDOM_SCCS = 400


def test_exact_and_fixpoint_engines_never_commit_to_opposite_signs():
    """Compare every query in 400 signed SCCs with the solver's negative diagonals."""
    rng = random.Random(RANDOM_SEED)
    queries = both_commit = contradictions = fixpoint_only = exact_only = 0

    for _ in range(RANDOM_SCCS):
        size = rng.randint(2, 8)
        node_ids = [f"n{i}" for i in range(size)]

        # A directed ring guarantees one SCC; random chords and signs diversify its loops.
        edge_pairs = {
            (node_ids[index], node_ids[(index + 1) % size]) for index in range(size)
        }
        edge_pairs.update(
            (source, target)
            for source in node_ids
            for target in node_ids
            if source != target and rng.random() < 0.28
        )
        internal_edges = [
            CausalEdge(source=source, target=target, sign=rng.choice((Sign.PLUS, Sign.MINUS)))
            for source, target in sorted(edge_pairs)
        ]

        forcing = [
            (target, rng.choice((Sign.PLUS, Sign.MINUS)))
            for target in node_ids
            if rng.random() < 0.35
        ]
        if not forcing:
            forcing = [(rng.choice(node_ids), rng.choice((Sign.PLUS, Sign.MINUS)))]

        nodes = [Node(id="theta", label="theta", scale=Scale.ORGAN_SYSTEM)] + [
            Node(id=node_id, label=node_id, scale=Scale.ORGAN_SYSTEM) for node_id in node_ids
        ]
        pmap = PhysioMap(
            nodes=nodes,
            causal_edges=internal_edges
            + [
                CausalEdge(source="theta", target=target, sign=sign)
                for target, sign in forcing
            ],
        )
        assert nx.is_strongly_connected(pmap.causal_subgraph().subgraph(node_ids))

        intervention = Intervention(targets={"theta": Sign.PLUS})
        exact = solve_signs(
            pmap, intervention, scc_exact_max=SCC_EXACT_MAX
        ).predicted
        fixpoint = solve_signs(pmap, intervention, scc_exact_max=0).predicted

        for node_id in node_ids:
            queries += 1
            exact_sign = exact.get(node_id)
            fixpoint_sign = fixpoint.get(node_id)
            exact_commits = exact_sign in (Sign.PLUS, Sign.MINUS)
            fixpoint_commits = fixpoint_sign in (Sign.PLUS, Sign.MINUS)
            if exact_commits and fixpoint_commits:
                both_commit += 1
                contradictions += exact_sign is not fixpoint_sign
            elif fixpoint_commits:
                fixpoint_only += 1
            elif exact_commits:
                exact_only += 1

    print(
        "solver differential: "
        f"sccs={RANDOM_SCCS}, queries={queries}, both_commit={both_commit}, "
        f"contradictions={contradictions}, fixpoint_only={fixpoint_only}, "
        f"exact_only={exact_only}"
    )
    assert contradictions == 0
    assert fixpoint_only > 0
