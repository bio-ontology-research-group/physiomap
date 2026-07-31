"""Numeric cross-validation: the qualitative solver vs ground-truth stable dynamics."""

from __future__ import annotations

from pathlib import Path

import pytest

from physiomap_core.model import PhysioMap, Sign
from physiomap_core.qualitative import Intervention
from physiomap_core.validate import cross_validate

GUYTON = Path(__file__).resolve().parent.parent / "benchmarks" / "guyton" / "guyton_cv_core.yaml"


@pytest.mark.parametrize(
    "do",
    [
        {"angiotensin_II": Sign.MINUS},          # ACE inhibitor
        {"sodium_water_reabsorption": Sign.PLUS},  # primary Na retention
        {"sympathetic_tone": Sign.PLUS},          # sympathetic activation
        {"aldosterone": Sign.PLUS},               # primary aldosteronism
    ],
)
def test_determinate_signs_are_numerically_sound(do):
    """Every determinate qualitative sign must hold across the stable numeric ensemble."""
    pm = PhysioMap.from_yaml(GUYTON)
    summary = cross_validate(pm, Intervention(targets=do), n_samples=250, seed=7)
    assert summary.samples >= 100  # enough stable draws were found
    assert summary.determinate_confirmed > 0
    assert summary.sound, f"numeric contradictions: {summary.contradictions}"


def test_unknowns_are_mostly_warranted():
    """Most '?' predictions genuinely flip sign across the stable ensemble."""
    pm = PhysioMap.from_yaml(GUYTON)
    s = cross_validate(
        pm, Intervention(targets={"sympathetic_tone": Sign.PLUS}), n_samples=250, seed=3
    )
    n_unknown = len(s.warranted_unknown) + len(s.conservative_unknown)
    if n_unknown:
        assert len(s.warranted_unknown) >= n_unknown // 2
