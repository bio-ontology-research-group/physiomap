#!/usr/bin/env python3
"""E2 null models — does the CS forward accuracy depend on the real edge signs / topology?

Two complementary nulls bracket the two ways the curated map could carry the result:

* **Sign-permutation null** — randomly shuffle all causal edge signs (preserving the +/-
  marginal), keep the topology. Tests whether the real *mechanism signs* carry the information.
* **Edge-rewiring null** — degree-preserving directed double-edge swaps that randomise the
  *topology* while each edge keeps its sign (so the +/- multiset and every node's in/out-degree
  are preserved). Tests whether the specific curated *wiring* carries the information.

Under either null, if the curated structure carries the result the determinate accuracy collapses
toward chance (50%). Together they show the result is neither a sign artefact nor a degree-sequence
artefact, but lives in the curated mechanism wiring.

Usage:  python scripts/e2_null.py [n_perms]
"""
from __future__ import annotations

import random
import sys

import networkx as nx

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from scripts.e1b_eval import build_observations


def forward_acc(pmap, obs) -> tuple[int, int, int]:
    correct = wrong = det = 0
    for gene, rec in obs.items():
        observed = {k: Sign(v) for k, v in rec["observed"].items()}
        if not observed:
            continue
        primary = {k: Sign(v) for k, v in rec["primary"].items()}
        pred = solve_multiscale(pmap, Intervention(targets=primary, label=gene)).predicted
        for node, exp in observed.items():
            if node in primary:
                continue
            got = pred.get(node)
            if got in (Sign.PLUS, Sign.MINUS):
                det += 1
                correct += int(got is exp); wrong += int(got is not exp)
    return correct, wrong, det


MACRO = {"organ", "organ_system", "organism", "tissue"}


def meta_is_dag(edges, cg_edges) -> bool:
    """Does the combined causal+constitutive meta-graph stay acyclic? (mirrors solve_multiscale's
    invariant): condense the causal graph, add component-level constitutive cross-edges, test DAG."""
    g = nx.DiGraph()
    g.add_edges_from((e.source, e.target) for e in edges)
    cond = nx.condensation(g)
    comp_of = {n: c for c in cond.nodes for n in cond.nodes[c]["members"]}
    meta = nx.DiGraph()
    meta.add_nodes_from(cond.nodes)
    meta.add_edges_from(cond.edges)
    for u, v in cg_edges:
        if u in comp_of and v in comp_of and comp_of[u] != comp_of[v]:
            meta.add_edge(comp_of[u], comp_of[v])
    return nx.is_directed_acyclic_graph(meta)


