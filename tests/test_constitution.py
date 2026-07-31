"""part_of backbone + constitutive-edge validation + conservation (family 9 seed)."""

from __future__ import annotations

import glob
from pathlib import Path

from physiomap_core.constitution import (
    check_conservation,
    classify_macro_grounding,
    is_part_of,
    partof_graph,
    validate_constitution,
)
from physiomap_core.model import (
    ConstitutiveEdge,
    Node,
    PhysioMap,
    Scale,
    Sign,
)

ROOT = Path(__file__).resolve().parent.parent
FRAGS = (
    [ROOT / "benchmarks/guyton/guyton_cv_core.yaml"]
    + sorted((ROOT / "benchmarks/human/systems").glob("*.yaml"))
    + sorted((ROOT / "benchmarks/multiscale").glob("*.yaml"))
)


def _full():
    return PhysioMap.load_composed(FRAGS, name="full")


def test_partof_backbone_is_a_dag_with_transitive_membership():
    g = partof_graph()
    # direct + transitive part_of
    assert is_part_of(g, "CL:0000359", "UBERON:0002049")  # VSMC ⊂ vasculature
    assert is_part_of(g, "CL:0000359", "UBERON:0001009")  # ⊂ circulatory system (transitive)
    assert is_part_of(g, "CL:1000850", "UBERON:0002113")  # macula densa ⊂ kidney
    assert is_part_of(g, "UBERON:0001969", "UBERON:0000178")  # plasma ⊂ blood
    assert not is_part_of(g, "UBERON:0002049", "CL:0000359")  # not the reverse


def test_real_map_constitution_validates_clean():
    rep = validate_constitution(_full())
    assert rep.ok, f"constitution errors: {rep.errors}"
    # Constitution is restricted to four material aggregations. The former two-edge
    # vascular-tone vertical is causal; process output/consumption remains in the
    # independent production layer.
    assert "part_of+determination" not in rep.by_kind
    assert rep.by_kind.get("aggregation") == 4
    assert "production" not in rep.by_kind
    assert len(_full().production_edges) >= 42


def test_real_map_structural_partof_is_machine_verifiable_via_bearers():
    # every structural edge now resolves its part_of via an anatomical entity or a recorded
    # bearer_entity_iri — so the validator emits NO "part_of unverifiable" notes.
    rep = validate_constitution(_full())
    assert not any("unverifiable" in n for n in rep.notes), f"unverifiable notes: {rep.notes}"


def test_bearer_entity_resolves_structural_partof():
    # a subcellular quality borne by a cardiomyocyte structurally constitutes a heart quality
    nodes = [
        Node(id="pka", label="PKA activity", scale=Scale.SUBCELLULAR,
             entity_iri="GO:0004691", bearer_entity_iri="CL:0000746"),
        Node(id="hr", label="heart rate", scale=Scale.ORGAN, entity_iri="UBERON:0000948"),
        Node(id="pka_nobearer", label="PKA (no bearer)", scale=Scale.SUBCELLULAR,
             entity_iri="GO:0004691"),
        Node(id="hr2", label="heart rate 2", scale=Scale.ORGAN, entity_iri="UBERON:0000948"),
    ]
    pm = PhysioMap(name="t", nodes=nodes, constitutive_edges=[
        ConstitutiveEdge(micro="pka", macro="hr", relation="part_of+determination", sign=Sign.PLUS),
        ConstitutiveEdge(micro="pka_nobearer", macro="hr2",
                         relation="part_of+determination", sign=Sign.PLUS),
    ])
    rep = validate_constitution(pm)
    assert rep.ok, rep.errors
    # the one with a bearer is verified (no note); the one without is flagged unverifiable
    assert any("pka_nobearer" in n and "unverifiable" in n for n in rep.notes)
    assert not any("pka ▷ hr:" in n for n in rep.notes)


