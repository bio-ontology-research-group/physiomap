from physiomap_core.model import (
    CausalEdge,
    ConstitutiveEdge,
    Node,
    PhysioMap,
    ProductionEdge,
    ProductionEvidenceClass,
    QuantitativeArgumentDefinition,
    QuantitativeDefinition,
    Scale,
    Sign,
)
from scripts.e5_typed_layer_ablation import (
    CONFIGURATIONS,
    compare_forward,
    configure_layers,
    operational_inventory,
    render_latex,
)


def _toy_map() -> PhysioMap:
    nodes = [Node(id=node, label=node, scale=Scale.ORGAN) for node in "abcdef"]
    return PhysioMap(
        nodes=nodes,
        causal_edges=[CausalEdge(source="a", target="b", sign=Sign.PLUS)],
        production_edges=[
            ProductionEdge(
                source="b",
                target="c",
                sign=Sign.PLUS,
                mechanism="test process output",
                evidence="test source",
                production_evidence=ProductionEvidenceClass.MECHANISTIC_MODEL,
            )
        ],
        quantitative_definitions=[
            QuantitativeDefinition(
                kind="product",
                result="e",
                arguments=[
                    QuantitativeArgumentDefinition(
                        node="c", role="factor", derivative_sign=Sign.PLUS
                    ),
                    QuantitativeArgumentDefinition(
                        node="d", role="factor", derivative_sign=Sign.PLUS
                    ),
                ],
            )
        ],
        constitutive_edges=[
            ConstitutiveEdge(micro="e", macro="f", relation="aggregation")
        ],
    )


def test_cumulative_layer_configurations_change_only_selected_records():
    base = _toy_map()
    expected = (
        (0, 0, 0),
        (1, 0, 0),
        (1, 1, 0),
        (1, 1, 1),
    )
    for config, counts in zip(CONFIGURATIONS, expected):
        model = configure_layers(base, config)
        assert (
            len(model.production_edges),
            len(model.quantitative_definitions),
            len(model.constitutive_edges),
        ) == counts
        assert len(model.causal_edges) == 1


def test_operational_inventory_distinguishes_typed_shadows():
    inventory = operational_inventory(
        configure_layers(_toy_map(), CONFIGURATIONS[-1])
    )
    assert inventory == {
        "causal_arcs": 1,
        "production_shadow_arcs": 1,
        "quantitative_shadow_arcs": 2,
        "constitutive_constraints": 1,
        "modulation_records_present_but_inactive": 0,
    }


def test_forward_comparison_separates_loss_gain_and_sign_flip():
    comparison = compare_forward(
        {"g1\tx": "+", "g2\ty": "?", "g3\tz": "-"},
        {"g1\tx": "?", "g2\ty": "+", "g3\tz": "+"},
    )
    assert comparison["changed_pairs"] == 3
    assert comparison["determinate_to_abstain"] == 1
    assert comparison["abstain_to_determinate"] == 1
    assert comparison["sign_flips"] == 1


def test_latex_table_reports_coverage_and_inverse_ranking():
    results = {}
    for index, config in enumerate(CONFIGURATIONS):
        results[config.id] = {
            "label": config.label,
            "forward": {
                "metrics": {
                    "determinate": 20 - index,
                    "coverage": 0.20 - index / 100,
                }
            },
            "inverse": {
                "metrics": {
                    "top3": 10 - index,
                    "genes_scored": 12,
                    "mrr": 0.75 - index / 100,
                }
            },
        }
    table = render_latex(
        {
            "configuration_order": [config.id for config in CONFIGURATIONS],
            "results": results,
        }
    )
    assert "determinate & coverage & top-3 & MRR" in table
    assert "causal & 20 & 20.0\\% & 10/12 & 0.750" in table
