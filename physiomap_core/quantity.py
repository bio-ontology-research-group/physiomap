"""Quality-typed determination: the composition semantics of a cross-scale edge is fixed by the
PATO quality's **measurement type**, not asserted per edge.

The insight (grounded in representational measurement theory -- Krantz, Luce, Suppes & Tversky
1971 Ch.3 "Extensive Measurement" -- and Wimsatt's aggregativity): whether and how a macro
quantity is composed from its micro parts depends on what *kind* of quantity it is. In the trait
model a PhysioMap node is ``(E, Q)`` and parthood holds between the entities ``E``; the quality
``Q`` decides what parthood between entities *means* for the trait-nodes:

* **extensive** (mass, volume, amount): additive over ``part_of`` -- whole = sum of parts, and the
  *same* extensive quality on part and whole. An extensive quantity is *defined* by an empirical
  concatenation with additive representation ``phi(a . b) = phi(a) + phi(b)``. This is
  **aggregation** (sign ``+``): the one case where parthood between entities directly induces a
  2-node constitutive edge between trait-nodes.
* **rate** (amount / time; flux, frequency): parallel fluxes add (sign ``+``). A rate is itself a
  *ratio* over the process's temporal extent, composed over the **occurrent** (temporal) mereology
  of sub-processes -- e.g. the beat frequency composing the flow volume of extended "heart
  beating"; duration plays the role a diluting volume plays for a concentration.
* **ratio** (concentration = amount / volume; density; osmolarity): NOT a parthood-induced
  constitutive edge. A ratio quality is a **ternary** measurement identity over *three* trait-nodes
  (ratio, numerator, denominator) -- a :class:`~physiomap_core.model.RatioDefinition`, handled as a
  definitional (deterministic) relation, ``d(ratio)/d(numerator)=+``, ``d(ratio)/d(denominator)=-``.
* **intensive** (pressure, pH, temperature, potential, activity, resistance, tone): no aggregative
  rule. Parthood between entities may still fix such a macro quality -- a **structural**
  determination (VSMC tone ▷ TPR) -- but the sign is **not derivable** from the quality type; it is
  asserted from an explicit mechanism (or the solver abstains).

This module classifies each node's quality (``ontology/quality_kinds.yaml``, keyed on the PATO
determinable, default ``intensive``), derives the determination sign an *aggregation* edge must
carry, and validates constitutive edges and ratio definitions against these rules. Novelty note:
the extensive/intensive typology is standard in measurement theory; deriving a *signed cross-scale
determination* from it, and separating ratio (ternary, measure-theoretic) from aggregation
(2-node, parthood), is not in the causal-abstraction / constitution literature (see
``paper/resources/SOTA_INDEX.md``).
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from physiomap_core.model import ConstitutiveEdge, Node, PhysioMap, Sign

__all__ = [
    "QualityKind",
    "load_quality_kinds",
    "quality_kind",
    "aggregation_sign",
    "effective_determination_sign",
    "validate_quantity",
    "QuantityReport",
]

_DEFAULT_KINDS = Path(__file__).resolve().parent.parent / "ontology" / "quality_kinds.yaml"


class QualityKind(str, Enum):
    """Measurement type of a PATO quality (fixes its part->whole composition rule)."""

    EXTENSIVE = "extensive"   # additive: whole = sum of parts (same quality on part and whole)
    RATIO = "ratio"           # intensive = numerator_extensive / denominator_extensive (ternary)
    RATE = "rate"             # temporal flux; parallel contributions add
    INTENSIVE = "intensive"   # no aggregative rule (default) -> sign asserted or abstain


_CACHE: dict[str, dict] | None = None


def load_quality_kinds(path: str | Path | None = None) -> dict[str, dict]:
    """PATO IRI -> ``{kind, label, ...}`` from the curated map (cached)."""
    global _CACHE
    if path is None and _CACHE is not None:
        return _CACHE
    data = yaml.safe_load(Path(path or _DEFAULT_KINDS).read_text()) or {}
    out = data.get("qualities", {}) or {}
    if path is None:
        _CACHE = out
    return out


def quality_kind(node_or_iri: Node | str | None, kinds: dict | None = None) -> QualityKind:
    """Measurement kind of a node's (or IRI's) quality; default ``INTENSIVE`` (safe/abstaining).

    A :class:`~physiomap_core.model.Node` may override the map via its ``quality_kind`` field
    (for a misused/ambiguous PATO IRI).
    """
    kinds = load_quality_kinds() if kinds is None else kinds
    iri: str | None
    if isinstance(node_or_iri, Node):
        if node_or_iri.quality_kind:
            return QualityKind(node_or_iri.quality_kind)
        iri = node_or_iri.quality_iri
    else:
        iri = node_or_iri
    if iri and iri in kinds:
        return QualityKind(kinds[iri]["kind"])
    return QualityKind.INTENSIVE


def aggregation_sign(macro_kind: QualityKind) -> Sign | None:
    """Sign an **aggregation** constitutive edge carries, from the macro quality kind.

    Extensive and rate macros aggregate additively over their parts (``+``); any other kind has no
    aggregative rule (``None`` -- the edge is structural and its sign is asserted, or a ratio which
    is not an aggregation at all).
    """
    if macro_kind in (QualityKind.EXTENSIVE, QualityKind.RATE):
        return Sign.PLUS
    return None


def effective_determination_sign(pmap: PhysioMap, edge: ConstitutiveEdge) -> Sign:
    """Determination sign the solver should use for a constitutive edge: ``+`` for an aggregation
    into an extensive/rate macro (derived), else the edge's asserted ``sign`` (a structural
    determination into an intensive macro, backward compatible)."""
    nodes = {n.id: n for n in pmap.nodes}
    macro = nodes.get(edge.macro)
    if macro is None:
        return edge.sign
    if edge.relation == "aggregation":
        derived = aggregation_sign(quality_kind(macro))
        if derived is not None:
            return derived
    return edge.sign


class QuantityReport(BaseModel):
    """Result of validating edges/definitions against quality-typed composition rules."""

    errors: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_quantity(pmap: PhysioMap, kinds: dict | None = None) -> QuantityReport:
    """Check constitutive edges and ratio definitions against quality-typed composition rules.

    **Errors**: an ``aggregation`` into a non-extensive/rate macro (you cannot sum concentrations /
    pressures); an ``aggregation`` whose micro quality kind differs from the macro's (unlike
    extensives do not aggregate -- surfaces mass▷volume-style mislabels); a ratio definition whose
    existing numerator edge is ``-`` or denominator edge is ``+`` (sign contradicts the quotient).
    **Notes** (advisory): a *structural* determination into an intensive macro (sign asserted from
    mechanism, not derivable -- expected, not a defect); a constitutive edge whose macro is a ratio
    quality (should be a :class:`~physiomap_core.model.RatioDefinition`, not a parthood edge); a
    ratio definition whose numerator/denominator is not extensive.
    """
    kinds = load_quality_kinds() if kinds is None else kinds
    nodes = {n.id: n for n in pmap.nodes}
    rep = QuantityReport()
    causal_pairs = {(edge.source, edge.target) for edge in pmap.causal_edges}
    for definition in pmap.quantitative_definitions:
        overlap = sorted(
            argument.node for argument in definition.arguments
            if (argument.node, definition.result) in causal_pairs
        )
        if overlap:
            rep.errors.append(
                f"{definition.kind}:{definition.result}: quantitative arguments also authored "
                f"as causal influences: {', '.join(overlap)}"
            )
    # Production and authored causal influences are separate layers; only genuine
    # material constitution belongs in these composition checks.
    for e in pmap.material_constitutive_edges:
        macro = nodes.get(e.macro)
        micro = nodes.get(e.micro)
        if macro is None:
            continue
        Mk = quality_kind(macro, kinds)
        mk = quality_kind(micro, kinds) if micro is not None else None
        tag = f"{e.micro} ▷ {e.macro} ({e.relation})"
        if e.relation == "aggregation":
            if Mk not in (QualityKind.EXTENSIVE, QualityKind.RATE):
                rep.errors.append(
                    f"{tag}: aggregation into a {Mk.value} macro quality; only extensive/rate "
                    "quantities are additive over parts (a ratio is a RatioDefinition, not this)"
                )
            elif (micro is not None and micro.quality_iri and macro.quality_iri
                  and micro.quality_iri != macro.quality_iri):
                rep.errors.append(
                    f"{tag}: aggregation of {micro.quality_iri} into {macro.quality_iri}; part and "
                    "whole must share the same extensive quality (you cannot sum unlike quantities)"
                )
        elif Mk == QualityKind.RATIO:
            rep.notes.append(
                f"{tag}: constitutive edge into a ratio macro quality; a ratio (=amount/volume) is "
                "a ternary RatioDefinition (measurement theory), not a 2-node parthood edge"
            )
        elif Mk == QualityKind.INTENSIVE:
            rep.notes.append(
                f"{tag}: structural determination into an intensive quality; sign {e.sign.value} is "
                "asserted from the mechanism (not derivable from the quality type)"
            )
    rep = _validate_ratio_definitions(pmap, kinds, rep)
    return rep


def _validate_ratio_definitions(pmap: PhysioMap, kinds: dict, rep: QuantityReport) -> QuantityReport:
    nodes = {n.id: n for n in pmap.nodes}
    causal_sign = {(e.source, e.target): e.sign for e in pmap.causal_edges}
    for r in pmap.ratio_definitions:
        ratio, num, den = nodes.get(r.ratio), nodes.get(r.numerator), nodes.get(r.denominator)
        tag = f"{r.ratio} = {r.numerator} / {r.denominator}"
        if ratio is not None and quality_kind(ratio, kinds) not in (QualityKind.RATIO,):
            rep.notes.append(
                f"{tag}: ratio node quality is {quality_kind(ratio, kinds).value}, expected ratio")
        for role, nd in (("numerator", num), ("denominator", den)):
            if nd is not None and quality_kind(nd, kinds) not in (
                    QualityKind.EXTENSIVE, QualityKind.RATE):
                rep.notes.append(
                    f"{tag}: {role} {nd.id} is {quality_kind(nd, kinds).value}, expected extensive")
        # existing causal edges must agree with the quotient's signs
        ns = causal_sign.get((r.numerator, r.ratio))
        ds = causal_sign.get((r.denominator, r.ratio))
        if ns is not None and ns is not Sign.PLUS:
            rep.errors.append(
                f"{tag}: numerator edge {r.numerator}->{r.ratio} is {ns.value}, but a ratio rises "
                "with its numerator (+)")
        if ds is not None and ds is not Sign.MINUS:
            rep.errors.append(
                f"{tag}: denominator edge {r.denominator}->{r.ratio} is {ds.value}, but a ratio "
                "falls with its denominator (-)")
    return rep
