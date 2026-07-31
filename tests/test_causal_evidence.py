"""Tests for the causal-evidence gate (interventional vs associational edge import)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from physiomap_core.causal_evidence import (
    ASSOCIATIONAL,
    INTERVENTIONAL,
    admit,
    admit_modulation,
    audit_map,
    audit_modulations,
    classify_source,
)
from physiomap_core.model import (
    CausalEdge,
    CausalEvidenceClass,
    ModulationEdge,
    Node,
    PhysioMap,
    Scale,
    Sign,
)

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "benchmarks" / "multiscale" / "hif_epo_oxygen_sensing.yaml"


def _edge(cls: CausalEvidenceClass | None) -> CausalEdge:
    return CausalEdge(source="a", target="b", sign=Sign.PLUS, causal_evidence=cls)


def test_partition_total_and_disjoint():
    # every class is exactly one of interventional / associational
    assert INTERVENTIONAL | ASSOCIATIONAL == set(CausalEvidenceClass)
    assert not (INTERVENTIONAL & ASSOCIATIONAL)


@pytest.mark.parametrize("cls", sorted(INTERVENTIONAL, key=lambda c: c.value))
def test_interventional_classes_admitted(cls):
    ok, _ = admit(_edge(cls))
    assert ok


@pytest.mark.parametrize("cls", sorted(ASSOCIATIONAL, key=lambda c: c.value))
def test_associational_classes_rejected(cls):
    ok, reason = admit(_edge(cls))
    assert not ok
    assert reason


def test_missing_class_rejected():
    ok, reason = admit(_edge(None))
    assert not ok
    assert "no causal_evidence" in reason


def test_classify_source_maps_dbs():
    assert classify_source("BioModels BIOMD0000000271") == CausalEvidenceClass.MECHANISTIC_MODEL
    assert classify_source("SIGNOR curated") == CausalEvidenceClass.CURATED_MECHANISTIC
    # association-only resources must NOT be classed interventional
    assert classify_source("ARACNe co-expression network") in ASSOCIATIONAL
    assert classify_source("ChIP-seq peak") == CausalEvidenceClass.BINDING_ONLY
    assert classify_source("some unlisted resource") == CausalEvidenceClass.UNKNOWN
    # the source default never silently upgrades an association to a cause
    assert not any(
        classify_source(s) in INTERVENTIONAL
        for s in ("aracne", "wgcna", "chip-seq", "gwas catalog")
    )


def test_audit_map_require_all_flags_untagged():
    nodes = [Node(id="a", label="A", scale=Scale.MOLECULAR),
             Node(id="b", label="B", scale=Scale.MOLECULAR)]
    pm = PhysioMap(nodes=nodes, causal_edges=[_edge(None)])
    # default: untagged edges are left alone (hand-curated legacy edges)
    assert audit_map(pm) == []
    # require_all: every edge must carry an interventional class
    assert len(audit_map(pm, require_all=True)) == 1


def test_audit_map_flags_associational_even_by_default():
    nodes = [Node(id="a", label="A", scale=Scale.MOLECULAR),
             Node(id="b", label="B", scale=Scale.MOLECULAR)]
    pm = PhysioMap(nodes=nodes, causal_edges=[_edge(CausalEvidenceClass.COEXPRESSION)])
    assert len(audit_map(pm)) == 1


def test_pilot_fragment_all_edges_interventional():
    # the pilot cites a boundary node (erythropoietin) owned by a sibling fragment, so it
    # cannot load standalone as a complete PhysioMap; validate its edges directly.
    data = yaml.safe_load(PILOT.read_text())
    edges = [CausalEdge.model_validate(e) for e in data.get("causal_edges", [])]
    assert edges, "pilot must have causal edges"
    for e in edges:
        ok, reason = admit(e)
        assert ok, f"{e.source}->{e.target}: {reason}"


def test_validator_script_passes_on_pilot():
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_causal_evidence.py"), str(PILOT)],
        capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "RESULT: OK" in res.stdout


def test_validator_script_fails_on_associational(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "name: bad\n"
        "nodes:\n"
        "- {id: x, label: X, scale: molecular}\n"
        "- {id: y, label: Y, scale: molecular}\n"
        "causal_edges:\n"
        "- {source: x, target: y, sign: '+', causal_evidence: coexpression,\n"
        "   evidence: 'co-expression only'}\n"
    )
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_causal_evidence.py"), str(bad)],
        capture_output=True, text=True,
    )
    assert res.returncode == 1
    assert "ASSOCIATIONAL" in res.stdout


def _mod_map(mod_evidence):
    nodes = [Node(id=n, label=n, scale=Scale.ORGAN) for n in ("m", "s", "t")]
    causal = [
        CausalEdge(source="s", target="t", sign=Sign.PLUS,
                   causal_evidence=CausalEvidenceClass.PHARMACOLOGICAL),
        CausalEdge(source="m", target="t", sign=Sign.PLUS,
                   causal_evidence=CausalEvidenceClass.CURATED_MECHANISTIC),
    ]
    mod = ModulationEdge(modulator="m", edge_source="s", edge_target="t", sign=Sign.PLUS,
                         causal_evidence=mod_evidence)
    return PhysioMap(nodes=nodes, causal_edges=causal, modulation_edges=[mod])


def test_modulation_gate_requires_interventional_interaction_evidence():
    # admissible: an interventional class
    ok, _ = admit_modulation(_mod_map(CausalEvidenceClass.PHARMACOLOGICAL).modulation_edges[0])
    assert ok
    assert audit_modulations(_mod_map(CausalEvidenceClass.GENETIC_LOF_GOF)) == []
    # rejected: no class at all (a gain claim is unfalsifiable without interaction evidence)
    ok, reason = admit_modulation(_mod_map(None).modulation_edges[0])
    assert not ok and "INTERACTION" in reason
    assert audit_modulations(_mod_map(None))
    # rejected: associational class
    ok, reason = admit_modulation(_mod_map(CausalEvidenceClass.COEXPRESSION).modulation_edges[0])
    assert not ok and "ASSOCIATIONAL" in reason
    assert audit_modulations(_mod_map(CausalEvidenceClass.COEXPRESSION))


def test_validator_script_gates_modulation_without_class(tmp_path):
    bad = tmp_path / "badmod.yaml"
    bad.write_text(
        "name: badmod\n"
        "nodes:\n"
        "- {id: a, label: A, scale: organ}\n"
        "- {id: b, label: B, scale: organ}\n"
        "- {id: c, label: C, scale: organ}\n"
        "causal_edges:\n"
        "- {source: b, target: c, sign: '+', causal_evidence: pharmacological, evidence: x}\n"
        "modulation_edges:\n"
        "- {modulator: a, edge_source: b, edge_target: c, sign: '+'}\n"
    )
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_causal_evidence.py"), str(bad)],
        capture_output=True, text=True,
    )
    assert res.returncode == 1
    assert "modulation_edge" in res.stdout and "INTERACTION" in res.stdout
