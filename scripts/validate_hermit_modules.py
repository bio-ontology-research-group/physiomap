#!/usr/bin/env python3
"""Run all registered bounded HermiT locality-module checks."""

from pathlib import Path

from physiomap_core.hermit import run_registered_checks

ROOT = Path(__file__).resolve().parent.parent


if __name__ == "__main__":
    results = run_registered_checks(ROOT / "projection/hermit-checks.yaml", ROOT)
    print(f"bounded HermiT checks: OK ({len(results)} registered)")
