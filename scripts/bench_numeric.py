#!/usr/bin/env python3
"""Comprehensive numeric cross-validation benchmark (evaluation family 2/10).

For every intervention in every benchmark directory, Monte-Carlo over stable (Hurwitz)
numeric Jacobians consistent with the PhysioMap sign pattern and compare to the qualitative
solver: a determinate sign must never be numerically contradicted (soundness), and each
'?' is classed warranted (numerically flips) or conservative (numerically stable).

Run:  uv run python scripts/bench_numeric.py [n_samples] [--workers N]
Writes benchmarks/results/numeric_validation.{md,json}.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import yaml

from physiomap_core.model import PhysioMap, Sign
from physiomap_core.qualitative import Intervention
from physiomap_core.validate import cross_validate

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "benchmarks"
DIRS = ["guyton", "human"]  # causal-dynamics maps (constitutive layer is not stochastic)


def _load_map(d: Path) -> PhysioMap:
    spec = yaml.safe_load((d / "interventions.yaml").read_text())
    if spec.get("systems"):
        return PhysioMap.load_composed([d / p for p in spec["systems"]], name=d.name)
    return PhysioMap.from_yaml(d / spec.get("map", "guyton_cv_core.yaml"))


def _one(args):
    dname, case, n_samples = args
    d = BENCH / dname
    pmap = _load_map(d)
    do = {k: Sign(v) for k, v in case["do"].items()}
    s = cross_validate(
        pmap, Intervention(targets=do), n_samples=n_samples, seed=11, offdiag_max=0.8
    )
    return {
        "map": dname,
        "intervention": case["id"],
        "samples": s.samples,
        "evaluable": s.samples > 0,
        "determinate_confirmed": s.determinate_confirmed,
        "sound": s.sound,
        "contradictions": s.contradictions,
        "warranted_unknown": len(s.warranted_unknown),
        "conservative_unknown": s.conservative_unknown,
    }


def main(n_samples: int = 2000, max_workers: int | None = None) -> int:
    tasks = []
    for dname in DIRS:
        spec = yaml.safe_load((BENCH / dname / "interventions.yaml").read_text())
        for case in spec["interventions"]:
            tasks.append((dname, case, n_samples))

    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(_one, tasks))

    evaluable = [r for r in results if r["evaluable"]]
    unevaluable = [r for r in results if not r["evaluable"]]
    n_sound = sum(1 for r in evaluable if r["sound"])
    total_contra = sum(len(r["contradictions"]) for r in results)
    total_det = sum(r["determinate_confirmed"] for r in results)
    total_warr = sum(r["warranted_unknown"] for r in results)
    total_cons = sum(len(r["conservative_unknown"]) for r in results)

    out_dir = BENCH / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "numeric_validation.json").write_text(json.dumps(results, indent=2))

    lines = ["# Numeric cross-validation (family 2/10)", ""]
    lines.append(f"- samples/intervention (target): **{n_samples}**")
    lines.append(f"- interventions tested: **{len(results)}**")
    lines.append(
        f"- **SOUND: {n_sound}/{len(evaluable)} evaluable** interventions with zero numeric "
        f"contradictions ({total_contra} total contradictions)"
    )
    lines.append(
        f"- interventions with no stable draw (not evaluable): **{len(unevaluable)}**"
    )
    lines.append(f"- determinate signs confirmed numerically: **{total_det}**")
    lines.append(
        f"- '?' classed: **{total_warr} warranted** (flips), **{total_cons} conservative** "
        f"(numerically stable)"
    )
    lines.append("")
    lines.append("| map | intervention | stable draws | det. confirmed | sound | "
                 "warranted? | conservative? |")
    lines.append("|---|---|--:|--:|:--:|--:|--:|")
    for r in results:
        lines.append(
            f"| {r['map']} | {r['intervention']} | {r['samples']} | "
            f"{r['determinate_confirmed']} | "
            f"{'N/A' if not r['evaluable'] else ('OK' if r['sound'] else 'FAIL')} | "
            f"{r['warranted_unknown']} | {len(r['conservative_unknown'])} |"
        )
    if unevaluable:
        lines += ["", "## Interventions without a stable draw"]
        for r in unevaluable:
            lines.append(f"- [{r['map']}/{r['intervention']}] 0/{n_samples} stable draws")
    if total_contra:
        lines += ["", "## Contradictions (soundness failures)"]
        for r in results:
            for c in r["contradictions"]:
                lines.append(f"- [{r['map']}/{r['intervention']}] {c}")
    if total_cons:
        lines += ["", "## Conservative '?' (qualitatively abstains, numerically stable)"]
        for r in results:
            for c in r["conservative_unknown"]:
                lines.append(f"- [{r['map']}/{r['intervention']}] {c}")
    (out_dir / "numeric_validation.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if total_contra == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("n_samples", nargs="?", type=int, default=2000)
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="maximum worker processes (default: Python executor default)",
    )
    args = parser.parse_args()
    if args.workers is not None and args.workers < 1:
        parser.error("--workers must be at least 1")
    sys.exit(main(args.n_samples, args.workers))
