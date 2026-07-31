"""Tests for quality-typed determination (physiomap_core.quantity) + its solver effects."""
from __future__ import annotations

import pytest

from physiomap_core.model import (
    ConstitutiveEdge,
    Node,
    PhysioMap,
    RatioDefinition,
    Scale,
    Sign,
)
from physiomap_core.multiscale import solve_multiscale
from physiomap_core.qualitative import Intervention
from physiomap_core.quantity import (
    QualityKind,
    aggregation_sign,
    quality_kind,
    validate_quantity,
)
from physiomap_core.sigma import deterministic_closure

CONC = "PATO:0000033"   # concentration (ratio)
AMOUNT = "PATO:0000070"  # amount (extensive)
VOLUME = "PATO:0000918"  # volume (extensive)
MASS = "PATO:0000125"    # mass (extensive)
RATIOQ = "PATO:0001019"  # mass density / volume-fraction (ratio kind)
RATE = "PATO:0000161"    # rate
PRESSURE = "PATO:0001025"  # pressure (intensive)


# --------------------------------------------------------------------------- classification
def test_quality_kind_classification():
    assert quality_kind(CONC) == QualityKind.RATIO
    assert quality_kind(VOLUME) == QualityKind.EXTENSIVE
    assert quality_kind(AMOUNT) == QualityKind.EXTENSIVE
    assert quality_kind(RATE) == QualityKind.RATE
    assert quality_kind(PRESSURE) == QualityKind.INTENSIVE
    assert quality_kind("PATO:9999999") == QualityKind.INTENSIVE  # unknown -> safe default
    assert quality_kind(None) == QualityKind.INTENSIVE


def test_quality_kind_node_override():
    n = Node(id="x", label="x", scale=Scale.ORGAN, quality_iri=PRESSURE, quality_kind="extensive")
    assert quality_kind(n) == QualityKind.EXTENSIVE  # override wins over the IRI lookup


def test_aggregation_sign():
    assert aggregation_sign(QualityKind.EXTENSIVE) == Sign.PLUS
    assert aggregation_sign(QualityKind.RATE) == Sign.PLUS
    assert aggregation_sign(QualityKind.INTENSIVE) is None  # no aggregative rule
    assert aggregation_sign(QualityKind.RATIO) is None      # a ratio is not an aggregation


# --------------------------------------------------------------------------- ratio via RatioDefinition
def _ratio_map() -> PhysioMap:
    """A concentration = amount / volume ternary identity (numerator +, denominator -)."""
    nodes = [
        Node(id="amt", label="solute amount", scale=Scale.ORGAN, quality_iri=AMOUNT),
        Node(id="vol", label="volume", scale=Scale.ORGAN, quality_iri=VOLUME),
        Node(id="conc", label="concentration", scale=Scale.ORGAN, quality_iri=CONC),
    ]
    rd = RatioDefinition(ratio="conc", numerator="amt", denominator="vol")
    return PhysioMap(nodes=nodes, causal_edges=[], ratio_definitions=[rd])


def test_ratio_definition_validates_clean():
    assert validate_quantity(_ratio_map()).ok


def test_ratio_definition_injects_signed_edges_into_solver():
    pm = _ratio_map()
    up = solve_multiscale(pm, Intervention(targets={"amt": Sign.PLUS}, label="amt+")).predicted
    assert up["conc"] == Sign.PLUS                     # numerator raises the ratio
    dn = solve_multiscale(pm, Intervention(targets={"vol": Sign.PLUS}, label="vol+")).predicted
    assert dn["conc"] == Sign.MINUS                    # denominator dilutes the ratio


def test_ratio_ambiguous_when_numerator_and_denominator_co_move():
    pm = _ratio_map()
    both = solve_multiscale(
        pm, Intervention(targets={"amt": Sign.PLUS, "vol": Sign.PLUS}, label="both+")
    ).predicted
    assert both["conc"] == Sign.UNKNOWN                # opposite pushes -> undetermined