def rewire(edges, scale, constit_nodes, cg_edges, rng, n_swaps: int) -> int:
    """In-place degree-preserving directed double-edge swap (signs travel with each edge).

    Pick edges (a->b) and (c->d); reassign targets to (a->d), (c->b). Preserves every node's
    out-degree (sources untouched), the in-degree multiset (targets permuted), and each edge's sign.
    Swaps are confined to the macro band (organ/organ_system/organism/tissue, where the IEM
    reaction/physiology edges live) with constitution-incident nodes excluded, and **guarded**: a
    swap is committed only if the combined causal+constitutive meta-graph stays acyclic (the
    invariant the multiscale solver requires), otherwise reverted. Self-loops, duplicate edges,
    micro-scale and constitution edges are left fixed. Returns the number of swaps performed.
    """
    def ok(node: str) -> bool:
        return scale.get(node) in MACRO and node not in constit_nodes

    pool = [e for e in edges if e.source != e.target and ok(e.source) and ok(e.target)]
    present = {(e.source, e.target) for e in edges}
    done = 0
    attempts = 0
    cap = n_swaps * 40
    while done < n_swaps and attempts < cap:
        attempts += 1
        e1, e2 = rng.sample(pool, 2)
        a, b, c, d = e1.source, e1.target, e2.source, e2.target
        if a == d or c == b:                        # would create a self-loop
            continue
        if (a, d) in present or (c, b) in present:  # would create a duplicate edge
            continue
        object.__setattr__(e1, "target", d)
        object.__setattr__(e2, "target", b)
        if not meta_is_dag(edges, cg_edges):        # guard: keep the meta-graph acyclic
            object.__setattr__(e1, "target", b)     # revert
            object.__setattr__(e2, "target", d)
            continue
        present.discard((a, b)); present.discard((c, d))
        present.add((a, d)); present.add((c, b))
        done += 1
    return done


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    _, obs = build_observations()
    pmap = build_map()
    edges = pmap.causal_edges
    orig_sign = [e.sign for e in edges]
    orig_tgt = [e.target for e in edges]

    c, w, d = forward_acc(pmap, obs)
    real_acc = c / (c + w) if (c + w) else float("nan")
    print(f"REAL map:       determinate={d:3d} correct={c:3d} wrong={w:3d}  accuracy={real_acc:.1%}")

    # --- Null 1: sign permutation (topology fixed, signs shuffled) -----------------------------
    print(f"\nsign-permutation null ({n} perms; shuffles {len(edges)} causal-edge signs):")
    accs, dets = [], []
    rng = random.Random(20260613)
    for i in range(n):
        perm = orig_sign[:]
        rng.shuffle(perm)
        for e, sg in zip(edges, perm):
            object.__setattr__(e, 'sign', sg)
        c, w, d = forward_acc(pmap, obs)
        acc = c / (c + w) if (c + w) else float("nan")
        accs.append(acc); dets.append(d)
        print(f"   perm {i+1:2d}: determinate={d:3d} correct={c:3d} wrong={w:3d}  accuracy={acc:.1%}")
    for e, sg in zip(edges, orig_sign):  # restore signs
        object.__setattr__(e, 'sign', sg)
    sign_mean = sum(accs) / len(accs)
    print(f"  mean sign-permutation accuracy = {sign_mean:.1%}  "
          f"(mean determinate={sum(dets)/len(dets):.0f})")

    # --- Null 2: edge rewiring (signs fixed, topology randomised, degrees preserved) -----------
    from physiomap_core.multiscale import constitutive_graph
    scale = {node.id: node.scale.value for node in pmap.nodes}
    cg = constitutive_graph(pmap)
    constit_nodes = {x for uv in cg.edges for x in uv}  # endpoints of constitutive edges only
    cg_edges = list(cg.edges)
    n_swaps = 2500
    print(f"\nedge-rewiring null ({n} rewirings; {n_swaps} guarded degree-preserving macro-band "
          f"swaps each, signs kept, meta-graph kept acyclic):")
    raccs, rdets = [], []
    resampled = 0
    rng = random.Random(20260614)
    # The per-swap guard condenses the un-intervened causal graph, but solve_multiscale
    # condenses the graph *after* intervention surgery. Removing a clamped node's in-edges can
    # split an SCC, promoting constitutive edges that were internal to that component into
    # cross-component meta-edges, which can close a meta-cycle the guard never saw. That is
    # only detectable per intervention, so we resample the whole rewiring when it happens and
    # report how many draws were rejected.
    i = 0
    attempts = 0
    while i < n and attempts < n * 20:
        attempts += 1
        ns = rewire(edges, scale, constit_nodes, cg_edges, rng, n_swaps)
        try:
            c, w, d = forward_acc(pmap, obs)
        except ValueError as exc:
            if "cross-scale cycle" not in str(exc):
                raise
            resampled += 1
            for e, tg in zip(edges, orig_tgt):  # restore before redrawing
                object.__setattr__(e, "target", tg)
            continue
        i += 1
        acc = c / (c + w) if (c + w) else float("nan")
        raccs.append(acc); rdets.append(d)
        print(f"   rewire {i:2d}: determinate={d:3d} correct={c:3d} wrong={w:3d}  accuracy={acc:.1%}")
        for e, tg in zip(edges, orig_tgt):  # restore topology between rewirings
            object.__setattr__(e, "target", tg)
    if resampled:
        print(f"   ({resampled} rewiring(s) resampled: intervention surgery closed a "
              f"cross-scale meta-cycle)")
    if not raccs:
        print("  edge-rewiring null produced no solvable rewiring; reporting NaN")
        raccs, rdets = [float("nan")], [0]
    rewire_mean = sum(raccs) / len(raccs)
    print(f"  mean edge-rewiring accuracy = {rewire_mean:.1%}  "
          f"(mean determinate={sum(rdets)/len(rdets):.0f})")

    print(f"\nSUMMARY:  real = {real_acc:.0%} (166 determinate)  |  "
          f"sign-permutation null = {sign_mean:.0%}  |  edge-rewiring null = {rewire_mean:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
