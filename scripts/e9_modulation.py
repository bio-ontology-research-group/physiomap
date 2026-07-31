#!/usr/bin/env python3
"""E9 — the qualitative (sign-only) second-order layer of the multiplicative (gain) edges.

A multiplicative edge ``m scales (s -> t)`` is intrinsically a second-derivative object
(``d2 t / ds dm``). This experiment shows what is recoverable from **up/down alone** — no
magnitudes — and reports it with the usual calibrated abstention:

  (A) Interaction-sign census + independent validation. iota = mu . sigma (modulation sign x
      base-edge sign, curated in SEPARATE layers) vs the textbook interaction *direction*
      (amplify / dampen) in benchmarks/human/modulation_validation.yaml. A joint-consistency check.

  (B) Synergy / antagonism for joint interventions. For each gain edge, do(source UP, modulator UP)
      and read the qualitative super- vs sub-additivity verdict at the modulated target (the payoff
      of the multi-node knockout). Determinate where the additive target direction is determinate.

  (C) Sensitization coverage. Across the HPO monogenic-lesion panel, how many lesions determinately
      strengthen/weaken at least one coupling (a prediction class the additive graph cannot make).

Reproducible: `python scripts/e9_modulation.py` (committed fixtures only).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.modulation import (
    gain_changes,
    interaction_sign,
    synergies,
)
from physiomap_core.qualitative import Intervention, solve_signs
from scripts.e1b_eval import build_observations

ROOT = Path(__file__).resolve().parent.parent
VALID = ROOT / "benchmarks" / "human" / "modulation_validation.yaml"


def main() -> int:
    pmap = build_map()
    mods = pmap.modulation_edges

    # ---------- (A) interaction-sign census + validation ----------
    print("=" * 78)
    print("E9(A) — interaction sign iota = mu . sigma  (amplify + / dampen -)  vs textbook direction")
    print("=" * 78)
    gold = {}
    for row in (yaml.safe_load(VALID.read_text()) or {}).get("interactions", []):
        gold[(row["modulator"], row["edge_source"], row["edge_target"])] = row["expected"]
    determinate = correct = scored = 0
    for m in mods:
        iota = interaction_sign(pmap, m)
        iv = iota.value if iota in (Sign.PLUS, Sign.MINUS) else "?"
        if iv in ("+", "-"):
            determinate += 1
        key = (m.modulator, m.edge_source, m.edge_target)
        exp = gold.get(key)
        mark = ""
        if exp:
            scored += 1
            ok = (iv == exp)
            correct += ok
            mark = "  OK" if ok else f"  MISMATCH (expected {exp})"
        print(f"  iota={iv}  {m.modulator} : {m.edge_source} -> {m.edge_target}"
              + (f"   [exp {exp}]{mark}" if exp else ""))
    print(f"\n  determinate interaction signs : {determinate}/{len(mods)}")
    print(f"  validated vs textbook direction: {correct}/{scored} correct"
          f"  ({correct/scored:.0%})" if scored else "  (no gold)")
    print("  NB iota multiplies the base-edge sign (additive layer) by the gain sign (gain layer);")
    print("     agreement validates the two curated layers are JOINTLY consistent with physiology.")

    # ---------- (B) synergy / antagonism for joint do(source+, modulator+) ----------
    print("\n" + "=" * 78)
    print("E9(B) — joint do(source UP, modulator UP): qualitative super-/sub-additivity at the target")
    print("=" * 78)
    tally = {"synergistic": 0, "antagonistic": 0, "reinforces": 0}
    for m in mods:
        do = {m.edge_source: Sign.PLUS, m.modulator: Sign.PLUS}
        pred = solve_signs(pmap, Intervention(targets=do)).predicted
        sy = synergies(pmap, do, pred)
        hit = next((s for s in sy if s.edge_target == m.edge_target
                    and s.modulator == m.modulator and s.edge_source == m.edge_source), None)
        if hit is None:
            verdict = "abstain (cross or target undetermined)"
        else:
            tally[hit.verdict] = tally.get(hit.verdict, 0) + 1
            verdict = (f"{hit.verdict}  (cross={hit.cross_sign}, net target={hit.target_direction})")
        print(f"  do({m.edge_source}+, {m.modulator}+) -> {m.edge_target}: {verdict}")
    det = tally["synergistic"] + tally["antagonistic"]
    print(f"\n  determinate super/sub-additive verdicts : {det}/{len(mods)}"
          f"   (synergistic {tally['synergistic']}, antagonistic {tally['antagonistic']})")
    print(f"  reinforces-only (target net '?')        : {tally['reinforces']}")
    print(f"  abstained (no determinate cross term)   : {len(mods) - det - tally['reinforces']}")

    # ---------- (C) sensitization coverage over the monogenic-lesion panel ----------
    print("\n" + "=" * 78)
    print("E9(C) — sensitization: monogenic lesions that determinately change >=1 coupling gain")
    print("=" * 78)
    _, obs = build_observations()
    n_lesions = with_gain = total_changes = 0
    for gene, rec in obs.items():
        primary = {k: Sign(v) for k, v in rec["primary"].items()}
        if not primary:
            continue
        n_lesions += 1
        pred = solve_signs(pmap, Intervention(targets=primary)).predicted
        gc = gain_changes(pmap, primary, pred)
        if gc:
            with_gain += 1
            total_changes += len(gc)
    print(f"  monogenic lesions evaluated             : {n_lesions}")
    print(f"  lesions with >=1 determinate gain change: {with_gain}")
    print(f"  total determinate gain-change calls     : {total_changes}")
    print("\n  Reading: gain changes are a NEW predicate class (coupling strengthened/weakened),")
    print("  sign-only, sound, and abstaining wherever the modulator's response is itself '?'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
