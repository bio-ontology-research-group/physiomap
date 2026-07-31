#!/usr/bin/env python3
"""Generate the PSB rare-disease results figure and LaTeX result macros.

Inputs are the canonical SCM plus the machine-readable E1b, E2, E2c, and E4
evaluation outputs. Run the evaluation scripts first:

  uv run python scripts/e1b_eval.py --leakage-sensitivity
  uv run python scripts/e2_baseline.py
  uv run --extra analysis python scripts/e2c_risk_coverage.py
  uv run python scripts/e4_diagnose.py
"""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import PercentFormatter

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "benchmarks/results"
PAPER = ROOT / "paper"
FIGURE = PAPER / "figures/fig_rare_disease.pdf"
MACROS = PAPER / "generated/rare-disease-results.tex"
SUMMARY = ROOT / "docs/generated/rare-disease-results.json"
SCM_PATH = ROOT / "release/owl-scm/physiomap-scm.json"
WORKLIST = ROOT / "docs/generated/legacy-evidence-worklist.json"

BLUE = "#2F6690"
TEAL = "#2A9D8F"
ORANGE = "#E76F51"
GOLD = "#E9C46A"
GREY = "#6B7280"
LIGHT_BLUE = "#EAF2F8"
LIGHT_ORANGE = "#FCEFEA"

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
        "font.size": 8,
        "axes.titlesize": 9.5,
        "axes.labelsize": 8,
        "xtick.labelsize": 7.3,
        "ytick.labelsize": 7.3,
        "legend.fontsize": 7.2,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_int(value: int) -> str:
    return f"{value:,}".replace(",", "{,}")


def macro(name: str, value: object) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}}}"


def build_summary() -> dict:
    scm = load_json(SCM_PATH)
    forward = load_json(RESULTS / "e1b_forward.json")
    baseline = load_json(RESULTS / "e2_baseline.json")
    diagnosis = load_json(RESULTS / "e4_diagnosis.json")
    diagnosis_baselines = load_json(RESULTS / "e4b_diagnosis_baselines.json")
    worklist = load_json(WORKLIST)["summary"]
    evidence = Counter(
        edge.get("causal_evidence") or "unclassified" for edge in scm["influences"]
    )
    pmap = build_map()
    largest_scc = max(len(component) for component in pmap.sccs())

    # The biological example is also checked against the same solver and release.
    hfe = solve_multiscale(
        pmap, Intervention(targets={"hepcidin": Sign.MINUS}, label="HFE loss of function")
    ).predicted
    if hfe.get("plasma_iron") is not Sign.PLUS:
        raise SystemExit("HFE example drift: plasma iron is not predicted positive")
    if hfe.get("transferrin_saturation") is not Sign.PLUS:
        raise SystemExit("HFE example drift: transferrin saturation is not predicted positive")

    return {
        "schema_version": "1.0.0",
        "physiomap_version": scm["physiomap_version"],
        "traits": len(scm["nodes"]),
        "influences": len(scm["influences"]),
        "production_relations": len(scm["production_relations"]),
        "constitutive_constraints": len(scm["constitutive_constraints"]),
        "quantitative_expressions": len(scm["quantitative_expressions"]),
        "modulations": len(scm["modulation"]),
        "largest_scc": largest_scc,
        "controlled_influences": sum(
            edge["evidence_status"] == "controlled" for edge in scm["influences"]
        ),
        "legacy_unclassified": evidence["unclassified"],
        "interventional_influences": (
            evidence["genetic_lof_gof"]
            + evidence["pharmacological"]
            + evidence["perturbation"]
        ),
        "mechanistic_influences": (
            evidence["curated_mechanistic"] + evidence["mechanistic_model"]
        ),
        "legacy_review": {
            "baseline": worklist["baseline_total"],
            "approved": worklist["approved_resolved"],
            "open": worklist["open"],
        },
        "forward": forward,
        "baseline": baseline,
        "diagnosis": diagnosis,
        "diagnosis_baselines": diagnosis_baselines,
    }


