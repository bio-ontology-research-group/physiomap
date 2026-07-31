#!/usr/bin/env python3
"""Validate generated SCM structure and exact compatibility with YAML inputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from physiomap_core.model import PhysioMap
from physiomap_core.bfo import validate_bearer, validate_bfo
from physiomap_core.constitution import validate_constitution
from physiomap_core.scm import ScmManifest
from physiomap_core.quantity import validate_quantity
from physiomap_core.quantitative_validation import validate_quantitative_manifest
from scripts.build_owl_scm import default_fragments

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path,
                        default=ROOT / "build/migration/physiomap-scm.json")
    parser.add_argument("inputs", nargs="*", type=Path)
    args = parser.parse_args()
    manifest = ScmManifest.from_json(args.manifest)
    source = PhysioMap.load_composed(args.inputs or default_fragments(), name=manifest.name)
    compatible = manifest.to_physiomap()
    if source != compatible:
        differing = [name for name in type(source).model_fields
                     if getattr(source, name) != getattr(compatible, name)]
        raise SystemExit(f"SCM compatibility mismatch: {', '.join(differing)}")
    constitution = validate_constitution(compatible)
    if not constitution.ok:
        raise SystemExit("constitution validation failed:\n" + "\n".join(constitution.errors))
    bfo = validate_bfo(compatible)
    if not bfo.ok:
        raise SystemExit("BFO validation failed:\n" + "\n".join(bfo.errors))
    bearer = validate_bearer(compatible)
    if not bearer.ok:
        raise SystemExit("bearer validation failed:\n" + "\n".join(bearer.errors))
    quantity = validate_quantity(compatible)
    if not quantity.ok:
        raise SystemExit("quantity validation failed:\n" + "\n".join(quantity.errors))
    numerical = validate_quantitative_manifest(manifest)
    if not numerical.ok:
        raise SystemExit("quantitative semantics failed:\n" + "\n".join(numerical.errors))
    print(f"SCM structural validation and YAML compatibility: OK "
          f"({len(manifest.nodes)} nodes, {len(manifest.influences)} influences; "
          f"{bearer.checked} bearer axioms, {len(bearer.notes)} baselined bearer notes; "
          f"{numerical.exact_rules_checked} derivative rules, "
          f"{numerical.numerical_trials} numerical trials)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
