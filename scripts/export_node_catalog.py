#!/usr/bin/env python3
"""Export the canonical PhysioMap node catalog for extraction + de-duplication.

Every extraction agent receives this catalog and MUST reuse an existing node's exact
``id`` when its variable matches one — never invent a second id for an existing variable.
The catalog is also the reference set for :mod:`physiomap_core.reconcile`, the semantic
de-duplication gate run on every candidate fragment before it is admitted.

Outputs (under ``benchmarks/results/``):
* ``node_catalog.tsv``  — human/agent-readable: id, scale, entity_iri, quality_iri, label
* ``node_catalog.json`` — machine-readable list of node records (for the reconciler)

Usage:  uv run python scripts/export_node_catalog.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from physiomap_core.hpo import build_map  # noqa: E402

OUT_DIR = ROOT / "benchmarks/results"


def main() -> int:
    pmap = build_map()
    records = []
    for n in pmap.nodes:
        records.append(
            {
                "id": n.id,
                "label": n.label,
                "scale": n.scale.value if hasattr(n.scale, "value") else str(n.scale),
                "entity_iri": n.entity_iri,
                "quality_iri": n.quality_iri,
                "bearer_entity_iri": n.bearer_entity_iri,
            }
        )
    records.sort(key=lambda r: r["id"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "node_catalog.json").write_text(json.dumps(records, indent=0), encoding="utf-8")

    lines = ["# PhysioMap node catalog — REUSE these ids; do not create a duplicate.",
             "# id\tscale\tentity_iri\tquality_iri\tlabel"]
    for r in records:
        lines.append(
            "\t".join(
                [
                    r["id"],
                    r["scale"],
                    r["entity_iri"] or "-",
                    r["quality_iri"] or "-",
                    r["label"],
                ]
            )
        )
    (OUT_DIR / "node_catalog.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"wrote {len(records)} nodes -> {OUT_DIR/'node_catalog.tsv'} (+ .json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
