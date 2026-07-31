from pathlib import Path

import pytest

from physiomap_core.model import (
    CausalEdge,
    ModulationEdge,
    Node,
    PhysioMap,
    QuantitativeArgumentDefinition,
    QuantitativeDefinition,
    RatioDefinition,
    Scale,
    Sign,
)
from physiomap_core.owl_projection import MigrationBuilder
from physiomap_core.quantitative_validation import validate_quantitative_manifest

ROOT = Path(__file__).resolve().parent.parent


def test_generated_ratio_and_modulation_have_realizable_derivatives():
    nodes = [Node(id=x, label=x, scale=Scale.CELLULAR) for x in "abcd"]
    from physiomap_core.model import CausalEdge
    pmap = PhysioMap(nodes=nodes,
        causal_edges=[CausalEdge(source="a", target="b", sign=Sign.PLUS)],
        modulation_edges=[ModulationEdge(modulator="c", edge_source="a", edge_target="b",
                                         sign=Sign.MINUS)],
        ratio_definitions=[RatioDefinition(ratio="d", numerator="a", denominator="b")])
    _, manifest, _ = MigrationBuilder(ROOT / "projection/patterns.yaml").build(pmap)
    report = validate_quantitative_manifest(manifest, trials=4)
    assert report.ok
    assert report.exact_rules_checked == 3
    assert report.numerical_trials == 8


def test_wrong_ratio_derivative_is_rejected():
    nodes = [Node(id=x, label=x, scale=Scale.CELLULAR) for x in "abc"]
    pmap = PhysioMap(nodes=nodes,
        ratio_definitions=[RatioDefinition(ratio="c", numerator="a", denominator="b")])
    _, manifest, _ = MigrationBuilder(ROOT / "projection/patterns.yaml").build(pmap)
    manifest.quantitative_expressions[0].arguments[1].derivative_sign = "+"
    report = validate_quantitative_manifest(manifest, trials=1)
    assert not report.ok
    assert "ratio derivative signs" in report.errors[0]


def test_quantitative_argument_cannot_also_be_authored_as_causal():
    nodes = [Node(id=x, label=x, scale=Scale.CELLULAR) for x in "abc"]
    definition = QuantitativeDefinition(
        kind="product",
        result="c",
        arguments=[
            QuantitativeArgumentDefinition(node="a", role="factor", derivative_sign=Sign.PLUS),
            QuantitativeArgumentDefinition(node="b", role="factor", derivative_sign=Sign.PLUS),
        ],
    )
    pmap = PhysioMap(
            nodes=nodes,
            causal_edges=[CausalEdge(source="a", target="c", sign=Sign.PLUS)],
            quantitative_definitions=[definition],
        )
    with pytest.raises(ValueError, match="also occur as causal influences"):
        MigrationBuilder(ROOT / "projection/patterns.yaml").build(pmap)
