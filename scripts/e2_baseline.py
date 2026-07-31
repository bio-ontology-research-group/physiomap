#!/usr/bin/env python3
"""E2 — naive forward propagation baseline + disagreement analysis (evaluation experiment).

The methodological payoff: PhysioMap's comparative-statics (CS) solver is right *where naive
pathway/network propagation is wrong, because of feedback*. For the same 183-gene IEM forward
setup (scripts/e1b_eval), we compare per (gene, observed-HPO-node):
  * CS          = solve_multiscale(do(lesion)).predicted[node]   (feedback-aware; abstains in SCCs)
  * naive-short = sign product along the SHORTEST signed path from the clamp (feedback-blind; the
                  de-facto signed-network-propagation baseline; commits on any reachable node)
  * naive-fwd   = consensus of bounded simple-path products (trace.signed_paths); ? if paths conflict
against the HPOA observed direction. Reports the disagreement set and each method's precision /
coverage, and the key feedback contrast: where CS abstains but naive commits, naive ~ chance.

Usage:  python scripts/e2_baseline.py
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from physiomap_core.trace import combined_do_graph, signed_paths
from scripts.e1b_eval import build_observations

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "benchmarks/results/e2_baseline.json"
OUT_MD = ROOT / "benchmarks/results/e2_baseline.md"


def naive_shortest(g: nx.DiGraph, primary: dict[str, Sign], node: str) -> Sign | None:
    best, blen = None, 1 << 30
    for src, ssign in primary.items():
        if g.has_node(src) and g.has_node(node) and nx.has_path(g, src, node):
            path = nx.shortest_path(g, src, node)
            if len(path) < blen:
                s = ssign
                for a, b in zip(path, path[1:]):
                    s = s * Sign(g.edges[a, b]["sign"])
                best, blen = s, len(path)
    return best


def naive_forward(g: nx.DiGraph, primary: dict[str, Sign], node: str) -> Sign | None:
    signs = set()
    for src, ssign in primary.items():
        for p in signed_paths(g, src, node, ssign):
            signs.add(p.net)
    if not signs:
        return None
    return next(iter(signs)) if len(signs) == 1 else Sign.UNKNOWN


def det(s):  # determinate?
    return s in (Sign.PLUS, Sign.MINUS)


def main() -> int:
    _, obs = build_observations()
    pmap = build_map()
    rows = []  # (gene, node, cs, nshort, nfwd, hpoa)
    for gene, rec in obs.items():
        observed = {k: Sign(v) for k, v in rec["observed"].items()}
        if not observed:
            continue
        primary = {k: Sign(v) for k, v in rec["primary"].items()}
        cs_pred = solve_multiscale(pmap, Intervention(targets=primary, label=gene)).predicted
        g = combined_do_graph(pmap, primary)
        for node, hpoa in observed.items():
            if node in primary:
                continue
            rows.append((gene, node, cs_pred.get(node), naive_shortest(g, primary, node),
                         naive_forward(g, primary, node), hpoa))

    scores = {}

    def score(idx, name):
        cor = sum(1 for r in rows if det(r[idx]) and r[idx] is r[5])
        wro = sum(1 for r in rows if det(r[idx]) and r[idx] is not r[5])
        ab = sum(1 for r in rows if not det(r[idx]))
        acc = cor / (cor + wro) if (cor + wro) else float("nan")
        print(f"  {name:14s} determinate={cor+wro:3d} correct={cor:3d} wrong={wro:3d} "
              f"abstain={ab:3d}  precision={acc:.1%}")
        scores[name] = {
            "determinate": cor + wro,
            "correct": cor,
            "wrong": wro,
            "abstain": ab,
            "precision": acc,
        }
        return cor, wro, ab

    print("=" * 72)
    print(f"E2 baseline — {len(rows)} (gene, observed-node) prediction pairs")
    print("=" * 72)
    score(2, "CS (PhysioMap)")
    score(3, "naive-shortest")
    score(4, "naive-forward")

    # disagreement: CS determinate & naive-shortest determinate & differ
    dis = [r for r in rows if det(r[2]) and det(r[3]) and r[2] is not r[3]]
    cs_right = sum(1 for r in dis if r[2] is r[5])
    nv_right = sum(1 for r in dis if r[3] is r[5])
    print("-" * 72)
    print(f"DISAGREEMENT set (CS vs naive-shortest both determinate, differ): {len(dis)}")
    print(f"   CS correct: {cs_right}/{len(dis)}    naive correct: {nv_right}/{len(dis)}")
    for r in dis[:20]:
        print(f"     {r[0]:9s} {r[1]:34s} CS={r[2].value} naive={r[3].value} HPOA={r[5].value}"
              f"  -> {'CS' if r[2] is r[5] else 'naive'} right")

    # feedback contrast: CS abstains but naive-shortest commits
    fb = [r for r in rows if not det(r[2]) and det(r[3])]
    fb_cor = sum(1 for r in fb if r[3] is r[5])
    print("-" * 72)
    print(f"FEEDBACK contrast — CS abstains (?) but naive-shortest commits: {len(fb)} pairs")
    print(f"   naive-shortest accuracy on these: {fb_cor}/{len(fb)} = "
          f"{fb_cor/len(fb):.1%}  (≈chance ⇒ naive guesses inside feedback loops)")
    OUT_JSON.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "pairs": len(rows),
                "methods": scores,
                "disagreement": {
                    "pairs": len(dis),
                    "physiomap_correct": cs_right,
                    "naive_shortest_correct": nv_right,
                },
                "feedback_contrast": {
                    "pairs": len(fb),
                    "naive_shortest_correct": fb_cor,
                    "naive_shortest_accuracy": fb_cor / len(fb) if fb else None,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    feedback_accuracy = fb_cor / len(fb) if fb else None
    feedback_text = (
        f"{feedback_accuracy:.1%}" if feedback_accuracy is not None else "not applicable"
    )
    method_rows = "\n".join(
        f"| {name} | {record['determinate']} | {record['correct']} | "
        f"{record['wrong']} | {record['abstain']} | {record['precision']:.1%} |"
        for name, record in scores.items()
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# E2 — feedback-aware and path-based forward prediction",
                "",
                "Generated by `scripts/e2_baseline.py`; do not edit.",
                "",
                f"Evaluation contains **{len(rows)}** gene–phenotype pairs.",
                "",
                "| method | determinate | correct | wrong | abstain | precision |",
                "|---|--:|--:|--:|--:|--:|",
                method_rows,
                "",
                "## Feedback-sensitive contrast",
                "",
                f"PhysioMap abstained while shortest-path propagation committed on "
                f"**{len(fb)}** pairs. The shortest-path prediction agreed with HPOA on "
                f"**{fb_cor}/{len(fb)} ({feedback_text})** of these pairs.",
                "",
                f"When both methods were determinate, they disagreed on **{len(dis)}** pairs "
                f"(PhysioMap correct: {cs_right}; shortest path correct: {nv_right}).",
                "",
                "This comparison reports selectivity and directional agreement against the "
                "external HPOA reference; it does not establish that every abstention is "
                "mathematically necessary.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
