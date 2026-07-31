from __future__ import annotations

from types import SimpleNamespace

from scripts import generate_golden_baseline
from scripts.bootstrap_release_inputs import FROZEN_INPUTS, file_sha256, materialize


def test_frozen_hpo_inputs_materialize_with_expected_checksums(tmp_path):
    outputs = materialize(tmp_path / ".obo_cache")

    assert [path.name for path in outputs] == [item.output for item in FROZEN_INPUTS]
    assert [file_sha256(path) for path in outputs] == [
        item.output_sha256 for item in FROZEN_INPUTS
    ]


def test_golden_baseline_uses_only_version_controlled_results(tmp_path, monkeypatch):
    results = tmp_path / "benchmarks/results"
    results.mkdir(parents=True)
    public = results / "public.json"
    public.write_text("{}\n", encoding="utf-8")
    (results / "ignored.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(generate_golden_baseline, "ROOT", tmp_path)
    monkeypatch.setattr(generate_golden_baseline.subprocess, "run", lambda *args, **kwargs:
                        SimpleNamespace(returncode=0,
                                        stdout="benchmarks/results/public.json\n"))

    assert generate_golden_baseline.release_result_files() == [public]