def test_classify_macro_grounding_buckets_real_map():
    c = classify_macro_grounding(_full())
    # buckets partition all macro nodes.
    assert set(c) == {"grounded", "exogenous", "derived", "ungrounded"}
    # Only genuine material constitution 'grounds' a macro. Produced substances and process rates
    # are 'derived' through explicitly tagged production/quantitative shadow edges. So the
    # invariant is the *explained* set (grounded + derived), not the small constitutively-grounded count.
    assert len(c["grounded"]) >= 2
    # the curated/edged macros remain causally explained (constitutively grounded or within-scale
    # derived). NOTE: the HPO gap-fill (v0.8.0) deliberately added ~600 ontologically-grounded but
    # causally-ISLAND leaf-analyte nodes (verified entity IRIs, no fabricated edges) — legitimately
    # "ungrounded" causal roots that abstain soundly. So `ungrounded` now dominates by design
    # (node-first, edge-conservative growth); the invariant is that the *explained* set stays
    # substantial, not that it exceeds the leaf-analyte count.
    assert len(c["grounded"]) + len(c["derived"]) >= 200


def test_exogenous_macro_is_not_a_grounding_gap():
    from physiomap_core.constitution import free_floating_macro
    nodes = [
        Node(id="intake", label="water intake", scale=Scale.ORGANISM, exogenous=True),
        Node(id="pool", label="plasma pool", scale=Scale.ORGAN_SYSTEM),
    ]
    pm = PhysioMap(name="t", nodes=nodes)
    ff = free_floating_macro(pm)
    assert "intake" not in ff and "pool" in ff
    c = classify_macro_grounding(pm)
    assert c["exogenous"] == ["intake"] and c["ungrounded"] == ["pool"]


def test_conservation_relations_registered():
    cons = check_conservation(_full())
    assert set(cons["body_weight"]) == {"adipose_tissue_mass", "lean_body_mass"}
    assert set(cons["blood_volume"]) == {"red_cell_mass", "plasma_volume"}


def _tiny(edges):
    ids = {x for e in edges for x in (e.micro, e.macro)}
    scale = {
        "vsmc": Scale.CELLULAR, "vasc": Scale.ORGAN_SYSTEM,
        "fat": Scale.ORGAN_SYSTEM, "weight": Scale.ORGANISM,
        "hormone": Scale.ORGAN_SYSTEM, "cell": Scale.CELLULAR,
    }
    ent = {"vsmc": "CL:0000359", "vasc": "UBERON:0002049",
           "hormone": "CHEBI:50266", "cell": "CL:0000169"}
    nodes = [Node(id=i, label=i, scale=scale.get(i, Scale.ORGAN_SYSTEM),
                  entity_iri=ent.get(i)) for i in ids]
    return PhysioMap(name="t", nodes=nodes, constitutive_edges=edges)


def test_scale_inversion_is_an_error():
    pm = _tiny([ConstitutiveEdge(micro="weight", macro="fat",  # organism ▷ organ_system (inverted)
                                 relation="aggregation", sign=Sign.PLUS)])
    assert any("scale inversion" in e for e in validate_constitution(pm).errors)


def test_aggregation_requires_plus_sign():
    pm = _tiny([ConstitutiveEdge(micro="fat", macro="weight",
                                 relation="aggregation", sign=Sign.MINUS)])
    assert any("aggregation must have sign" in e for e in validate_constitution(pm).errors)


def test_partof_determination_into_a_substance_is_flagged_as_production():
    # a cell structurally "part_of+determination" a hormone (substance) is wrong -> should be production
    pm = _tiny([ConstitutiveEdge(micro="cell", macro="hormone",
                                 relation="part_of+determination", sign=Sign.PLUS)])
    assert any("SUBSTANCE" in e or "production" in e for e in validate_constitution(pm).errors)


def test_structural_anatomical_edge_without_partof_path_errors():
    # vasculature is NOT part_of vsmc -> reverse structural edge has no part_of path
    pm = _tiny([ConstitutiveEdge(micro="vasc", macro="vsmc",
                                 relation="part_of+determination", sign=Sign.PLUS)])
    rep = validate_constitution(pm)
    assert any("scale inversion" in e or "no part_of path" in e for e in rep.errors)
