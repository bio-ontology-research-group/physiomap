"""Tests for the lexical HPO->PhysioMap aligner (scripts/hpo_align.py).

Pure-function tests run offline; the full alignment run is gated on the OBO cache being present
(``scripts/build_hpo_observations.py`` downloads it). The committed artifacts
(``hpo_alignment.yaml`` / ``node_gaps.md``) are also sanity-checked offline.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

from physiomap_core.hpo import build_map

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("hpo_align", ROOT / "scripts" / "hpo_align.py")
al = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(al)

CACHE_OK = al.HP_OBO.exists() and al.G2P.exists()


def test_direction_detection():
    assert al.direction("Hyperkalemia") == "+"
    assert al.direction("Hypokalemia") == "-"
    assert al.direction("Elevated circulating cortisol level") == "+"
    assert al.direction("Decreased circulating iron concentration") == "-"
    assert al.direction("Abnormal circulating cortisol concentration") is None  # no direction


def test_analyte_tokens_strip_and_clinical_roots():
    assert "potassium" in al.analyte_tokens("Hyperkalemia")     # -emia root expanded
    assert al.analyte_tokens("Increased circulating cortisol level") == {"cortisol"}
    assert "c" not in al.analyte_tokens("Decreased circulating vitamin C concentration")  # len<=2 dropped


def test_has_specific():
    assert al.has_specific({"cortisol"})
    assert not al.has_specific({"pressure"})        # generic-only
    assert al.has_specific({"cardiac", "output"})   # cardiac is specific


@pytest.mark.skipif(not CACHE_OK, reason="OBO cache absent; run scripts/build_hpo_observations.py")
def test_alignment_run_is_sound_and_useful():
    res = al.run()
    repro = res["repro"]
    # the matcher must NEVER contradict a curated sign (soundness of the lexical aligner)
    assert repro["sign_conflict"] == [], f"lexical sign conflicts: {repro['sign_conflict']}"
    # it reproduces a solid majority of curated mappings
    assert repro["matched"] >= 40
    # it surfaces real coverage gaps and confident candidates
    assert len(res["gaps_ranked"]) > 100
    assert len(res["candidates"]) >= 20
    # every proposed candidate node exists in the map
    ids = set(build_map().node_ids)
    bad = [c["node"] for c in res["candidates"] if c["node"] not in ids]
    assert not bad, f"candidate nodes absent from map: {bad}"


def test_committed_artifacts_present_and_consistent():
    doc = yaml.safe_load((ROOT / "benchmarks/hpo/hpo_alignment.yaml").read_text())
    assert doc["curated_reproduction_detail"]["sign_conflict"] == []
    ids = set(build_map().node_ids)
    bad = [c["node"] for c in doc.get("candidates", []) if c["node"] not in ids]
    assert not bad, f"committed candidate nodes absent from map: {bad}"
    assert (ROOT / "benchmarks/hpo/node_gaps.md").exists()
