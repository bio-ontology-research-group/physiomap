#!/usr/bin/env python3
"""E4 — backward diagnosis at scale: abduce the primary lesion from the phenotype set.

The forward solver predicts sign(dx*/dθ) for a do(lesion). INVERTING that is differential
diagnosis: given an observed pattern of directional abnormalities (the HPO presentation), rank
candidate single-gene lesions by how well their *predicted* sign pattern matches the observation
(agree +1, contradict -1, abstain 0; ties broken by fewer contradictions). This is the E1b/E2
forward setup run backwards, over the full gene set.

Efficiency: a candidate's predicted pattern depends only on its clamp, not on the gene being
diagnosed, so we **precompute each candidate (node, sign) prediction once** and score every gene
against the cache (N solves total, not N×genes).

Metrics over the genes whose lesion is in the candidate pool and which have >=1 determinate
observed direction: unique top-1 plus best-tied-rank top-3, top-10, mean reciprocal rank,
median rank, and pool size.

Usage:  python scripts/e4_diagnose.py
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from scripts.e1b_eval import build_observations

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "benchmarks/results/e4_diagnosis.md"
OUT_JSON = ROOT / "benchmarks/results/e4_diagnosis.json"


def main() -> int:
    release, obs = build_observations()
    pmap = build_map()

    # candidate pool = every single-node lesion (node, sign) used by the gene set
    pool: set[tuple[str, str]] = set()
    for rec in obs.values():
        prim = rec["primary"]
        if len(prim) == 1:
            (n, s), = prim.items()
            pool.add((n, s))
    pool = sorted(pool)
    print(f"candidate pool: {len(pool)} (node, sign) lesions; release {release}")

    # precompute each candidate's predicted sign pattern once
    cache: dict[tuple[str, str], dict[str, str]] = {}
    for n, s in pool:
        pred = solve_multiscale(pmap, Intervention(targets={n: Sign(s)}, label=f"{n}{s}")).predicted
        cache[(n, s)] = {k: v.value for k, v in pred.items() if v.value in ("+", "-")}
    print(f"precomputed {len(cache)} candidate predictions")

    def score(cand: tuple[str, str], observed: dict[str, str]) -> tuple[int, int]:
        pred = cache[cand]
        agree = dis = 0
        for node, o in observed.items():
            p = pred.get(node)
            if p is None:
                continue  # abstain / no change -> neutral
            if p == o:
                agree += 1
            else:
                dis += 1
        return agree, dis

    ranks: list[int] = []
    top1 = top3 = top10 = scored = 0
    detail = []
    for gene, rec in obs.items():
        prim = rec["primary"]
        if len(prim) != 1:
            continue
        (tn, ts), = prim.items()
        if (tn, ts) not in cache:
            continue
        observed = {k: v for k, v in rec["observed"].items() if k != tn}  # exclude the clamp node
        if not observed:
            continue
        # rank: the true lesion must have a determinate match somewhere
        scored_cands = []
        for cand in pool:
            a, d = score(cand, observed)
            scored_cands.append((cand, a - d, -d, a))
        # sort best-first: higher net agreement, then fewer contradictions, then more agreements
        scored_cands.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
        true = next(c for c in scored_cands if c[0] == (tn, ts))
        better = sum(1 for c in scored_cands if (c[1], c[2], c[3]) > (true[1], true[2], true[3]))
        equal = sum(1 for c in scored_cands
                    if (c[1], c[2], c[3]) == (true[1], true[2], true[3]) and c[0] != (tn, ts))
        rank = 1 + better
        uniq = better == 0 and equal == 0
        scored += 1
        ranks.append(rank)
        top1 += int(uniq)
        top3 += int(rank <= 3)
        top10 += int(rank <= 10)
        detail.append((gene, f"{tn}{ts}", rank, uniq, equal, true[3], -true[2]))

    mrr = sum(1.0 / r for r in ranks) / len(ranks) if ranks else 0.0
    print("=" * 70)
    print(f"E4 BACKWARD DIAGNOSIS @ scale: genes scored={scored}, pool={len(pool)}")
    print(f"  unique top-1 = {top1}/{scored} ({top1/scored:.0%})")
    print(f"  top-3        = {top3}/{scored} ({top3/scored:.0%})")
    print(f"  top-10       = {top10}/{scored} ({top10/scored:.0%})")
    print(f"  MRR          = {mrr:.3f}   median rank = {median(ranks):.0f}")
    print("  worst-ranked (gene, lesion, rank, ties):")
    for gene, lesion, rank, uniq, equal, ag, di in sorted(detail, key=lambda d: -d[2])[:12]:
        print(f"    {gene:10s} {lesion:28s} rank=#{rank} ties={equal} agree={ag} contra={di}")
    payload = {
        "schema_version": "1.0.0",
        "hpo_release": release,
        "candidate_pool": len(pool),
        "genes_scored": scored,
        "rank_definition": "best rank within ties (1 + number of strictly better candidates)",
        "unique_top1": top1,
        "top3": top3,
        "top10": top10,
        "mrr": mrr,
        "median_rank": median(ranks),
        "detail": [
            {
                "gene": gene,
                "lesion": lesion,
                "rank": rank,
                "unique_top1": unique,
                "tied_candidates": equal,
                "agreements": agreements,
                "contradictions": contradictions,
            }
            for gene, lesion, rank, unique, equal, agreements, contradictions in detail
        ],
    }
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# E4 — inverse lesion ranking from directional phenotypes",
                "",
                "Generated by `scripts/e4_diagnose.py`; do not edit.",
                "",
                f"External reference: HPOA `{release}`. The closed candidate pool contains "
                f"{len(pool)} single-lesion hypotheses, and the true lesion is always present.",
                "",
                "| metric | result |",
                "|---|---:|",
                f"| genes scored | {scored} |",
                f"| unique top-1 | {top1}/{scored} ({top1/scored:.0%}) |",
                f"| best-tied-rank top-3 | {top3}/{scored} ({top3/scored:.0%}) |",
                f"| best-tied-rank top-10 | {top10}/{scored} ({top10/scored:.0%}) |",
                f"| best-tied-rank mean reciprocal rank | {mrr:.3f} |",
                f"| best-tied-rank median | {median(ranks):.0f} |",
                "",
                "Candidates receive +1 for a matching determinate sign, -1 for a "
                "contradiction, and zero for abstention. Rank is 1 plus the number of "
                "strictly better candidates; therefore top-k, reciprocal rank, and median "
                "use the most favourable rank within a tie. Unique top-1 requires no tied "
                "candidate. This evaluates ranking among known lesions, not open-set "
                "clinical diagnosis.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
