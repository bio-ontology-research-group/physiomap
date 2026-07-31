#!/usr/bin/env python3
"""E3 — drug-effect forward eval: ChEMBL MoA target clamp vs SIDEKICK side effects.

A drug is a pharmacological do(): its mechanism-of-action target is clamped by action
direction (inhibitor/antagonist/blocker -> '-'; agonist/activator/opener -> '+'), and the
comparative-statics solver predicts the directional abnormal-quantity phenotypes. Gold =
directional HPO side effects recorded for that drug in SIDEKICK (e3_gold.json), which are
node+direction (Hyperkalemia -> plasma_potassium '+').

Pipeline:
  1. ChEMBL target (UniProt) -> PhysioMap node, via the PR entity_iri of each node and the
     PRO promapping UniProt<->PR table (benchmarks/.imports/uniprot_to_pr.json).
  2. Group mechanisms by drug; clamp all resolved target-nodes jointly (drop a node that two
     targets push in opposite directions). Restrict to human single-protein targets.
  3. Crosswalk drug -> SIDEKICK by ChEMBL pref_name / synonym (lowercased) == ingredient label.
  4. solve do(clamp); score each determinate prediction that (a) maps to a measurable HPO
     analyte and (b) SIDEKICK records for this drug:
        sign in gold[node]          -> corroborated (TP)
        only the OPPOSITE in gold   -> contradicted (FP)   [the soundness test]
     predictions for analytes SIDEKICK does not record at all are unscored (gold incomplete).
  5. Baseline: naive direct-target propagation (1-hop sign from clamp), same scoring.

Usage:  python scripts/e3_drug_eval.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import yaml

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention

ROOT = Path(__file__).resolve().parent.parent
IMP = ROOT / "benchmarks/.imports/sidekick"
TERM_MAP = ROOT / "benchmarks/hpo/hpo_term_map.yaml"
U2P = ROOT / "benchmarks/.imports/uniprot_to_pr.json"
OUT_MD = ROOT / "benchmarks/results/e3_drug.md"

# ChEMBL action_type -> clamp sign. Only unambiguous directions; others are skipped.
ACTION_SIGN = {
    "INHIBITOR": "-", "ANTAGONIST": "-", "BLOCKER": "-", "NEGATIVE ALLOSTERIC MODULATOR": "-",
    "NEGATIVE MODULATOR": "-", "INVERSE AGONIST": "-", "ANTISENSE INHIBITOR": "-",
    "RNAI INHIBITOR": "-", "DEGRADER": "-", "GENE EDITING NEGATIVE MODULATOR": "-",
    "PROTEOLYTIC ENZYME": "-",
    "AGONIST": "+", "ACTIVATOR": "+", "POSITIVE ALLOSTERIC MODULATOR": "+",
    "POSITIVE MODULATOR": "+", "PARTIAL AGONIST": "+", "OPENER": "+", "RELEASING AGENT": "+",
}
FEEDBACK_PARADOX = {  # drug -> (node, expected sign, why naive direct effect is wrong)
    "spironolactone": ("plasma_potassium", "+", "aldosterone antagonist (K-sparing) raises K"),
    "enalapril": ("plasma_potassium", "+", "ACE inhibitor raises K via aldosterone drop"),
    "lisinopril": ("plasma_potassium", "+", "ACE inhibitor raises K via aldosterone drop"),
    "captopril": ("plasma_potassium", "+", "ACE inhibitor raises K via aldosterone drop"),
    "hydrochlorothiazide": ("plasma_urate", "+", "thiazide raises urate (reabsorption)"),
}


def build_uniprot_to_node(pmap) -> dict[str, set[str]]:
    """UniProt accession -> {PhysioMap node ids}, via each node's PR entity_iri."""
    pr_to_nodes: dict[str, set[str]] = defaultdict(set)
    for n in pmap.nodes:
        e = getattr(n, "entity_iri", None)
        if e and e.startswith("PR:"):
            pr_to_nodes[e].add(n.id)
    u2p = json.loads(U2P.read_text())["uniprot_to_pr"]
    uni_to_node: dict[str, set[str]] = defaultdict(set)
    for uni, pr in u2p.items():
        base = uni.split("-")[0]  # drop isoform suffix
        if pr in pr_to_nodes:
            uni_to_node[base] |= pr_to_nodes[pr]
    return uni_to_node


