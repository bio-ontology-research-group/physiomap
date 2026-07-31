"""Qualitative differential diagnosis (abduction) over the human-scale map."""

from __future__ import annotations

from pathlib import Path

import yaml

from physiomap_core.diagnose import rank_explanations
from physiomap_core.model import PhysioMap, Sign

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "benchmarks"


def _human_map_and_cases():
    systems = [BASE / "guyton" / "guyton_cv_core.yaml"] + sorted(
        (BASE / "human" / "systems").glob("*.yaml")
    )
    pm = PhysioMap.load_composed(systems, name="human")
    spec = yaml.safe_load((BASE / "human" / "interventions.yaml").read_text())
    return pm, spec["interventions"]


def _grounded_single_target(pm, cases):
    """Single-lesion interventions whose do-target and observed nodes are all in the map.

    (The intervention gold set also contains multi-target syndromes and molecular-vertical
    lesions that live in the multi-scale map; abductive single-lesion diagnosis is scoped to
    cases grounded in this single-scale human map.)
    """
    ids = set(pm.node_ids)
    return [
        c
        for c in cases
        if len(c["do"]) == 1
        and next(iter(c["do"])) in ids
        and all(k in ids for k in c["expected"])
    ]


def _candidates(cases):
    out = []
    for c in cases:
        (target, sgn), = c["do"].items()
        out.append((target, Sign(sgn)))
    return out


def test_diagnosis_recovers_determinate_subsystem_lesions_top1():
    pm, cases = _human_map_and_cases()
    valid = _grounded_single_target(pm, cases)
    cands = _candidates(valid)
    by_id = {c["id"]: c for c in valid}
    # Lesions in self-contained tight SCCs (the HPT axis) stay determinate at whole-body scale
    # and are recovered top-1 with zero contradiction.
    # Dropped as richer coupling pulled them into magnitude-dependent (`?`) SCCs:
    #   - metabolic_acidosis: respiratory chemoreflex absorbed into the whole-body SCC.
    #   - primary_hyperparathyroidism / hypoparathyroidism: the FGF23-klotho counter-regulatory
    #     loop (phosphate_fgf23.yaml) now couples pth-calcium-phosphate-calcitriol-fgf23 into a
    #     6-node SCC whose sign pattern is no longer sign-solvable (direct PTH effects vs
    #     FGF23-mediated counter-effects on calcitriol/phosphate) — the solver honestly returns
    #     `?`, so these are no longer determinate-top-1. (Sound, not wrong; see test_human.)
    for cid in (
        "hyperthyroidism",
        "hypothyroidism",
    ):
        c = by_id[cid]
        observed = {k: Sign(v) for k, v in c["expected"].items()}
        ranked = rank_explanations(pm, observed, cands)
        (true_target, true_sign), = c["do"].items()
        assert ranked[0].target == true_target and ranked[0].sign.value == true_sign, (
            f"{cid}: top explanation was {ranked[0].target}{ranked[0].sign.value}"
        )
        assert ranked[0].disagree == 0  # the true lesion never contradicts its presentation


def test_overall_top3_recovery_is_high():
    pm, cases = _human_map_and_cases()
    valid = _grounded_single_target(pm, cases)
    cands = _candidates(valid)
    top3 = 0
    for c in valid:
        observed = {k: Sign(v) for k, v in c["expected"].items()}
        if not observed:
            continue
        ranked = rank_explanations(pm, observed, cands)
        (tt, ts), = c["do"].items()
        rank = next(
            (i for i, e in enumerate(ranked) if e.target == tt and e.sign.value == ts),
            len(ranked),
        )
        if rank < 3:
            top3 += 1
    # observed 28/50 grounded single-lesion cases recovered in the top 3; guard for regressions
    assert top3 >= 24
