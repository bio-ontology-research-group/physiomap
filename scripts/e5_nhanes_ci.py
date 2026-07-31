#!/usr/bin/env python3
"""E5 (stretch) — population conditional-independence validation on NHANES.

PhysioMap implies a set of (conditional) independences via **σ-separation** (acyclification +
d-separation, determinism-aware). NHANES 2017-2018 gives population lab/vital measurements; we map
~20 analytes to PhysioMap nodes, compute the empirical partial-correlation structure, and ask whether
σ-separation predicts which analyte pairs are conditionally (in)dependent in the data.

The discriminating prediction: a pair the model says is **σ-separated given Z** should show a
**near-zero partial correlation** given Z; a σ-connected pair may correlate. Inside the whole-body
homeostatic SCC σ-separation says *connected* (the SCC is a bidirected clique under acyclification),
so the model-implied independences come from (a) distinct subsystems and (b) the deterministic closure
of definitional identities. We score how well σ-separation separates the conditionally-independent from
the conditionally-dependent pairs (AUC + a 2x2 at a Fisher-z significance threshold), against the
trivial "everything dependent" baseline.

Reproducible: `scripts/e5_nhanes_ci.py`. Data: NHANES 2017-2018 public XPT (CDC), not redistributed.
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from physiomap_core.sigma import sigma_separated
from physiomap_core.hpo import build_map

ROOT = Path(__file__).resolve().parent.parent
NH = ROOT / "benchmarks/.imports/nhanes"
OUT_MD = ROOT / "benchmarks/results/e5_nhanes.md"

# NHANES variable -> (PhysioMap node, file). Conventional-unit columns.
VARMAP = {
    "LBXSGL":  ("plasma_glucose", "BIOPRO_J"),
    "LBXSNASI": ("plasma_sodium_concentration", "BIOPRO_J"),
    "LBXSKSI": ("plasma_potassium", "BIOPRO_J"),
    "LBXSCLSI": ("plasma_chloride", "BIOPRO_J"),
    "LBXSCA":  ("plasma_calcium", "BIOPRO_J"),
    "LBXSPH":  ("plasma_phosphate", "BIOPRO_J"),
    "LBXSCR":  ("plasma_creatinine", "BIOPRO_J"),
    "LBXSBU":  ("blood_urea_nitrogen", "BIOPRO_J"),
    "LBXSUA":  ("plasma_urate", "BIOPRO_J"),
    "LBXSC3SI": ("plasma_bicarbonate", "BIOPRO_J"),
    "LBXSATSI": ("plasma_transaminases", "BIOPRO_J"),
    "LBXSAL":  ("plasma_albumin", "BIOPRO_J"),
    "LBXSCK":  ("plasma_creatine_kinase", "BIOPRO_J"),
    "LBXSIR":  ("plasma_iron", "BIOPRO_J"),
    "LBXHGB":  ("blood_hemoglobin_concentration", "CBC_J"),
    "LBXHCT":  ("hematocrit", "CBC_J"),
    "LBXPLTSI": ("platelet_count", "CBC_J"),
    "LBDLDL":  ("ldl_cholesterol", "TRIGLY_J"),
    "LBXTR":   ("plasma_triglycerides", "TRIGLY_J"),
    "LBDHDD":  ("hdl_cholesterol", "HDL_J"),
    "LBXTC":   ("plasma_total_cholesterol", "TCHOL_J"),
    "LBXHSCRP": ("c_reactive_protein", "HSCRP_J"),
    "LBDPCT":  ("transferrin_saturation", "FETIB_J"),
}


def load() -> pd.DataFrame:
    files = sorted({f for _, f in VARMAP.values()})
    df = pd.read_sas(NH / "DEMO_J.xpt")[["SEQN", "RIDAGEYR"]]
    for f in files:
        cols = ["SEQN"] + [v for v, (_, ff) in VARMAP.items() if ff == f]
        d = pd.read_sas(NH / f"{f}.xpt")[cols]
        df = df.merge(d, on="SEQN", how="outer")
    # MAP from BP (mean arterial pressure = DBP + (SBP-DBP)/3)
    bp = pd.read_sas(NH / "BPX_J.xpt")[["SEQN", "BPXSY1", "BPXDI1"]]
    bp = bp[(bp.BPXDI1 > 0)]
    bp["MAP"] = bp.BPXDI1 + (bp.BPXSY1 - bp.BPXDI1) / 3.0
    df = df.merge(bp[["SEQN", "MAP"]], on="SEQN", how="outer")
    df = df[df.RIDAGEYR >= 18]
    return df


def rename_to_nodes(df: pd.DataFrame) -> pd.DataFrame:
    ren = {v: node for v, (node, _) in VARMAP.items()}
    ren["MAP"] = "mean_arterial_pressure"
    return df.rename(columns=ren)


def partial_corr_matrix(data: np.ndarray) -> np.ndarray:
    """Full partial-correlation matrix from the precision (inverse covariance) matrix."""
    cov = np.cov(data, rowvar=False)
    prec = np.linalg.pinv(cov)
    d = np.sqrt(np.diag(prec))
    pc = -prec / np.outer(d, d)
    np.fill_diagonal(pc, 1.0)
    return pc


def fisher_p(r: float, n: int, k: int) -> float:
    """Two-sided p-value for zero partial correlation (Fisher z), k = conditioning size."""
    from scipy.stats import norm

    r = max(min(r, 0.999999), -0.999999)
    z = 0.5 * np.log((1 + r) / (1 - r))
    se = 1.0 / np.sqrt(max(n - k - 3, 1))
    return float(2 * (1 - norm.cdf(abs(z / se))))


def main() -> int:
    df = rename_to_nodes(load())
    nodes = [n for n in df.columns if n not in ("SEQN", "RIDAGEYR")]
    pmap = build_map()
    pm_nodes = {n.id for n in pmap.nodes}
    nodes = [n for n in nodes if n in pm_nodes]
    print(f"mapped analytes present in PhysioMap: {len(nodes)}")

    sub = df[nodes].apply(pd.to_numeric, errors="coerce").dropna()
    n = len(sub)
    print(f"complete-case adults: n={n}")
    X = sub.values.astype(float)
    pc = partial_corr_matrix(X)
    k = len(nodes) - 2  # conditioning-set size for full partial correlation

    # undirected causal-graph distance between analytes (edges either direction)
    import networkx as nx

    g = pmap.causal_subgraph()
    ug = g.to_undirected()
    dist = dict(nx.all_pairs_shortest_path_length(ug))

    idx = {node: i for i, node in enumerate(nodes)}
    rows = []
    for a, b in combinations(nodes, 2):
        rest = [x for x in nodes if x not in (a, b)]
        sep = sigma_separated(pmap, {a}, {b}, set(rest))
        r = pc[idx[a], idx[b]]
        p = fisher_p(r, n, k)
        d = dist.get(a, {}).get(b, 99)
        rows.append((a, b, sep, abs(r), p, d))

    # data conditional-independence at Bonferroni-corrected alpha
    m = len(rows)
    alpha = 0.05 / m
    indep_data = [r for r in rows if r[4] > alpha]   # fail to reject -> conditionally independent
    dep_data = [r for r in rows if r[4] <= alpha]
    sep_model = [r for r in rows if r[2]]
    con_model = [r for r in rows if not r[2]]
    print("=" * 70)
    print(f"E5 NHANES conditional-independence vs sigma-separation (n={n}, {m} pairs, "
          f"Bonferroni alpha={alpha:.2e})")
    print(f"  model: sigma-separated given rest = {len(sep_model)}, sigma-connected = {len(con_model)}")
    print(f"  data : conditionally independent = {len(indep_data)}, dependent = {len(dep_data)}")

    # 2x2: does sigma-separation predict data conditional independence?
    tp = sum(1 for r in rows if r[2] and r[4] > alpha)      # sep & indep
    fp = sum(1 for r in rows if r[2] and r[4] <= alpha)     # sep but dep (model wrong-ish)
    fn = sum(1 for r in rows if not r[2] and r[4] > alpha)  # connected but indep
    tn = sum(1 for r in rows if not r[2] and r[4] <= alpha) # connected & dep
    print(f"  sigma-sep & data-independent (TP)  = {tp}")
    print(f"  sigma-sep & data-dependent   (FP)  = {fp}")
    print(f"  sigma-con & data-independent (FN)  = {fn}")
    print(f"  sigma-con & data-dependent   (TN)  = {tn}")
    if sep_model:
        print(f"  -> of model-implied conditional INDEPENDENCES, "
              f"{tp}/{len(sep_model)} = {tp/len(sep_model):.0%} corroborated (partial r ~ 0)")
    # mean |partial r| in each model class (the cleanest signal)
    mr_sep = np.mean([r[3] for r in sep_model]) if sep_model else float("nan")
    mr_con = np.mean([r[3] for r in con_model]) if con_model else float("nan")
    print(f"  mean |partial r|: sigma-separated pairs = {mr_sep:.3f}  vs  "
          f"sigma-connected pairs = {mr_con:.3f}")

    from scipy.stats import mannwhitneyu

    # The informative test: does CAUSAL GRAPH PROXIMITY predict conditional dependence?
    # (sigma-sep-given-all is uninformative inside the one giant SCC; local structure is not.)
    print("-" * 70)
    print("  Does causal-graph distance predict NHANES conditional dependence?")
    near = [r for r in rows if r[5] <= 2]    # directly or 1-intermediate causally linked
    far = [r for r in rows if r[5] > 2]
    for label, grp in [("graph-distance<=2", near), ("graph-distance>2", far)]:
        if grp:
            frac_dep = sum(1 for r in grp if r[4] <= alpha) / len(grp)
            mean_r = np.mean([r[3] for r in grp])
            print(f"    {label:20s}: {len(grp):3d} pairs, {frac_dep:.0%} conditionally dependent, "
                  f"mean |partial r|={mean_r:.3f}")
    # AUC: does graph proximity (-distance) rank data-dependent pairs above independent ones?
    dep_d = [r[5] for r in rows if r[4] <= alpha]
    ind_d = [r[5] for r in rows if r[4] > alpha]
    if dep_d and ind_d:
        u, _ = mannwhitneyu(ind_d, dep_d, alternative="greater")  # independent pairs farther?
        auc = u / (len(dep_d) * len(ind_d))
        print(f"    AUC(graph proximity predicts conditional dependence) = {auc:.3f}")
    print("\n  strongest NHANES partial correlations + their causal-graph distance:")
    for a, b, sep, r, p, d in sorted(rows, key=lambda x: -x[3])[:12]:
        print(f"    {a:28s} {b:28s} |r|={r:.3f} p={p:.1e} graph_dist={d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
