"""The standing HPO soundness gate must pass on the committed map.

Any future relation, fragment, or gene-mapping change that makes a determinate
prediction contradict the curated pilot or the HPO gene-to-phenotype data fails here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "hpo_regression_gate", ROOT / "scripts" / "hpo_regression_gate.py"
)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def test_hpo_soundness_gate_passes():
    ok, violations = gate.check(quiet=True)
    assert ok, "HPO soundness gate violations:\n" + "\n".join(violations)
