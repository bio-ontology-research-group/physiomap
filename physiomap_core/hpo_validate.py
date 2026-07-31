"""Quantitative validation of PhysioMap against the REAL HPO gene->phenotype annotations.

Uses the committed, reproducible artifact ``benchmarks/hpo/hpo_gene_observations.yaml`` (built by
``scripts/build_hpo_observations.py`` from HPO ``genes_to_phenotype.txt`` + ``hp.obo``): for each
gene, the observed increased/decreased directions of its real HPO phenotypes that map onto a
PhysioMap node. Two tasks, scored quantitatively:

* **forward** — ``do(primary)`` comparative statics vs each observed HPO direction: a determinate
  prediction is *correct*/*wrong*; ``?`` is *abstain* (not scored). Soundness = 0 wrong.
* **backward** — abduce the gene's primary lesion from its observed HPO directions
  (``rank_explanations``); top-k recovery of the true ``(node, sign)``.

HPO gene-level annotations aggregate across diseases/alleles (a gene with both LoF and GoF diseases
carries both directions); such conflicts are dropped at build time and reported as coverage loss.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from physiomap_core.diagnose import rank_explanations
from physiomap_core.hpo import build_map
from physiomap_core.model import PhysioMap, Sign
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention

ROOT = Path(__file__).resolve().parent.parent
OBS = ROOT / "benchmarks/hpo/hpo_gene_observations.yaml"
GENES = ROOT / "benchmarks/hpo/gene_lesions.yaml"

__all__ = ["load_observations", "ForwardReport", "BackwardReport", "validate", "render"]


def load_observations(path: Path = OBS) -> tuple[str, dict]:
    d = yaml.safe_load(path.read_text())
    return d.get("hpo_release", "?"), d["observations"]


class ForwardReport(BaseModel):
    release: str
    genes_scored: int = 0
    observations: int = 0     # determinate predictions scored
    correct: int = 0
    wrong: int = 0
    abstain: int = 0
    wrong_calls: list[str] = Field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.observations if self.observations else float("nan")


class BackwardReport(BaseModel):
    genes_scored: int = 0
    top1: int = 0
    top3: int = 0
    detail: list[str] = Field(default_factory=list)


def _candidates(genes: dict) -> list[tuple[str, Sign]]:
    nodes = {n for g in genes.values() for n in g["primary"]}
    return sorted(((n, s) for n in nodes for s in (Sign.PLUS, Sign.MINUS)),
                  key=lambda c: (c[0], c[1].value))


def validate(pmap: PhysioMap | None = None) -> tuple[ForwardReport, BackwardReport]:
    pmap = pmap or build_map()
    release, obs = load_observations()
    genes = yaml.safe_load(GENES.read_text())["genes"]
    cands = _candidates(genes)

    fwd = ForwardReport(release=release)
    bwd = BackwardReport()
    for gene, rec in obs.items():
        observed = {k: Sign(v) for k, v in rec.get("observed", {}).items()}
        if not observed:
            continue
        primary = {k: Sign(v) for k, v in rec["primary"].items()}
        # ----- forward -----
        fwd.genes_scored += 1
        pred = solve_multiscale(pmap, Intervention(targets=primary, label=gene)).predicted
        for node, exp in observed.items():
            if node in primary:
                continue  # the intervened (lesion) node is SET by do(), not a forward prediction
            got = pred.get(node)
            if got is None or got is Sign.UNKNOWN:
                fwd.abstain += 1
            elif got is exp:
                fwd.observations += 1; fwd.correct += 1
            else:
                fwd.observations += 1; fwd.wrong += 1
                fwd.wrong_calls.append(f"{gene}: {node} HPO={exp.value} predicted={got.value}")
        # ----- backward (single-target primaries) -----
        if len(primary) == 1:
            (tn, ts), = primary.items()
            ranked = rank_explanations(pmap, observed, cands)
            true = next((e for e in ranked if e.target == tn and e.sign is ts), None)
            if true is not None:
                bwd.genes_scored += 1
                better = sum(1 for e in ranked if e.score > true.score)
                equal = sum(1 for e in ranked if e.score == true.score
                            and not (e.target == tn and e.sign is ts))
                rank = 1 + better
                uniq = better == 0 and equal == 0
                bwd.top1 += int(uniq)
                bwd.top3 += int(rank <= 3)
                bwd.detail.append(f"{gene:8s} true={tn}{ts.value:1s} rank=#{rank}"
                                  + ("" if uniq else f" (tie x{equal})"))
    return fwd, bwd


def render(fwd: ForwardReport, bwd: BackwardReport) -> str:
    L = ["=" * 76, f"PhysioMap vs REAL HPO gene->phenotype annotations  (HPO {fwd.release})", "=" * 76]
    L.append("FORWARD (do(gene primary) -> predicted direction vs observed HPO direction):")
    L.append(f"  genes scored:            {fwd.genes_scored}")
    L.append(f"  determinate predictions: {fwd.observations}")
    L.append(f"  correct:                 {fwd.correct}")
    L.append(f"  WRONG (soundness):       {fwd.wrong}")
    L.append(f"  abstain (?):             {fwd.abstain}")
    acc = "n/a" if not fwd.observations else f"{fwd.accuracy:.0%}"
    L.append(f"  directional accuracy:    {acc}  (on determinate predictions)")
    for w in fwd.wrong_calls:
        L.append(f"    WRONG {w}")
    L.append("-" * 76)
    L.append("BACKWARD (abduce the gene's primary lesion from its observed HPO directions):")
    L.append(f"  genes scored: {bwd.genes_scored}   unique top-1: {bwd.top1}/{bwd.genes_scored}"
             f"   top-3: {bwd.top3}/{bwd.genes_scored}")
    for d in bwd.detail:
        L.append(f"    {d}")
    L.append("=" * 76)
    return "\n".join(L)


def main() -> int:  # pragma: no cover
    fwd, bwd = validate()
    print(render(fwd, bwd))
    return 0 if fwd.wrong == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