def load_drug_clamps(uni_to_node: dict[str, set[str]]) -> dict[str, dict[str, str]]:
    """drug pref_name(lower) -> {node: clamp sign}; joint over its MoA targets."""
    mechs = json.loads((IMP / "chembl_mechanisms.json").read_text())
    mols = json.loads((IMP / "chembl_molecules.json").read_text())
    tgts = json.loads((IMP / "chembl_targets.json").read_text())

    drug_node_signs: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    drug_names: dict[str, set[str]] = defaultdict(set)
    for m in mechs:
        act = ACTION_SIGN.get(m.get("action_type"))
        if not act:
            continue
        mol = mols.get(m.get("molecule_chembl_id"))
        tgt = tgts.get(m.get("target_chembl_id"))
        if not mol or not tgt or tgt.get("organism") != "Homo sapiens":
            continue
        if tgt.get("target_type") != "SINGLE PROTEIN":
            continue
        nodes: set[str] = set()
        for acc in tgt.get("accessions", []):
            nodes |= uni_to_node.get(acc, set())
        if not nodes:
            continue
        name = (mol.get("pref_name") or "").lower()
        if not name:
            continue
        names = {name} | {s.lower() for s in mol.get("synonyms", [])}
        for nd in nodes:
            drug_node_signs[name][nd].add(act)
        drug_names[name] |= names

    clamps: dict[str, dict[str, str]] = {}
    name_aliases: dict[str, set[str]] = {}
    for name, ns in drug_node_signs.items():
        clamp = {nd: next(iter(s)) for nd, s in ns.items() if len(s) == 1}
        if clamp:
            clamps[name] = clamp
            name_aliases[name] = drug_names[name]
    return clamps, name_aliases


