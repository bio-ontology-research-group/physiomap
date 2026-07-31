#!/usr/bin/env python3
"""Apply de-dup decisions to a candidate fragment, producing the final integrable fragment.

Combines (a) the auto-`duplicate` remaps from reconcile_fragment and (b) the adjudicated
`review` decisions into one id-remap, then: drops merged nodes, repoints every edge/constitutive/
modulation reference, removes self-loops created by a merge, and de-duplicates identical edges
(combining a conflicting sign to '?').

decisions.json: {"proposed_id": "existing_id"  (merge)  | "NOVEL" (keep as new node)}
Auto-`duplicate` cases are added to the remap automatically (no need to list them).

Usage: uv run python scripts/finalize_fragment.py <candidate.yaml> <out.yaml> [--decisions d.json]
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


def _combine(a: str, b: str) -> str:
    return a if a == b else "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate")
    ap.add_argument("out")
    ap.add_argument("--decisions", default=None)
    ap.add_argument("--catalog", default=str(ROOT / "benchmarks/results/node_catalog.json"))
    args = ap.parse_args()

    frag = yaml.safe_load(Path(args.candidate).read_text(encoding="utf-8")) or {}
    rc = Reconciler(load_catalog(Path(args.catalog)))
    decisions = json.loads(Path(args.decisions).read_text()) if args.decisions else {}

    remap: dict[str, str] = {}
    drop_ids: set[str] = set()  # ids already in the map -> drop the redeclaration, keep edge refs
    for nd in frag.get("nodes", []) or []:
        v = rc.classify(nd["id"], nd.get("label", nd["id"]), scale=nd.get("scale"),
                        entity_iri=nd.get("entity_iri"), quality_iri=nd.get("quality_iri"))
        if v.status == "duplicate" and v.best:
            remap[nd["id"]] = v.best.existing_id          # auto-merge
        elif v.status == "existing":
            drop_ids.add(nd["id"])                         # already in the map; do not redeclare
        elif nd["id"] in decisions and decisions[nd["id"]] not in (None, "NOVEL", ""):
            remap[nd["id"]] = decisions[nd["id"]]          # adjudicated merge

    nodes = [nd for nd in frag.get("nodes", []) or []
             if nd["id"] not in remap and nd["id"] not in drop_ids]

    edges: dict[tuple, dict] = {}
    for e in frag.get("causal_edges", []) or []:
        s = remap.get(e["source"], e["source"])
        t = remap.get(e["target"], e["target"])
        if s == t:
            continue  # self-loop from a merge
        key = (s, t)
        e2 = dict(e); e2["source"] = s; e2["target"] = t
        if key in edges:
            edges[key]["sign"] = _combine(edges[key]["sign"], e2["sign"])
            edges[key]["evidence"] = (edges[key].get("evidence", "") + "  ||  " + e2.get("evidence", ""))[:1500]
        else:
            edges[key] = e2

    out = dict(frag)
    out["nodes"] = nodes
    out["causal_edges"] = list(edges.values())
    for coll in ("production_edges", "constitutive_edges", "modulation_edges"):
        if coll in out:
            for e in out[coll]:
                for k in ("micro", "macro", "modulator", "source", "target"):
                    if e.get(k) in remap:
                        e[k] = remap[e[k]]

    Path(args.out).write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True, width=120),
                              encoding="utf-8")
    print(f"finalized: {len(nodes)} nodes, {len(out['causal_edges'])} edges "
          f"({len(remap)} merged: {remap}) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
