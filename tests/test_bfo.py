"""Tests for the BFO bearer-category layer and the constitution/causation divide."""
from __future__ import annotations

import json

import physiomap_core.bfo as bfo_module
from physiomap_core.bfo import (
    BearerKind,
    DeterminationRegime,
    bearer_kind,
    determination_regime,
    entity_bearer_kind,
    quality_required_bearer,
    validate_bearer,
    validate_bfo,
)
from physiomap_core.model import (
    ConstitutiveEdge,
    Node,
    PhysioMap,
    ProductionEdge,
    ProductionEvidenceClass,
    Scale,
    Sign,
)
from physiomap_core.multiscale import constitutive_graph

RATE = "PATO:0000161"    # rate -> occurrent (quality of a process)
CONC = "PATO:0000033"    # concentration -> continuant (quality of a substance)
VOLUME = "PATO:0000918"  # volume -> continuant


def _n(nid, q, scale=Scale.CELLULAR, **kw):
    return Node(id=nid, label=nid, scale=scale, quality_iri=q, **kw)


# --------------------------------------------------------------------------- bearer classification
def test_bearer_kind_process_quality_is_occurrent():
    assert bearer_kind(_n("secr", RATE)) == BearerKind.OCCURRENT     # a secretion RATE
    assert bearer_kind(_n("conc", CONC, scale=Scale.ORGAN)) == BearerKind.CONTINUANT
    assert bearer_kind(_n("vol", VOLUME)) == BearerKind.CONTINUANT


def test_bearer_kind_override():
    n = _n("x", CONC, bearer_kind="occurrent")
    assert bearer_kind(n) == BearerKind.OCCURRENT


# --------------------------------------------------------------------------- the divide
def _secretion_map() -> PhysioMap:
    """beta-cell insulin-secretion RATE (occurrent) -> plasma insulin CONCENTRATION (continuant)."""
    nodes = [_n("secretion", RATE, scale=Scale.CELLULAR),
             _n("plasma_insulin", CONC, scale=Scale.ORGAN_SYSTEM)]
    edges = [ProductionEdge(
        source="secretion",
        target="plasma_insulin",
        sign=Sign.PLUS,
        production_evidence=ProductionEvidenceClass.LEGACY_UNCLASSIFIED,
    )]
    return PhysioMap(nodes=nodes, causal_edges=[], production_edges=edges)


def test_production_is_typed_separately_from_constitution_and_influences():
    pm = _secretion_map()
    # The authored relation is neither an SCM influence nor constitution. The compatibility
    # graph exposes only an explicitly tagged production shadow.
    assert len(pm.material_constitutive_edges) == 0
    assert len(pm.production_edges) == 1
    assert pm.causal_subgraph().has_edge("secretion", "plasma_insulin")
    assert pm.causal_subgraph().edges["secretion", "plasma_insulin"]["edge_kind"] == "production-derived"
    assert not constitutive_graph(pm).has_edge("secretion", "plasma_insulin")


def test_molecular_state_into_process_rate_must_not_be_hidden_in_constitution():
    # A cross-BFO record is not silently converted into a causal edge.
    nodes = [_n("mlc", CONC, scale=Scale.SUBCELLULAR),        # a continuant molecular quality
             _n("cardiac_output", RATE, scale=Scale.ORGAN)]    # a process rate (occurrent)
    edges = [ConstitutiveEdge(micro="mlc", macro="cardiac_output",
                              relation="part_of+determination", sign=Sign.PLUS)]
    pm = PhysioMap(nodes=nodes, causal_edges=[], constitutive_edges=edges)
    assert len(pm.material_constitutive_edges) == 0
    assert not pm.causal_subgraph().has_edge("mlc", "cardiac_output")
    assert not validate_bfo(pm).ok


def test_material_constitution_is_continuant_continuant():
    # two continuant volume qualities: micro part_of macro -> genuine material constitution
    nodes = [_n("p", VOLUME, scale=Scale.TISSUE), _n("whole", VOLUME, scale=Scale.ORGAN)]
    edges = [ConstitutiveEdge(micro="p", macro="whole", relation="aggregation", sign=Sign.PLUS)]
    pm = PhysioMap(nodes=nodes, causal_edges=[], constitutive_edges=edges)
    assert len(pm.material_constitutive_edges) == 1
    assert len(pm.production_edges) == 0
    assert constitutive_graph(pm).has_edge("p", "whole")          # in the determination lift
    assert not pm.causal_subgraph().has_edge("p", "whole")        # not causal


def test_validate_bfo_rejects_mislabelled_constitution():
    # A molecular state determining an occurrent rate crosses the BFO divide -> hard error.
    nodes = [_n("mlc", CONC, scale=Scale.SUBCELLULAR), _n("co", RATE, scale=Scale.ORGAN)]
    edges = [ConstitutiveEdge(micro="mlc", macro="co", relation="part_of+determination", sign=Sign.PLUS)]
    rep = validate_bfo(PhysioMap(nodes=nodes, causal_edges=[], constitutive_edges=edges))
    assert not rep.ok
    assert any("crosses the occurrent/continuant divide" in error for error in rep.errors)


# --------------------------------------------------------------------------- the trichotomy
def test_determination_regime_material_is_continuant_continuant():
    micro = _n("part", VOLUME, scale=Scale.TISSUE)
    macro = _n("whole", VOLUME, scale=Scale.ORGAN)
    assert determination_regime(micro, macro) == DeterminationRegime.MATERIAL


