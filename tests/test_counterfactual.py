"""Tests for rung-three qualitative counterfactuals (physiomap_core.counterfactual)."""

from __future__ import annotations

import pytest

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign

pytest.importorskip("clingo")
from physiomap_core.counterfactual import (  # noqa: E402
    abduction_resolves,
    but_for_necessity,
)


def test_hemochromatosis_but_for_is_necessary():
    """do(hepcidin-) makes transferrin saturation necessarily attributable to the lesion."""
    pmap = build_map()
    bf = but_for_necessity(pmap, {"hepcidin": Sign.MINUS})
    fv, cf, nec = bf["transferrin_saturation"]
    assert fv == "+" and cf == "0" and nec is True


def test_abduction_only_resolves_undetermined_signs():
    """Abduction may turn marginal '?' into a determinate sign; it never reports a determinate->flip."""
    pmap = build_map()
    res = abduction_resolves(
        pmap,
        {"hepcidin": Sign.MINUS},
        {"transferrin_saturation": Sign.PLUS, "plasma_iron": Sign.PLUS},
    )
    # every reported node went from marginal '?' to a determinate +/-
    for node, d in res.items():
        assert d["marginal"] == "?"
        assert d["abduced"] in ("+", "-")
