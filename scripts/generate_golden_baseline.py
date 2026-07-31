#!/usr/bin/env python3
"""Generate or verify the versioned behavioral golden snapshot for OWL migration."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from physiomap_core import __version__
from physiomap_core.bfo import validate_bearer, validate_bfo
from physiomap_core.constitution import validate_constitution
from physiomap_core.eval import run_benchmark
from physiomap_core.hpo import build_map
from physiomap_core.hpo_validate import validate as validate_hpo
from physiomap_core.scm import ScmManifest
from web import api
from web.export_data import load_exported_web_payload

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "benchmarks/golden/owl-scm-v2.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section(items: list[Any]) -> dict[str, Any]:
    return {"count": len(items), "sha256": digest(items)}


def release_result_files() -> list[Path]:
    """Return public, version-controlled result files included in the snapshot.

    Development helpers create ignored files in ``benchmarks/results``.  A
    golden baseline must not depend on their presence in a curator's working
    tree.  Git provides the authoritative public file set in a checkout; a
    source archive safely falls back to the files it contains.
    """
    relative_dir = Path("benchmarks/results")
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "--", relative_dir.as_posix()],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        tracked = None
    if tracked is not None and tracked.returncode == 0:
        paths = [ROOT / line for line in tracked.stdout.splitlines()]
    else:
        paths = list((ROOT / relative_dir).iterdir())
    return sorted(
        path for path in paths
        if path.is_file() and path.suffix in {".json", ".md", ".txt"}
    )


def build_snapshot() -> dict[str, Any]:
    pmap = build_map()
    manifest = ScmManifest.from_json(ROOT / "build/migration/physiomap-scm.json")
    constitution_report = validate_constitution(pmap)
    bfo_report = validate_bfo(pmap)
    bearer_report = validate_bearer(pmap)
    nodes = [n.model_dump(mode="json", exclude_none=True) for n in pmap.nodes]
    causal = [e.model_dump(mode="json", exclude_none=True) for e in pmap.causal_edges]
    production = [e.model_dump(mode="json", exclude_none=True) for e in pmap.production_edges]
    constitutive = [e.model_dump(mode="json", exclude_none=True) for e in pmap.constitutive_edges]
    modulation = [e.model_dump(mode="json", exclude_none=True) for e in pmap.modulation_edges]
    quantitative = [
        expression.model_dump(
            mode="json", exclude_none=True, exclude={"id", "trace_ids"}
        )
        for expression in manifest.quantitative_expressions
    ]
    sccs = [sorted(component) for component in pmap.sccs()]
    sccs.sort(key=lambda component: (-len(component), component))

    benchmark_dirs = ["guyton", "human", "drug_panel", "human_multiscale"]
    benchmarks = {}
    for name in benchmark_dirs:
        report = run_benchmark(ROOT / "benchmarks" / name)
        payload = report.model_dump(mode="json")
        benchmarks[name] = {
            "cases": len(report.cases), "correct": report.correct, "wrong": report.wrong,
            "ambiguous": report.ambiguous, "directional_accuracy": report.directional_accuracy,
            "loop_correct": report.loop_correct, "loop_total": report.loop_total,
            "sha256": digest(payload),
        }

    hpo_forward, hpo_backward = validate_hpo(pmap)
    hpo_payload = {"forward": hpo_forward.model_dump(mode="json"),
                   "backward": hpo_backward.model_dump(mode="json")}

    website = load_exported_web_payload(ROOT / "web")
    normalized_web = copy.deepcopy(website)
    normalized_web.pop("generated", None)
    normalized_web.pop("git_commit", None)
    for node in normalized_web["nodes"]:
        node.pop("x", None)
        node.pop("y", None)
    interventions = normalized_web.get("interventions", [])

    api.PMAP = pmap
    api.NODE_LABELS = {node.id: node.label for node in pmap.nodes}
    api_payloads = {
        "health": {"ok": True, "nodes": len(pmap.nodes),
                   "curation": {"submit_enabled": False, "review_enabled": False}},
        "nodes": {"nodes": [{"id": key, "label": value}
                             for key, value in api.NODE_LABELS.items()]},
        "knockout_mean_arterial_pressure_down": api._knockout_payload(
            {"mean_arterial_pressure": "-"}),
        "knockout_plasma_glucose_up": api._knockout_payload({"plasma_glucose": "+"}),
        "knockout_tsh_down": api._knockout_payload({"tsh": "-"}),
    }

    result_files = {path.name: file_digest(path) for path in release_result_files()}

    release_dir = ROOT / "build/migration"
    artifact_names = (
        "migration-report.json",
        "physiomap-dl.owl",
        "physiomap-el.owl",
        "physiomap-scm.json",
        "physiomap.owl",
        "projection-entailments.tsv",
        "projection-traces.json",
        "trait-classification.tsv",
    )
    artifacts = {name: file_digest(release_dir / name) for name in artifact_names}
    projection_version = json.loads((release_dir / "physiomap-scm.json").read_text())[
        "projection_version"]
    return {
        "schema_version": "2.0.0", "baseline_id": "owl-scm-v2",
        "physiomap_version": __version__, "projection_version": projection_version,
        "model": {
            "nodes": section(nodes),
            "causal_edges": section(causal),
            "production_edges": section(production),
            "constitutive_edges": section(constitutive),
            "modulation_edges": section(modulation),
            "quantitative_definitions": section(quantitative),
        },
        "graph": {"scc_count": len(sccs), "largest_scc": len(sccs[0]),
                  "size_distribution": [len(component) for component in sccs],
                  "components_sha256": digest(sccs)},
        "semantic_validation": {
            "constitution_errors": section(constitution_report.errors),
            "constitution_notes": section(constitution_report.notes),
            "bfo_errors": section(bfo_report.errors),
            "bfo_notes": section(bfo_report.notes),
            "bearer_checked": bearer_report.checked,
            "bearer_errors": section(bearer_report.errors),
            "bearer_notes": section(bearer_report.notes),
        },
        "benchmarks": benchmarks,
        "hpo": {"forward": hpo_forward.model_dump(mode="json"),
                "backward": {key: value for key, value in hpo_backward.model_dump(mode="json").items()
                             if key != "detail"}, "sha256": digest(hpo_payload)},
        "interventions": {"count": len(interventions), "sha256": digest(interventions),
                          "cases": {case["id"]: digest(case) for case in interventions}},
        "api": {name: {"sha256": digest(payload),
                       "top_level_keys": sorted(payload)} for name, payload in api_payloads.items()},
        "website": {"sha256": digest(normalized_web), "stats": normalized_web["stats"]},
        "benchmark_result_files": result_files,
        "release_artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = json.dumps(build_snapshot(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != current:
            raise SystemExit("golden behavioral baseline is stale")
        print("golden behavioral baseline: current")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(current, encoding="utf-8")
    print(f"wrote {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
