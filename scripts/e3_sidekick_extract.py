#!/usr/bin/env python3
"""E3 step 1 — extract drug -> directional-HP side-effects from SIDEKICK.

SIDEKICK (Zenodo 10.5281/zenodo.17779317, Sidekick_v1.ttl) records SPL-derived
drug side effects as ``sk:SideEffect`` associations:
    sk:assoc_*  sk:refersToDrug sk:ingredient_set_* ;
                sk:hasSideEffect obo:HP_xxxxxxx .
A drug is an INGREDIENT SET (``sk:DrugCollection``) with an ``rdfs:label`` and one
``sio:SIO_000059 rxnorm:NNNN`` per ingredient. We keep SINGLE-ingredient drugs and
restrict the side-effect HP terms to the directional abnormal-quantity subtree
encoded in ``benchmarks/hpo/hpo_term_map.yaml`` (each such HP term carries a
(node, sign) — Hyperkalemia -> (plasma_potassium, +)). The result is the gold set:
    drug name -> { (node, sign) }   plus the raw HP terms for provenance.

Streaming, blank-line-delimited block parser (the TTL is 160 MB).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TTL = ROOT / "benchmarks/.imports/sidekick/Sidekick_v1.ttl"
TERM_MAP = ROOT / "benchmarks/hpo/hpo_term_map.yaml"
OUT = ROOT / "benchmarks/.imports/sidekick/e3_gold.json"

HP_RE = re.compile(r"obo:HP_(\d+)")
RXNORM_RE = re.compile(r"rxnorm:(\d+)")
ISET_RE = re.compile(r"sk:(ingredient_set_[0-9_]+)")


def load_directional_terms() -> dict[str, dict]:
    doc = yaml.safe_load(TERM_MAP.read_text())
    out = {}
    for hp, v in doc["terms"].items():
        out[hp.replace("HP:", "")] = {"node": v["node"], "sign": v["sign"], "label": v.get("label", "")}
    return out


def iter_blocks(path: Path):
    """Yield TTL subject blocks (text between blank lines)."""
    buf: list[str] = []
    with path.open() as fh:
        for line in fh:
            if line.strip() == "":
                if buf:
                    yield "".join(buf)
                    buf = []
            else:
                buf.append(line)
    if buf:
        yield "".join(buf)


def main() -> None:
    terms = load_directional_terms()
    print(f"directional HP terms: {len(terms)}")

    # Pass 1: ingredient_set -> {label, rxnorm_ids}
    iset_label: dict[str, str] = {}
    iset_rxnorm: dict[str, list[str]] = {}
    # Pass collecting side-effect assocs: iset -> set(HP digits)
    iset_se: dict[str, set[str]] = {}

    n_dc = n_se = 0
    for block in iter_blocks(TTL):
        if "a sk:DrugCollection" in block:
            n_dc += 1
            m = re.search(r"sk:(ingredient_set_[0-9_]+)\s+a sk:DrugCollection", block)
            if not m:
                continue
            iset = m.group(1)
            lab = re.search(r'rdfs:label\s+"([^"]+)"', block)
            if lab:
                iset_label[iset] = lab.group(1)
            iset_rxnorm[iset] = RXNORM_RE.findall(block)
        elif "sk:SideEffect" in block and "sk:hasSideEffect" in block:
            n_se += 1
            mi = re.search(r"sk:refersToDrug\s+sk:(ingredient_set_[0-9_]+)", block)
            mh = re.search(r"sk:hasSideEffect\s+obo:HP_(\d+)", block)
            if mi and mh:
                iset_se.setdefault(mi.group(1), set()).add(mh.group(1))

    print(f"DrugCollections: {n_dc}, SideEffect assocs: {n_se}")
    print(f"ingredient_sets with side effects: {len(iset_se)}")

    # Single-ingredient drugs: ingredient_set name has exactly one numeric id,
    # AND the DrugCollection has exactly one rxnorm ingredient.
    gold = {}
    n_single = 0
    for iset, hps in iset_se.items():
        # single ingredient => ingredient_set_<one number> (no underscores after prefix)
        suffix = iset[len("ingredient_set_"):]
        if "_" in suffix:
            continue  # combination
        rxids = iset_rxnorm.get(iset, [])
        if len(rxids) != 1:
            continue
        n_single += 1
        label = iset_label.get(iset, iset)
        directional = {}
        raw = sorted(hps)
        for hp in hps:
            if hp in terms:
                t = terms[hp]
                key = f"{t['node']}|{t['sign']}"
                directional.setdefault(key, []).append("HP:" + hp)
        if directional:
            gold[label.lower()] = {
                "ingredient_set": iset,
                "rxnorm": rxids[0],
                "label": label,
                "directional": directional,   # "node|sign" -> [HP ids]
                "n_raw_se": len(raw),
            }

    print(f"single-ingredient drugs with side effects: {n_single}")
    print(f"single-ingredient drugs with >=1 DIRECTIONAL side effect: {len(gold)}")
    OUT.write_text(json.dumps(gold, indent=2, sort_keys=True))
    print(f"wrote {OUT}")

    # quick peek at a few feedback-relevant drugs
    for d in ["spironolactone", "enalapril", "hydrochlorothiazide", "lisinopril", "furosemide"]:
        if d in gold:
            print(f"  {d}: {list(gold[d]['directional'])}")


if __name__ == "__main__":
    main()
