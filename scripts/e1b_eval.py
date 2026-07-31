#!/usr/bin/env python3
"""E1b — large-scale IEM gene-knockout forward eval vs real HPOA (evaluation experiment).

Builds observed HPO directions for the expanded gene set (benchmarks/hpo/gene_lesions_e1b.yaml:
21 curated + auto-resolved IEM enzyme genes), is_a-propagated and matched to hpo_term_map, with
two evidence-based exclusions: block_propagation (true-path-rule traps) and
annotation_discordances.yaml (literature-verified non-specific/variable gene-level annotations).
Then runs do(lesion) comparative statics and scores each observed direction (determinate =
correct/wrong; ? = abstain; the intervened node is not scored). Reports + rewrites the result md.

Usage:
  python scripts/e1b_eval.py
  python scripts/e1b_eval.py --leakage-sensitivity
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from scripts.build_hpo_observations import ancestors, parse_hp

ROOT = Path(__file__).resolve().parent.parent
GENES = ROOT / "benchmarks/hpo/gene_lesions_e1b.yaml"
TERM_MAP = ROOT / "benchmarks/hpo/hpo_term_map.yaml"
G2P = ROOT / "ontology/.obo_cache/genes_to_phenotype.txt"
DISC = ROOT / "benchmarks/hpo/annotation_discordances.yaml"
OUT_MD = ROOT / "benchmarks/results/e1b_forward.md"
OUT_JSON = ROOT / "benchmarks/results/e1b_forward.json"
OUT_PAIRS = ROOT / "benchmarks/results/e1b_forward_pairs.tsv"
LEAKAGE_GENES = frozenset(
    {
        "ADA", "ADA2", "ADSL", "AK1", "AMPD1", "APRT", "DPYD", "DPYS", "ITPA",
        "PRPS1", "TYMP", "UGT1A1", "UMPS", "UPB1", "XDH",
    }
)


@dataclass
class ForwardCounts:
    genes_scored: int = 0
    correct: int = 0
    wrong: int = 0
    abstain: int = 0
    genes_with_prediction: int = 0
    wrong_calls: list[str] = field(default_factory=list)

    @property
    def determinate(self) -> int:
        return self.correct + self.wrong


def build_observations() -> tuple[str, dict]:
    names, parents, version = parse_hp()
    tm = yaml.safe_load(TERM_MAP.read_text())
    term_map, block = tm["terms"], set(tm.get("block_propagation", []))
    genes = yaml.safe_load(GENES.read_text())["genes"]
    disc = {(d["gene"], d["node"]) for d in yaml.safe_load(DISC.read_text())["discordances"]}

    gene_hpo: dict[str, set[str]] = {}
    with G2P.open() as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        gi, hi = hdr.index("gene_symbol"), hdr.index("hpo_id")
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) > max(gi, hi):
                gene_hpo.setdefault(f[gi], set()).add(f[hi])

    obs: dict[str, dict] = {}
    n_disc = 0
    for gene, rec in genes.items():
        ann = gene_hpo.get(gene)
        if not ann:
            continue
        node_signs: dict[str, dict[str, int]] = {}
        node_supports: dict[str, dict[str, set[tuple[str, str]]]] = {}
        for hp in ann:
            for anc in ({hp} if hp in block else ancestors(hp, parents)):
                m = term_map.get(anc)
                if m:
                    node_signs.setdefault(m["node"], {}).setdefault(m["sign"], 0)
                    node_signs[m["node"]][m["sign"]] += 1
                    node_supports.setdefault(m["node"], {}).setdefault(
                        m["sign"], set()
                    ).add(
                        (
                            f"{hp} {names.get(hp, '')}".strip(),
                            f"{anc} {names.get(anc, '')}".strip(),
                        )
                    )
        observed = {}
        supports = {}
        for node, signs in node_signs.items():
            if len(signs) != 1:
                continue  # both directions annotated -> drop (conflict)
            if (gene, node) in disc:
                n_disc += 1
                continue  # literature-verified discordance/variable -> exclude
            sign = next(iter(signs))
            observed[node] = sign
            supports[node] = sorted(node_supports[node][sign])
        obs[gene] = {
            "primary": rec["primary"],
            "mapping_note": rec.get("note", ""),
            "observed": observed,
            "supports": supports,
        }
    print(f"  built observations for {len(obs)} genes; {n_disc} (gene,node) discordances excluded")
    return version, obs


def write_pair_table(release: str, obs: dict) -> int:
    rows: list[dict[str, str]] = []
    for gene, rec in sorted(obs.items()):
        primary = rec["primary"]
        intervention = "; ".join(
            f"{node} {sign}" for node, sign in sorted(primary.items())
        )
        for node, sign in sorted(rec["observed"].items()):
            if node in primary:
                continue
            supports = rec["supports"][node]
            rows.append(
                {
                    "gene": gene,
                    "primary_intervention": intervention,
                    "lesion_mapping_note": rec["mapping_note"],
                    "physiomap_variable": node,
                    "reference_direction": sign,
                    "direct_hpo_annotations": "; ".join(
                        sorted({direct for direct, _ in supports})
                    ),
                    "mapped_directional_hpo_classes": "; ".join(
                        sorted({mapped for _, mapped in supports})
                    ),
                    "hpo_release": release.rsplit("/", 1)[-1],
                }
            )
    fieldnames = [
        "gene",
        "primary_intervention",
        "lesion_mapping_note",
        "physiomap_variable",
        "reference_direction",
        "direct_hpo_annotations",
        "mapped_directional_hpo_classes",
        "hpo_release",
    ]
    with OUT_PAIRS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def score_observations(pmap, obs, excluded_genes=frozenset()) -> ForwardCounts:
    counts = ForwardCounts()
    for gene, rec in obs.items():
        if gene in excluded_genes:
            continue
        observed = {k: Sign(v) for k, v in rec["observed"].items()}
        if not observed:
            continue
        primary = {k: Sign(v) for k, v in rec["primary"].items()}
        counts.genes_scored += 1
        pred = solve_multiscale(pmap, Intervention(targets=primary, label=gene)).predicted
        det = 0
        for node, exp in observed.items():
            if node in primary:
                continue
            got = pred.get(node)
            if got is None or got is Sign.UNKNOWN:
                counts.abstain += 1
            elif got is exp:
                counts.correct += 1
                det += 1
            else:
                counts.wrong += 1
                det += 1
                counts.wrong_calls.append(
                    f"{gene}: {node} HPO={exp.value} pred={got.value}"
                )
        counts.genes_with_prediction += int(det > 0)
    return counts


def print_score(release: str, counts: ForwardCounts, label: str = "E1b FORWARD") -> None:
    acc = counts.correct / counts.determinate if counts.determinate else float("nan")
    print("=" * 64)
    print(
        f"{label} (HPO {release}): genes={counts.genes_scored}, "
        f"determinate={counts.determinate}, correct={counts.correct}, "
        f"WRONG={counts.wrong}, abstain={counts.abstain}"
    )
    print(
        f"  directional accuracy={acc:.1%}; genes with >=1 downstream prediction="
        f"{counts.genes_with_prediction}"
    )
    for w in counts.wrong_calls:
        print("   WRONG", w)


def serialize_score(counts: ForwardCounts) -> dict[str, object]:
    return {
        "genes_scored": counts.genes_scored,
        "genes_with_prediction": counts.genes_with_prediction,
        "determinate": counts.determinate,
        "correct": counts.correct,
        "wrong": counts.wrong,
        "abstain": counts.abstain,
        "precision": (
            counts.correct / counts.determinate if counts.determinate else None
        ),
        "wrong_calls": counts.wrong_calls,
    }


def write_report(release: str, full: ForwardCounts, controlled: ForwardCounts | None) -> None:
    full_precision = full.correct / full.determinate if full.determinate else float("nan")
    lines = [
        "# E1b — directional phenotype prediction for rare metabolic disease",
        "",
        "Generated by `scripts/e1b_eval.py --leakage-sensitivity`; do not edit.",
        "",
        f"External reference: HPOA `{release}`. The intervened lesion node is not scored, "
        "and four literature-adjudicated annotation discordances are excluded before scoring.",
        "",
        "| evaluation | genes | determinate | correct | wrong | abstain | precision |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| full | {full.genes_scored} | {full.determinate} | {full.correct} | "
        f"{full.wrong} | {full.abstain} | {full_precision:.1%} |",
    ]
    if controlled is not None:
        controlled_precision = (
            controlled.correct / controlled.determinate if controlled.determinate else float("nan")
        )
        lines.append(
            f"| leakage-controlled | {controlled.genes_scored} | {controlled.determinate} | "
            f"{controlled.correct} | {controlled.wrong} | {controlled.abstain} | "
            f"{controlled_precision:.1%} |"
        )
        lines.extend(
            [
                "",
                "The leakage-controlled sensitivity analysis excludes the 15 genes named in "
                "phenotype-directed curation-fragment headers. It reduces overlap with explicit "
                "benchmark-directed curation, but does not make the literature used to construct "
                "the map fully independent of HPOA.",
            ]
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--leakage-sensitivity",
        action="store_true",
        help="report the full run and a run excluding the 15 genes named in curation headers",
    )
    args = parser.parse_args(argv)

    release, obs = build_observations()
    pair_count = write_pair_table(release, obs)
    pmap = build_map()
    full = score_observations(pmap, obs)
    print_score(release, full)
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "hpo_release": release,
        "full": serialize_score(full),
    }
    controlled = None
    if args.leakage_sensitivity:
        controlled = score_observations(pmap, obs, LEAKAGE_GENES)
        print_score(release, controlled, "E1b FORWARD leakage-controlled")
        excluded_present = LEAKAGE_GENES.intersection(obs)
        payload["leakage_controlled"] = serialize_score(controlled)
        payload["excluded_genes"] = sorted(excluded_present)
        print(
            f"  excluded evaluation genes={len(excluded_present)}/{len(LEAKAGE_GENES)}: "
            f"{', '.join(sorted(excluded_present))}"
        )
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_report(release, full, controlled)
    expected_pairs = full.determinate + full.abstain
    if pair_count != expected_pairs:
        raise SystemExit(
            f"materialized pair count {pair_count} != scored pair count {expected_pairs}"
        )
    print(
        f"  wrote {OUT_JSON.relative_to(ROOT)}, {OUT_MD.relative_to(ROOT)}, "
        f"and {OUT_PAIRS.relative_to(ROOT)} ({pair_count} pairs)"
    )
    return 0 if full.wrong == 0 and (controlled is None or controlled.wrong == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
