#!/usr/bin/env python3
"""Run the complete OWL-to-SCM release acceptance contract."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(label: str, command: list[str], cwd: Path = ROOT) -> dict[str, object]:
    started = time.perf_counter()
    print(f"[release] {label}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)
    return {"gate": label, "status": "passed", "seconds": round(time.perf_counter() - started, 3)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true", help="development-only fast run")
    parser.add_argument(
        "--require-paper",
        action="store_true",
        help="fail unless a linked paper checkout is present and compiles",
    )
    args = parser.parse_args()
    if args.skip_tests and args.require_paper:
        parser.error("--require-paper cannot be combined with --skip-tests")
    uv = ["uv", "run", "python"]
    results = []
    results.append(run("frozen HPO evaluation inputs", uv + [
        "scripts/bootstrap_release_inputs.py"]))
    results.append(run("SCM schema current", uv + ["scripts/generate_scm_schema.py", "--check"]))
    results.append(run("OWL/SCM build with ELK equivalence", uv + [
        "scripts/build_owl_scm.py", "--output-dir", "build/migration"]))
    results.append(run("OWL-only canonical SCM reconstruction", uv + [
        "scripts/project_owl_scm.py", "build/migration/physiomap.owl",
        "--check", "build/migration/physiomap-scm.json"]))
    results.append(run("SCM structure, compatibility, and quantitative semantics", uv + [
        "scripts/validate_owl_scm.py", "build/migration/physiomap-scm.json"]))
    results.append(run("bounded registered HermiT modules", uv + ["scripts/validate_hermit_modules.py"]))
    results.append(run("golden behavioral baseline", uv + ["scripts/generate_golden_baseline.py", "--check"]))
    results.append(run("generated manuscript statistics", uv + [
        "scripts/generate_migration_statistics.py", "--check"]))
    results.append(run("generated manuscript figures", uv + [
        "scripts/generate_migration_figures.py", "--check"]))
    results.append(run("rare-disease forward evaluation", uv + [
        "scripts/e1b_eval.py", "--leakage-sensitivity"]))
    results.append(run("forward inference comparisons", uv + [
        "scripts/e2_baseline.py"]))
    results.append(run("forward precision-coverage comparison", [
        "uv", "run", "--extra", "analysis", "python",
        "scripts/e2c_risk_coverage.py"]))
    results.append(run("inverse lesion ranking", uv + [
        "scripts/e4_diagnose.py"]))
    results.append(run("inverse inference comparisons", [
        "uv", "run", "--extra", "analysis", "python",
        "scripts/e4b_diagnosis_baselines.py"]))
    results.append(run("typed relation-layer ablation", uv + [
        "scripts/e5_typed_layer_ablation.py", "--check"]))
    results.append(run("PSB rare-disease figure and results", [
        "uv", "run", "--extra", "analysis", "python",
        "scripts/generate_psb_rare_disease_figure.py", "--check"]))
    results.append(run("public release package", uv + ["scripts/package_owl_scm_release.py", "--check"]))
    results.append(run("legacy evidence worklist", uv + [
        "scripts/generate_legacy_evidence_worklist.py", "--check"]))
    results.append(run("stratified expert content review", uv + [
        "scripts/import_expert_gold_review.py", "--check"]))
    results.append(run("generated disease traces", uv + ["web/export_traces.py", "--check"]))
    results.append(run("sharded web payload freshness and compression", uv + [
        "web/export_data.py", "--check"]))
    results.append(run("web JavaScript syntax", ["node", "--check", "web/app.js"]))
    results.append(run("editor JavaScript syntax", ["node", "--check", "web/editor.js"]))
    results.append(run("headless website/editor rendering", uv + ["scripts/web_render_smoke.py"]))
    results.append(run("ontology unit tests", ["gradle", "--quiet", "-p", "ontology", "test"]))
    if not args.skip_tests:
        results.append(run("Python regression suite", ["uv", "run", "pytest", "-q"]))
        with tempfile.TemporaryDirectory() as temporary:
            one, two = Path(temporary) / "one", Path(temporary) / "two"
            results.append(run("deterministic rebuild one", uv + [
                "scripts/build_owl_scm.py", "--output-dir", str(one)]))
            results.append(run("deterministic rebuild two", uv + [
                "scripts/build_owl_scm.py", "--output-dir", str(two)]))
            differing = [path.relative_to(one) for path in one.iterdir()
                         if not (two / path.name).is_file() or path.read_bytes() != (two / path.name).read_bytes()]
            if differing:
                raise SystemExit(f"deterministic rebuild mismatch: {differing}")
            results.append({"gate": "byte-identical deterministic rebuild", "status": "passed",
                            "seconds": 0.0})
        paper = ROOT / "paper"
        missing_paper_sources = [
            source.name for source in (paper / "main.tex", paper / "supplement.tex")
            if not source.is_file()
        ]
        if not missing_paper_sources:
            results.append(run("main paper compile", ["latexmk", "-pdf", "-interaction=nonstopmode",
                                                       "-halt-on-error", "main.tex"], paper))
            results.append(run("supplement compile", ["latexmk", "-pdf", "-interaction=nonstopmode",
                                                       "-halt-on-error", "supplement.tex"], paper))
        elif args.require_paper:
            missing = ", ".join(missing_paper_sources)
            raise SystemExit(f"linked paper checkout is incomplete; missing: {missing}")
        else:
            print("[release] paper compilation skipped (no linked paper checkout)")
    report = {"schema_version": "1.0.0", "status": "passed", "gates": results}
    target = ROOT / "build/migration/release-validation.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[release] PASS ({len(results)} gates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
