#!/usr/bin/env python3
"""E2b — a *stronger* baseline: signed diffusion / random-walk-with-restart (RWR).

The two naive baselines in E2 (shortest signed path, forward-path consensus) are path-product
propagators. A network-medicine reviewer will object that the field's actual workhorse for
"signed effect through a directed network" is diffusion / RWR (Cowen et al. 2017) and SPIA-style
perturbation-factor accumulation (Tarca et al. 2009). This script adds that stronger baseline on
the IDENTICAL signed causal graph and scores it on the SAME (gene, phenotype) pairs as E1b/E2.

Method (signed RWR). On the do-surgered causal graph, build the signed adjacency W (entries =
edge sign in {+1,-1}); column-normalize the magnitude so each source's out-mass is 1, carrying the
sign -> transition S. Seed e at the clamped node(s) with their imposed sign. Solve the closed form
    r = (1 - alpha) (I - alpha S)^{-1} e
and read sign(r_v) as the predicted direction (|r_v| <= eps -> abstain). This is the signed
analogue of Cowen's universal propagator and a damped surrogate for the comparative static
-(dF/dx)^{-1} (dF/dtheta): (I - alpha S)^{-1} = sum_n alpha^n S^n sums signed walks of all lengths
but uses a fixed scalar alpha instead of the per-node dissipation that makes dF/dx Hurwitz, and it
NEVER tests sign-solvability -- so inside a negative-feedback SCC it commits to the sign of whichever
walk-length dominates (typically the short forward path, the WRONG net sign) exactly where the
comparative-statics solver abstains.

Reproducible: `python scripts/e2b_diffusion_baseline.py`. No map mutation.
"""
from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from physiomap_core.trace import combined_do_graph
from scripts.e1b_eval import build_observations

ALPHA = 0.85
EPS = 1e-9


def signed_rwr(g, primary: dict[str, Sign], targets: set[str]) -> dict[str, Sign]:
    """Signed RWR sign per reachable target node (Sign.UNKNOWN if |r|<=EPS)."""
    import networkx as nx

    reach: set[str] = set(primary)
    for s in primary:
        if g.has_node(s):
            reach |= nx.descendants(g, s)
    reach &= set(g.nodes)
    if not reach:
        return {}
    nodes = sorted(reach)
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    # column-normalized signed transition S[v,u] = sign(u->v) / outdeg_mag(u)
    rows, cols, vals = [], [], []
    for u in nodes:
        outs = [(v, g.edges[u, v]["sign"]) for v in g.successors(u) if v in idx]
        if not outs:
            continue
        w = 1.0 / len(outs)
        for v, s in outs:
            rows.append(idx[v])
            cols.append(idx[u])
            vals.append((1.0 if s == "+" else -1.0) * w)
    S = sp.csr_matrix((vals, (rows, cols)), shape=(n, n))
    e = np.zeros(n)
    for s, sg in primary.items():
        if s in idx:
            e[idx[s]] = 1.0 if sg is Sign.PLUS else -1.0
    A = sp.eye(n, format="csr") - ALPHA * S
    r = spla.spsolve(A.tocsc(), (1.0 - ALPHA) * e)
    out: dict[str, Sign] = {}
    for t in targets:
        if t in idx:
            val = r[idx[t]]
            out[t] = Sign.PLUS if val > EPS else Sign.MINUS if val < -EPS else Sign.UNKNOWN
    return out


def det(s) -> bool:
    return s in (Sign.PLUS, Sign.MINUS)


def main() -> int:
    _, obs = build_observations()
    pmap = build_map()
    rows = []  # (gene, node, cs, diff, hpoa)
    for gene, rec in obs.items():
        observed = {k: Sign(v) for k, v in rec["observed"].items()}
        if not observed:
            continue
        primary = {k: Sign(v) for k, v in rec["primary"].items()}
        cs_pred = solve_multiscale(pmap, Intervention(targets=primary, label=gene)).predicted
        g = combined_do_graph(pmap, primary)
        tgts = {nde for nde in observed if nde not in primary}
        diff = signed_rwr(g, primary, tgts)
        for node in tgts:
            rows.append((gene, node, cs_pred.get(node), diff.get(node), observed[node]))

    def score(idx, name):
        cor = sum(1 for r in rows if det(r[idx]) and r[idx] is r[4])
        wro = sum(1 for r in rows if det(r[idx]) and r[idx] is not r[4])
        ab = sum(1 for r in rows if not det(r[idx]))
        acc = cor / (cor + wro) if (cor + wro) else float("nan")
        print(f"  {name:22s} determinate={cor + wro:3d} correct={cor:3d} wrong={wro:3d} "
              f"abstain={ab:3d}  precision={acc:.1%}")
        return cor, wro, ab

    print("=" * 76)
    print(f"E2b signed-diffusion (RWR, alpha={ALPHA}) — {len(rows)} (gene, node) pairs")
    print("=" * 76)
    score(2, "CS (PhysioMap)")
    score(3, "signed-diffusion RWR")

    # feedback contrast: CS abstains but diffusion commits
    fb = [r for r in rows if not det(r[2]) and det(r[3])]
    fb_cor = sum(1 for r in fb if r[3] is r[4])
    print("-" * 76)
    print(f"FEEDBACK contrast — CS abstains (?) but diffusion commits: {len(fb)} pairs")
    if fb:
        print(f"   diffusion accuracy on these: {fb_cor}/{len(fb)} = {fb_cor / len(fb):.1%} "
              f"(≈chance ⇒ diffusion guesses inside feedback loops)")
    # head-to-head where both determinate and differ
    dis = [r for r in rows if det(r[2]) and det(r[3]) and r[2] is not r[3]]
    cs_right = sum(1 for r in dis if r[2] is r[4])
    print(f"DISAGREEMENT (both determinate, differ): {len(dis)}  CS right: {cs_right}/{len(dis)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
