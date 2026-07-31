"""Numeric cross-validation of the qualitative solver against ground-truth dynamics.

The qualitative comparative-statics solver makes a falsifiable claim: a **determinate**
sign (`+`/`-`) must hold for *every* stable parameterization of the system, and a `?`
means the sign genuinely depends on the (unknown) magnitudes. This module checks that
claim by Monte-Carlo over numeric realizations consistent with the PhysioMap sign pattern.

For an intervention we build the linearized steady-state system on the (do-surgered,
reachable) causal graph: ``dx/dt = J x + b``, with ``J`` carrying a negative diagonal
(dissipation) and off-diagonal entries whose *sign* is the edge sign and whose *magnitude*
is sampled; ``b`` is the forcing from the clamped intervened nodes. We keep only **Hurwitz**
(asymptotically stable) draws and read ``sign(x*) = sign(-J^{-1} b)`` per node.

Then per reachable node:
* **soundness** — if the qualitative solver returned a determinate sign, the numeric sign
  must (almost) never contradict it across the stable ensemble;
* **sharpness** — a qualitative `?` is *warranted* when the numeric sign flips across the
  ensemble; a `?` whose numeric sign never flips is a (sound but) conservative miss.
"""

from __future__ import annotations

import numpy as np
import networkx as nx
from pydantic import BaseModel, Field

from physiomap_core.model import PhysioMap, Sign
from physiomap_core.qualitative import Intervention, solve_signs

__all__ = ["NumericSummary", "numeric_signs", "cross_validate"]


def _numeric_sign(value: float, tol: float) -> str:
    if value > tol:
        return "+"
    if value < -tol:
        return "-"
    return "0"


def numeric_signs(
    pmap: PhysioMap,
    intervention: Intervention,
    n_samples: int = 300,
    seed: int = 0,
    tol: float = 1e-9,
    offdiag_max: float = 1.0,
) -> dict[str, dict[str, int]]:
    """Sample stable numeric realizations; return per-node sign-count distributions.

    Returns ``{node: {'+': k+, '-': k-, '0': k0}}`` over the kept (Hurwitz) samples.
    """
    g = pmap.causal_subgraph()
    fixed = {t: (1.0 if s is Sign.PLUS else -1.0) for t, s in intervention.targets.items()}
    gi = g.copy()
    for t in fixed:
        gi.remove_edges_from([(p, t) for p in list(gi.predecessors(t))])

    reach: set[str] = set(fixed)
    for t in fixed:
        reach |= nx.descendants(gi, t)
    internal = sorted(reach - set(fixed))
    idx = {n: i for i, n in enumerate(internal)}
    m = len(internal)
    counts: dict[str, dict[str, int]] = {n: {"+": 0, "-": 0, "0": 0} for n in internal}
    if m == 0:
        return counts

    # static edge sign maps
    edges_int = [
        (idx[u], idx[v], 1.0 if g.edges[u, v]["sign"] == "+" else -1.0)
        for u, v in gi.edges
        if u in idx and v in idx
    ]
    edges_fix = [
        (idx[v], fixed[u], 1.0 if g.edges[u, v]["sign"] == "+" else -1.0)
        for u, v in gi.edges
        if u in fixed and v in idx
    ]

    rng = np.random.default_rng(seed)
    kept = 0
    attempts = 0
    max_attempts = n_samples * 50
    while kept < n_samples and attempts < max_attempts:
        attempts += 1
        jac = np.zeros((m, m))
        for i in range(m):
            jac[i, i] = -rng.uniform(0.2, 1.5)  # negative diagonal (dissipation)
        # J[v, u] = sign * magnitude: partial of v's equation w.r.t. its parent u
        for u_i, v_i, s in edges_int:
            jac[v_i, u_i] = s * rng.uniform(0.1, offdiag_max)
        eig = np.linalg.eigvals(jac)
        if np.max(eig.real) >= -1e-9:
            continue  # reject non-Hurwitz draw
        b = np.zeros(m)
        for v_i, xfix, s in edges_fix:
            b[v_i] += s * rng.uniform(0.1, offdiag_max) * xfix
        try:
            x = np.linalg.solve(jac, -b)  # J x = -b  ->  x* = -J^{-1} b
        except np.linalg.LinAlgError:
            continue
        for n in internal:
            counts[n][_numeric_sign(x[idx[n]], tol)] += 1
        kept += 1
    counts["__kept__"] = {"samples": kept, "attempts": attempts}  # type: ignore[assignment]
    return counts


class NumericSummary(BaseModel):
    """Per-node comparison of the qualitative prediction to the numeric ensemble."""

    samples: int = 0
    sound: bool = True
    contradictions: list[str] = Field(default_factory=list)
    warranted_unknown: list[str] = Field(default_factory=list)  # '?' that numerically flips
    conservative_unknown: list[str] = Field(default_factory=list)  # '?' numerically stable
    determinate_confirmed: int = 0


def cross_validate(
    pmap: PhysioMap,
    intervention: Intervention,
    n_samples: int = 300,
    seed: int = 0,
    dominance: float = 0.98,
    offdiag_max: float = 1.0,
) -> NumericSummary:
    """Compare the qualitative solver to the stable numeric ensemble for one intervention.

    ``dominance`` is the fraction of samples that must agree for a numeric sign to count as
    "the" numeric sign (robust to a few near-zero draws).
    """
    counts = numeric_signs(
        pmap, intervention, n_samples=n_samples, seed=seed, offdiag_max=offdiag_max
    )
    kept = counts.pop("__kept__", {"samples": 0})["samples"]  # type: ignore[index]
    qual = solve_signs(pmap, intervention).predicted

    out = NumericSummary(samples=kept)
    for node, dist in counts.items():
        total = dist["+"] + dist["-"] + dist["0"]
        if total == 0:
            continue
        frac_plus, frac_minus = dist["+"] / total, dist["-"] / total
        numeric_determinate = max(frac_plus, frac_minus) >= dominance
        numeric_sign = "+" if frac_plus >= frac_minus else "-"
        q = qual.get(node)
        if q in (Sign.PLUS, Sign.MINUS):
            out.determinate_confirmed += 1
            # soundness: a determinate qualitative sign must not be numerically contradicted
            opposite = "-" if q is Sign.PLUS else "+"
            if (dist[opposite] / total) > (1.0 - dominance):
                out.sound = False
                out.contradictions.append(
                    f"{node}: qualitative {q.value} but numeric {opposite}="
                    f"{dist[opposite]}/{total}"
                )
        elif q is Sign.UNKNOWN:
            if numeric_determinate:
                out.conservative_unknown.append(f"{node}: numeric {numeric_sign} stable")
            else:
                out.warranted_unknown.append(node)
    return out
