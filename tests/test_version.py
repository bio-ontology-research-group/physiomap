"""The version string must be consistent across all sources and a valid semver.

`scripts/release.py` keeps `pyproject.toml`, `physiomap_core/__init__.py`, and the
`CHANGELOG.md` heading in lock-step; this guards against a manual edit drifting them apart.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import physiomap_core

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("release", ROOT / "scripts" / "release.py")
rel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rel)

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def test_versions_agree_and_are_semver():
    vs = rel.read_versions()
    assert len(set(vs.values())) == 1, f"version mismatch: {vs}"
    assert _SEMVER.match(rel.current_version())


def test_package_dunder_matches():
    assert physiomap_core.__version__ == rel.current_version()


def test_changelog_has_current_version_section():
    text = (ROOT / "CHANGELOG.md").read_text()
    assert "## [Unreleased]" in text
    assert re.search(rf"## \[{re.escape(rel.current_version())}\]", text), (
        "CHANGELOG.md must contain a released section for the current version"
    )
