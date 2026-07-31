"""Monogenic HPO phenotype prediction and lesion abduction.

A PhysioMap node is an ``(entity, PATO determinable-quality)`` pair; an HPO abnormal-quantity
term is *defined* as exactly that plus a direction (Hypertension ≡ blood pressure *increased*).
A monogenic loss/gain-of-function supplies a biological intervention. This module scores
two dual tasks against that reference (see ``benchmarks/hpo/disorders.yaml``):

* **forward**: ``do(primary)`` produces comparative-statics predicted signs; score directional
  agreement + **soundness** (no wrong sign) on the annotated secondary phenotypes; emit
  determinate predictions on *un-annotated* nodes as **novel hypotheses**.
* **backward**: observe the phenotype signs, abduce the primary lesion
  (:func:`physiomap_core.diagnose.rank_explanations`); score top-k recovery of the true
  ``(node, sign)``.

HPO annotations are incomplete and chronic/compensated, so we score *direction + soundness*,
never recall, and an absent phenotype is never a negative. Comparative statics (the steady
state after feedback) is the right target for the compensated clinical presentation.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from physiomap_core.diagnose import rank_explanations
from physiomap_core.model import PhysioMap, Sign
from physiomap_core.qualitative import Intervention, solve_signs

__all__ = [
    "Phenotype",
    "Disorder",
    "ForwardScore",
    "BackwardScore",
    "load_disorders",
    "build_map",
    "forward_eval",
    "backward_eval",
    "render",
]

ROOT = Path(__file__).resolve().parent.parent


def _default_frags() -> list[Path]:
    return (
        [ROOT / "benchmarks/guyton/guyton_cv_core.yaml"]
        + sorted((ROOT / "benchmarks/human/systems").glob("*.yaml"))
        + sorted((ROOT / "benchmarks/human/curated").glob("*.yaml"))  # merged curator contributions
        + sorted((ROOT / "benchmarks/multiscale").glob("*.yaml"))
    )


class Phenotype(BaseModel):
    node: str
    sign: Sign
    label: str | None = None
    hpo: str | None = None


class Disorder(BaseModel):
    name: str
    gene: str | None = None
    omim: str | None = None
    mechanism: str | None = None
    provenance: str | None = None
    primary: dict[str, Sign]
    phenotypes: list[Phenotype] = Field(default_factory=list)


class ForwardScore(BaseModel):
    disorder: str
    scored: int = 0          # phenotypes the solver predicts with a determinate sign
    correct: int = 0
    wrong: int = 0
    abstain: int = 0         # phenotypes left '?' / unreachable (not scored)
    wrong_calls: list[str] = Field(default_factory=list)
    novel: dict[str, Sign] = Field(default_factory=dict)  # determinate, un-annotated -> hypotheses

    @property
    def directional_accuracy(self) -> float:
        return self.correct / self.scored if self.scored else float("nan")


class BackwardScore(BaseModel):
    disorder: str
    true_lesion: str          # "node=sign" (single-target disorders)
    rank: int | None = None   # 1-based shared rank of the true lesion (None if multi-target)
    unique_top1: bool = False
    top3: bool = False
    note: str | None = None


def load_disorders(path: str | Path) -> list[Disorder]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return [Disorder.model_validate(d) for d in data.get("disorders", [])]


def build_map(frags: list[Path] | None = None) -> PhysioMap:
    if frags is not None:
        return PhysioMap.load_composed(frags, name="hpo")
    # The approved OWL/SCM release is authoritative. Explicit fragment lists remain
    # supported for fixture, curation-import, and migration-equivalence workflows.
    from physiomap_core.scm import load_canonical_physiomap
    return load_canonical_physiomap()


def forward_eval(pmap: PhysioMap, disorders: list[Disorder]) -> list[ForwardScore]:
    """Predict secondary phenotypes from each primary lesion and score direction + soundness."""
    out: list[ForwardScore] = []
    for d in disorders:
        targets = {n: s for n, s in d.primary.items()}
        pred = solve_signs(pmap, Intervention(targets=targets, label=d.name)).predicted
        fs = ForwardScore(disorder=d.name)
        annotated = {p.node for p in d.phenotypes}
        for p in d.phenotypes:
            got = pred.get(p.node)
            if got is None or got is Sign.UNKNOWN:
                fs.abstain += 1
            elif got is p.sign:
                fs.scored += 1
                fs.correct += 1
            else:
                fs.scored += 1
                fs.wrong += 1
                fs.wrong_calls.append(f"{p.node}: expected {p.sign.value}, predicted {got.value}")
        # determinate predictions on nodes that are neither annotated nor the lesion itself
        fs.novel = {
            n: s
            for n, s in pred.items()
            if s in (Sign.PLUS, Sign.MINUS) and n not in annotated and n not in targets
        }
        out.append(fs)
    return out


def _candidate_lesions(disorders: list[Disorder]) -> list[tuple[str, Sign]]:
    """Differential = each distinct primary node, BOTH directions (must get the sign right)."""
    nodes = {n for d in disorders for n in d.primary}
    return sorted(((n, s) for n in nodes for s in (Sign.PLUS, Sign.MINUS)), key=lambda c: (c[0], c[1].value))


def backward_eval(pmap: PhysioMap, disorders: list[Disorder]) -> list[BackwardScore]:
    """Abduce the primary lesion from the observed phenotype signs; score top-k recovery."""
    candidates = _candidate_lesions(disorders)
    out: list[BackwardScore] = []
    for d in disorders:
        observed = {p.node: p.sign for p in d.phenotypes}
        ranked = rank_explanations(pmap, observed, candidates)
        bs = BackwardScore(
            disorder=d.name,
            true_lesion=", ".join(f"{n}={s.value}" for n, s in d.primary.items()),
        )
        if len(d.primary) != 1:
            bs.note = "multi-target lesion; top-k not scored (single-target abduction)"
            out.append(bs)
            continue
        (tn, ts), = d.primary.items()
        true = next((e for e in ranked if e.target == tn and e.sign is ts), None)
        if true is None:
            bs.note = "true lesion not in candidate set"
            out.append(bs)
            continue
        better = [e for e in ranked if e.score > true.score]
        equal = [e for e in ranked if e.score == true.score and not (e.target == tn and e.sign is ts)]
        bs.rank = 1 + len(better)
        bs.unique_top1 = (len(better) == 0 and len(equal) == 0)
        bs.top3 = bs.rank <= 3
        if equal and len(better) == 0:
            bs.note = f"tied at top with {len(equal)} other lesion(s) (SCC abstention)"
        out.append(bs)
    return out


def render(fwd: list[ForwardScore], bwd: list[BackwardScore]) -> str:
    L: list[str] = []
    L.append("=" * 78)
    L.append("HPO monogenic pilot: forward phenotype prediction (comparative statics)")
    L.append("=" * 78)
    tot_s = tot_c = tot_w = tot_a = 0
    for f in fwd:
        tot_s += f.scored; tot_c += f.correct; tot_w += f.wrong; tot_a += f.abstain
        acc = "n/a" if not f.scored else f"{f.directional_accuracy:.0%}"
        L.append(
            f"  {f.disorder:42s} det={f.scored} ok={f.correct} wrong={f.wrong} "
            f"abstain(?)={f.abstain} acc={acc} novel={len(f.novel)}"
        )
        for w in f.wrong_calls:
            L.append(f"      WRONG {w}")
    acc = "n/a" if not tot_s else f"{tot_c / tot_s:.0%}"
    L.append("-" * 78)
    L.append(
        f"  FORWARD total: determinate={tot_s} correct={tot_c} WRONG={tot_w} "
        f"abstain(?)={tot_a}  directional accuracy={acc}  (soundness: WRONG must be 0)"
    )
    L.append("")
    L.append("=" * 78)
    L.append("HPO monogenic pilot: backward lesion abduction (which primary cause?)")
    L.append("=" * 78)
    n_top1 = n_top3 = n_scored = 0
    for b in bwd:
        if b.rank is not None:
            n_scored += 1
            n_top1 += int(b.unique_top1)
            n_top3 += int(b.top3)
        rk = "NA" if b.rank is None else f"#{b.rank}"
        flag = "TOP1" if b.unique_top1 else ("top3" if b.top3 else "")
        L.append(f"  {b.disorder:42s} true={b.true_lesion:34s} rank={rk:4s} {flag}")
        if b.note:
            L.append(f"      note: {b.note}")
    L.append("-" * 78)
    L.append(
        f"  BACKWARD: unique top-1 = {n_top1}/{n_scored}   top-3 = {n_top3}/{n_scored}"
    )
    L.append("=" * 78)
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    import sys

    args = sys.argv[1:] if argv is None else argv
    path = args[0] if args else str(ROOT / "benchmarks/hpo/disorders.yaml")
    disorders = load_disorders(path)
    pmap = build_map()
    fwd = forward_eval(pmap, disorders)
    bwd = backward_eval(pmap, disorders)
    print(render(fwd, bwd))
    # soundness gate: no forward prediction may contradict the curated phenotype direction
    return 0 if sum(f.wrong for f in fwd) == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
