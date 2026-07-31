"""Curation gates: a proposed contribution is validated with the SAME checks we deploy on."""

from __future__ import annotations

import tempfile

from physiomap_core.curation import (
    Submission,
    SubmissionStore,
    compose_candidate,
    contribution_to_fragment,
    axiom_preview,
    make_submission_id,
    normalize_legacy_contribution,
    ontology_lookup,
    validate_contribution,
)
from physiomap_core.hpo import build_map

PM = build_map()


def _good_contribution() -> dict:
    """A downstream sink analyte off plasma_glucose — backward-safe, fully provenanced."""
    return {
        "nodes": [{
            "id": "plasma_curation_test_marker", "label": "plasma curation test marker",
            "scale": "organ_system", "entity_iri": "CHEBI:17234", "quality_iri": "PATO:0000033",
        }],
        "causal_edges": [{
            "source": "plasma_glucose", "target": "plasma_curation_test_marker", "sign": "+",
            "mechanism": "hyperglycaemia raises the marker (test fixture)",
            "evidence": "unit-test fixture", "causal_evidence": "pharmacological",
        }],
    }


def test_good_contribution_passes_all_live_gates():
    r = validate_contribution(PM, _good_contribution())
    assert r.ok, r.summary
    assert {g.gate for g in r.gates} >= {
        "schema", "provenance", "causal_evidence", "ontology", "constitution",
        "bearer_bfo", "acyclicity"}
    assert all(g.ok for g in r.gates)


def test_missing_evidence_is_rejected():
    c = _good_contribution()
    c["causal_edges"][0].pop("evidence")
    r = validate_contribution(PM, c)
    assert not r.ok
    assert any("MISSING evidence" in e for e in r.errors)


def test_associational_evidence_class_is_rejected():
    c = _good_contribution()
    c["causal_edges"][0]["causal_evidence"] = "coexpression"
    r = validate_contribution(PM, c)
    assert not r.ok
    assert any("ASSOCIATIONAL" in e for e in r.errors)


def test_missing_causal_evidence_class_is_rejected():
    c = _good_contribution()
    c["causal_edges"][0].pop("causal_evidence")
    r = validate_contribution(PM, c)
    assert not r.ok
    assert any("causal_evidence" in g.gate and not g.ok for g in r.gates)


def test_dangling_reference_fails_schema():
    c = {"causal_edges": [{
        "source": "plasma_glucose", "target": "no_such_node", "sign": "+",
        "evidence": "x", "causal_evidence": "perturbation"}]}
    r = validate_contribution(PM, c)
    assert not r.ok
    assert any(g.gate == "schema" and not g.ok for g in r.gates)


def test_modulation_must_modulate_an_existing_edge():
    c = {"modulation_edges": [{
        "modulator": "cortisol", "edge_source": "plasma_glucose", "edge_target": "no_such_node",
        "sign": "+", "evidence": "x", "causal_evidence": "mechanistic_model"}]}
    r = validate_contribution(PM, c)
    assert not r.ok  # schema: modulates a non-existent causal edge / unknown node


def test_bad_ontology_prefix_is_rejected():
    c = _good_contribution()
    c["nodes"][0]["entity_iri"] = "FOO:123"
    r = validate_contribution(PM, c)
    assert not r.ok
    assert any(g.gate == "ontology" and not g.ok for g in r.gates)


def test_alphanumeric_protein_ontology_curie_is_accepted():
    contribution = {
        "nodes": [{
            "id": "fgf23_fixture",
            "label": "FGF23 fixture concentration",
            "scale": "organ_system",
            "entity_iri": "PR:Q9GZV9",
            "quality_iri": "PATO:0000033",
        }]
    }
    report = validate_contribution(PM, contribution)
    ontology = next(gate for gate in report.gates if gate.gate == "ontology")
    assert ontology.ok, ontology.errors
    assert any("PR:Q9GZV9 ✓ verified" in warning for warning in ontology.warnings)


def test_new_entity_quality_bearer_mismatch_is_rejected():
    contribution = {
        "nodes": [{
            "id": "bad_rate_trait",
            "label": "rate incorrectly borne by a cell",
            "scale": "cellular",
            "entity_iri": "CL:0000232",
            "quality_iri": "PATO:0000161",
        }]
    }
    report = validate_contribution(PM, contribution)
    gate = next(gate for gate in report.gates if gate.gate == "bearer_bfo")
    assert not gate.ok
    assert any("demands a occurrent bearer" in error for error in gate.errors)


def test_empty_contribution_is_not_admissible():
    r = validate_contribution(PM, {})
    assert not r.ok


def test_compose_candidate_rejects_redefining_a_node():
    c = {"nodes": [{"id": "plasma_glucose", "label": "DIFFERENT", "scale": "molecular"}]}
    try:
        compose_candidate(PM, c)
        assert False, "expected a conflict on redefining an existing node"
    except ValueError as exc:
        assert "already exists" in str(exc)


def test_submission_store_roundtrip_and_fragment_export():
    with tempfile.TemporaryDirectory() as d:
        store = SubmissionStore(d)
        sid = make_submission_id("George Gkoutos", "2026-06-10T12:00:00", "test marker")
        sub = Submission(id=sid, curator="George Gkoutos", created="2026-06-10T12:00:00",
                         title="test marker", contribution=_good_contribution())
        store.save(sub)
        assert store.load(sid).curator == "George Gkoutos"
        assert any(s.id == sid for s in store.list())
        store.update(sid, status="approved")
        assert store.load(sid).status == "approved"
        frag = contribution_to_fragment(store.load(sid))
        assert "plasma_curation_test_marker" in frag and "DRAFT FOR DOMAIN REVIEW" in frag


def test_legacy_contribution_is_normalized_and_previewed():
    legacy = {
        "nodes": [{"id": "legacy_marker", "label": "legacy", "scale": "organ_system",
                   "entity": "CHEBI:17234", "quality": "PATO:0000033"}],
        "edges": [{"from": "plasma_glucose", "to": "legacy_marker", "effect": "increases",
                   "evidence": "fixture", "causal_evidence": "perturbation"}],
    }
    normalized = normalize_legacy_contribution(legacy)
    assert normalized["nodes"][0]["entity_iri"] == "CHEBI:17234"
    assert normalized["causal_edges"][0]["sign"] == "+"
    preview = axiom_preview(legacy)
    assert any("pm:causedBy" in axiom and "legacy_marker" in axiom for axiom in preview)
    assert validate_contribution(PM, legacy).ok


def test_local_ontology_lookup_uses_checksum_bound_registry():
    terms = ontology_lookup("glucose")
    assert terms
    assert any(term["id"] == "CHEBI:17234" for term in terms)
    assert ontology_lookup("") == []


def test_deep_candidate_runs_owl_projection_gate():
    report = validate_contribution(PM, _good_contribution(), deep=True)
    gate = next(gate for gate in report.gates if gate.gate == "owl_projection")
    assert gate.ok, gate.errors
