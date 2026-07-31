"""Evaluation harness: run interventions through the solver and score against gold.

Loads a benchmark directory containing a PhysioMap fixture and an ``interventions.yaml``
gold file, runs :func:`physiomap_core.qualitative.solve_signs`, and reports **directional
accuracy** (correct signs / signs scored), with ambiguous (``?``) predictions counted
separately, plus a per-node table and per-loop ("loop-critical") accuracy.

CLI::

    python -m physiomap_core.eval benchmarks/guyton
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from physiomap_core.model import PhysioMap, Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention, solve_signs

__all__ = ["CaseScore", "BenchmarkReport", "run_benchmark", "main"]


class NodeOutcome(BaseModel):
    node: str
    expected: Sign
    predicted: Sign | None = None  # None = no change / unreachable
    loop_critical: bool = False

    @property
    def status(self) -> str:
        if self.predicted is None:
            return "missing"
        if self.predicted is Sign.UNKNOWN:
            return "ambiguous"
        return "correct" if self.predicted is self.expected else "wrong"


class CaseScore(BaseModel):
    intervention: str
    label: str | None = None
    contexts: list[str] = Field(default_factory=list)
    outcomes: list[NodeOutcome] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)

    def _count(self, status: str) -> int:
        return sum(1 for o in self.outcomes if o.status == status)

    @property
    def correct(self) -> int:
        return self._count("correct")

    @property
    def wrong(self) -> int:
        return self._count("wrong")

    @property
    def ambiguous(self) -> int:
        return self._count("ambiguous") + self._count("missing")

    @property
    def loop_correct(self) -> int:
        return sum(1 for o in self.outcomes if o.loop_critical and o.status == "correct")

    @property
    def loop_total(self) -> int:
        return sum(1 for o in self.outcomes if o.loop_critical)


class BenchmarkReport(BaseModel):
    cases: list[CaseScore] = Field(default_factory=list)

    @property
    def correct(self) -> int:
        return sum(c.correct for c in self.cases)

    @property
    def wrong(self) -> int:
        return sum(c.wrong for c in self.cases)

    @property
    def ambiguous(self) -> int:
        return sum(c.ambiguous for c in self.cases)

    @property
    def scored(self) -> int:
        return self.correct + self.wrong

    @property
    def total(self) -> int:
        return self.correct + self.wrong + self.ambiguous

    @property
    def directional_accuracy(self) -> float:
        """Correct / (correct + wrong) — ambiguous '?' excluded (reported separately)."""
        return (self.correct / self.scored) if self.scored else 0.0

    @property
    def loop_correct(self) -> int:
        return sum(c.loop_correct for c in self.cases)

    @property
    def loop_total(self) -> int:
        return sum(c.loop_total for c in self.cases)


def run_benchmark(benchmark_dir: str | Path) -> BenchmarkReport:
    """Load fixtures + gold interventions from ``benchmark_dir`` and score the solver."""
    d = Path(benchmark_dir)
    spec = yaml.safe_load((d / "interventions.yaml").read_text(encoding="utf-8"))
    if spec.get("systems"):  # composed multi-fragment map
        pmap = PhysioMap.load_composed([d / p for p in spec["systems"]], name=d.name)
    else:
        pmap = PhysioMap.from_yaml(d / spec.get("map", "guyton_cv_core.yaml"))

    multiscale = bool(spec.get("multiscale"))
    report = BenchmarkReport()
    for case in spec["interventions"]:
        do = {k: Sign(v) for k, v in case["do"].items()}
        expected = {k: Sign(v) for k, v in case["expected"].items()}
        loop_set = set(case.get("loop_critical") or [])
        contexts = list(case.get("contexts") or [])
        intervention = Intervention(targets=do, label=case.get("id"))
        result = (
            solve_multiscale(pmap, intervention, contexts=contexts)
            if multiscale
            else solve_signs(pmap, intervention, contexts=contexts)
        )

        outcomes = [
            NodeOutcome(
                node=node,
                expected=ev,
                predicted=result.predicted.get(node),
                loop_critical=node in loop_set,
            )
            for node, ev in expected.items()
        ]
        report.cases.append(
            CaseScore(
                intervention=case["id"],
                label=case.get("label"),
                contexts=contexts,
                outcomes=outcomes,
                ambiguities=result.ambiguities,
            )
        )
    return report


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

_MARK = {"correct": "OK ", "wrong": "XX ", "ambiguous": " ? ", "missing": " . "}


def _render(report: BenchmarkReport) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("PhysioMap benchmark — qualitative comparative-statics signs")
    lines.append("=" * 72)
    for c in report.cases:
        lines.append("")
        context_label = f" [context: {', '.join(c.contexts)}]" if c.contexts else ""
        lines.append(f"### {c.intervention}{context_label}  —  {c.label or ''}".rstrip())
        for o in c.outcomes:
            pv = o.predicted.value if o.predicted is not None else "—"
            tag = " [loop]" if o.loop_critical else ""
            lines.append(
                f"  {_MARK[o.status]} {o.node:30s} expected={o.expected.value}  "
                f"predicted={pv}{tag}"
            )
        lines.append(
            f"   -> correct={c.correct} wrong={c.wrong} ambiguous={c.ambiguous}"
            f"   (loop-critical {c.loop_correct}/{c.loop_total})"
        )
    lines.append("")
    lines.append("-" * 72)
    lines.append(
        f"TOTAL  scored={report.scored}  correct={report.correct}  wrong={report.wrong}"
        f"  ambiguous={report.ambiguous}"
    )
    lines.append(
        f"Directional accuracy (correct / scored) = {report.directional_accuracy:.1%}"
        f"   |  ambiguous = {report.ambiguous}/{report.total}"
    )
    lines.append(
        f"Loop-critical net signs correct = {report.loop_correct}/{report.loop_total}"
    )
    lines.append("-" * 72)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``python -m physiomap_core.eval <benchmark_dir>``."""
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: python -m physiomap_core.eval <benchmark_dir>", file=sys.stderr)
        return 2
    report = run_benchmark(args[0])
    print(_render(report))
    # Exit 0 as long as nothing is predicted with the WRONG sign (soundness).
    return 0 if report.wrong == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
