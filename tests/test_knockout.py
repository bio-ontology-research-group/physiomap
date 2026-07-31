"""Dynamic synthetic knockout: clamp any node, derive phenotypes via comparative statics."""

from __future__ import annotations

from physiomap_core.hpo import build_map
from physiomap_core.knockout import (
    abnormality_index,
    knockout,
    knockout_multi,
    phenotype_index,
    trace_many,
    trace_many_multi,
)
from physiomap_core.model import CausalEdge, InfluenceContext, Node, PhysioMap, Scale, Sign

PM = build_map()


def test_phenotype_index_inverts_term_map():
    idx = phenotype_index()
    assert idx["mean_arterial_pressure"]["+"]["label"].lower().startswith("hypertension")
    assert idx["mean_arterial_pressure"]["-"]["label"].lower().startswith("hypotension")


def test_knockout_unknown_node_errors_soundly():
    r = knockout(PM, "definitely_not_a_node", "+")
    assert r.error and "unknown node" in r.error
    assert r.phenotypes == [] and r.predicted == {}


def test_hepcidin_overexpression_derives_iron_phenotypes():
    """do(hepcidin ↑) → ↓ plasma iron, ↓ transferrin saturation, ↑ TIBC (determinate, sound)."""
    r = knockout(PM, "hepcidin", "+")
    assert r.error is None
    hits = {h.node: h.sign for h in r.phenotypes}
    assert hits.get("transferrin_saturation") == "-"
    assert hits.get("plasma_iron") == "-"
    assert hits.get("total_iron_binding_capacity") == "+"


def test_every_phenotype_hit_matches_the_solver_sign():
    """Soundness: a reported phenotype's direction is exactly the comparative-statics sign."""
    r = knockout(PM, "cortisol", "-")
    for h in r.phenotypes:
        assert r.predicted[h.node] == h.sign      # never report a sign the solver did not give
        assert h.sign in ("+", "-")               # only determinate predictions surface


def test_knockout_sign_accepts_enum_and_str():
    a = knockout(PM, "hepcidin", "+")
    b = knockout(PM, "hepcidin", Sign.PLUS)
    assert {h.node: h.sign for h in a.phenotypes} == {h.node: h.sign for h in b.phenotypes}


def test_trace_many_returns_signed_path_to_phenotype():
    paths = trace_many(PM, "hepcidin", "-", ["transferrin_saturation"])
    steps = paths["transferrin_saturation"]
    assert [s["dst"] for s in steps] == ["ferroportin_activity", "plasma_iron", "transferrin_saturation"]
    assert steps[-1]["running"] == "+"            # hepcidin↓ ⇒ tsat↑


def test_single_node_knockout_equals_knockout_multi():
    """The one-node convenience wrapper agrees with the multi-node entry point."""
    a = knockout(PM, "hepcidin", "-")
    b = knockout_multi(PM, {"hepcidin": Sign.MINUS})
    assert a.do == b.do == {"hepcidin": "-"}
    assert {h.node: h.sign for h in a.phenotypes} == {h.node: h.sign for h in b.phenotypes}


def test_multi_node_knockout_clamps_all_targets():
    """A joint do() clamps every target and reports the full clamp set in `do`/`do_labels`."""
    r = knockout_multi(PM, {"hepcidin": "-", "water_intake": "+"})
    assert r.error is None
    assert r.do == {"hepcidin": "-", "water_intake": "+"}
    assert set(r.do_labels) == {"hepcidin", "water_intake"}
    # clamped nodes are not themselves reported as derived phenotypes
    assert all(h.node not in r.do for h in r.phenotypes)
    # the iron arm still fires under the joint clamp
    assert {h.node: h.sign for h in r.phenotypes}.get("transferrin_saturation") == "+"


def test_multi_node_knockout_unknown_node_errors_soundly():
    r = knockout_multi(PM, {"hepcidin": "-", "definitely_not_a_node": "+"})
    assert r.error and "unknown node" in r.error
    assert r.phenotypes == []


def test_knockout_accepts_an_explicit_context_slice():
    nodes = [
        Node(id="x", label="X", scale=Scale.ORGAN),
        Node(id="y", label="Y", scale=Scale.ORGAN),
    ]
    pmap = PhysioMap(nodes=nodes, causal_edges=[
        CausalEdge(source="x", target="y", sign=Sign.PLUS,
                   context=InfluenceContext(id="fed", label="fed")),
        CausalEdge(source="x", target="y", sign=Sign.MINUS,
                   context=InfluenceContext(id="fasted", label="fasted")),
    ])
    assert knockout(pmap, "x", "+").predicted["y"] == "?"
    fed = knockout(pmap, "x", "+", contexts=["fed"])
    fasted = knockout(pmap, "x", "+", contexts=["fasted"])
    assert fed.predicted["y"] == "+" and fed.contexts == ["fed"]
    assert fasted.predicted["y"] == "-" and fasted.contexts == ["fasted"]


def test_trace_many_multi_paths_from_nearest_clamp():
    paths = trace_many_multi(PM, {"hepcidin": "-", "water_intake": "+"}, ["transferrin_saturation"])
    steps = paths["transferrin_saturation"]
    assert steps[0]["src"] == "hepcidin"          # nearest clamped source on this path
    assert steps[-1]["running"] == "+"


# ---- "X affected": reachable HPO traits whose net direction is undetermined ----

def test_abnormality_index_links_neutral_hpo_terms():
    abn = abnormality_index()
    assert abn["mean_arterial_pressure"]["hpo"] == "HP:0030972"  # Abnormal systemic blood pressure
    assert abn["plasma_potassium"]["hpo"] == "HP:0011042"        # Abnormal circulating potassium conc.


def test_affected_are_reachable_ambiguous_traits_disjoint_from_directional():
    """An 'affected' trait is reachable (in predicted), has net sign '?', and is HPO-mapped;
    the affected and directional lists never overlap."""
    r = knockout_multi(PM, {"water_intake": "+"})
    assert r.affected, "water-intake forcing should affect many feedback-core traits"
    det_nodes = {h.node for h in r.phenotypes}
    for h in r.affected:
        assert h.effect == "affected" and h.sign == "?"
        assert r.predicted.get(h.node) == "?"      # reachable but direction undetermined
        assert h.node in phenotype_index()         # an HPO-recognized trait
        assert h.node not in det_nodes             # never both directional and affected


def test_affected_only_reachable_nodes_never_unreached():
    """Every affected trait is reachable (present in `predicted` with sign '?'); a trait absent from
    `predicted` (not reached) is never reported affected — soundness of the 'affected' claim."""
    r = knockout(PM, "hepcidin", "-")
    for h in r.affected:
        assert r.predicted.get(h.node) == "?"   # reachable & ambiguous, never a no-change/unreached
    # the iron arm itself resolves with a determinate direction, so it is NOT in 'affected'
    assert "transferrin_saturation" not in {h.node for h in r.affected}