def render_macros(summary: dict) -> str:
    full = summary["forward"]["full"]
    controlled = summary["forward"]["leakage_controlled"]
    baseline = summary["baseline"]["methods"]
    diagnosis = summary["diagnosis"]
    feedback = summary["baseline"]["feedback_contrast"]
    values = [
        ("PMVersion", summary["physiomap_version"]),
        ("PMTraits", fmt_int(summary["traits"])),
        ("PMInfluences", fmt_int(summary["influences"])),
        ("PMProduction", fmt_int(summary["production_relations"])),
        ("PMConstitutive", fmt_int(summary["constitutive_constraints"])),
        ("PMQuantitative", fmt_int(summary["quantitative_expressions"])),
        ("PMModulations", fmt_int(summary["modulations"])),
        ("PMLargestSCC", fmt_int(summary["largest_scc"])),
        ("PMControlledInfluences", fmt_int(summary["controlled_influences"])),
        ("PMLegacyUnclassified", fmt_int(summary["legacy_unclassified"])),
        ("PMInterventionalInfluences", fmt_int(summary["interventional_influences"])),
        ("PMMechanisticInfluences", fmt_int(summary["mechanistic_influences"])),
        ("PMReviewBaseline", fmt_int(summary["legacy_review"]["baseline"])),
        ("PMReviewApproved", fmt_int(summary["legacy_review"]["approved"])),
        ("PMReviewOpen", fmt_int(summary["legacy_review"]["open"])),
        ("PMHPORelease", summary["forward"]["hpo_release"].rsplit("/", 1)[-1]),
        ("PMForwardGenes", fmt_int(full["genes_scored"])),
        ("PMForwardPairs", fmt_int(full["determinate"] + full["abstain"])),
        ("PMForwardDeterminate", fmt_int(full["determinate"])),
        ("PMForwardCorrect", fmt_int(full["correct"])),
        ("PMForwardWrong", fmt_int(full["wrong"])),
        ("PMForwardAbstain", fmt_int(full["abstain"])),
        ("PMForwardPrecision", f"{100 * full['precision']:.1f}\\%"),
        (
            "PMForwardCoverage",
            f"{100 * full['determinate'] / (full['determinate'] + full['abstain']):.1f}\\%",
        ),
        ("PMLeakageGenes", fmt_int(controlled["genes_scored"])),
        ("PMLeakageDeterminate", fmt_int(controlled["determinate"])),
        ("PMLeakageCorrect", fmt_int(controlled["correct"])),
        ("PMLeakageAbstain", fmt_int(controlled["abstain"])),
        ("PMShortestDeterminate", fmt_int(baseline["naive-shortest"]["determinate"])),
        ("PMShortestCorrect", fmt_int(baseline["naive-shortest"]["correct"])),
        ("PMShortestWrong", fmt_int(baseline["naive-shortest"]["wrong"])),
        ("PMShortestPrecision", f"{100 * baseline['naive-shortest']['precision']:.1f}\\%"),
        ("PMForwardPathDeterminate", fmt_int(baseline["naive-forward"]["determinate"])),
        ("PMForwardPathCorrect", fmt_int(baseline["naive-forward"]["correct"])),
        ("PMForwardPathWrong", fmt_int(baseline["naive-forward"]["wrong"])),
        ("PMForwardPathPrecision", f"{100 * baseline['naive-forward']['precision']:.1f}\\%"),
        ("PMFeedbackPairs", fmt_int(feedback["pairs"])),
        ("PMFeedbackNaiveCorrect", fmt_int(feedback["naive_shortest_correct"])),
        ("PMFeedbackNaiveAccuracy", f"{100 * feedback['naive_shortest_accuracy']:.1f}\\%"),
        ("PMDiagnosisGenes", fmt_int(diagnosis["genes_scored"])),
        ("PMDiagnosisPool", fmt_int(diagnosis["candidate_pool"])),
        ("PMDiagnosisTopOne", fmt_int(diagnosis["unique_top1"])),
        ("PMDiagnosisTopThree", fmt_int(diagnosis["top3"])),
        ("PMDiagnosisTopTen", fmt_int(diagnosis["top10"])),
        ("PMDiagnosisTopOnePct", f"{100 * diagnosis['unique_top1'] / diagnosis['genes_scored']:.0f}\\%"),
        ("PMDiagnosisTopThreePct", f"{100 * diagnosis['top3'] / diagnosis['genes_scored']:.0f}\\%"),
        ("PMDiagnosisTopTenPct", f"{100 * diagnosis['top10'] / diagnosis['genes_scored']:.0f}\\%"),
        ("PMDiagnosisMRR", f"{diagnosis['mrr']:.3f}"),
        ("PMDiagnosisMedian", f"{diagnosis['median_rank']:.0f}"),
    ]
    return (
        "% Generated by scripts/generate_psb_rare_disease_figure.py; do not edit.\n"
        + "\n".join(macro(name, value) for name, value in values)
        + "\n"
    )