def main() -> int:
    tm = yaml.safe_load(TERM_MAP.read_text())["terms"]
    measurable = {v["node"] for v in tm.values()}  # nodes that map to an HPO analyte
    gold = json.loads((IMP / "e3_gold.json").read_text())  # drug label(lower) -> {...}

    bm = yaml.safe_load((ROOT / "benchmarks/hpo/drug_biomarkers.yaml").read_text())["biomarkers"]
    pmap = build_map()
    uni_to_node = build_uniprot_to_node(pmap)
    print(f"UniProt->node entries: {len(uni_to_node)}")
    clamps, aliases = load_drug_clamps(uni_to_node)
    print(f"drugs with a resolved MoA target-node clamp: {len(clamps)}")

    # ---- Part A: determinate, on-target biomarker predictions vs established directions ----
    a_correct = a_wrong = a_abstain = 0
    a_drugs = 0
    a_detail = []
    for name, clamp in sorted(clamps.items()):
        gold_bm: dict[str, str] = {}
        for nd, s in clamp.items():
            key = f"{nd}|{s}"
            if key in bm:
                gold_bm.update({k: v for k, v in bm[key].items() if k != "source"})
        if not gold_bm:
            continue
        a_drugs += 1
        interv = Intervention(targets={k: Sign(v) for k, v in clamp.items()}, label=name)
        pred = {k: v.value for k, v in solve_multiscale(pmap, interv).predicted.items()}
        for node, exp in gold_bm.items():
            got = pred.get(node, "?")
            if got not in ("+", "-"):
                a_abstain += 1; tag = "abstain"
            elif got == exp:
                a_correct += 1; tag = "OK"
            else:
                a_wrong += 1; tag = "WRONG"
            a_detail.append(f"  {name:22s} {node:24s} exp={exp} pred={got} [{tag}]")
    print("=" * 70)
    print(f"E3 PART A — determinate on-target biomarker predictions ({a_drugs} drugs, "
          f"established directions): correct={a_correct}, WRONG={a_wrong}, abstain={a_abstain}")
    for d in a_detail:
        print(d)
    print("=" * 70)

    # crosswalk clamp drug -> SIDEKICK gold (by name or synonym)
    matched = {}
    for name, clamp in clamps.items():
        g = None
        for alias in {name} | aliases.get(name, set()):
            if alias in gold:
                g = gold[alias]
                break
        if g:
            matched[name] = (clamp, g)
    print(f"drugs matched to SIDEKICK directional gold: {len(matched)}")

    def gold_signs(g) -> dict[str, set[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for key in g["directional"]:
            node, sign = key.split("|")
            out[node].add(sign)
        return out

    def score(pred: dict[str, str], clamp, gsigns) -> tuple[int, int, int, list]:
        tp = fp = unscored = 0
        details = []
        for node, sign in pred.items():
            if sign not in ("+", "-"):
                continue  # abstention is not a prediction
            if node in clamp or node not in measurable:
                continue
            if node not in gsigns:
                unscored += 1
                continue
            if sign in gsigns[node]:
                tp += 1
                details.append((node, sign, "corroborated"))
            else:  # only the opposite documented
                fp += 1
                details.append((node, sign, f"CONTRADICTED gold={sorted(gsigns[node])}"))
        return tp, fp, unscored, details

    cs_tp = cs_fp = cs_uns = 0
    nv_tp = nv_fp = 0
    # recall view: over documented directional (drug, side-effect-node) pairs, what does CS do?
    se_total = se_determined = se_correct = se_abstain = 0
    paradox_hits = []
    contradictions = []
    g = pmap.causal_subgraph()
    for name, (clamp, gdoc) in sorted(matched.items()):
        gsigns = gold_signs(gdoc)
        interv = Intervention(targets={k: Sign(v) for k, v in clamp.items()}, label=name)
        pred = {k: v.value for k, v in solve_multiscale(pmap, interv).predicted.items()}
        tp, fp, uns, det = score(pred, clamp, gsigns)
        cs_tp += tp; cs_fp += fp; cs_uns += uns
        # recall over documented side-effect nodes (single-direction gold only, reachable)
        for node, signs in gsigns.items():
            if node in clamp or len(signs) != 1:
                continue
            se_total += 1
            got = pred.get(node, "?")
            if got in ("+", "-"):
                se_determined += 1
                if got in signs:
                    se_correct += 1
            else:
                se_abstain += 1
        for node, sign, tag in det:
            if tag.startswith("CONTRADICTED"):
                contradictions.append(f"{name}: {node} pred={sign} {tag}")

        # naive: 1-hop direct effect of the clamp (sign of immediate downstream)
        naive: dict[str, str] = {}
        for src, s in clamp.items():
            for tgt_n in g.successors(src):
                if tgt_n in clamp:
                    continue
                es = g.edges[src, tgt_n]["sign"]
                eff = "+" if s == es else ("-" if es in ("+", "-") else "?")
                if tgt_n in naive and naive[tgt_n] != eff:
                    naive[tgt_n] = "?"
                elif es in ("+", "-"):
                    naive[tgt_n] = eff
        ntp, nfp, _, _ = score({k: v for k, v in naive.items() if v in ("+", "-")}, clamp, gsigns)
        nv_tp += ntp; nv_fp += nfp

        # feedback paradox tracking
        if name in FEEDBACK_PARADOX:
            node, exp, why = FEEDBACK_PARADOX[name]
            got = pred.get(node, "?")
            nv = naive.get(node, "—")
            paradox_hits.append((name, node, exp, got, nv, why))

    print("=" * 70)
    print(f"E3 DRUG FORWARD vs SIDEKICK: drugs scored={len(matched)}")
    prec = f"{cs_tp/(cs_tp+cs_fp):.1%}" if cs_tp + cs_fp else "n/a"
    print(f"  precision on determinate calls: corroborated={cs_tp}, CONTRADICTED={cs_fp}, "
          f"precision={prec}  (unscored, gold-incomplete={cs_uns})")
    print(f"  RECALL over {se_total} documented single-direction (drug,side-effect-node) pairs: "
          f"determinate={se_determined} (correct={se_correct}), abstain={se_abstain} "
          f"({se_abstain/se_total:.0%} abstained -- feedback side effects sit in the whole-body SCC)")
    print(f"  naive direct-target 1-hop:       corroborated={nv_tp}, CONTRADICTED={nv_fp}, "
          f"precision={nv_tp/(nv_tp+nv_fp):.1%}" if nv_tp + nv_fp else "  naive: none")
    print("-- feedback paradoxes (naive direct effect gives the wrong/forward sign) --")
    for name, node, exp, got, nv, why in paradox_hits:
        flag = "OK" if got == exp else ("ABSTAIN" if got == "?" else "WRONG")
        print(f"  {name:20s} {node:20s} expect={exp} CS={got}[{flag}] naive1hop={nv}  ({why})")
    if contradictions:
        print("-- CONTRADICTIONS (CS predicted opposite of SIDEKICK-documented direction) --")
        for c in contradictions[:40]:
            print("   ", c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
