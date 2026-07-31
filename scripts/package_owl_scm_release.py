#!/usr/bin/env python3
"""Package the validated public OWL/projection/SCM release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from physiomap_core import __version__

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=ROOT / "build/migration")
    parser.add_argument("--release-dir", type=Path, default=ROOT / "release/owl-scm")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sources = {
        name: args.artifact_dir / name for name in (
            "physiomap.owl", "physiomap-el.owl", "physiomap-dl.owl", "physiomap-scm.json",
            "projection-traces.json", "projection-entailments.tsv", "trait-classification.tsv",
            "migration-report.json")
    }
    sources["patterns.yaml"] = ROOT / "projection/patterns.yaml"
    sources["physiomap-scm.schema.json"] = ROOT / "schemas/physiomap-scm.schema.json"
    sources["legacy-evidence-baseline.json"] = ROOT / "ontology/registry/legacy-evidence-baseline.json"
    sources["legacy-evidence-decisions.yaml"] = ROOT / "ontology/legacy-evidence-decisions.yaml"
    sources["legacy-evidence-worklist.json"] = ROOT / "docs/generated/legacy-evidence-worklist.json"
    sources["legacy-evidence-worklist.tsv"] = ROOT / "docs/generated/legacy-evidence-worklist.tsv"
    for path in sources.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    checksums = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                 for name, path in sorted(sources.items())}
    scm = json.loads(sources["physiomap-scm.json"].read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "1.0.0", "physiomap_version": __version__,
        "projection_version": scm["projection_version"],
        "generator_version": scm["generator_version"],
        "reasoning_configuration": scm["reasoning_configuration"],
        "ontology_provenance": scm["ontology_provenance"],
        "files": checksums,
        "generated_artifact_policy": "do not edit; regenerate through build_owl_scm.py",
    }
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    sums_text = "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items()))
    expected = {**{name: path.read_bytes() for name, path in sources.items()},
                "release-manifest.json": manifest_text.encode(), "SHA256SUMS": sums_text.encode()}
    if args.check:
        stale = [name for name, content in expected.items()
                 if not (args.release_dir / name).is_file()
                 or (args.release_dir / name).read_bytes() != content]
        if stale:
            raise SystemExit("stale public release package: " + ", ".join(stale))
        print("public OWL/SCM release package: current")
        return 0
    args.release_dir.mkdir(parents=True, exist_ok=True)
    for name, source in sources.items():
        shutil.copyfile(source, args.release_dir / name)
    (args.release_dir / "release-manifest.json").write_text(manifest_text, encoding="utf-8")
    (args.release_dir / "SHA256SUMS").write_text(sums_text, encoding="utf-8")
    print(f"packaged {len(expected)} files in {args.release_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
