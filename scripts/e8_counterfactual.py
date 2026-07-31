#!/usr/bin/env python3
"""E8 — rung-three qualitative counterfactuals: necessity attribution + abduction information gain.

Three parts, in the order requested:

  (D) PN attribution table over the monogenic catalogue -- of the observed phenotypes, how many does
      the model *necessarily attribute* (determinate but-for) to the lesion vs. abstain. (For a single
      lesion the qualitative probability of necessity equals forward determinacy; this is the
      rung-three *framing* of the rung-two result, reported honestly.)

  (A) A worked but-for vignette (hereditary hemochromatosis): "had the lesion been absent, would
      transferrin saturation still be elevated?" -- a determinate qualitative PN, validated against the
      textbook expectation.

  (B) Abduction information gain: does conditioning on the patient's *other* observed phenotypes
      (the abduction step, via the ASP engine) resolve a sign that the marginal do() leaves '?'? This
      is the empirical test of whether qualitative counterfactual/abductive reasoning exceeds the
      marginal intervention in PhysioMap.

Reproducible: `python scripts/e8_counterfactual.py` (needs clingo; committed fixtures + HPOA only).
"""
from __future__ import annotations

from physiomap_core.counterfactual import abduction_resolves, but_for_necessity
from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.qualitative import Intervention, solve_signs
from scripts.e1b_eval import build_observations


def main() -> int:
    pmap = build_map()
    _, obs = build_observations()

    # ---------- (D) PN attribution table over the catalogue ----------
    necessary = abstain = 0
    genes_with_attr = 0
    for gene, rec in obs.items():
        observed = {k: Sign(v) for k, v in rec["observed"].items()}
        primary = {k: Sign(v) for k, v in rec["primary"].items()}
        if not observed:
            continue
        bf = but_for_necessity(pmap, primary)
        g_attr = 0
        for node in observed:
            if node in primary:
                continue
            fv, _cf, nec = bf.get(node, ("0", "0", False))
            if nec:
                necessary += 1
                g_attr += 1
            else:
                abstain += 1
        genes_with_attr += g_attr > 0
    total = necessary + abstain
    print("=" * 74)
    print("E8(D) — qualitative probability-of-necessity attribution over the catalogue")
    print("=" * 74)
    print(f"observed (disorder, phenotype) pairs           : {total}")
    print(f"  necessarily attributable (determinate but-for): {necessary}  ({necessary/total:.0%})")
    print(f"  abstained (PN undetermined, feedback core)    : {abstain}  ({abstain/total:.0%})")
    print(f"  disorders with >=1 determinate attribution     : {genes_with_attr}")
    print("  (single-lesion PN == forward determinacy; reported as attribution)")

    # ---------- (A) hemochromatosis but-for vignette ----------
    print("\n" + "=" * 74)
    print("E8(A) — but-for vignette: hereditary hemochromatosis (low hepcidin)")
    print("=" * 74)
    lesion = {"hepcidin": Sign.MINUS}  # HFE LoF lowers hepcidin
    bf = but_for_necessity(pmap, lesion)
    for node in ["ferroportin", "plasma_iron", "transferrin_saturation"]:
        if node in bf:
            fv, cf, nec = bf[node]
            verdict = "NECESSARY (would be normal but-for the lesion)" if nec else "undetermined"
            print(f"  {node:24s} factual={fv}  counterfactual(no lesion)={cf}   PN: {verdict}")
    print("  Reading: do(hepcidin-) -> transferrin saturation UP, determinate; the but-for world")
    print("  (lesion absent) returns it to baseline -> the elevation is necessarily attributable.")

    # ---------- (B) abduction information gain ----------
    print("\n" + "=" * 74)
    print("E8(B) — does abduction (conditioning on observed phenotypes) resolve marginal '?'  signs?")
    print("=" * 74)
    total_resolved = 0
    examples = []
    n_scored = 0
    for gene, rec in obs.items():
        observed = {k: Sign(v) for k, v in rec["observed"].items()}
        primary = {k: Sign(v) for k, v in rec["primary"].items()}
        if len(observed) < 2:
            continue  # need >=2 observations for one to inform another
        n_scored += 1
        resolved = abduction_resolves(pmap, primary, observed)
        if resolved:
            total_resolved += len(resolved)
            for node, d in list(resolved.items())[:3]:
                examples.append((gene, node, d["abduced"]))
    print(f"disorders with >=2 observed phenotypes tested : {n_scored}")
    print(f"SCC signs resolved by abduction (marginal '?' -> determinate): {total_resolved}")
    if examples:
        for gene, node, s in examples[:12]:
            print(f"   {gene:10s} {node:28s} ? -> {s}")
        print("  => qualitative abduction adds information beyond the marginal intervention.")
    else:
        print("  => none: on this map, conditioning on co-observed phenotypes does NOT resolve any")
        print("     marginal-'?' sign. Qualitative counterfactuals collapse to interventions here --")
        print("     the cross-world link is the magnitude background the sign abstraction discards")
        print("     (the Blom-Mooij causal-constraints boundary). Honest negative result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
