#!/usr/bin/env python3
"""Build the parallel OWL TBox and canonical SCM release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import json
from pathlib import Path

from physiomap_core.model import PhysioMap
from physiomap_core.owl_projection import (MigrationBuilder, verify_elk_projection,
                                            write_artifacts)

ROOT = Path(__file__).resolve().parent.parent


def default_fragments() -> list[Path]:
    bench = ROOT / "benchmarks"
    return ([bench / "guyton/guyton_cv_core.yaml"]
            + sorted((bench / "human/systems").glob("*.yaml"))
            + sorted((bench / "human/curated").glob("*.yaml"))
            + sorted((bench / "multiscale").glob("*.yaml")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, help="YAML fragments (default: release corpus)")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--patterns", type=Path, default=ROOT / "projection/patterns.yaml")
    parser.add_argument("--no-source-registry", action="store_true")
    parser.add_argument("--skip-elk", action="store_true",
                        help="development-only: skip OWL profile/classification/projection gate")
    args = parser.parse_args()
    inputs = args.inputs or default_fragments()
    pmap = PhysioMap.load_composed(inputs, name="physiomap")
    builder = MigrationBuilder(args.patterns,
        None if args.no_source_registry else ROOT / "ontology/.obo_cache")
    owl, imported_manifest, report = builder.build(
        pmap, [str(p.relative_to(ROOT)) for p in inputs]
    )
    # The YAML model ends at the OWL compilation boundary. The release SCM used below is read
    # back from canonical OWL plus the projection registry, not retained from the importer.
    manifest = builder.project_owl(owl)
    if manifest != imported_manifest:
        raise SystemExit("OWL-only SCM projection differs from the migration import")
    write_artifacts(args.output_dir, owl, manifest, report, dl_owl=builder.dl_owl)
    if not args.skip_elk:
        artifact_dir = args.output_dir.resolve()
        module_manifest_path = ROOT / "ontology/modules/manifest.json"
        if not module_manifest_path.is_file():
            raise SystemExit("source locality modules are missing; run scripts/extract_source_modules.py")
        module_manifest = json.loads(module_manifest_path.read_text(encoding="utf-8"))
        module_paths = []
        for record in module_manifest["modules"]:
            if manifest.ontology_provenance["checksums"].get(record["source"]) != record["source_sha256"]:
                raise SystemExit(f"stale locality module source checksum: {record['source']}")
            module_path = ROOT / "ontology/modules" / record["module"]
            if hashlib.sha256(module_path.read_bytes()).hexdigest() != record["module_sha256"]:
                raise SystemExit(f"stale locality module artifact: {record['module']}")
            module_paths.append(module_path.resolve())
        merge_args = " ".join(str(path) for path in
                              [artifact_dir / "physiomap.owl", artifact_dir / "physiomap-el.owl",
                               *module_paths])
        subprocess.run(["gradle", "--quiet", "-p", str(ROOT / "ontology"), "run",
                        f"--args=--merge {merge_args}"], cwd=ROOT, check=True)
        manifest.ontology_provenance["source_modules"] = module_manifest
        manifest.ontology_provenance["primary_kb_sha256"] = hashlib.sha256(
            (artifact_dir / "physiomap.owl").read_bytes()).hexdigest()
        # The representation-level artifact is profile-checked but never reasoned over.
        subprocess.run(["gradle", "--quiet", "-p", str(ROOT / "ontology"), "run",
                        f"--args=--dl-profile {artifact_dir / 'physiomap-dl.owl'}"],
                       cwd=ROOT, check=True)
        entailments = artifact_dir / "projection-entailments.tsv"
        subprocess.run([
            "gradle", "--quiet", "-p", str(ROOT / "ontology"), "run",
            f"--args=--project {artifact_dir / 'physiomap-el.owl'} {entailments}",
        ], cwd=ROOT, check=True)
        counts = verify_elk_projection(entailments, manifest)
        trait_classification = artifact_dir / "trait-classification.tsv"
        classified = {}
        for line in trait_classification.read_text(encoding="utf-8").splitlines()[1:]:
            node_id, satisfiable, parents = (line.split("\t") + [""])[:3]
            classified[node_id] = {"satisfiable": satisfiable == "true",
                                   "inferred_parents": [value for value in parents.split("|") if value]}
        if set(classified) != {record["node_id"] for record in report["traits"]}:
            raise SystemExit("ELK trait-classification coverage mismatch")
        for record in report["traits"]:
            record.update(classified[record["node_id"]])
        digest = hashlib.sha256(entailments.read_bytes()).hexdigest()
        manifest.ontology_provenance["projection_entailments"] = {
            "file": entailments.name, "sha256": digest, "counts": counts,
        }
        report["reasoning_validation"] = {
            "owl2_el_profile": "passed", "elk_consistency": "passed",
            "elk_classification": "passed", "projection_equivalence": "passed",
            "entailment_counts": counts,
            "classified_traits": len(classified),
        }
        # Re-write JSON reports after provenance enrichment without replacing the merged primary KB.
        manifest.write_json(artifact_dir / "physiomap-scm.json")
        (artifact_dir / "migration-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"built {len(manifest.nodes)} traits, {len(manifest.influences)} influences, "
        f"{len(manifest.production_relations)} production relations, "
        f"{len(manifest.constitutive_constraints)} constitutive constraints, "
        f"{len(manifest.quantitative_expressions)} quantitative expressions, "
        f"{len(manifest.modulation)} modulations in {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
