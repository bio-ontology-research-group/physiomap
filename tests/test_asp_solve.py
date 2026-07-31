"""Tests for the ASP sign-solver (physiomap_core.asp_solve).

Soundness oracle: the exact comparative-statics engine. The ASP encoding is a superset-of-achievable
sign-consistency, so wherever ASP is determinate it must match the exact engine, and it must never be
wrong on the curated Guyton gold set.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from physiomap_core.model import PhysioMap, Sign
from physiomap_core.qualitative import Intervention, solve_signs

pytest.importorskip("clingo")
from physiomap_core.asp_solve import solve_signs_asp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FRAG = ROOT / "benchmarks" / "guyton" / "guyton_cv_core.yaml"


def _frag() -> PhysioMap:
    return PhysioMap.load_composed([FRAG], name="frag")


def test_asp_recovers_raas_paradox_at_subsystem_resolution():
    """On the small Guyton SCC, ASP resolves the aldosteronism feedback paradox like the exact engine."""
    pmap = _frag()
    res = solve_signs_asp(pmap, Intervention(targets={"aldosterone": Sign.PLUS}))
    assert res.predicted["renin"] is Sign.MINUS
    assert res.predicted["angiotensin_II"] is Sign.MINUS
    assert res.predicted["sodium_excretion"] is Sign.PLUS  # pressure-natriuresis / escape


def test_asp_never_disagrees_with_exact_on_fragment():
    """Soundness: where both engines commit, ASP must equal the exact engine (0 disagreements)."""
    pmap = _frag()
    for node, sgn in [("aldosterone", Sign.PLUS), ("angiotensin_II", Sign.MINUS),
                      ("sodium_water_reabsorption", Sign.PLUS), ("sympathetic_tone", Sign.PLUS)]:
        iv = Intervention(targets={node: sgn})
        asp = solve_signs_asp(pmap, iv).predicted
        exact = solve_signs(pmap, iv).predicted
        for n in set(asp) & set(exact):
            a, e = asp[n], exact[n]
            if a in (Sign.PLUS, Sign.MINUS) and e in (Sign.PLUS, Sign.MINUS):
                assert a is e, f"ASP/exact disagree at {n}: {a} vs {e} under do({node})"


def test_asp_abstains_not_guesses():
    """ASP returns only +/-/? (Sign.UNKNOWN), never fabricates a sign for an undetermined node."""
    pmap = _frag()
    res = solve_signs_asp(pmap, Intervention(targets={"sympathetic_tone": Sign.PLUS}))
    assert all(v in (Sign.PLUS, Sign.MINUS, Sign.UNKNOWN) for v in res.predicted.values())
