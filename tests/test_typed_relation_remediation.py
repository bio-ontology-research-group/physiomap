"""Regression locks for the five approved canonical typed-relation remediations."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from physiomap_core.scm import load_canonical_scm
from scripts.generate_legacy_evidence_worklist import build_outputs

ROOT = Path(__file__).resolve().parent.parent


def test_all_85_production_relations_stay_out_of_causal_and_constitutive_layers():
    manifest = load_canonical_scm()
    production = {(edge.source, edge.target, edge.sign)
                  for edge in manifest.production_relations}
    influences = {(edge.source, edge.target, edge.sign) for edge in manifest.influences}
    constitution = {(edge.micro, edge.macro, edge.sign)
                    for edge in manifest.constitutive_constraints}

    assert len(manifest.production_relations) == len(production) == 85
    assert production.isdisjoint(influences)
    assert production.isdisjoint(constitution)
    assert all(edge.trace_ids for edge in manifest.production_relations)


def test_all_nine_quantitative_identities_stay_typed_and_noncausal():
    manifest = load_canonical_scm()
    signatures = {
        (expression.kind, expression.origin, expression.result,
         tuple((argument.node, argument.role, argument.derivative_sign)
               for argument in expression.arguments))
        for expression in manifest.quantitative_expressions
    }
    assert signatures == {
        ("aggregation", "derived", "blood_volume",
         (("red_cell_mass", "summand", "+"), ("plasma_volume", "summand", "+"))),
        ("aggregation", "derived", "body_weight",
         (("adipose_tissue_mass", "summand", "+"), ("lean_body_mass", "summand", "+"))),
        ("product", "authored", "mean_arterial_pressure",
         (("cardiac_output", "factor", "+"),
          ("total_peripheral_resistance", "factor", "+"))),
        ("product", "authored", "cardiac_output",
         (("heart_rate", "factor", "+"), ("stroke_volume", "factor", "+"))),
        ("ratio", "authored", "hematocrit",
         (("red_cell_mass", "numerator", "+"), ("blood_volume", "denominator", "-"))),
        ("structural-function", "authored", "arterial_o2_content",
         (("hemoglobin_o2_saturation", "argument", "+"),
          ("hematocrit", "argument", "+"), ("arterial_po2", "argument", "+"))),
        ("product", "authored", "oxygen_delivery",
         (("cardiac_output", "factor", "+"),
          ("arterial_o2_content", "factor", "+"))),
        ("structural-function", "authored", "arterial_ph",
         (("arterial_pco2", "argument", "-"),
          ("plasma_bicarbonate", "argument", "+"))),
        ("structural-function", "authored", "alveolar_po2",
         (("inspired_po2", "argument", "+"),
          ("alveolar_pco2", "argument", "-"))),
    }
    causal_pairs = {(edge.source, edge.target) for edge in manifest.influences}
    assert all(
        (argument.node, expression.result) not in causal_pairs
        for expression in manifest.quantitative_expressions
        for argument in expression.arguments
    )


def test_legacy_evidence_inventory_and_human_approval_boundary_stay_reconciled():
    worklist, _ = build_outputs()
    summary = json.loads(worklist)["summary"]
    assert summary["baseline_total"] == 621
    assert summary["approved_resolved"] == 470
    assert summary["open"] == summary["proposal_pending"] == 151
    assert summary["approved_outcomes"] == {
        "curated_mechanistic": 28,
        "duplicate_removed": 1,
        "genetic_lof_gof": 129,
        "mechanistic_model": 141,
        "perturbation": 78,
        "pharmacological": 74,
        "reclassified_production": 5,
        "reclassified_quantitative": 10,
        "rejected_not_causal": 3,
        "superseded_by_scientific_correction": 1,
    }
    assert sum(
        edge.evidence_status == "legacy-evidence-unclassified"
        for edge in load_canonical_scm().influences
    ) == 153


def test_phosphate_fgf23_corrections_remain_typed_and_exactly_grounded():
    manifest = load_canonical_scm()
    nodes = {node.id: node for node in manifest.nodes}
    assert {
        node_id: (nodes[node_id].entity_iri, nodes[node_id].quality_iri)
        for node_id in (
            "fgf23", "klotho_activity", "renal_phosphate_reabsorption",
            "alkaline_phosphatase", "plasma_25oh_vitamin_d",
        )
    } == {
        "fgf23": ("PR:Q9GZV9", "PATO:0000033"),
        "klotho_activity": ("PR:Q9UEF7", "PATO:0001509"),
        "renal_phosphate_reabsorption": ("GO:0097291", "PATO:0000161"),
        "alkaline_phosphatase": ("PR:P05186", "PATO:0001414"),
        "plasma_25oh_vitamin_d": ("CHEBI:17933", "PATO:0000033"),
    }

    influences = {(edge.source, edge.target, edge.sign) for edge in manifest.influences}
    assert {
        ("fgf23", "renal_phosphate_reabsorption", "-"),
        ("fgf23", "calcitriol", "-"),
        ("klotho_activity", "renal_phosphate_reabsorption", "-"),
        ("plasma_phosphate", "fgf23", "+"),
        ("calcitriol", "fgf23", "+"),
    } <= influences
    assert ("pth", "fgf23", "+") not in influences
    assert ("plasma_25oh_vitamin_d", "calcitriol", "+") not in influences
    assert not any(source == "alkaline_phosphatase" and target == "plasma_phosphate"
                   for source, target, _ in influences)
    assert not any(source == "renal_phosphate_reabsorption" and target == "plasma_phosphate"
                   for source, target, _ in influences)

    productions = {(edge.source, edge.target, edge.sign)
                   for edge in manifest.production_relations}
    assert ("renal_phosphate_reabsorption", "plasma_phosphate", "+") in productions
    by_id = {edge.id: edge for edge in manifest.influences}
    klotho_modulation, = [edge for edge in manifest.modulation
                          if edge.modulator == "klotho_activity"]
    target = by_id[klotho_modulation.influence_id]
    assert (target.source, target.target, target.sign) == (
        "fgf23", "renal_phosphate_reabsorption", "-"
    )
    assert klotho_modulation.sign == "-" and not klotho_modulation.can_flip_sign


def test_projection_registry_release_and_behavioral_baseline_stay_aligned():
    registry = yaml.safe_load((ROOT / "projection/patterns.yaml").read_text(encoding="utf-8"))
    manifest = load_canonical_scm()
    baseline = json.loads(
        (ROOT / "benchmarks/golden/owl-scm-v2.json").read_text(encoding="utf-8")
    )

    assert registry["version"] == manifest.projection_version == baseline["projection_version"]
    assert registry["version"] == "1.4.0"
    assert baseline["baseline_id"] == "owl-scm-v2"
    assert baseline["schema_version"] == "2.0.0"
    assert {
        "nodes": baseline["model"]["nodes"]["count"],
        "influences": baseline["model"]["causal_edges"]["count"],
        "production": baseline["model"]["production_edges"]["count"],
        "constitution": baseline["model"]["constitutive_edges"]["count"],
        "quantitative": baseline["model"]["quantitative_definitions"]["count"],
        "modulation": baseline["model"]["modulation_edges"]["count"],
    } == {
        "nodes": 1699,
        "influences": 2270,
        "production": 85,
        "constitution": 4,
        "quantitative": 9,
        "modulation": 19,
    }
