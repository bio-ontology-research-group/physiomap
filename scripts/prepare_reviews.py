#!/usr/bin/env python3
"""Emit rich adjudication context for a fragment's de-dup REVIEW cases.

reconcile_fragment.py routes coarse-IRI / fuzzy collisions to a `review` bucket that must be
adjudicated (merge-to-existing vs keep-novel) — never auto-merged. This dumps, for each review
case, the proposed node alongside every candidate existing node's full record, so an adjudicator
can decide. Output: <frag>.reviewctx.json .

Usage: uv run python scripts/prepare_reviews.py <fragment.yaml> [--catalog node_catalog.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from physiomap_core.reconcile import Reconciler, load_catalog  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fragment")
    ap.add_argument("--catalog", default=str(ROOT / "benchmarks/results/node_catalog.json"))
    args = ap.parse_args()

    frag = yaml.safe_load(Path(args.fragment).read_text(encoding="utf-8")) or {}
    cat = load_catalog(Path(args.catalog))
    by_id = {c.id: c for c in cat}
    rc = Reconciler(cat)

    cases = []
    for nd in frag.get("nodes", []) or []:
        v = rc.classify(nd["id"], nd.get("label", nd["id"]), scale=nd.get("scale"),
                        entity_iri=nd.get("entity_iri"), quality_iri=nd.get("quality_iri"))
        if v.status != "review":
            continue
        cands = []
        for m in v.matches:
            c = by_id.get(m.existing_id)
            if c:
                cands.append({"id": c.id, "label": c.label, "scale": c.scale,
                              "entity_iri": c.entity_iri, "quality_iri": c.quality_iri,
                              "match_reason": m.reason})
        cases.append({
            "proposed": {"id": nd["id"], "label": nd.get("label"), "scale": nd.get("scale"),
                         "entity_iri": nd.get("entity_iri"), "quality_iri": nd.get("quality_iri")},
            "candidates": cands,
        })

    outp = Path(args.fragment).with_suffix(".reviewctx.json")
    outp.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(f"{len(cases)} review cases -> {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
