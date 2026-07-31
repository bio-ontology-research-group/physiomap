"""Tests for cross-scale constitutive reasoning (physiomap_core.multiscale)."""

from __future__ import annotations

from pathlib import Path

from physiomap_core.model import (
    CausalEdge,
    ConstitutiveEdge,
    Node,
    PhysioMap,
    Scale,
    Sign,
)
from physiomap_core.multiscale import (
    constitutive_graph,
    propagate_constitutive,
    solve_multiscale,
)
from physiomap_core.qualitative import Intervention, solve_signs

POC = Path(__file__).resolve().parent.parent / "benchmarks" / "multiscale" / "vascular_tone.yaml"
ROOT_HM = Path(__file__).resolve().parent.parent / "benchmarks" / "human_multiscale"


def test_reclassified_vascular_tone_vertical_is_causal():
    pm = PhysioMap.from_yaml(POC)
    g = pm.causal_subgraph()
    assert g.number_of_edges() == 5
    assert g.has_edge("mlc_phosphorylation", "vascular_smooth_muscle_tone")
    assert g.has_edge("vascular_smooth_muscle_tone", "total_peripheral_resistance")


def test_reclassified_vascular_tone_vertical_is_absent_from_constitution():
    pm = PhysioMap.from_yaml(POC)
    cg = constitutive_graph(pm)
    assert cg.number_of_edges() == 0


def test_causal_solver_follows_reclassified_vertical():
    pm = PhysioMap.from_yaml(POC)
    r = solve_signs(pm, Intervention(targets={"at1_receptor_activity": Sign.PLUS}))
    assert r.predicted["intracellular_calcium"] is Sign.PLUS
    assert r.predicted["mlc_phosphorylation"] is Sign.PLUS
    assert r.predicted["vascular_smooth_muscle_tone"] is Sign.PLUS
    assert r.predicted["total_peripheral_resistance"] is Sign.PLUS


def test_multiscale_solver_preserves_causal_vertical():
    pm = PhysioMap.from_yaml(POC)
    r = solve_multiscale(pm, Intervention(targets={"at1_receptor_activity": Sign.PLUS}))
    assert r.predicted["mlc_phosphorylation"] is Sign.PLUS
    assert r.predicted["vascular_smooth_muscle_tone"] is Sign.PLUS
    assert r.predicted["total_peripheral_resistance"] is Sign.PLUS
    assert r.causal_only["total_peripheral_resistance"] is Sign.PLUS


def test_ARB_blockade_flips_the_whole_vertical():
    pm = PhysioMap.from_yaml(POC)
    r = solve_multiscale(pm, Intervention(targets={"at1_receptor_activity": Sign.MINUS}))
    assert r.predicted["total_peripheral_resistance"] is Sign.MINUS


def test_negative_determination_sign_inverts_transfer():
    pm = PhysioMap(
        nodes=[
            Node(id="micro", label="m", scale=Scale.MOLECULAR),
            Node(id="macro", label="M", scale=Scale.ORGAN),
            Node(id="driver", label="d", scale=Scale.MOLECULAR),
        ],
        causal_edges=[CausalEdge(source="driver", target="micro", sign=Sign.PLUS)],
        constitutive_edges=[
            ConstitutiveEdge(micro="micro", macro="macro", sign=Sign.MINUS)
        ],
    )
    r = solve_multiscale(pm, Intervention(targets={"driver": Sign.PLUS}))
    assert r.predicted["micro"] is Sign.PLUS
    assert r.predicted["macro"] is Sign.MINUS  # negative determination inverts


def test_human_multiscale_rescore_is_sound_and_lifts_a_scale():
    """A molecular drug attached under the human map: sound, and the cross-scale
    determinate lift (cellular tone) is recovered where a single-scale causal solve fails."""
    from physiomap_core.eval import run_benchmark

    report = run_benchmark(ROOT_HM)
    wrong = [
        (c.intervention, o.node)
        for c in report.cases
        for o in c.outcomes
        if o.status == "wrong"
    ]
    assert wrong == [], f"wrong-sign predictions at multi-scale: {wrong}"
    arb = {o.node: o.status for o in report.cases[0].outcomes}
    assert arb["intracellular_calcium"] == "correct"
    assert arb["vascular_smooth_muscle_tone"] == "correct"   # determinate cross-scale lift
    assert arb["total_peripheral_resistance"] == "ambiguous"  # loop-trapped organ target


def test_propagate_constitutive_flags_causal_vs_determination_conflict():
    # macro has BOTH a causal sign (+) and a determination sign (-) -> '?' + note
    pm = PhysioMap(
        nodes=[
            Node(id="micro", label="m", scale=Scale.MOLECULAR),
            Node(id="macro", label="M", scale=Scale.ORGAN),
        ],
        constitutive_edges=[
            ConstitutiveEdge(micro="micro", macro="macro", sign=Sign.MINUS)
        ],
    )
    updated, notes = propagate_constitutive(
        pm, {"micro": Sign.PLUS, "macro": Sign.PLUS}
    )
    assert updated["macro"] is Sign.UNKNOWN
    assert any("macro" in n for n in notes)
