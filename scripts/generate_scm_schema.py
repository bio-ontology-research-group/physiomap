#!/usr/bin/env python3
"""Generate or verify the canonical SCM JSON Schema from Pydantic models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from physiomap_core.scm import ScmManifest

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "schemas/physiomap-scm.schema.json"


def schema_text() -> str:
    schema = ScmManifest.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://w3id.org/physiomap/schema/scm-1.0.0.json"
    schema["title"] = "PhysioMap SCM manifest"
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = schema_text()
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != content:
            raise SystemExit("SCM JSON Schema is stale")
        print("SCM JSON Schema: current")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8")
    print(f"wrote {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
