#!/usr/bin/env python3
"""E4b - comparators for the inverse (abductive) lesion-ranking task.

E4 ranks candidate lesions by matching each candidate's *comparative-static* prediction against
an observed directional profile. This script holds the abductive scoring fixed and swaps the
inference rule that produces each candidate's predicted profile, which is the inverse-task
analogue of the forward comparison in E2:

  * comparative static   -- the released solver (same numbers as E4),
  * shortest signed path -- sign product along an unweighted shortest directed path from the
                            candidate lesion to each observed trait,
  * signed diffusion     -- sign of the damped signed random walk, alpha as given,
  * chance               -- analytic expectation for a uniformly random ranking of the pool,
                            reported so the informative range of the metrics is visible.

Scoring, tie handling, and the metric definitions are identical to E4 in every arm, so the
arms differ only in how a candidate's predicted profile is produced.

Usage: uv run --extra analysis python scripts/e4b_diagnosis_baselines.py
Writes: benchmarks/results/e4b_diagnosis_baselines.{md,json}
        paper/generated/diagnosis-baselines.tex  (when a paper checkout is linked)
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import median

import networkx as nx
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from physiomap_core.trace import combined_do_graph
from scripts.e1b_eval import build_observations

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "benchmarks/results/e4b_diagnosis_baselines.md"
OUT_JSON = ROOT / "benchmarks/results/e4b_diagnosis_baselines.json"
OUT_TEX = ROOT / "paper/generated/diagnosis-baselines.tex"
ALPHA = 0.85
EPS = 1e-9


def shortest_profile(graph: nx.DiGraph, node: str, sign: Sign,
                     targets: set[str]) -> dict[str, str]:
    """Sign product along a shortest directed path from the lesion to each target."""
    out: dict[str, str] = {}
    if not graph.has_node(node):
        return out
    for target in targets:
        if target == node or not graph.has_node(target) or not nx.has_path(graph, node, target):
            continue
        path = nx.shortest_path(graph, node, target)
        value = sign
        for a, b in zip(path, path[1:]):
            value = value * Sign(graph.edges[a, b]["sign"])
        if value.value in ("+", "-"):
            out[target] = value.value
    return out


def diffusion_profile(graph: nx.DiGraph, node: str, sign: Sign,
                      targets: set[str], alpha: float = ALPHA) -> dict[str, str]:
    """Sign of the damped signed random walk seeded at the lesion."""
    if not graph.has_node(node):
        return {}
    reach = {node} | nx.descendants(graph, node)
    nodes = sorted(reach)
    index = {n: i for i, n in enumerate(nodes)}
    rows, cols, vals = [], [], []
    for u in nodes:
        outs = [(v, graph.edges[u, v]["sign"]) for v in graph.successors(u) if v in index]
        if not outs:
            continue
        weight = 1.0 / len(outs)
        for v, s in outs:
            rows.append(index[v])
            cols.append(index[u])
            vals.append((1.0 if s == "+" else -1.0) * weight)
    matrix = sp.csr_matrix((vals, (rows, cols)), shape=(len(nodes), len(nodes)))
    seed = np.zeros(len(nodes))
    seed[index[node]] = 1.0 if sign is Sign.PLUS else -1.0
    result = spla.spsolve((sp.eye(len(nodes), format="csr") - alpha * matrix).tocsc(),
                          (1.0 - alpha) * seed)
    out: dict[str, str] = {}
    for target in targets:
        if target in index and target != node:
            value = result[index[target]]
            if abs(value) > EPS:
                out[target] = "+" if value > 0 else "-"
    return out


def rank_metrics(pool: list[tuple[str, str]], profiles: dict[tuple[str, str], dict[str, str]],
                 obs: dict) -> dict[str, float]:
    """E4's scoring and tie handling, applied to whichever profiles were supplied."""
    def score(candidate: tuple[str, str], observed: dict[str, str]) -> tuple[int, int]:
        predicted = profiles.get(candidate, {})
        agree = contra = 0
        for node, direction in observed.items():
            got = predicted.get(node)
            if got is None:
                continue
            if got == direction:
                agree += 1
            else:
                contra += 1
        return agree, contra

    ranks: list[int] = []
    top1 = top3 = top10 = scored = 0
    for rec in obs.values():
        primary = rec["primary"]
        if len(primary) != 1:
            continue
        (true_node, true_sign), = primary.items()
        if (true_node, true_sign) not in profiles:
            continue
        observed = {k: v for k, v in rec["observed"].items() if k != true_node}
        if not observed:
            continue
        ordered = []
        for candidate in pool:
            agree, contra = score(candidate, observed)
            ordered.append((candidate, agree - contra, -contra, agree))
        true = next(c for c in ordered if c[0] == (true_node, true_sign))
        key = (true[1], true[2], true[3])
        better = sum(1 for c in ordered if (c[1], c[2], c[3]) > key)
        equal = sum(1 for c in ordered if (c[1], c[2], c[3]) == key and c[0] != (true_node, true_sign))
        rank = 1 + better
        scored += 1
        ranks.append(rank)
        top1 += int(better == 0 and equal == 0)
        top3 += int(rank <= 3)
        top10 += int(rank <= 10)
    return {
        "scored": scored, "top1": top1, "top3": top3, "top10": top10,
        "mrr": sum(1.0 / r for r in ranks) / len(ranks) if ranks else 0.0,
        "median_rank": median(ranks) if ranks else 0.0,
    }