def test_determination_regime_process_is_occurrent_occurrent():
    # a fine sub-process RATE composing a coarse process RATE: temporal-mereological constitution
    beat_rate = _n("heart_beat_rate", RATE, scale=Scale.ORGAN)     # frequency of single beats
    cardiac_output = _n("cardiac_output", RATE, scale=Scale.ORGAN)  # flow volume over the beating
    assert determination_regime(beat_rate, cardiac_output) == DeterminationRegime.PROCESS


def test_determination_regime_cross_bfo_is_causal():
    # occurrent rate -> continuant concentration crosses the divide: no parthood bridges it
    secretion = _n("secretion", RATE, scale=Scale.CELLULAR)
    conc = _n("plasma_insulin", CONC, scale=Scale.ORGAN_SYSTEM)
    assert determination_regime(secretion, conc) == DeterminationRegime.CAUSAL
    assert determination_regime(conc, secretion) == DeterminationRegime.CAUSAL  # symmetric divide


def test_validate_bfo_keeps_process_constitution_out_of_causal_graph():
    # Occurrent -> occurrent temporal parthood stays in the separate determination layer.
    nodes = [_n("beat_rate", RATE, scale=Scale.ORGAN), _n("cardiac_output", RATE, scale=Scale.ORGAN)]
    edges = [ConstitutiveEdge(micro="beat_rate", macro="cardiac_output",
                              relation="part_of+determination", sign=Sign.PLUS)]
    rep = validate_bfo(PhysioMap(nodes=nodes, causal_edges=[], constitutive_edges=edges))
    assert rep.ok
    assert any("process (occurrent, temporal-mereological) constitution" in n for n in rep.notes)
    pm = PhysioMap(nodes=nodes, causal_edges=[], constitutive_edges=edges)
    assert constitutive_graph(pm).has_edge("beat_rate", "cardiac_output")
    assert not pm.causal_subgraph().has_edge("beat_rate", "cardiac_output")


# --------------------------------------------------------------------------- entity/quality axiom
def test_quality_required_bearer():
    assert quality_required_bearer(RATE) == BearerKind.OCCURRENT          # rate -> process
    assert quality_required_bearer(CONC) == BearerKind.CONTINUANT         # concentration (curated)
    assert quality_required_bearer(VOLUME) == BearerKind.CONTINUANT       # volume (PATO is_a)
    assert quality_required_bearer(None) is None


def test_entity_bearer_kind_from_ontology_prefix():
    assert entity_bearer_kind(_n("c", RATE, entity_iri="CL:0000232")) == BearerKind.CONTINUANT
    assert entity_bearer_kind(_n("g", RATE, entity_iri="GO:0001503")) == BearerKind.OCCURRENT  # ossification (BP)
    assert entity_bearer_kind(_n("x", RATE)) is None                      # no entity -> unresolved


def test_bearer_ancestry_uses_frozen_registry_without_raw_obo(tmp_path, monkeypatch):
    registry = tmp_path / "used-terms.json"
    registry.write_text(json.dumps({"terms": {
        "GO:1234567": {"parents": ["GO:7654321"]},
        "GO:7654321": {"parents": ["GO:0008150"]},
        "GO:0008150": {"parents": []},
        "PATO:1234567": {"parents": ["PATO:7654321"]},
        "PATO:7654321": {"parents": ["PATO:0001241"]},
        "PATO:0001241": {"parents": []},
    }}), encoding="utf-8")
    monkeypatch.setattr(bfo_module, "_SOURCE_REGISTRY", registry)
    monkeypatch.setattr(bfo_module, "_OBO", tmp_path / "absent-obo-cache")
    bfo_module._isa_cache.clear()

    assert bfo_module._isa_ancestors("GO", "GO:1234567") == {
        "GO:7654321", "GO:0008150"
    }
    assert bfo_module._isa_ancestors("PATO", "PATO:1234567") == {
        "PATO:7654321", "PATO:0001241"
    }

    bfo_module._isa_cache.clear()


def test_validate_bearer_flags_rate_borne_by_continuant():
    # a secretion RATE (process quality) whose modelled entity is the secreting CELL (continuant):
    # inconsistent trait pairing -> advisory note (entity should be the secretion process)
    n = _n("secr", RATE, scale=Scale.CELLULAR, entity_iri="CL:0000232")
    rep = validate_bearer(PhysioMap(nodes=[n], causal_edges=[]))
    assert rep.ok and rep.checked == 1
    assert any("demands a occurrent bearer but entity" in note for note in rep.notes)


def test_validate_bearer_strict_mode_rejects_new_mismatch():
    n = _n("secr", RATE, scale=Scale.CELLULAR, entity_iri="CL:0000232")
    rep = validate_bearer(PhysioMap(nodes=[n], causal_edges=[]), strict=True)
    assert not rep.ok and rep.checked == 1
    assert any("demands a occurrent bearer but entity" in error for error in rep.errors)


def test_validate_bearer_consistent_trait_ok():
    # a concentration (continuant quality) borne by a substance (continuant) is consistent
    n = _n("conc", CONC, scale=Scale.ORGAN_SYSTEM, entity_iri="CHEBI:16469")
    rep = validate_bearer(PhysioMap(nodes=[n], causal_edges=[]))
    assert rep.ok and not rep.notes


def test_released_bearer_and_bfo_debt_counts_are_regression_locked():
    from physiomap_core.hpo import build_map

    pmap = build_map()
    bearer = validate_bearer(pmap)
    bfo = validate_bfo(pmap)
    # The phene recode moved 134 process qualities off their continuant bearers; what is left is
    # a GO coverage gap (no term for leptin/GLP-1/GIP/ANP secretion), so the debt can only shrink.
    assert bearer.ok and bearer.checked == 1549 and len(bearer.notes) == 59
    assert bfo.ok and len(bfo.notes) == 25
