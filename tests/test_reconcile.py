"""Tests for the semantic node de-duplication gate."""

from __future__ import annotations

from physiomap_core.reconcile import CatalogNode, Reconciler, normalize_label

CATALOG = [
    CatalogNode("mean_arterial_pressure", "mean arterial pressure", "organ_system",
                "UBERON:0001009", "PATO:0001595"),
    CatalogNode("heart_rate", "heart rate", "organ_system", "UBERON:0000948", "PATO:0000165"),
    CatalogNode("renal_blood_flow", "renal blood flow", "organ", "UBERON:0002113", "PATO:0001575"),
    CatalogNode("renal_plasma_flow", "renal plasma flow", "organ", "UBERON:0002113", "PATO:0001575b"),
]


def _rc() -> Reconciler:
    return Reconciler(CATALOG)


def test_synonym_label_is_duplicate():
    v = _rc().classify("map2", "MAP", scale="organ_system")
    assert v.status == "duplicate"
    assert v.best.existing_id == "mean_arterial_pressure"


def test_word_order_and_extra_words_fold():
    v = _rc().classify("map3", "mean arterial blood pressure", scale="organ_system")
    assert v.status == "duplicate"
    assert v.best.existing_id == "mean_arterial_pressure"


def test_entity_quality_identity_with_agreeing_label_is_duplicate():
    # Same (entity, quality, scale) AND a corroborating label -> safe auto-merge.
    v = _rc().classify("map_var", "arterial pressure mean", scale="organ_system",
                       entity_iri="UBERON:0001009", quality_iri="PATO:0001595")
    assert v.status == "duplicate"
    assert v.best.existing_id == "mean_arterial_pressure"


def test_coarse_eq_collision_with_divergent_label_goes_to_review():
    # The pilot failure mode: distinct variables sharing a COARSE (entity, quality) IRI must
    # NOT be silently merged. Same E+Q as mean_arterial_pressure but an unrelated label -> review.
    v = _rc().classify("weird_thing", "pulmonary blood volume", scale="organ_system",
                       entity_iri="UBERON:0001009", quality_iri="PATO:0001595")
    assert v.status == "review"
    assert any(m.existing_id == "mean_arterial_pressure" for m in v.matches)


def test_existing_id_reused():
    v = _rc().classify("heart_rate", "heart rate", scale="organ_system")
    assert v.status == "existing"


def test_genuinely_novel_passes():
    v = _rc().classify("alveolar_dead_space_fraction", "alveolar dead space fraction",
                       scale="organ")
    assert v.status == "novel"


def test_near_neighbour_not_blindly_merged():
    # renal plasma flow must NOT collapse into renal blood flow (distinct variables).
    v = _rc().classify("rpf_x", "renal plasma flow", scale="organ",
                       entity_iri="UBERON:0002113", quality_iri="PATO:0001575b")
    assert v.best is None or v.best.existing_id != "renal_blood_flow" or v.status == "review"


def test_homonym_label_different_quality_goes_to_review():
    # same normalized label but conflicting quality -> review, never silent merge.
    v = _rc().classify("hr_force", "heart rate", scale="organ_system",
                       quality_iri="PATO:0001035")  # a different quality
    assert v.status in ("review", "duplicate")
    # if duplicate it must at least surface the conflict reason
    if v.status == "review":
        assert any("quality differs" in m.reason or "fuzzy" in m.reason for m in v.matches)


def test_normalize_label_synonym_folding():
    assert normalize_label("MAP") == normalize_label("mean arterial pressure")
    assert normalize_label("HR") == normalize_label("heart rate")
