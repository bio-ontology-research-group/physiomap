#!/usr/bin/env python3
"""E2d - sweep the signed-diffusion damping alpha.

The diffusion comparator in E2b fixes alpha=0.85 (the conventional PageRank damping). That
constant is not identifiable from the map, so this script reruns the identical comparison over
alpha in [0.05, 0.99] and reports determinate/correct/wrong at each value, plus the number of
sign flips against the alpha=0.85 operating point. Used to show the comparison does not depend
on the constant. Reproducible: `uv run --extra analysis python scripts/e2d_diffusion_alpha_sweep.py`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from physiomap_core.trace import combined_do_graph
from scripts.e1b_eval import build_observations

EPS = 1e-9


def signed_rwr(g, primary, targets, alpha):
    import networkx as nx
    reach = set(primary)
    for s in primary:
        if g.has_node(s):
            reach |= nx.descendants(g, s)
    reach &= set(g.nodes)
    if not reach:
        return {}
    nodes = sorted(reach)
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    rows, cols, vals = [], [], []
    for u in nodes:
        outs = [(v, g.edges[u, v]["sign"]) for v in g.successors(u) if v in idx]
        if not outs:
            continue
        w = 1.0 / len(outs)
        for v, s in outs:
            rows.append(idx[v]); cols.append(idx[u])
            vals.append((1.0 if s == "+" else -1.0) * w)
    S = sp.csr_matrix((vals, (rows, cols)), shape=(n, n))
    e = np.zeros(n)
    for s, sg in primary.items():
        if s in idx:
            e[idx[s]] = 1.0 if sg is Sign.PLUS else -1.0
    A = sp.eye(n, format="csr") - alpha * S
    r = spla.spsolve(A.tocsc(), (1.0 - alpha) * e)
    out = {}
    for t in targets:
        if t in idx:
            val = r[idx[t]]
            out[t] = Sign.PLUS if val > EPS else Sign.MINUS if val < -EPS else Sign.UNKNOWN
    return out


def det(s):
    return s in (Sign.PLUS, Sign.MINUS)


def main():
    _, obs = build_observations()
    pmap = build_map()
    cases = []
    for gene, rec in obs.items():
        observed = {k: Sign(v) for k, v in rec["observed"].items()}
        if not observed:
            continue
        primary = {k: Sign(v) for k, v in rec["primary"].items()}
        cs = solve_multiscale(pmap, Intervention(targets=primary, label=gene)).predicted
        g = combined_do_graph(pmap, primary)
        tgts = {n for n in observed if n not in primary}
        cases.append((gene, primary, g, tgts, observed, cs))

    alphas = [0.05, 0.15, 0.30, 0.50, 0.70, 0.85, 0.95, 0.99]
    print(f"{'alpha':>6} {'determinate':>12} {'correct':>8} {'wrong':>6} {'precision':>10} "
          f"{'signflips_vs_0.85':>18}")
    ref = {}
    results = {}
    for a in alphas:
        rows = []
        for gene, primary, g, tgts, observed, cs in cases:
            d = signed_rwr(g, primary, tgts, a)
            for node in tgts:
                rows.append((gene, node, cs.get(node), d.get(node), observed[node]))
        cor = sum(1 for r in rows if det(r[3]) and r[3] is r[4])
        wro = sum(1 for r in rows if det(r[3]) and r[3] is not r[4])
        prec = cor / (cor + wro) if (cor + wro) else float("nan")
        cur = {(r[0], r[1]): r[3] for r in rows}
        if a == 0.85:
            ref = dict(cur)
        results[a] = (cor, wro, prec, cur)
    for a in alphas:
        cor, wro, prec, cur = results[a]
        flips = sum(1 for k in cur if ref.get(k) is not cur[k])
        print(f"{a:>6} {cor + wro:>12} {cor:>8} {wro:>6} {prec:>9.1%} {flips:>18}")
    print()
    print("PhysioMap comparative static, same pairs:")
    rows = []
    for gene, primary, g, tgts, observed, cs in cases:
        for node in tgts:
            rows.append((cs.get(node), observed[node]))
    cor = sum(1 for r in rows if det(r[0]) and r[0] is r[1])
    wro = sum(1 for r in rows if det(r[0]) and r[0] is not r[1])
    print(f"  determinate={cor + wro} correct={cor} wrong={wro} "
          f"precision={cor / (cor + wro):.1%}")


if __name__ == "__main__":
    raise SystemExit(main())
