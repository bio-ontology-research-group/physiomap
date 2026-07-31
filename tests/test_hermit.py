from pathlib import Path

import pytest

from physiomap_core.hermit import HermitRegistry, run_registered_checks


def test_empty_registry_is_a_valid_explicit_boundary(tmp_path):
    path = tmp_path / "checks.yaml"
    path.write_text("version: 1.0.0\nchecks: []\n")
    assert HermitRegistry.load(path).checks == []
    assert run_registered_checks(path, tmp_path) == []


def test_registry_requires_resource_bounds_and_contradiction_fixture(tmp_path):
    path = tmp_path / "checks.yaml"
    path.write_text("""version: 1.0.0
checks:
  - id: unsafe
    module: module.owl
    signature: []
    maximum_module_axioms: 0
    timeout_seconds: 0
    maximum_memory_mb: 64
    contradiction_fixture: ''
""")
    with pytest.raises(ValueError):
        HermitRegistry.load(path)


def test_duplicate_check_ids_are_rejected(tmp_path):
    entry = """  - id: duplicate
    module: module.owl
    signature: [pm:A]
    maximum_module_axioms: 10
    timeout_seconds: 5
    maximum_memory_mb: 256
    contradiction_fixture: broken.owl
"""
    path = tmp_path / "checks.yaml"
    path.write_text("version: 1.0.0\nchecks:\n" + entry + entry)
    with pytest.raises(ValueError, match="duplicate HermiT"):
        HermitRegistry.load(path)


def test_timeout_is_a_hard_failure(tmp_path, monkeypatch):
    module = tmp_path / "module.owl"; module.write_text("Ontology()")
    broken = tmp_path / "broken.owl"; broken.write_text("Ontology()")
    registry = tmp_path / "checks.yaml"
    registry.write_text("""version: 1.0.0
checks:
  - id: bounded
    module: module.owl
    signature: [pm:A]
    maximum_module_axioms: 10
    timeout_seconds: 1
    maximum_memory_mb: 256
    contradiction_fixture: broken.owl
""")
    import subprocess
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 1)
    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        run_registered_checks(registry, tmp_path)
