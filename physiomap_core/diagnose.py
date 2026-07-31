"""Qualitative differential diagnosis by abduction.

The solver predicts the sign pattern of an intervention. **Inverting** that gives a useful
capability: given an observed pattern of qualitative changes (a clinical presentation —
which labs/vitals are up or down), rank candidate single-variable lesions by how well their
*predicted* sign pattern matches the observation. This is abductive diagnosis over the
causal map, and it is only possible because the map reasons about steady-state
comparative-static signs (not forward propagation).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from physiomap_core.model import PhysioMap, Sign
from physiomap_core.qualitative import Intervention, solve_signs

__all__ = ["Explanation", "rank_explanations"]


class Explanation(BaseModel):
    """A candidate lesion scored against an observed presentation."""

    target: str
    sign: Sign
    agree: int = 0
    disagree: int = 0
    ambiguous: int = 0  # observed nodes the candidate predicts as '?' / no change

    @property
    def score(self) -> int:
        """Net agreement: matches minus contradictions (ambiguous count as neutral)."""
        return self.agree - self.disagree


def rank_explanations(
    pmap: PhysioMap,
    observed: dict[str, Sign],
    candidates: list[tuple[str, Sign]],
    scc_exact_max: int | None = None,
) -> list[Explanation]:
    """Rank candidate ``(node, imposed_sign)`` lesions by fit to ``observed``.

    A candidate scores +1 for each observed node whose predicted sign matches, -1 for each
    contradiction, and 0 for nodes it leaves ``?`` / unchanged. Returns explanations sorted
    best-first (higher net agreement, then fewer contradictions).
    """
    results: list[Explanation] = []
    for target, sgn in candidates:
        kwargs = {} if scc_exact_max is None else {"scc_exact_max": scc_exact_max}
        pred = solve_signs(pmap, Intervention(targets={target: sgn}), **kwargs).predicted
        agree = disagree = ambiguous = 0
        for node, obs in observed.items():
            p = pred.get(node)
            if p is None or p is Sign.UNKNOWN:
                ambiguous += 1
            elif p is obs:
                agree += 1
            else:
                disagree += 1
        results.append(
            Explanation(
                target=target, sign=sgn, agree=agree, disagree=disagree, ambiguous=ambiguous
            )
        )
    results.sort(key=lambda e: (e.score, -e.disagree, e.agree), reverse=True)
    return results
