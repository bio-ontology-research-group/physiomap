"""Tests for multiplicative (gain) edges — the second-order layer."""

from pathlib import Path

import pytest

from physiomap_core.model import ModulationEdge, Node, PhysioMap, Scale, Sign, CausalEdge
from physiomap_core.modulation import (
    first_order_shadow,
    gain_changes,
    gain_sensitivity,
    interaction_sign,
    modulations_of,
    regime_conditional_signs,
    shadow_is_present,
    synergies,
)
from physiomap_core.qualitative import Intervention

ROOT = Path(__file__).resolve().parent.parent
GEORGE = ROOT / "benchmarks" / "human" / "systems" / "george_heart_rate.yaml"


def _toy() -> PhysioMap:
    """theta -> M (the modulator), and M scales the edge S -> T (sign +)."""
    nodes = [Node(id=n, label=n, scale=Scale.ORGAN) for n in ("theta", "M", "S", "T")]
    causal = [
        CausalEdge(source="theta", target="M", sign=Sign.PLUS),
        CausalEdge(source="S", target="T", sign=Sign.PLUS),
        CausalEdge(source="M", target="T", sign=Sign.PLUS),  # first-order shadow
    ]
    mod = [
        ModulationEdge(
            modulator="M", edge_source="S", edge_target="T", sign=Sign.PLUS
        )
    ]
    return PhysioMap(nodes=nodes, causal_edges=causal, modulation_edges=mod)


def test_modulation_validation_requires_existing_nodes_and_edge():
    base = _toy()
    # unknown modulator node
    with pytest.raises(ValueError):
        PhysioMap(
            nodes=base.nodes,
            causal_edges=base.causal_edges,
            modulation_edges=[
                ModulationEdge(modulator="ZZZ", edge_source="S", edge_target="T", sign=Sign.PLUS)
            ],
        )
    # modulates a non-existent causal edge
    with pytest.raises(ValueError):
        PhysioMap(
            nodes=base.nodes,
            causal_edges=base.causal_edges,
            modulation_edges=[
                ModulationEdge(modulator="M", edge_source="T", edge_target="S", sign=Sign.PLUS)
            ],
        )


def test_gain_sensitivity_sign_is_path_times_modulation():
    pm = _toy()
    # do(theta+) -> M+ , modulation + => gain of S->T rises (+)
    gs = gain_sensitivity(pm, Intervention(targets={"theta": Sign.PLUS}), ("S", "T"))
    assert gs == Sign.PLUS
    # do(theta-) -> M- , modulation + => gain falls (-)
    gs = gain_sensitivity(pm, Intervention(targets={"theta": Sign.MINUS}), ("S", "T"))
    assert gs == Sign.MINUS
    # intervening on S itself does not move the modulator M -> no gain change
    assert gain_sensitivity(pm, Intervention(targets={"S": Sign.PLUS}), ("S", "T")) is None
    # negative modulation flips the sense
    pm2 = pm.model_copy(
        update={
            "modulation_edges": [
                ModulationEdge(modulator="M", edge_source="S", edge_target="T", sign=Sign.MINUS)
            ]
        }
    )
    assert gain_sensitivity(pm2, Intervention(targets={"theta": Sign.PLUS}), ("S", "T")) == Sign.MINUS


def test_first_order_shadow_present():
    pm = _toy()
    m = pm.modulation_edges[0]
    assert first_order_shadow(m) == ("M", "T", Sign.PLUS)
    assert shadow_is_present(pm, m)


def test_george_fragment_modulation_loads_and_queries():
    # the fragment references boundary nodes (heart_rate, free_t3) owned by other fragments,
    # so it is loaded composed (same set as the human map / build_map).
    from physiomap_core.hpo import build_map

    pm = build_map()
    george = next(m for m in pm.modulation_edges
                  if m.modulator == "beta1_adrenergic_chronotropic_responsiveness")
    assert (george.edge_source, george.edge_target) == ("sympathetic_tone", "heart_rate")
    assert george.sign == Sign.PLUS
    assert shadow_is_present(pm, george)
    # the second-order gain query: do(free_t3 +) raises the gain of sympathetic_tone -> heart_rate
    gs = gain_sensitivity(pm, Intervention(targets={"free_t3": Sign.PLUS}),
                          ("sympathetic_tone", "heart_rate"))
    assert gs == Sign.PLUS


def test_modulations_of_filters_by_edge():
    pm = _toy()
    assert len(modulations_of(pm, ("S", "T"))) == 1
    assert modulations_of(pm, ("M", "T")) == []


# ---- second-order sign-only layer (interaction sign / sensitization / synergy / regimes) ----

def test_interaction_sign_is_modulation_times_base_edge():
    pm = _toy()  # M scales[+] S->T, base edge S->T is +
    assert interaction_sign(pm, pm.modulation_edges[0]) == Sign.PLUS


def test_gain_change_under_intervention():
    pm = _toy()
    pred = {"M": Sign.PLUS}  # do(theta+) raises the modulator M
    gc = gain_changes(pm, {"theta": Sign.PLUS}, pred)
    assert len(gc) == 1
    assert gc[0].edge_source == "S" and gc[0].edge_target == "T" and gc[0].direction == "+"


def test_synergy_super_additive_when_cross_aligns_with_target():
    pm = _toy()  # clamp both S and M up; cross = iota*+*+ = +, target T predicted +
    do = {"S": Sign.PLUS, "M": Sign.PLUS}
    pred = {"S": Sign.PLUS, "M": Sign.PLUS, "T": Sign.PLUS}
    sy = synergies(pm, do, pred)
    assert len(sy) == 1
    assert sy[0].cross_sign == "+" and sy[0].verdict == "synergistic"


def test_synergy_needs_both_endpoints_moved():
    pm = _toy()
    # only the modulator moves -> no cross term -> no synergy reported
    assert synergies(pm, {"M": Sign.PLUS}, {"M": Sign.PLUS, "T": Sign.PLUS}) == []


def test_regime_case_analysis_for_flip_edge():
    nodes = [Node(id=n, label=n, scale=Scale.ORGAN) for n in ("M", "S", "T")]
    causal = [CausalEdge(source="S", target="T", sign=Sign.PLUS)]
    mod = [ModulationEdge(modulator="M", edge_source="S", edge_target="T",
                          sign=Sign.PLUS, can_flip_sign=True)]
    pm = PhysioMap(nodes=nodes, causal_edges=causal, modulation_edges=mod)
    r = regime_conditional_signs(pm, pm.modulation_edges[0])
    # gain rises with M; base edge +, so M-high keeps +, M-low flips to -
    assert r == {"modulator_high": "+", "modulator_low": "-", "unconditional": "?"}
    # a non-flipping gain has no regime split
    assert regime_conditional_signs(_toy(), _toy().modulation_edges[0]) is None