def test_clean_ratio_node_is_deterministic():
    pm = _ratio_map()
    assert "conc" in deterministic_closure(pm, {"amt", "vol"})   # both constituents fix it
    assert "conc" not in deterministic_closure(pm, {"amt"})      # numerator alone does not


def test_ratio_definition_sign_conflict_is_error():
    # An identity argument may not also be authored as a causal influence.
    nodes = [
        Node(id="amt", label="amt", scale=Scale.ORGAN, quality_iri=AMOUNT),
        Node(id="vol", label="vol", scale=Scale.ORGAN, quality_iri=VOLUME),
        Node(id="conc", label="conc", scale=Scale.ORGAN, quality_iri=CONC),
    ]
    from physiomap_core.model import CausalEdge
    edges = [CausalEdge(source="vol", target="conc", sign=Sign.PLUS)]  # wrong: should dilute (-)
    rd = RatioDefinition(ratio="conc", numerator="amt", denominator="vol")
    rep = validate_quantity(PhysioMap(nodes=nodes, causal_edges=edges, ratio_definitions=[rd]))
    assert not rep.ok
    assert any("also authored as causal influences" in error for error in rep.errors)


# --------------------------------------------------------------------------- aggregation validation
def test_aggregation_quality_mismatch_is_error():
    # a mass part cannot aggregate into a volume whole (unlike extensive quantities)
    nodes = [
        Node(id="rcm", label="red cell mass", scale=Scale.TISSUE, quality_iri=MASS),
        Node(id="bv", label="blood volume", scale=Scale.ORGAN, quality_iri=VOLUME),
    ]
    e = [ConstitutiveEdge(micro="rcm", macro="bv", relation="aggregation", sign=Sign.PLUS)]
    rep = validate_quantity(PhysioMap(nodes=nodes, causal_edges=[], constitutive_edges=e))
    assert not rep.ok
    assert any("part and whole must share the same extensive quality" in m for m in rep.errors)


def test_aggregation_into_ratio_is_error():
    nodes = [
        Node(id="p", label="part", scale=Scale.TISSUE, quality_iri=RATIOQ),
        Node(id="w", label="whole", scale=Scale.ORGAN, quality_iri=RATIOQ),
    ]
    e = [ConstitutiveEdge(micro="p", macro="w", relation="aggregation", sign=Sign.PLUS)]
    rep = validate_quantity(PhysioMap(nodes=nodes, causal_edges=[], constitutive_edges=e))
    assert not rep.ok
    assert any("aggregation into a ratio" in m for m in rep.errors)


def test_structural_determination_into_intensive_is_note():
    # part_of+determination into an intensive macro: sign asserted from mechanism (expected)
    nodes = [
        Node(id="mlc", label="MLC phos", scale=Scale.SUBCELLULAR, quality_iri=RATIOQ),
        Node(id="tone", label="vascular tone", scale=Scale.TISSUE, quality_iri=PRESSURE),
    ]
    e = [ConstitutiveEdge(micro="mlc", macro="tone", relation="part_of+determination", sign=Sign.PLUS)]
    rep = validate_quantity(PhysioMap(nodes=nodes, causal_edges=[], constitutive_edges=e))
    assert rep.ok
    assert any("structural determination into an intensive quality" in m for m in rep.notes)


def test_extensive_aggregation_whole_is_deterministic():
    nodes = [
        Node(id="p1", label="part1 vol", scale=Scale.TISSUE, quality_iri=VOLUME),
        Node(id="p2", label="part2 vol", scale=Scale.TISSUE, quality_iri=VOLUME),
        Node(id="whole", label="whole vol", scale=Scale.ORGAN, quality_iri=VOLUME),
    ]
    edges = [
        ConstitutiveEdge(micro="p1", macro="whole", relation="aggregation", sign=Sign.PLUS),
        ConstitutiveEdge(micro="p2", macro="whole", relation="aggregation", sign=Sign.PLUS),
    ]
    pm = PhysioMap(nodes=nodes, causal_edges=[], constitutive_edges=edges)
    assert "whole" in deterministic_closure(pm, {"p1", "p2"})