def draw_box(
    ax,
    xy,
    width,
    height,
    text,
    *,
    face="#ffffff",
    edge=GREY,
    weight="normal",
):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.025",
        facecolor=face,
        edgecolor=edge,
        linewidth=0.9,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=7.8,
        fontweight=weight,
    )
    return patch


def draw_arrow(ax, start, end, sign, *, color=GREY):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=1.0,
            color=color,
        )
    )
    midx = (start[0] + end[0]) / 2
    midy = (start[1] + end[1]) / 2
    ax.text(
        midx + 0.045,
        midy,
        sign,
        ha="left",
        va="center",
        fontsize=8.0,
        fontweight="bold",
    )


def render_figure(summary: dict, target: Path) -> None:
    with (RESULTS / "e2c_risk_coverage.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    diffusion = [row for row in rows if row["method"] == "signed_diffusion"]
    full = summary["forward"]["full"]
    shortest = summary["baseline"]["methods"]["naive-shortest"]
    diagnosis = summary["diagnosis"]
    diagnosis_arms = summary["diagnosis_baselines"]["arms"]
    total_pairs = full["determinate"] + full["abstain"]

    fig = plt.figure(figsize=(10.3, 5.25))
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=(0.92, 1.50),
        height_ratios=(1.12, 0.96),
        hspace=0.52,
        wspace=0.34,
    )
    trace = fig.add_subplot(grid[:, 0])
    risk = fig.add_subplot(grid[0, 1])
    rank = fig.add_subplot(grid[1, 1])

    trace.set_xlim(0, 1)
    trace.set_ylim(0, 1)
    trace.axis("off")
    trace.set_title(
        "a  One forward prediction",
        loc="left",
        fontweight="bold",
        pad=5,
    )
    trace.text(
        0.5,
        0.955,
        "HFE-related haemochromatosis",
        ha="center",
        va="top",
        fontsize=8.3,
        fontweight="bold",
    )
    [
        draw_box(
            trace,
            (0.14, 0.78),
            0.72,
            0.105,
            "intervention\n$\\mathrm{do}(\\mathrm{hepcidin}\\!\\downarrow)$",
            face=LIGHT_ORANGE,
            edge=ORANGE,
            weight="bold",
        ),
        draw_box(
            trace,
            (0.14, 0.56),
            0.72,
            0.105,
            "ferroportin activity $\\uparrow$",
        ),
        draw_box(
            trace,
            (0.14, 0.34),
            0.72,
            0.105,
            "plasma iron $\\uparrow$   $\\checkmark$ HPOA",
            face=LIGHT_BLUE,
            edge=BLUE,
        ),
        draw_box(
            trace,
            (0.14, 0.12),
            0.72,
            0.105,
            "transferrin saturation $\\uparrow$   $\\checkmark$ HPOA",
            face=LIGHT_BLUE,
            edge=BLUE,
        ),
    ]
    draw_arrow(trace, (0.50, 0.78), (0.50, 0.67), "$-$")
    draw_arrow(trace, (0.50, 0.56), (0.50, 0.45), "$+$")
    draw_arrow(trace, (0.50, 0.34), (0.50, 0.23), "$+$")
    trace.text(
        0.5,
        0.025,
        "Blue boxes are mapped directional HPOA phenotypes.",
        ha="center",
        va="bottom",
        fontsize=7.0,
        color=GREY,
        wrap=True,
    )

    risk.plot(
        [float(row["coverage"]) for row in diffusion],
        [float(row["precision"]) for row in diffusion],
        color=BLUE,
        linewidth=1.8,
        label="thresholded signed diffusion",
        zorder=1,
    )
    coverage = full["determinate"] / total_pairs
    shortest_coverage = shortest["determinate"] / total_pairs
    risk.scatter(
        [coverage],
        [full["precision"]],
        marker="D",
        s=54,
        color=ORANGE,
        edgecolor="white",
        linewidth=0.7,
        zorder=4,
        label="PhysioMap solver",
    )
    risk.scatter(
        [shortest_coverage],
        [shortest["precision"]],
        marker="o",
        s=48,
        color=GREY,
        edgecolor="white",
        linewidth=0.7,
        zorder=4,
        label="shortest signed path",
    )
    risk.annotate(
        f"{full['correct']}/{full['determinate']} correct, "
        f"{full['wrong']} wrong",
        xy=(coverage, full["precision"]),
        xytext=(coverage + 0.025, 0.985),
        ha="left",
        va="top",
        fontsize=7.1,
        color=ORANGE,
        arrowprops={"arrowstyle": "-", "color": ORANGE, "lw": 0.7},
    )
    risk.annotate(
        f"{shortest['correct']}/{shortest['determinate']} correct, "
        f"{shortest['wrong']} wrong",
        xy=(shortest_coverage, shortest["precision"]),
        xytext=(shortest_coverage - 0.012, 0.735),
        ha="right",
        va="bottom",
        fontsize=7.1,
        color=GREY,
        arrowprops={"arrowstyle": "-", "color": GREY, "lw": 0.7},
    )
    risk.set_title("b  Forward prediction", loc="left", fontweight="bold", pad=5)
    risk.set(
        xlabel="Coverage of 866 gene–phenotype pairs",
        ylabel="Precision",
        xlim=(0, 0.48),
        ylim=(0.70, 1.015),
    )
    risk.xaxis.set_major_formatter(PercentFormatter(1.0))
    risk.yaxis.set_major_formatter(PercentFormatter(1.0))
    risk.grid(alpha=0.16, linewidth=0.6)
    risk.spines[["top", "right"]].set_visible(False)
    risk.legend(loc="lower left", frameon=False, ncol=3, columnspacing=1.1)

    categories = ["unique top-1", "best-tied top-3", "best-tied top-10"]
    x_positions = range(len(categories))
    arm_specs = [
        ("comparative static", "PhysioMap solver", ORANGE, "D", "-", 2.2),
        ("shortest signed path", "shortest signed path", GREY, "o", "-", 1.3),
        (
            "signed diffusion (alpha=0.85)",
            "signed diffusion",
            BLUE,
            "s",
            "-",
            1.3,
        ),
        ("chance", "chance expectation", GOLD, "^", ":", 1.3),
    ]
    for key, label, color, marker, linestyle, linewidth in arm_specs:
        arm = diagnosis_arms[key]
        denominator = arm["scored"]
        values = [
            arm["top1"] / denominator,
            arm["top3"] / denominator,
            arm["top10"] / denominator,
        ]
        rank.plot(
            x_positions,
            values,
            label=label,
            color=color,
            marker=marker,
            markersize=4.6,
            linewidth=linewidth,
            linestyle=linestyle,
            zorder=3 if key == "comparative static" else 2,
        )
    rank.set_title(
        f"c  Inverse ranking among {diagnosis['candidate_pool']} lesions",
        loc="left",
        fontweight="bold",
        pad=5,
    )
    rank.set_xticks(list(x_positions), categories)
    rank.set(
        ylabel=f"Fraction of {diagnosis['genes_scored']} genes",
        ylim=(0, 1.04),
    )
    rank.yaxis.set_major_formatter(PercentFormatter(1.0))
    rank.grid(axis="y", alpha=0.16, linewidth=0.6)
    rank.spines[["top", "right"]].set_visible(False)
    rank.legend(loc="upper left", frameon=False, ncol=2, columnspacing=1.2)

    fig.subplots_adjust(left=0.055, right=0.985, top=0.94, bottom=0.115)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        target,
        bbox_inches="tight",
        metadata={
            "Title": "PhysioMap rare metabolic disease evaluation",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary = build_summary()
    macros = render_macros(summary)
    summary_text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    paper_outputs = PAPER.is_dir()

    if args.check:
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary) / "figure.pdf"
            render_figure(summary, candidate)
            stale = []
            if paper_outputs:
                if not FIGURE.is_file() or FIGURE.read_bytes() != candidate.read_bytes():
                    stale.append(str(FIGURE))
                if not MACROS.is_file() or MACROS.read_text(encoding="utf-8") != macros:
                    stale.append(str(MACROS))
            if not SUMMARY.is_file() or SUMMARY.read_text(encoding="utf-8") != summary_text:
                stale.append(str(SUMMARY))
            if stale:
                raise SystemExit("stale PSB rare-disease artifacts: " + ", ".join(stale))
        if paper_outputs:
            print("PSB rare-disease figure and macros: current")
        else:
            print("PSB rare-disease summary and figure rendering: current")
        return 0

    if paper_outputs:
        render_figure(summary, FIGURE)
        MACROS.parent.mkdir(parents=True, exist_ok=True)
        MACROS.write_text(macros, encoding="utf-8")
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(summary_text, encoding="utf-8")
    outputs = [str(SUMMARY.relative_to(ROOT))]
    if paper_outputs:
        outputs[:0] = [str(FIGURE), str(MACROS)]
    print(f"wrote {', '.join(outputs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
