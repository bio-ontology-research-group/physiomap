"""Tests for the PhysioMap data model (physiomap_core.model)."""

from __future__ import annotations

import networkx as nx
import pytest

from physiomap_core.model import (
    CausalEdge,
    ConstitutiveEdge,
    ContextKind,
    InfluenceContext,
    ModulationEdge,
    Node,
    PhysioMap,
    Scale,
    Sign,
    combine_parallel,
)


def _small_map() -> PhysioMap:
    """A tiny cyclic map: a -> b -> c -> a (a 3-cycle) plus a constitutive edge."""
    nodes = [
        Node(id="a", label="A", scale=Scale.ORGAN_SYSTEM),
        Node(id="b", label="B", scale=Scale.ORGAN_SYSTEM),
        Node(id="c", label="C", scale=Scale.ORGAN_SYSTEM),
        Node(id="m", label="micro", scale=Scale.CELLULAR),
    ]
    causal = [
        CausalEdge(source="a", target="b", sign=Sign.PLUS),
        CausalEdge(source="b", target="c", sign=Sign.MINUS),
        CausalEdge(source="c", target="a", sign=Sign.PLUS),
    ]
    const = [ConstitutiveEdge(micro="m", macro="a")]
    return PhysioMap(name="t", nodes=nodes, causal_edges=causal, constitutive_edges=const)


# --- Sign algebra -------------------------------------------------------------


def test_sign_multiplication():
    assert Sign.PLUS * Sign.PLUS is Sign.PLUS
    assert Sign.PLUS * Sign.MINUS is Sign.MINUS
    assert Sign.MINUS * Sign.MINUS is Sign.PLUS
    assert Sign.MINUS * Sign.UNKNOWN is Sign.UNKNOWN
    assert Sign.UNKNOWN * Sign.PLUS is Sign.UNKNOWN


def test_combine_parallel():
    assert combine_parallel([Sign.PLUS, Sign.PLUS]) is Sign.PLUS
    assert combine_parallel([Sign.PLUS, Sign.MINUS]) is Sign.UNKNOWN
    assert combine_parallel([Sign.PLUS, Sign.UNKNOWN]) is Sign.UNKNOWN
    assert combine_parallel([]) is Sign.UNKNOWN


# --- Node / edge validation ---------------------------------------------------


def test_node_requires_non_empty_id_label():
    with pytest.raises(ValueError):
        Node(id="", label="x", scale=Scale.ORGAN)
    with pytest.raises(ValueError):
        Node(id="x", label="  ", scale=Scale.ORGAN)


def test_node_optional_iris():
    n = Node(
        id="map",
        label="mean arterial pressure",
        scale=Scale.ORGAN_SYSTEM,
        entity_iri="UBERON:0001009",
        quality_iri="PATO:0001595",
    )
    assert n.entity_iri == "UBERON:0001009"
    assert n.quality_iri == "PATO:0001595"


def test_unknown_node_reference_rejected():
    with pytest.raises(ValueError):
        PhysioMap(
            nodes=[Node(id="a", label="A", scale=Scale.ORGAN)],
            causal_edges=[CausalEdge(source="a", target="ghost", sign=Sign.PLUS)],
        )


def test_duplicate_node_ids_rejected():
    with pytest.raises(ValueError):
        PhysioMap(
            nodes=[
                Node(id="a", label="A", scale=Scale.ORGAN),
                Node(id="a", label="A2", scale=Scale.ORGAN),
            ]
        )


def test_extra_fields_forbidden():
    with pytest.raises(ValueError):
        Node(id="a", label="A", scale=Scale.ORGAN, bogus=1)  # type: ignore[call-arg]


def _contextual_parallel_map() -> PhysioMap:
    nodes = [
        Node(id="x", label="X", scale=Scale.ORGAN),
        Node(id="y", label="Y", scale=Scale.ORGAN),
        Node(id="m", label="M", scale=Scale.ORGAN),
    ]
    positive = CausalEdge(
        source="x",
        target="y",
        sign=Sign.PLUS,
        context=InfluenceContext(id="fed", label="fed state"),
    )
    negative = CausalEdge(
        source="x",
        target="y",
        sign=Sign.MINUS,
        context=InfluenceContext(id="fasted", label="fasted state"),
    )
    return PhysioMap(
        nodes=nodes,
        causal_edges=[positive, negative],
        modulation_edges=[
            ModulationEdge(modulator="m", influence_id=positive.id, sign=Sign.PLUS)
        ],
    )


