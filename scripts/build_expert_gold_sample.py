#!/usr/bin/env python3
"""Draw the stratified sample used for the expert content review.

The published curator audit measures *enrichment* within one cohort of low- and
medium-confidence proposals. It does not assess the content across all relation
types. This script draws a reproducible sample from the archived v1.1.1 sampling
frame and covers every relation type.

Sampling is stratified so each stratum can be reported on its own:

  * causal influences  -- 50, split across evidence classes in proportion to the release
                          (a minimum of 5 per class where the class has at least 5 records),
  * production         -- 10 of 85,
  * modulation         -- 10 of 19,
  * constitution       -- all 4 (fewer than 10 exist),
  * quantitative       -- all 9 (fewer than 10 exist).

The seed and sampling frame are fixed, so re-running reproduces the identical
sample. Because relation types were sampled at different rates, the unweighted
fraction accepted is a review count, not a map-wide accuracy estimate.

Usage: uv run python scripts/build_expert_gold_sample.py [--seed 20260728]
Writes: benchmarks/results/expert_gold_sample.tsv (review workbook, one row per item)
        benchmarks/results/expert_gold_sample.json (same rows, machine readable)
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCM = ROOT / "benchmarks/data/physiomap-scm-expert-review-2026-07-28.json.gz"
SCM_SHA256 = "9e4ff3dba9c9c5754c38f4cf7c71188c6c628ccdc5fbe10a5514e7fa6d165afa"
OUT_TSV = ROOT / "benchmarks/results/expert_gold_sample.tsv"
OUT_JSON = ROOT / "benchmarks/results/expert_gold_sample.json"

CAUSAL_N = 50
PRODUCTION_N = 10
MODULATION_N = 10
MIN_PER_CLASS = 5

FIELDS = [
    "review_id", "relation_type", "stratum", "source", "target", "sign",
    "evidence_class", "mechanism", "evidence",
    "expert_verdict", "expert_comment",
]


def _label(node_by_id: dict[str, str], node_id: str) -> str:
    label = node_by_id.get(node_id)
    return f"{label} [{node_id}]" if label else node_id


def load_sampling_frame() -> dict:
    with gzip.open(SCM, "rb") as handle:
        content = handle.read()
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != SCM_SHA256:
        raise ValueError(
            f"sampling-frame checksum mismatch: {actual_sha256} != {SCM_SHA256}"
        )
    return json.loads(content)


def sample_causal(influences: list[dict], rng: random.Random) -> list[tuple[str, dict]]:
    """Proportional allocation over evidence classes, with a floor on non-trivial classes."""
    by_class: dict[str, list[dict]] = defaultdict(list)
    for item in influences:
        by_class[item.get("causal_evidence") or "unclassified"].append(item)
    total = len(influences)
    quota: dict[str, int] = {}
    for name, items in by_class.items():
        share = round(CAUSAL_N * len(items) / total)
        if len(items) >= MIN_PER_CLASS:
            share = max(share, MIN_PER_CLASS)
        quota[name] = min(share, len(items))
    # trim or pad to exactly CAUSAL_N, largest strata absorbing the difference
    order = sorted(quota, key=lambda name: -len(by_class[name]))
    while sum(quota.values()) > CAUSAL_N:
        for name in order:
            if sum(quota.values()) == CAUSAL_N:
                break
            if quota[name] > MIN_PER_CLASS:
                quota[name] -= 1
    while sum(quota.values()) < CAUSAL_N:
        for name in order:
            if sum(quota.values()) == CAUSAL_N:
                break
            if quota[name] < len(by_class[name]):
                quota[name] += 1
    out: list[tuple[str, dict]] = []
    for name in sorted(quota):
        picked = rng.sample(sorted(by_class[name], key=lambda x: x["id"]), quota[name])
        out.extend((name, item) for item in picked)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260728)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    scm = load_sampling_frame()
    node_by_id = {n["id"]: n.get("label", n["id"]) for n in scm["nodes"]}
    influence_by_id = {i["id"]: i for i in scm["influences"]}
    rows: list[dict[str, str]] = []

    def add(relation_type: str, stratum: str, source: str, target: str, sign: str,
            evidence_class: str, mechanism: str, evidence: str) -> None:
        rows.append({
            "review_id": f"{relation_type}-{len(rows) + 1:03d}",
            "relation_type": relation_type,
            "stratum": stratum,
            "source": _label(node_by_id, source),
            "target": _label(node_by_id, target),
            "sign": sign,
            "evidence_class": evidence_class or "",
            "mechanism": (mechanism or "").replace("\n", " "),
            "evidence": (evidence or "").replace("\n", " "),
            "expert_verdict": "",
            "expert_comment": "",
        })

    for stratum, item in sample_causal(scm["influences"], rng):
        add("causal", stratum, item["source"], item["target"], item["sign"],
            item.get("causal_evidence") or "unclassified",
            item.get("mechanism", ""), item.get("evidence", ""))

    production = rng.sample(sorted(scm["production_relations"], key=lambda x: x["id"]),
                            min(PRODUCTION_N, len(scm["production_relations"])))
    for item in production:
        add("production", item.get("production_evidence", ""), item["source"], item["target"],
            item["sign"], item.get("production_evidence", ""),
            item.get("mechanism", ""), item.get("evidence", ""))

    for item in sorted(scm["constitutive_constraints"], key=lambda x: x["id"]):
        add("constitution", item.get("relation", ""), item["micro"], item["macro"],
            item["sign"], item.get("relation", ""), "", "")

    for item in sorted(scm["quantitative_expressions"], key=lambda x: x["id"]):
        arguments = ", ".join(f"{a['node']} ({a['role']}, {a['derivative_sign']})"
                              for a in item["arguments"])
        add("quantitative", item["kind"], arguments, item["result"], "",
            item["kind"], item.get("mechanism", ""), item.get("evidence", ""))

    modulation = rng.sample(sorted(scm["modulation"], key=lambda x: x["id"]),
                            min(MODULATION_N, len(scm["modulation"])))
    for item in modulation:
        influenced = influence_by_id[item["influence_id"]]
        add("modulation", item.get("causal_evidence") or "unclassified",
            _label(node_by_id, item["modulator"]),
            f"edge {_label(node_by_id, influenced['source'])} -> "
            f"{_label(node_by_id, influenced['target'])}",
            item["sign"], item.get("causal_evidence") or "unclassified",
            item.get("mechanism", ""), item.get("evidence", ""))

    OUT_TSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_TSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(
            {
                key: (value.rstrip() if value else r"\N")
                for key, value in row.items()
            }
            for row in rows
        )
    OUT_JSON.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")

    counts = Counter(row["relation_type"] for row in rows)
    print(f"seed={args.seed}  wrote {len(rows)} items to {OUT_TSV.relative_to(ROOT)}")
    for name, count in sorted(counts.items()):
        print(f"  {name:14s} {count:3d}")
    causal_strata = Counter(row["stratum"] for row in rows if row["relation_type"] == "causal")
    print("  causal strata: " + ", ".join(f"{k}={v}" for k, v in sorted(causal_strata.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
