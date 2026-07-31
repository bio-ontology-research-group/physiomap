from types import SimpleNamespace

import pytest

from scripts.generate_legacy_evidence_worklist import validate_decision_application


def edge(causal_evidence=None, evidence_status="legacy-evidence-unclassified"):
    return SimpleNamespace(
        causal_evidence=causal_evidence,
        evidence_status=evidence_status,
    )


@pytest.mark.parametrize(
    "outcome",
    ["curated_mechanistic", "reclassified_quantitative", "reclassified_production"],
)
def test_proposal_must_remain_present_and_unclassified(outcome):
    decision = {"status": "proposed", "decision": outcome}
    validate_decision_application("item", decision, edge(), edge())

    with pytest.raises(ValueError, match="proposed promotion prematurely reflected"):
        validate_decision_application(
            "item",
            decision,
            edge("curated_mechanistic", "controlled"),
            edge(),
        )

    with pytest.raises(ValueError, match="prematurely removed/reclassified"):
        validate_decision_application("item", decision, edge(), None)


def test_approved_promotion_must_match_source_and_release():
    decision = {"status": "approved", "decision": "perturbation"}
    controlled = edge("perturbation", "controlled")
    validate_decision_application("item", decision, controlled, controlled)

    with pytest.raises(ValueError, match="approved promotion not reflected"):
        validate_decision_application("item", decision, edge(), controlled)


def test_approved_reclassification_must_be_absent_from_causal_layers():
    decision = {"status": "approved", "decision": "reclassified_quantitative"}
    validate_decision_application("item", decision, None, None)

    with pytest.raises(ValueError, match="still causal"):
        validate_decision_application("item", decision, edge(), None)


def test_approved_scientific_supersession_requires_absent_original_and_exact_replacement():
    decision = {
        "status": "approved",
        "decision": "superseded_by_scientific_correction",
        "replacement": {
            "source": "source",
            "target": "corrected_target",
            "sign": "+",
            "causal_evidence": "curated_mechanistic",
            "source_file": "benchmarks/example.yaml",
        },
    }
    replacement = edge("curated_mechanistic", "controlled")
    validate_decision_application(
        "item", decision, None, None, replacement, replacement
    )

    with pytest.raises(ValueError, match="superseded causal influence is still present"):
        validate_decision_application(
            "item", decision, edge(), None, replacement, replacement
        )

    with pytest.raises(ValueError, match="replacement not reflected"):
        validate_decision_application(
            "item", decision, None, None, replacement, None
        )

    wrong_class = edge("mechanistic_model", "controlled")
    with pytest.raises(ValueError, match="replacement not reflected"):
        validate_decision_application(
            "item", decision, None, None, replacement, wrong_class
        )


def test_approved_scientific_supersession_requires_complete_replacement_declaration():
    decision = {
        "status": "approved",
        "decision": "superseded_by_scientific_correction",
    }
    with pytest.raises(ValueError, match="lacks a complete replacement"):
        validate_decision_application("item", decision, None, None)


def test_proposed_scientific_supersession_keeps_original_unclassified():
    decision = {
        "status": "proposed",
        "decision": "superseded_by_scientific_correction",
        "replacement": {
            "source": "source",
            "target": "corrected_target",
            "sign": "+",
            "causal_evidence": "curated_mechanistic",
            "source_file": "benchmarks/example.yaml",
        },
    }
    validate_decision_application("item", decision, edge(), edge())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("sign", "up", "invalid sign"),
        ("causal_evidence", "observational_association", "invalid evidence class"),
    ],
)
def test_proposed_scientific_supersession_rejects_invalid_replacement(field, value, message):
    replacement = {
        "source": "source",
        "target": "corrected_target",
        "sign": "+",
        "causal_evidence": "curated_mechanistic",
        "source_file": "benchmarks/example.yaml",
    }
    replacement[field] = value
    decision = {
        "status": "proposed",
        "decision": "superseded_by_scientific_correction",
        "replacement": replacement,
    }
    with pytest.raises(ValueError, match=message):
        validate_decision_application("item", decision, edge(), edge())
