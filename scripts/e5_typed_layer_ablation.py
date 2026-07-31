#!/usr/bin/env python3
"""E5 — ablate typed relation layers in the rare-disease experiments.

The primary rare-disease evaluation uses ``solve_multiscale``.  Its operational
graph contains authored causal influences plus tagged production and quantitative
shadows, while constitutive constraints enter as separate upward forcing.  This
experiment determines whether those supplementary layers change the reported
forward predictions or inverse lesion rankings.

Run this benchmark on a compute host, not a laptop:

    uv run python scripts/e5_typed_layer_ablation.py

The four cumulative configurations are:

1. authored causal influences only;
2. causal influences plus production shadows;
3. causal influences plus production and quantitative shadows; and
4. the complete evaluated fragment, adding constitutive determination.

Modulation is deliberately not a configuration step because the current
comparative-static solver never reads modulation records.  The output records
that boundary explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from physiomap_core.hpo import build_map
from physiomap_core.model import PhysioMap, Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from physiomap_core.scm import load_canonical_scm
from scripts.e1b_eval import (
    DISC,
    G2P,
    GENES,
    TERM_MAP,
    build_observations,
)
from scripts.build_hpo_observations import HP_OBO

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "benchmarks/results/e5_typed_layer_ablation.json"
OUT_MD = ROOT / "benchmarks/results/e5_typed_layer_ablation.md"
OUT_TEX = ROOT / "paper/generated/typed-layer-ablation.tex"


@dataclass(frozen=True)
class LayerConfiguration:
    id: str
    label: str
    production: bool
    quantitative: bool
    constitution: bool


CONFIGURATIONS = (
    LayerConfiguration("causal_only", "causal", False, False, False),
    LayerConfiguration("causal_production", "causal + production", True, False, False),
    LayerConfiguration(
        "causal_production_quantitative",
        "causal + production + quantitative",
        True,
        True,
        False,
    ),
    LayerConfiguration(
        "full_evaluated_fragment",
        "causal + production + quantitative + constitution",
        True,
        True,
        True,
    ),
)


def configure_layers(pmap: PhysioMap, config: LayerConfiguration) -> PhysioMap:
    """Return ``pmap`` restricted to one cumulative evaluated-layer configuration."""
    return pmap.model_copy(
        update={
            "production_edges": list(pmap.production_edges) if config.production else [],
            "quantitative_definitions": (
                list(pmap.quantitative_definitions) if config.quantitative else []
            ),
            "constitutive_edges": (
                list(pmap.constitutive_edges) if config.constitution else []
            ),
        }
    )


def operational_inventory(pmap: PhysioMap) -> dict[str, int]:
    """Count unique directed arcs and constraints that can affect the current solver.

    ``causal_subgraph`` is a ``DiGraph``: parallel causal records with the same
    source and target are combined into one operational arc.  Production records
    and quantitative arguments contribute a shadow only when a higher-priority
    arc for the same ordered pair is not already present.
    """
    kinds = Counter(
        data.get("edge_kind", "causal-influence")
        for _, _, data in pmap.causal_subgraph().edges(data=True)
    )
    return {
        "causal_arcs": kinds["causal-influence"],
        "production_shadow_arcs": kinds["production-derived"],
        "quantitative_shadow_arcs": kinds["quantitative-derived"],
        "constitutive_constraints": len(pmap.constitutive_edges),
        "modulation_records_present_but_inactive": len(pmap.modulation_edges),
    }


def prediction_symbol(value: Sign | None) -> str:
    return value.value if value in (Sign.PLUS, Sign.MINUS) else "?"


def forward_evaluation(pmap: PhysioMap, observations: dict[str, dict]) -> dict[str, Any]:
    """Run the E1b forward task and retain one normalized prediction per scored pair."""
    predictions: dict[str, str] = {}
    expected: dict[str, str] = {}
    genes_scored = genes_with_prediction = correct = wrong = abstain = 0
    for gene, record in observations.items():
        observed = record["observed"]
        if not observed:
            continue
        primary = {node: Sign(sign) for node, sign in record["primary"].items()}
        solved = solve_multiscale(
            pmap, Intervention(targets=primary, label=gene)
        ).predicted
        genes_scored += 1
        determinate_for_gene = 0
        for node, gold in observed.items():
            if node in primary:
                continue
            key = f"{gene}\t{node}"
            got = prediction_symbol(solved.get(node))
            predictions[key] = got
            expected[key] = gold
            if got == "?":
                abstain += 1
            elif got == gold:
                correct += 1
                determinate_for_gene += 1
            else:
                wrong += 1
                determinate_for_gene += 1
        genes_with_prediction += int(determinate_for_gene > 0)
    determinate = correct + wrong
    return {
        "metrics": {
            "genes_scored": genes_scored,
            "genes_with_prediction": genes_with_prediction,
            "pairs": len(predictions),
            "determinate": determinate,
            "correct": correct,
            "wrong": wrong,
            "abstain": abstain,
            "precision": correct / determinate if determinate else None,
            "coverage": determinate / len(predictions) if predictions else None,
        },
        "predictions": predictions,
        "expected": expected,
    }


def inverse_evaluation(pmap: PhysioMap, observations: dict[str, dict]) -> dict[str, Any]:
    """Repeat the E4 closed-pool ranking under one typed-layer configuration."""
    pool: set[tuple[str, str]] = set()
    for record in observations.values():
        primary = record["primary"]
        if len(primary) == 1:
            (node, sign), = primary.items()
            pool.add((node, sign))
    candidates = sorted(pool)

    cache: dict[tuple[str, str], dict[str, str]] = {}
    for node, sign in candidates:
        solved = solve_multiscale(
            pmap,
            Intervention(targets={node: Sign(sign)}, label=f"{node}{sign}"),
        ).predicted
        cache[(node, sign)] = {
            target: value.value
            for target, value in solved.items()
            if value in (Sign.PLUS, Sign.MINUS)
        }

    def candidate_score(
        candidate: tuple[str, str], observed: dict[str, str]
    ) -> tuple[int, int]:
        predicted = cache[candidate]
        agree = disagree = 0
        for node, gold in observed.items():
            got = predicted.get(node)
            if got is None:
                continue
            if got == gold:
                agree += 1
            else:
                disagree += 1
        return agree, disagree

    ranks: dict[str, int] = {}
    unique_top1 = top3 = top10 = 0
    for gene, record in observations.items():
        primary = record["primary"]
        if len(primary) != 1:
            continue
        (true_node, true_sign), = primary.items()
        true_candidate = (true_node, true_sign)
        if true_candidate not in cache:
            continue
        observed = {
            node: sign
            for node, sign in record["observed"].items()
            if node != true_node
        }
        if not observed:
            continue
        scored = []
        for candidate in candidates:
            agree, disagree = candidate_score(candidate, observed)
            scored.append((candidate, agree - disagree, -disagree, agree))
        true = next(item for item in scored if item[0] == true_candidate)
        better = sum(
            1
            for item in scored
            if (item[1], item[2], item[3]) > (true[1], true[2], true[3])
        )
        tied = sum(
            1
            for item in scored
            if item[0] != true_candidate
            and (item[1], item[2], item[3]) == (true[1], true[2], true[3])
        )
        rank = 1 + better
        ranks[gene] = rank
        unique_top1 += int(rank == 1 and tied == 0)
        top3 += int(rank <= 3)
        top10 += int(rank <= 10)

    ordered_ranks = list(ranks.values())
    return {
        "metrics": {
            "candidate_pool": len(candidates),
            "genes_scored": len(ordered_ranks),
            "unique_top1": unique_top1,
            "top3": top3,
            "top10": top10,
            "mrr": (
                sum(1.0 / rank for rank in ordered_ranks) / len(ordered_ranks)
                if ordered_ranks
                else 0.0
            ),
            "median_rank": median(ordered_ranks) if ordered_ranks else None,
        },
        "ranks": ranks,
    }


def compare_forward(
    reference: dict[str, str], candidate: dict[str, str]
) -> dict[str, Any]:
    """Describe normalized per-pair changes relative to the complete fragment."""
    if set(reference) != set(candidate):
        raise ValueError("forward configurations do not contain the same evaluation pairs")
    changed = []
    determinate_to_abstain = abstain_to_determinate = sign_flips = 0
    for key in sorted(reference):
        full = reference[key]
        other = candidate[key]
        if full == other:
            continue
        changed.append({"pair": key, "candidate": other, "full": full})
        if full in {"+", "-"} and other == "?":
            determinate_to_abstain += 1
        elif full == "?" and other in {"+", "-"}:
            abstain_to_determinate += 1
        elif full in {"+", "-"} and other in {"+", "-"}:
            sign_flips += 1
    return {
        "changed_pairs": len(changed),
        "determinate_to_abstain": determinate_to_abstain,
        "abstain_to_determinate": abstain_to_determinate,
        "sign_flips": sign_flips,
        "examples": changed[:20],
    }


def compare_ranks(reference: dict[str, int], candidate: dict[str, int]) -> dict[str, Any]:
    if set(reference) != set(candidate):
        raise ValueError("inverse configurations do not contain the same genes")
    changes = {
        gene: candidate[gene] - reference[gene]
        for gene in reference
        if candidate[gene] != reference[gene]
    }
    return {
        "changed_genes": len(changes),
        "improved_without_layer": sum(delta < 0 for delta in changes.values()),
        "worsened_without_layer": sum(delta > 0 for delta in changes.values()),
        "maximum_absolute_rank_change": max(map(abs, changes.values()), default=0),
        "examples": [
            {
                "gene": gene,
                "candidate_rank": candidate[gene],
                "full_rank": reference[gene],
            }
            for gene in sorted(changes)[:20]
        ],
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_checksums() -> dict[str, str]:
    paths = (GENES, TERM_MAP, G2P, DISC, HP_OBO, ROOT / "release/owl-scm/physiomap-scm.json")
    return {str(path.relative_to(ROOT)): sha256(path) for path in paths}


def build_result() -> dict[str, Any]:
    hpo_release, observations = build_observations()
    base = build_map()
    manifest = load_canonical_scm()
    results: dict[str, dict[str, Any]] = {}
    for config in CONFIGURATIONS:
        print(f"[ablation] {config.label}", flush=True)
        model = configure_layers(base, config)
        results[config.id] = {
            "label": config.label,
            "active_relations": operational_inventory(model),
            "forward": forward_evaluation(model, observations),
            "inverse": inverse_evaluation(model, observations),
        }

    full = results["full_evaluated_fragment"]
    comparisons = {}
    for config in CONFIGURATIONS[:-1]:
        candidate = results[config.id]
        comparisons[config.id] = {
            "label": f"{config.label} versus complete evaluated fragment",
            "forward": compare_forward(
                full["forward"]["predictions"], candidate["forward"]["predictions"]
            ),
            "inverse": compare_ranks(
                full["inverse"]["ranks"], candidate["inverse"]["ranks"]
            ),
        }

    full_graph = base.causal_subgraph()
    no_modulation = base.model_copy(update={"modulation_edges": []}).causal_subgraph()
    modulation_graph_invariant = (
        set(full_graph.edges) == set(no_modulation.edges)
        and all(full_graph.edges[edge] == no_modulation.edges[edge] for edge in full_graph.edges)
    )
    return {
        "schema_version": "1.0.0",
        "physiomap_version": manifest.physiomap_version,
        "hpo_release": hpo_release,
        "input_sha256": input_checksums(),
        "configuration_order": [config.id for config in CONFIGURATIONS],
        "results": results,
        "comparisons_to_full": comparisons,
        "modulation": {
            "records": len(base.modulation_edges),
            "read_by_comparative_static_solver": False,
            "removal_changes_operational_graph": not modulation_graph_invariant,
        },
    }


def _percent(value: float | None) -> str:
    return "---" if value is None else f"{100 * value:.1f}%"


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# E5 — typed-layer ablation in rare-disease prediction",
        "",
        "Generated by `scripts/e5_typed_layer_ablation.py`; do not edit.",
        "",
        f"PhysioMap `{result['physiomap_version']}`; HPO `{result['hpo_release']}`.",
        "",
        "## Forward phenotype prediction",
        "",
        "| configuration | causal arcs | production shadow arcs | quantitative shadow arcs | constitution constraints | determinate | correct | wrong | abstain | precision |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for config_id in result["configuration_order"]:
        record = result["results"][config_id]
        active = record["active_relations"]
        metrics = record["forward"]["metrics"]
        lines.append(
            f"| {record['label']} | {active['causal_arcs']} | "
            f"{active['production_shadow_arcs']} | {active['quantitative_shadow_arcs']} | "
            f"{active['constitutive_constraints']} | {metrics['determinate']} | "
            f"{metrics['correct']} | {metrics['wrong']} | {metrics['abstain']} | "
            f"{_percent(metrics['precision'])} |"
        )
    lines.extend(
        [
            "",
            "## Inverse closed-pool lesion ranking",
            "",
            "| configuration | genes | unique top-1 | top-3 | top-10 | MRR | median rank |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for config_id in result["configuration_order"]:
        record = result["results"][config_id]
        metrics = record["inverse"]["metrics"]
        lines.append(
            f"| {record['label']} | {metrics['genes_scored']} | "
            f"{metrics['unique_top1']} | {metrics['top3']} | {metrics['top10']} | "
            f"{metrics['mrr']:.3f} | {metrics['median_rank']} |"
        )
    lines.extend(
        [
            "",
            "## Pairwise effect relative to the complete evaluated fragment",
            "",
            "| configuration | changed forward pairs | lost determinate | gained determinate | sign flips | changed inverse ranks |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for config_id in result["configuration_order"][:-1]:
        comparison = result["comparisons_to_full"][config_id]
        forward = comparison["forward"]
        inverse = comparison["inverse"]
        lines.append(
            f"| {result['results'][config_id]['label']} | "
            f"{forward['changed_pairs']} | {forward['determinate_to_abstain']} | "
            f"{forward['abstain_to_determinate']} | {forward['sign_flips']} | "
            f"{inverse['changed_genes']} |"
        )
    modulation = result["modulation"]
    lines.extend(
        [
            "",
            "Modulation records are not read by the comparative-static solver. "
            f"Removing all {modulation['records']} records changes the operational graph: "
            f"**{str(modulation['removal_changes_operational_graph']).lower()}**.",
            "",
        ]
    )
    return "\n".join(lines)


def render_latex(result: dict[str, Any]) -> str:
    rows = []
    for config_id in result["configuration_order"]:
        record = result["results"][config_id]
        forward = record["forward"]["metrics"]
        inverse = record["inverse"]["metrics"]
        label = record["label"].replace("+", r"\(+\)")
        coverage = _percent(forward["coverage"]).replace("%", r"\%")
        rows.append(
            f"{label} & {forward['determinate']} & {coverage} & "
            f"{inverse['top3']}/{inverse['genes_scored']} & "
            f"{inverse['mrr']:.3f} \\\\"
        )
    return "\n".join(
        [
            "% Generated by scripts/e5_typed_layer_ablation.py; do not edit.",
            r"\begin{tabular}{lrrrr}",
            r"\toprule",
            r"active relation layers & determinate & coverage & top-3 & MRR\\",
            r"\midrule",
            *rows,
            r"\bottomrule",
            r"\end{tabular}",
            "",
        ]
    )


def write_or_check(path: Path, content: str, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            raise SystemExit(f"stale typed-layer ablation artifact: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-json", type=Path, default=OUT_JSON)
    parser.add_argument("--output-md", type=Path, default=OUT_MD)
    parser.add_argument("--output-tex", type=Path)
    args = parser.parse_args()

    result = build_result()
    json_text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    write_or_check(args.output_json, json_text, args.check)
    write_or_check(args.output_md, render_markdown(result), args.check)
    output_tex = args.output_tex or OUT_TEX
    paper_outputs = args.output_tex is not None or (ROOT / "paper").is_dir()
    if paper_outputs:
        write_or_check(output_tex, render_latex(result), args.check)
    if args.check:
        print("typed-layer ablation artifacts: current")
    else:
        print(f"wrote {args.output_json}")
        print(f"wrote {args.output_md}")
        if paper_outputs:
            print(f"wrote {output_tex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
