"""Tests for the evaluation harness (physiomap_core.eval) on the Guyton benchmark."""

from __future__ import annotations

from pathlib import Path

from physiomap_core.eval import run_benchmark

BENCH = Path(__file__).resolve().parent.parent / "benchmarks" / "guyton"


def test_run_benchmark_loads_and_scores():
    report = run_benchmark(BENCH)
    assert len(report.cases) == 4
    assert report.total > 0


def test_known_ecf_endpoint_regressions_are_explicit_and_bounded():
    """Lock the two known broad-Guyton errors after the approved endpoint correction.

    The direct sodium/water-reabsorption target is now blood volume rather than ECF
    volume. The subsystem solver consequently reaches ECF only through the opposing
    pressure-natriuresis route in these two cases. Keep the physiological gold signs
    unchanged and fail if the error set silently grows or changes.
    """
    report = run_benchmark(BENCH)
    wrong = [
        (c.intervention, o.node, o.expected.value, o.predicted.value)
        for c in report.cases
        for o in c.outcomes
        if o.status == "wrong"
    ]
    assert wrong == [
        ("primary_aldosteronism", "extracellular_fluid_volume", "+", "-"),
        ("primary_sodium_retention", "extracellular_fluid_volume", "+", "-"),
    ]


def test_directional_accuracy_matches_declared_broad_benchmark_limit():
    report = run_benchmark(BENCH)
    assert report.scored == 24
    assert report.correct == 22
    assert report.wrong == 2
    assert report.directional_accuracy == 22 / 24


def test_pressure_natriuresis_and_baroreflex_net_signs():
    """The non-trivial pass: correct NET signs through the feedback loops where naive
    forward propagation would be wrong."""
    report = run_benchmark(BENCH)
    by_id = {c.intervention: c for c in report.cases}

    # Pressure-natriuresis loop: raising Na reabsorption must (a) raise Na excretion and
    # (b) SUPPRESS renin/angiotensin/aldosterone/sympathetic at the new steady state.
    na = {o.node: o for o in by_id["primary_sodium_retention"].outcomes}
    for node in (
        "sodium_excretion",
        "renin",
        "angiotensin_II",
        "aldosterone",
        "sympathetic_tone",
        "mean_arterial_pressure",
    ):
        assert na[node].status == "correct", f"{node}: {na[node].status}"

    # RAAS suppression by pressure (primary aldosteronism): low renin / low AngII.
    aldo = {o.node: o for o in by_id["primary_aldosteronism"].outcomes}
    for node in ("renin", "angiotensin_II", "sympathetic_tone", "sodium_excretion"):
        assert aldo[node].status == "correct", f"{node}: {aldo[node].status}"

    # Baroreflex (ACE inhibitor): reactive renin RISE — unreachable by forward propagation.
    ace = {o.node: o for o in by_id["ace_inhibitor"].outcomes}
    assert ace["renin"].status == "correct"
    assert ace["mean_arterial_pressure"].status == "correct"

    # Every loop-critical target across the benchmark is resolved correctly.
    assert report.loop_correct == report.loop_total


def test_main_cli_exposes_known_broad_benchmark_errors(capsys):
    from physiomap_core.eval import main

    rc = main([str(BENCH)])
    out = capsys.readouterr().out
    assert "Directional accuracy" in out
    assert rc == 1
