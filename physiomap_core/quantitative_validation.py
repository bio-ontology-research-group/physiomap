"""Exact and numerical validation of generated quantitative SCM semantics."""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, Field

from physiomap_core.scm import ScmManifest


class QuantitativeValidationReport(BaseModel):
    errors: list[str] = Field(default_factory=list)
    exact_rules_checked: int = 0
    numerical_trials: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _sign(value: float, tolerance: float = 1e-7) -> str:
    if value > tolerance:
        return "+"
    if value < -tolerance:
        return "-"
    return "?"


def validate_quantitative_manifest(manifest: ScmManifest, trials: int = 16,
                                   seed: int = 20260711) -> QuantitativeValidationReport:
    """Check predefined derivatives exactly and realize every sign numerically.

    General structural functions are realized as signed linear functions. This does not assert
    linear physiology; it proves the declared local derivative constraints are jointly realizable.
    Modulation uses ``y = mu*m*x`` and verifies the declared mixed derivative by finite differences.
    """
    report = QuantitativeValidationReport()
    rng = np.random.default_rng(seed)
    for expression in manifest.quantitative_expressions:
        if expression.kind == "ratio":
            if len(expression.arguments) != 2 or [a.role for a in expression.arguments] != [
                    "numerator", "denominator"]:
                report.errors.append(f"{expression.id}: ratio requires numerator and denominator")
                continue
            expected = ["+", "-"]
            got = [a.derivative_sign for a in expression.arguments]
            report.exact_rules_checked += 2
            if got != expected:
                report.errors.append(f"{expression.id}: ratio derivative signs {got}, expected {expected}")
            for _ in range(trials):
                numerator, denominator = rng.uniform(0.1, 100, size=2)
                exact = (1.0 / denominator, -numerator / denominator**2)
                if [_sign(value) for value in exact] != expected:
                    report.errors.append(f"{expression.id}: ratio numerical realization failed")
                    break
                report.numerical_trials += 1
        elif expression.kind in {"aggregation", "sum"}:
            report.exact_rules_checked += len(expression.arguments)
            bad = [a.node for a in expression.arguments if a.derivative_sign != "+"]
            if bad:
                report.errors.append(f"{expression.id}: additive arguments are not positive: {bad}")
            for _ in range(trials):
                values = rng.normal(size=len(expression.arguments))
                baseline = float(values.sum())
                epsilon = 1e-5
                signs = []
                for index in range(len(values)):
                    moved = values.copy(); moved[index] += epsilon
                    signs.append(_sign((float(moved.sum()) - baseline) / epsilon))
                if signs != ["+"] * len(values):
                    report.errors.append(f"{expression.id}: aggregation numerical realization failed")
                    break
                report.numerical_trials += 1
        elif expression.kind == "product":
            report.exact_rules_checked += len(expression.arguments)
            if any(argument.derivative_sign != "+" for argument in expression.arguments):
                report.errors.append(f"{expression.id}: positive-domain product factors must be positive")
            for _ in range(trials):
                values = rng.uniform(0.1, 10, size=len(expression.arguments))
                derivatives = [float(np.prod(np.delete(values, index)))
                               for index in range(len(values))]
                if [_sign(value) for value in derivatives] != [argument.derivative_sign
                                                                for argument in expression.arguments]:
                    report.errors.append(f"{expression.id}: product derivative realization failed")
                    break
                report.numerical_trials += 1
        elif expression.kind in {"structural-function", "rate"}:
            coefficients = np.array([1.0 if a.derivative_sign == "+" else
                                     -1.0 if a.derivative_sign == "-" else 0.0
                                     for a in expression.arguments])
            report.exact_rules_checked += len(expression.arguments)
            for _ in range(trials):
                values = rng.normal(size=len(coefficients))
                epsilon = 1e-5
                baseline = float(coefficients @ values)
                signs = []
                for index in range(len(values)):
                    moved = values.copy(); moved[index] += epsilon
                    signs.append(_sign((float(coefficients @ moved) - baseline) / epsilon))
                declared = [a.derivative_sign for a in expression.arguments]
                if signs != declared:
                    report.errors.append(f"{expression.id}: sign constraints are not realizable")
                    break
                report.numerical_trials += 1
    for modulation in manifest.modulation:
        mu = 1.0 if modulation.sign == "+" else -1.0
        epsilon = 1e-4
        for _ in range(trials):
            x, m = rng.uniform(0.1, 10, size=2)
            f = lambda xv, mv: mu * xv * mv
            mixed = (f(x + epsilon, m + epsilon) - f(x + epsilon, m - epsilon)
                     - f(x - epsilon, m + epsilon) + f(x - epsilon, m - epsilon)) / (4 * epsilon**2)
            if not math.isfinite(mixed) or _sign(mixed, 1e-5) != modulation.sign:
                report.errors.append(f"{modulation.id}: mixed-derivative realization failed")
                break
            report.numerical_trials += 1
        report.exact_rules_checked += 1
    return report
