"""Monogenic (HPO) phenotype prediction & lesion abduction pilot (applied benchmark §0)."""

from __future__ import annotations

from pathlib import Path

from physiomap_core.hpo import (
    backward_eval,
    build_map,
    forward_eval,
    load_disorders,
)

ROOT = Path(__file__).resolve().parent.parent
DISORDERS = ROOT / "benchmarks" / "hpo" / "disorders.yaml"


def _setup():
    disorders = load_disorders(DISORDERS)
    return build_map(), disorders


def test_pilot_loads():
    disorders = load_disorders(DISORDERS)
    assert len(disorders) >= 18
    # every disorder's nodes must exist in the composed map
    pmap = build_map()
    ids = set(pmap.node_ids)
    for d in disorders:
        for n in d.primary:
            assert n in ids, f"{d.name}: primary node {n} not in map"
        for p in d.phenotypes:
            assert p.node in ids, f"{d.name}: phenotype node {p.node} not in map"


def test_forward_is_sound():
    """No forward (comparative-statics) prediction may contradict a curated phenotype sign."""
    pmap, disorders = _setup()
    fwd = forward_eval(pmap, disorders)
    wrong = [(f.disorder, f.wrong_calls) for f in fwd if f.wrong]
    assert wrong == [], f"unsound forward predictions: {wrong}"


def test_forward_determinate_predictions_are_correct():
    """Where the solver commits (no '?'), it agrees with textbook direction."""
    pmap, disorders = _setup()
    fwd = forward_eval(pmap, disorders)
    scored = sum(f.scored for f in fwd)
    correct = sum(f.correct for f in fwd)
    assert scored >= 15  # feedback axes + the self-contained metabolic subsystems commit
    assert correct == scored  # and they are all correct


def test_backward_recovers_feedback_axis_lesions_top1():
    """Disorders whose secondary phenotypes are determinate uniquely recover the lesion."""
    pmap, disorders = _setup()
    bwd = {b.disorder: b for b in backward_eval(pmap, disorders)}
    for name in (
        "Familial hypercholesterolemia",
        "Hereditary hemochromatosis (HFE-related)",
        "Congenital hypothyroidism",
        # self-contained metabolic subsystems added by the coverage expansion:
        "Phenylketonuria",
        "Maple syrup urine disease",
        "Hereditary xanthinuria",
        "Glycogen storage disease type Ia (von Gierke)",
        "Crigler-Najjar / Gilbert (UGT1A1)",
    ):
        assert bwd[name].unique_top1, f"{name} not uniquely recovered: rank {bwd[name].rank}"

    # The integrated PTH/bone-remodelling relations connect the FGF23 axis to the
    # enlarged homeostatic SCC. The conservative solver therefore keeps the true
    # XLH lesion first but abstains from claiming a unique winner without loop gains.
    xlh = bwd["X-linked hypophosphatemic rickets"]
    assert xlh.rank == 1 and xlh.top3 and not xlh.unique_top1
    assert "SCC abstention" in xlh.note


def test_backward_all_within_top3():
    pmap, disorders = _setup()
    bwd = backward_eval(pmap, disorders)
    scored = [b for b in bwd if b.rank is not None]
    assert all(b.top3 for b in scored), [(b.disorder, b.rank) for b in scored if not b.top3]
