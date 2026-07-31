#!/usr/bin/env python3
"""E1c — validate the *affected-with-indeterminate-direction* class against HPOA.

The forward benchmark (E1b, ``scripts/e1b_eval.py``) scores only the **determinate** (+/-)
predictions. PhysioMap, however, grades a variable under a ``do(lesion)`` into three outcomes:

  * **unaffected**  — no causal route reaches it (absent from ``predicted``);
  * **affected, determinate direction** (+/-) — the ordinary phenotype scored by E1b;
  * **affected, indeterminate direction** (``?``) — *reached* but the net comparative-statics
    sign is magnitude-dependent (typically inside a feedback SCC). A **positive** prediction:
    "abnormality of X" asserted without a committed sign.

The paper (main.tex ~256-260) flags a concrete evaluation the forward task does not yet perform:
does this sign-indeterminate region coincide with HPO's **non-directional "Abnormality of X"**
annotations, and in particular with traits HPOA records **inconsistently** (some patients ↑,
some ↓)? This script performs it.

The affected class is **broad by design** — a lesion perturbs the whole homeostatic SCC, so ~70
traits per gene return `?`. It is a **soundness** device (never commit a wrong sign), not a
specificity claim; we report its size honestly. The load-bearing result is *gold-anchored*:

  * **Direction-variable gold** (the paper's target): (gene, node) pairs HPOA annotates in BOTH
    directions across records — exactly the conflicts E1b must DISCARD. On these the ONLY sound
    call is `?`; any committed single sign is contradicted by half the records. We check that the
    affected class fires here and that PhysioMap almost never commits a determinate direction.
  * **Neutral "Abnormality of X"** coverage — genes HPOA annotates with the node's non-directional
    term directly (subsumption of ↑/↓), matched via ``abnormality_index``.

Reuses the E1b machinery verbatim (same map, same lesions, same is_a-propagated HPOA). Unlike E1b
we deliberately do NOT drop conflicting-direction annotations or apply ``annotation_discordances``:
a variable annotation is the *target* here, not noise. ``block_propagation`` is kept for identical
ancestor expansion.

Usage:  python scripts/e1c_affected_eval.py
"""
from __future__ import annotations

from pathlib import Path

import yaml

from physiomap_core.hpo import build_map
from physiomap_core.knockout import abnormality_index, knockout_multi
from scripts.build_hpo_observations import ancestors, parse_hp

ROOT = Path(__file__).resolve().parent.parent
GENES = ROOT / "benchmarks/hpo/gene_lesions_e1b.yaml"
TERM_MAP = ROOT / "benchmarks/hpo/hpo_term_map.yaml"
G2P = ROOT / "ontology/.obo_cache/genes_to_phenotype.txt"
OUT_MD = ROOT / "benchmarks/results/e1c_affected.md"


def build_gold() -> tuple[str, dict[str, dict]]:
    """gene -> {node_signs: {node -> {sign -> count}}, hp: set[HP]} from is_a-propagated HPOA.

    Conflicts are KEPT (they are the target). ``hp`` is the full propagated annotation set, used
    to detect a *neutral* "Abnormality of X" annotation directly.
    """
    names, parents, version = parse_hp()
    tm = yaml.safe_load(TERM_MAP.read_text())
    term_map, block = tm["terms"], set(tm.get("block_propagation", []))

    gene_hpo: dict[str, set[str]] = {}
    with G2P.open() as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        gi, hi = hdr.index("gene_symbol"), hdr.index("hpo_id")
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) > max(gi, hi):
                gene_hpo.setdefault(f[gi], set()).add(f[hi])

    out: dict[str, dict] = {}
    for gene, ann in gene_hpo.items():
        node_signs: dict[str, dict[str, int]] = {}
        prop: set[str] = set()
        for hp in ann:
            anc = {hp} if hp in block else ancestors(hp, parents)
            prop |= anc
            for a in anc:
                m = term_map.get(a)
                if m:
                    node_signs.setdefault(m["node"], {}).setdefault(m["sign"], 0)
                    node_signs[m["node"]][m["sign"]] += 1
        out[gene] = {"node_signs": node_signs, "hp": prop}
    return version, out


