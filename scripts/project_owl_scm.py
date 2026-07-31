#!/usr/bin/env python3
"""Project a complete canonical SCM from PhysioMap OWL and the pattern registry only."""

from __future__ import annotations

import argparse
from pathlib import Path

from physiomap_core.owl_projection import MigrationBuilder
from physiomap_core.scm import ScmManifest

ROOT = Path(__file__).resolve().parent.parent


def projection_core(manifest: ScmManifest) -> dict:
    """Semantic projection payload, excluding reasoner/package provenance added afterwards."""
    payload = manifest.model_dump(mode="json", exclude_none=True)
    provenance = dict(payload["ontology_provenance"])
    for key in ("source_modules", "primary_kb_sha256", "projection_entailments"):
        provenance.pop(key, None)
    payload["ontology_provenance"] = provenance
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("owl", type=Path)
    parser.add_argument(
        "--patterns", type=Path, default=ROOT / "projection/patterns.yaml"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    parser.add_argument("--traces", type=Path)
    args = parser.parse_args()

    manifest = MigrationBuilder(args.patterns).project_owl(args.owl)
    if not args.output and not args.check:
        parser.error("at least one of --output or --check is required")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_json(args.output)
    if args.check:
        expected = ScmManifest.from_json(args.check)
        if projection_core(manifest) != projection_core(expected):
            raise SystemExit("OWL-only SCM projection differs from the canonical SCM")
    if args.traces:
        import json

        args.traces.parent.mkdir(parents=True, exist_ok=True)
        args.traces.write_text(
            json.dumps(
                [trace.model_dump(mode="json") for trace in manifest.projection_traces],
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    print(
        f"projected {len(manifest.nodes)} nodes, {len(manifest.influences)} influences, "
        f"{len(manifest.projection_traces)} traces from {args.owl}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
