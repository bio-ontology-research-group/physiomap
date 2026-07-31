#!/usr/bin/env python3
"""De-duplicate a candidate PhysioMap fragment against the canonical node catalog.

This is the gate that prevents extraction from adding a *second* node for a variable that
already exists under a different name/id. Run it on every candidate fragment BEFORE the
schema/provenance/causal-evidence/soundness gates.

For each node declared in the fragment it prints a verdict:
  existing   the id is already in the map (the contributor reused it)
  duplicate  matches an existing node on (entity,quality,scale) or synonym-folded label
             -> SHOULD be remapped to the existing id (use --rewrite to do it)
  review     a strong fuzzy/partial match a curator must adjudicate (ambiguous entity)
  novel      genuinely new -> admit

With --rewrite, writes ``<frag>.reconciled.yaml`` where every ``duplicate`` node is dropped
and all edge/constitutive references to it are repointed to the existing id; ``review`` cases
are left as-is and listed in ``<frag>.review.tsv`` for adjudication.

Usage:
  uv run python scripts/reconcile_fragment.py candidate.yaml [--catalog node_catalog.json] [--rewrite]
Exit 0 = no unresolved duplicates (only existing/novel, or all rewritten); 1 = duplicates/reviews remain.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from physiomap_core.reconcile import Reconciler, Verdict, load_catalog  # noqa: E402


def _verdicts(frag: dict, rc: Reconciler) -> list[Verdict]:
    out = []
    for nd in frag.get("nodes", []) or []:
        out.append(
            rc.classify(
                nd["id"],
                nd.get("label", nd["id"]),
                scale=nd.get("scale"),
                entity_iri=nd.get("entity_iri"),
                quality_iri=nd.get("quality_iri"),
            )
        )
    return out


def _rewrite(frag: dict, remap: dict[str, str]) -> dict:
    keep_nodes = [nd for nd in frag.get("nodes", []) or [] if nd["id"] not in remap]
    out = dict(frag)
    out["nodes"] = keep_nodes
    for e in out.get("causal_edges", []) or []:
        for k in ("source", "target"):
            if e.get(k) in remap:
                e[k] = remap[e[k]]
    for e in out.get("production_edges", []) or []:
        for k in ("source", "target"):
            if e.get(k) in remap:
                e[k] = remap[e[k]]
    for e in out.get("constitutive_edges", []) or []:
        for k in ("micro", "macro"):
            if e.get(k) in remap:
                e[k] = remap[e[k]]
    for e in out.get("modulation_edges", []) or []:
        for k in ("modulator", "source", "target"):
            if e.get(k) in remap:
                e[k] = remap[e[k]]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fragment")
    ap.add_argument("--catalog", default=str(ROOT / "benchmarks/results/node_catalog.json"))
    ap.add_argument("--rewrite", action="store_true")
    args = ap.parse_args()

    frag = yaml.safe_load(Path(args.fragment).read_text(encoding="utf-8")) or {}
    rc = Reconciler(load_catalog(Path(args.catalog)))
    verds = _verdicts(frag, rc)

    counts = {"existing": 0, "duplicate": 0, "review": 0, "novel": 0}
    remap: dict[str, str] = {}
    reviews: list[Verdict] = []
    print(f"fragment: {args.fragment}  ({len(verds)} declared nodes)")
    for v in verds:
        counts[v.status] += 1
        if v.status == "duplicate" and v.best:
            remap[v.proposed_id] = v.best.existing_id
            print(f"  DUPLICATE  {v.proposed_id!r}  ->  {v.best.existing_id!r}   [{v.best.reason}]")
        elif v.status == "review":
            reviews.append(v)
            top = "; ".join(f"{m.existing_id} ({m.reason},{m.score})" for m in v.matches[:3])
            print(f"  REVIEW     {v.proposed_id!r}  ?  {top}")
        elif v.status == "existing":
            print(f"  existing   {v.proposed_id!r} (id already in map — reused)")
    print(f"\n  summary: {counts}")

    if args.rewrite:
        fp = Path(args.fragment)
        if remap:
            out = _rewrite(frag, remap)
            outp = fp.with_suffix(".reconciled.yaml")
            outp.write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")
            print(f"  wrote remapped fragment ({len(remap)} nodes merged) -> {outp}")
        if reviews:
            rp = fp.with_suffix(".review.tsv")
            lines = ["proposed_id\tproposed_label\tcandidate_existing_ids"]
            for v in reviews:
                cand = ",".join(m.existing_id for m in v.matches)
                lines.append(f"{v.proposed_id}\t{v.proposed_label}\t{cand}")
            rp.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"  wrote {len(reviews)} review cases -> {rp}")

    return 0 if (counts["duplicate"] == 0 and counts["review"] == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