def test_parallel_contextual_influences_never_overwrite_each_other():
    pmap = _contextual_parallel_map()
    unsliced = pmap.causal_subgraph().edges["x", "y"]
    assert unsliced["sign"] == "?"
    assert len(unsliced["parallel_influences"]) == 2
    assert set(unsliced["influence_ids"]) == {edge.id for edge in pmap.causal_edges}
    assert pmap.causal_subgraph(["fed"]).edges["x", "y"]["sign"] == "+"
    assert pmap.causal_subgraph(["fasted"]).edges["x", "y"]["sign"] == "-"


def test_single_context_only_influence_abstains_until_context_is_selected():
    pmap = PhysioMap(
        nodes=[
            Node(id="x", label="X", scale=Scale.ORGAN),
            Node(id="y", label="Y", scale=Scale.ORGAN),
        ],
        causal_edges=[
            CausalEdge(
                source="x",
                target="y",
                sign=Sign.PLUS,
                context=InfluenceContext(id="fed", label="fed state"),
            )
        ],
    )

    unsliced = pmap.causal_subgraph().edges["x", "y"]
    assert unsliced["sign"] == "?"
    assert unsliced["context_ambiguous"] is True
    assert pmap.causal_subgraph(["fed"]).edges["x", "y"]["sign"] == "+"
    assert not pmap.causal_subgraph([]).has_edge("x", "y")
    fixed = pmap.context_slice(["fed"])
    assert fixed.contexts == []
    assert fixed.causal_edges[0].id == pmap.causal_edges[0].id
    assert fixed.causal_subgraph().edges["x", "y"]["sign"] == "+"


def test_context_slice_is_available_to_the_solver():
    from physiomap_core.qualitative import Intervention, solve_signs

    pmap = _contextual_parallel_map()
    intervention = Intervention(targets={"x": Sign.PLUS})
    assert solve_signs(pmap, intervention).predicted["y"] is Sign.UNKNOWN
    assert solve_signs(pmap, intervention, contexts=["fed"]).predicted["y"] is Sign.PLUS
    assert solve_signs(pmap, intervention, contexts=["fasted"]).predicted["y"] is Sign.MINUS


def test_modulation_must_name_exact_parallel_influence():
    pmap = _contextual_parallel_map()
    assert pmap.modulation_edges[0].influence_id == pmap.causal_edges[0].id
    assert pmap.modulation_edges[0].edge_source == "x"
    assert pmap.modulation_edges[0].edge_target == "y"
    with pytest.raises(ValueError, match="ambiguous; supply influence_id"):
        PhysioMap(
            nodes=pmap.nodes,
            causal_edges=pmap.causal_edges,
            modulation_edges=[
                ModulationEdge(modulator="m", edge_source="x", edge_target="y", sign=Sign.PLUS)
            ],
        )


def test_dynamic_context_cannot_claim_a_fixed_steady_state_sign():
    with pytest.raises(ValueError, match=r"must use sign '\?'"):
        CausalEdge(
            source="x",
            target="y",
            sign=Sign.PLUS,
            context=InfluenceContext(
                id="pulse-phase", label="pulse phase", kind=ContextKind.DYNAMIC
            ),
        )


# --- Graph views --------------------------------------------------------------


def test_causal_subgraph_excludes_constitutive_edges():
    g = _small_map().causal_subgraph()
    assert isinstance(g, nx.DiGraph)
    assert g.number_of_nodes() == 4  # all nodes present (incl. micro)
    assert g.number_of_edges() == 3  # only the 3 causal edges
    assert g.edges["b", "c"]["sign"] == "-"
    # the constitutive (micro -> macro) edge must NOT appear as a causal edge
    assert not g.has_edge("m", "a")
    assert not g.has_edge("a", "m")


def test_sccs_finds_the_cycle():
    sccs = _small_map().sccs()
    big = max(sccs, key=len)
    assert big == {"a", "b", "c"}
    assert {"m"} in sccs


def test_condensation_is_a_dag():
    cond = _small_map().condensation()
    assert nx.is_directed_acyclic_graph(cond)
    # the 3-cycle collapses to a single condensation node
    members = [frozenset(cond.nodes[n]["members"]) for n in cond.nodes]
    assert frozenset({"a", "b", "c"}) in members


# --- YAML round-trip ----------------------------------------------------------


def test_yaml_round_trip(tmp_path):
    pm = _small_map()
    path = tmp_path / "m.yaml"
    pm.to_yaml(path)
    loaded = PhysioMap.from_yaml(path)
    assert loaded.node_ids == pm.node_ids
    assert {(e.source, e.target, e.sign) for e in loaded.causal_edges} == {
        (e.source, e.target, e.sign) for e in pm.causal_edges
    }
    assert loaded.constitutive_edges == pm.constitutive_edges


def test_node_accessor():
    pm = _small_map()
    assert pm.node("b").label == "B"
    with pytest.raises(KeyError):
        pm.node("nope")