def chance_metrics(pool_size: int, scored: int) -> dict[str, float]:
    """Uniformly random ranking of the pool: expectations, not a simulation."""
    harmonic = sum(1.0 / k for k in range(1, pool_size + 1))
    return {
        "scored": scored,
        "top1": scored * 1.0 / pool_size,
        "top3": scored * min(3, pool_size) / pool_size,
        "top10": scored * min(10, pool_size) / pool_size,
        "mrr": harmonic / pool_size,
        "median_rank": (pool_size + 1) / 2,
    }


def main() -> int:
    release, obs = build_observations()
    pmap = build_map()

    pool_set: set[tuple[str, str]] = set()
    for rec in obs.values():
        primary = rec["primary"]
        if len(primary) == 1:
            (node, sign), = primary.items()
            pool_set.add((node, sign))
    pool = sorted(pool_set)
    observed_traits = {t for rec in obs.values() for t in rec["observed"]}
    print(f"pool={len(pool)} lesions; {len(observed_traits)} observed traits; release {release}")

    comparative: dict[tuple[str, str], dict[str, str]] = {}
    shortest: dict[tuple[str, str], dict[str, str]] = {}
    diffusion: dict[tuple[str, str], dict[str, str]] = {}
    for node, sign in pool:
        clamp = {node: Sign(sign)}
        predicted = solve_multiscale(pmap, Intervention(targets=clamp, label=node)).predicted
        comparative[(node, sign)] = {k: v.value for k, v in predicted.items()
                                     if v.value in ("+", "-")}
        graph = combined_do_graph(pmap, clamp)
        shortest[(node, sign)] = shortest_profile(graph, node, Sign(sign), observed_traits)
        diffusion[(node, sign)] = diffusion_profile(graph, node, Sign(sign), observed_traits)
    print("precomputed candidate profiles for all three inference rules")

    arms = {
        "comparative static": rank_metrics(pool, comparative, obs),
        "shortest signed path": rank_metrics(pool, shortest, obs),
        f"signed diffusion (alpha={ALPHA})": rank_metrics(pool, diffusion, obs),
    }
    arms["chance"] = chance_metrics(len(pool), arms["comparative static"]["scored"])

    lines = ["# E4b - inverse-task comparators", "",
             f"External reference: HPOA `{release}`. Closed pool of {len(pool)} single-lesion "
             "hypotheses; the true lesion is always present. Scoring, tie handling, and metrics "
             "are identical across arms; only the rule producing each candidate's predicted "
             "profile differs.", "",
             "| inference rule | unique top-1 | top-3 | top-10 | MRR | median rank |",
             "|---|---:|---:|---:|---:|---:|"]
    for name, m in arms.items():
        scored = m["scored"]
        lines.append(
            f"| {name} | {m['top1']:.0f}/{scored} | {m['top3']:.0f}/{scored} | "
            f"{m['top10']:.0f}/{scored} | {m['mrr']:.3f} | {m['median_rank']:.0f} |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps(
        {"schema_version": "1.0.0", "hpo_release": release, "candidate_pool": len(pool),
         "alpha": ALPHA, "arms": arms}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    tex = ["% Generated by scripts/e4b_diagnosis_baselines.py; do not edit.",
           "\\begin{tabular}{lrrrr}", "\\toprule",
           "inference rule & unique top-1 & top-3 & top-10 & MRR\\\\", "\\midrule"]
    label = {"comparative static": "PhysioMap comparative static",
             "shortest signed path": "shortest signed path",
             f"signed diffusion (alpha={ALPHA})": "signed diffusion",
             "chance": "chance"}
    for name, m in arms.items():
        scored = m["scored"]
        tex.append(f"{label[name]} & {m['top1']:.0f} & {m['top3']:.0f} & {m['top10']:.0f} & "
                   f"{m['mrr']:.3f}\\\\")
    tex += ["\\bottomrule", "\\end{tabular}"]
    paper_outputs = (ROOT / "paper").is_dir()
    if paper_outputs:
        OUT_TEX.write_text("\n".join(tex) + "\n", encoding="utf-8")

    for name, m in arms.items():
        print(f"  {name:34s} top1={m['top1']:6.1f} top3={m['top3']:6.1f} "
              f"top10={m['top10']:6.1f} MRR={m['mrr']:.3f}")
    outputs = [OUT_MD.name, OUT_JSON.name]
    if paper_outputs:
        outputs.append(OUT_TEX.name)
    print(f"wrote {', '.join(outputs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
