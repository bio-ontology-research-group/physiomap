"""Quantitative validation against the REAL HPO gene->phenotype annotations.

Runs offline against the committed, HPO-derived ``hpo_gene_observations.yaml`` (regenerate with
``scripts/build_hpo_observations.py`` after an HPO release). Asserts soundness + the measured
forward/backward metrics, and that every mapped node id exists in the map.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from physiomap_core.hpo import build_map
from physiomap_core.hpo_validate import validate

ROOT = Path(__file__).resolve().parent.parent
PM = build_map()


def test_forward_is_sound_against_real_hpo():
    fwd, _ = validate(PM)
    assert fwd.wrong == 0, f"unsound vs HPO: {fwd.wrong_calls}"
    assert fwd.observations >= 10
    assert fwd.accuracy == 1.0


def test_backward_recovers_real_hpo_lesions():
    _, bwd = validate(PM)
    # The expanded renal/homeostatic SCC introduces additional tied lesion candidates.
    # Nineteen of twenty genes remain within top-3; SLC12A1 is the single documented
    # near miss at rank 4 under conservative SCC abstention.
    assert bwd.top3 == bwd.genes_scored - 1
    assert any(line.startswith("SLC12A1") and "rank=#4" in line for line in bwd.detail)
    assert bwd.top1 >= 8                      # metabolic/iron/lipid lesions cleanly recovered


def test_term_map_and_gene_nodes_exist_in_map():
    ids = set(PM.node_ids)
    tm = yaml.safe_load((ROOT / "benchmarks/hpo/hpo_term_map.yaml").read_text())["terms"]
    bad_terms = sorted({r["node"] for r in tm.values() if r["node"] not in ids})
    assert not bad_terms, f"hpo_term_map nodes absent from map: {bad_terms}"
    genes = yaml.safe_load((ROOT / "benchmarks/hpo/gene_lesions.yaml").read_text())["genes"]
    bad_genes = sorted({n for g in genes.values() for n in g["primary"] if n not in ids})
    assert not bad_genes, f"gene_lesions primary nodes absent from map: {bad_genes}"