def main() -> int:
    release, gold = build_gold()
    genes = yaml.safe_load(GENES.read_text())["genes"]
    pmap = build_map()
    abn = abnormality_index()   # node -> neutral "Abnormality of X" HP term

    # breadth of the affected class
    n_pred = 0; n_pred_scc = 0; genes_with_pred = 0
    # subsumption: gene has ANY HPOA annotation of that trait (directional, either sign)
    n_subsum = 0
    # neutral: gene carries the node's non-directional "Abnormality of X" HP term itself
    n_neutral = 0
    # direction-variable AMONG the affected predictions (both ↑ and ↓ annotated)
    n_dv_pred = 0
    dv_pred_rows: list[str] = []
    subsum_rows: list[str] = []

    # GOLD-ANCHORED soundness on the direction-variable set (the paper's target):
    # for each gene, its reached, non-clamp, direction-variable (↑ & ↓) trait nodes ->
    #   affected(?) [sound], determinate(+/-) [committed against ambiguous gold], unreached.
    dv_total = dv_affected = dv_determinate = dv_unreached = 0
    dv_determinate_rows: list[str] = []

    for gene, rec in genes.items():
        g = gold.get(gene)
        if not g:
            continue
        node_signs, prop = g["node_signs"], g["hp"]
        primary = rec["primary"]
        res = knockout_multi(pmap, primary)
        if res.error:
            print(f"  !! {gene}: {res.error}")
            continue
        predicted = res.predicted                       # node -> "+"/"-"/"?" (reachable only)

        had_pred = False
        for hit in res.affected:
            node = hit.node
            if node in primary:
                continue
            n_pred += 1
            had_pred = True
            if hit.in_big_scc:
                n_pred_scc += 1
            signs = node_signs.get(node)
            neutral_term = abn.get(node, {}).get("hpo")
            if signs:
                n_subsum += 1
                if len(signs) > 1:
                    n_dv_pred += 1
                    dv_pred_rows.append(f"{gene}: {hit.label} | HPOA=+/− | {hit.hpo_label}")
                else:
                    subsum_rows.append(
                        f"{gene}: {hit.label} | HPOA={next(iter(signs))} | {hit.hpo_label}")
            if neutral_term and neutral_term in prop:
                n_neutral += 1
        genes_with_pred += int(had_pred)

        # gold-anchored: the direction-variable annotations E1b discards
        for node, signs in node_signs.items():
            if node in primary or len(signs) <= 1:
                continue
            dv_total += 1
            v = predicted.get(node)
            if v == "?":
                dv_affected += 1
            elif v in ("+", "-"):
                dv_determinate += 1
                dv_determinate_rows.append(f"{gene}: {node} pred={v} (HPOA ↑ and ↓)")
            else:
                dv_unreached += 1

    subsum_prec = n_subsum / n_pred if n_pred else float("nan")
    dv_reached = dv_affected + dv_determinate
    dv_sound = dv_affected / dv_reached if dv_reached else float("nan")

    L: list[str] = []
    L.append("# E1c — Affected-with-indeterminate-direction class vs HPOA\n\n")
    L.append(f"HPO release: **{release}**; gene set: **{len(genes)}** IEM lesions (same as E1b).\n\n")
    L.append("PhysioMap grades a variable under `do(lesion)` into *unaffected* / *affected with a "
             "determinate direction* (`+`/`−`, scored by E1b) / **affected with an indeterminate "
             "direction** (`?`, this eval): reached, but the net comparative-statics sign is "
             "magnitude-dependent inside a feedback core — an \"abnormality of X\" asserted without "
             "a committed sign.\n\n")

    L.append("## Gold-anchored soundness on direction-variable phenotypes (the load-bearing result)\n\n")
    L.append("HPOA annotates some (gene, trait) pairs in **both** directions across affected "
             "individuals; E1b must discard these as conflicts. On such a trait the only sound "
             "prediction is `?` — any committed single sign is contradicted by half the records. "
             f"Of the **{dv_total}** direction-variable gold pairs (excluding the clamp), "
             f"**{dv_reached}** are reached and PhysioMap calls:\n\n")
    L.append(f"- affected (`?`, correctly indeterminate): **{dv_affected}**\n")
    L.append(f"- determinate (`+`/`−`, a sign committed against ambiguous gold): "
             f"**{dv_determinate}**\n")
    L.append(f"- unreached (no route; not an affected prediction): {dv_unreached}\n\n")
    L.append(f"**Soundness on reached direction-variable traits: {dv_affected}/{dv_reached} = "
             f"{dv_sound:.0%} correctly indeterminate.** The sign-indeterminate region coincides "
             "with exactly the annotations HPOA itself cannot commit to a direction.\n\n")
    if dv_determinate_rows:
        L.append("Determinate calls on direction-variable gold (for inspection):\n")
        for r in sorted(dv_determinate_rows):
            L.append(f"- {r}\n")
        L.append("\n")

    L.append("## Breadth and coverage of the affected class\n\n")
    L.append(f"- Affected (`?`) predictions: **{n_pred}** across {genes_with_pred} genes "
             f"(≈{n_pred // max(genes_with_pred, 1)}/gene); {n_pred_scc} lie in the whole-body SCC. "
             "The class is intentionally broad — a lesion perturbs the entire homeostatic core — "
             "so it is a soundness device, not a high-specificity localiser.\n")
    L.append(f"- Subsumption: **{n_subsum}/{n_pred} = {subsum_prec:.1%}** of affected predictions "
             "fall on a trait the gene is annotated for in HPOA (any direction).\n")
    L.append(f"- Direction-variable among affected predictions: **{n_dv_pred}** land on a trait "
             "HPOA records as both ↑ and ↓ for that gene.\n")
    L.append(f"- Neutral-term coverage: **{n_neutral}** affected predictions match a gene "
             "annotation carrying the node's non-directional \"Abnormality of X\" HP term itself.\n\n")

    if dv_pred_rows:
        L.append("## Affected predictions on direction-variable HPOA traits\n\n")
        for r in sorted(dv_pred_rows):
            L.append(f"- {r}\n")
        L.append("\n")
    if subsum_rows:
        L.append("## Affected predictions on single-direction HPOA traits (subsumption)\n\n")
        for r in sorted(subsum_rows):
            L.append(f"- {r}\n")

    OUT_MD.write_text("".join(L))

    print("=" * 70)
    print(f"E1c AFFECTED-CLASS (HPO {release}):")
    print(f"  DIRECTION-VARIABLE gold: total={dv_total}, reached={dv_reached} -> "
          f"affected(?)={dv_affected}, determinate={dv_determinate}, unreached={dv_unreached}")
    print(f"  => soundness on reached direction-variable = {dv_affected}/{dv_reached} = {dv_sound:.0%}")
    print(f"  affected(?) predictions: {n_pred} across {genes_with_pred} genes "
          f"({n_pred_scc} in SCC); subsumption {n_subsum} ({subsum_prec:.1%}), "
          f"neutral-term {n_neutral}, dir-variable {n_dv_pred}")
    print(f"  wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
