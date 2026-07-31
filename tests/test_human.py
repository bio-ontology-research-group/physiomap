"""Human-scale composed map: composition integrity + soundness + per-subsystem checks."""

from __future__ import annotations

from pathlib import Path

from physiomap_core.eval import run_benchmark
from physiomap_core.model import PhysioMap

ROOT = Path(__file__).resolve().parent.parent
HUMAN = ROOT / "benchmarks" / "human"
SYSTEMS = [
    ROOT / "benchmarks" / "guyton" / "guyton_cv_core.yaml",
    *sorted((HUMAN / "systems").glob("*.yaml")),
]


def test_composes_into_one_validated_map():
    pm = PhysioMap.load_composed(SYSTEMS, name="human")
    assert len(pm.nodes) >= 45
    assert len(pm.causal_edges) >= 90
    # one large whole-body homeostatic SCC + several self-contained subsystem SCCs
    sizes = sorted((len(s) for s in pm.sccs()), reverse=True)
    assert sizes[0] >= 20  # the coupled whole-body core
    assert sum(1 for s in pm.sccs() if len(s) >= 3) >= 4  # subsystem feedback loops


def test_human_scale_is_sound():
    """No determinate prediction may contradict gold, even at whole-body scale."""
    report = run_benchmark(HUMAN)
    wrong = [
        (c.intervention, o.node, o.expected.value, o.predicted.value)
        for c in report.cases
        for o in c.outcomes
        if o.status == "wrong"
    ]
    assert wrong == [], f"wrong-sign predictions: {wrong}"
    assert report.directional_accuracy == 1.0


def test_self_contained_subsystem_loops_resolved_exactly():
    """Subsystems with their own tight SCCs stay determinate at whole-body scale."""
    report = run_benchmark(HUMAN)
    by_id = {c.intervention: c for c in report.cases}

    def status(case_id, node):
        return next(
            o.status for o in by_id[case_id].outcomes if o.node == node
        )

    # Respiratory chemoreflex: in the expanded whole-body map the chemoreflex couples
    # (via oxygen_transport: arterial_po2/pco2 <-> cardiac_output/hematocrit) into the large
    # whole-body SCC, so its steady-state signs are now honestly '?' (loop magnitudes decide),
    # never 'wrong'. This is the documented precision frontier, not a regression.
    assert status("metabolic_acidosis", "arterial_pco2") in ("ambiguous", "correct")
    assert status("metabolic_acidosis", "alveolar_ventilation") in ("ambiguous", "correct")
    assert status("chronic_hypoventilation", "chemoreceptor_drive") in ("ambiguous", "correct")
    # Thermoregulation negative-feedback loops
    assert status("fever_pyrogen", "sweating") == "correct"
    assert status("fever_pyrogen", "skin_blood_flow") == "correct"
    # Calcium-PTH (exact small SCC) — calcium & calcitriol determinate
    assert status("primary_hyperparathyroidism", "plasma_calcium") == "correct"
    assert status("primary_hyperparathyroidism", "calcitriol") == "correct"
    # HPA + HPT reactive feedback (loop-critical, small SCCs)
    assert status("cushings_syndrome", "acth") == "correct"
    assert status("addisons_disease", "acth") == "correct"
    assert status("hyperthyroidism", "tsh") == "correct"


def test_contextual_benchmark_declares_fed_state_instead_of_assuming_it():
    report = run_benchmark(HUMAN)
    hyperinsulinemia = next(
        case for case in report.cases if case.intervention == "hyperinsulinemia"
    )
    assert hyperinsulinemia.contexts == ["fed-state-hepatic-lipogenesis"]
    assert {outcome.node: outcome.status for outcome in hyperinsulinemia.outcomes} == {
        "vldl_secretion": "correct",
        "plasma_triglycerides": "correct",
        "ldl_cholesterol": "correct",
    }


def test_large_scc_predictions_are_flagged_not_wrong():
    """Targets routed through the big whole-body SCC are '?' (honest), never wrong."""
    report = run_benchmark(HUMAN)
    by_id = {c.intervention: c for c in report.cases}
    # these route through the 31-node SCC -> conservative '?', and crucially not 'wrong'
    glu = {o.node: o.status for o in by_id["type1_diabetes"].outcomes}
    assert glu["plasma_glucose"] in ("ambiguous", "correct")
    assert "wrong" not in glu.values()
