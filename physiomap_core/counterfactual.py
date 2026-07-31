"""Qualitative rung-three (counterfactual) reasoning on the sign-SCM.

A counterfactual is the abduction -> action -> prediction procedure (Pearl; Bareinboim et al.):
infer the background from the factual world, alter the antecedent in a submodel holding that
background fixed, and re-predict. We lift it to the sign algebra.

Two honest facts shape what is computable qualitatively:

1. **But-for necessity collapses to forward determinacy for a single lesion.** With one clamp
   ``do(L)``, the counterfactual world "had L been absent" is the baseline (all changes ``0``), so a
   phenotype ``Y`` is *necessarily attributable* to ``L`` iff its factual change is determinate. The
   qualitative *probability of necessity* PN(Y) is therefore ``1`` where the forward solve commits and
   undetermined where it abstains. This is the rung-three *framing* of the rung-two result -- honest,
   and the basis of the attribution table (Option D) and the worked but-for vignette (Option A).

2. **Abduction can add information beyond the marginal intervention (Option B).** Conditioning on the
   patient's *other* observed phenotypes filters the magnitude-realizations consistent with the sign
   pattern; via the ASP engine (integrity constraints, no surgery) this can resolve a sign the marginal
   ``do(L)`` query leaves ``?``. Whether it actually does in PhysioMap is an empirical question this
   module lets us answer -- and a genuine rung-one-over-rung-two information gain when it does.
"""

from __future__ import annotations

import networkx as nx

from physiomap_core.asp_solve import asp_scc_signs
from physiomap_core.model import PhysioMap, Sign
from physiomap_core.qualitative import (
    Intervention,
    _solve_singleton,
    solve_signs,
)

__all__ = ["but_for_necessity", "abduction_resolves"]


def but_for_necessity(
    pmap: PhysioMap, lesion: dict[str, Sign]
) -> dict[str, tuple[str, str, bool]]:
    """For each node reachable from a single lesion, return ``(factual, counterfactual, necessary)``.

    ``factual`` is the comparative-statics sign under ``do(lesion)``; ``counterfactual`` is the sign in
    the "had the lesion been absent" world (baseline, ``0``); ``necessary`` is the qualitative
    probability of necessity being determinate-1 (factual determinate and would be baseline without the
    lesion). For a single lesion the counterfactual world is the baseline, so ``necessary`` holds iff
    the factual sign is determinate.
    """
    fac = solve_signs(pmap, Intervention(targets=lesion)).predicted
    out: dict[str, tuple[str, str, bool]] = {}
    for node, s in fac.items():
        if node in lesion:
            continue
        fv = s.value
        out[node] = (fv, "0", fv in ("+", "-"))
    return out


def abduction_resolves(
    pmap: PhysioMap, lesion: dict[str, Sign], observed: dict[str, Sign]
) -> dict[str, dict]:
    """Test whether conditioning on observed phenotypes resolves signs the marginal do() abstains on.

    Re-solves the (largest reachable) feedback SCC under ``do(lesion)`` twice with the ASP engine:
    once marginally, once *conditioned* on the observed signs of the SCC's own members (the abduction
    step). Returns ``{node: {"marginal": s, "abduced": s}}`` only for SCC members whose sign changes
    from ``?`` (marginal) to a determinate ``+``/``-`` (abduced) -- i.e. resolved by abduction.
    """
    g = pmap.causal_subgraph()
    fixed = {t: s.value for t, s in lesion.items()}
    gi = g.copy()
    for t in fixed:
        gi.remove_edges_from([(p, t) for p in list(gi.predecessors(t))])
    reach: set[str] = set(fixed)
    for t in fixed:
        reach |= nx.descendants(gi, t)

    sign: dict[str, str] = dict(fixed)
    ambig: list[str] = []
    obs = {k: v.value for k, v in observed.items()}
    resolved: dict[str, dict] = {}
    cond = nx.condensation(gi)
    for comp in nx.topological_sort(cond):
        members: set[str] = set(cond.nodes[comp]["members"])
        if members.isdisjoint(reach):
            continue
        if len(members) == 1:
            (node,) = tuple(members)
            if node not in fixed:
                _solve_singleton(node, gi, sign, ambig)
        else:
            marginal = asp_scc_signs(members, gi, sign, fixed)
            obs_in = {n: obs[n] for n in members if n in obs and n not in fixed}
            abduced = asp_scc_signs(members, gi, sign, fixed, observed=obs_in)
            for n in members:
                m = marginal.get(n, "?")
                a = abduced.get(n, "?")
                if m == "?" and a in ("+", "-") and n not in obs_in and n not in fixed:
                    resolved[n] = {"marginal": "?", "abduced": a}
            # adopt marginal signs for downstream forcing (conservative)
            for n in members:
                sign[n] = marginal.get(n, "?") if n not in fixed else fixed[n]
    return resolved
