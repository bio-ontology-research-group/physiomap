"""Core PhysioMap data model.

Pydantic v2 types for the PhysioMap formalism plus YAML (de)serialisation and
networkx helpers. See ``README.md`` for the conceptual background.

A **Node** is a variable: a ``(biological entity, PATO determinable-quality)`` pair at a
named scale. A **CausalEdge** is a signed, interventionist causal relation (it may
participate in cycles); scale is descriptive and does not determine relation type. A
**ProductionEdge** records a typed
process-output or consumption relation with its own evidence vocabulary. A
**ConstitutiveEdge** is a *cross-scale* ``part_of`` + determination relation and is
**never** traversed by causal reasoning.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import re
from typing import Any, Iterable, Literal

import networkx as nx
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Scale(str, Enum):
    """Biological scale of a variable (coarse-grained, ordered fine -> coarse)."""

    MOLECULAR = "molecular"
    SUBCELLULAR = "subcellular"
    CELLULAR = "cellular"
    TISSUE = "tissue"
    ORGAN = "organ"
    ORGAN_SYSTEM = "organ_system"
    ORGANISM = "organism"


class Sign(str, Enum):
    """Sign of a causal influence or of a predicted change.

    ``UNKNOWN`` ('?') means *qualitatively undetermined* — used both for edges whose
    sign is not known and for solver outputs where the sign algebra cannot decide.
    """

    PLUS = "+"
    MINUS = "-"
    UNKNOWN = "?"

    def __mul__(self, other: "Sign") -> "Sign":
        """Compose two signs along a path (+·+=+, +·-=-, -·-=+, anything·?=?)."""
        if self is Sign.UNKNOWN or other is Sign.UNKNOWN:
            return Sign.UNKNOWN
        return Sign.PLUS if self is other else Sign.MINUS


class CausalEvidenceClass(str, Enum):
    """Class of evidence grounding a causal edge's **interventional** claim.

    A PhysioMap causal edge asserts ``do(source) -> Δtarget`` with everything else held
    fixed (Pearl/Woodward interventionist semantics). The *admissible* classes establish
    that **manipulating the source actually shifts the target**; the *associational*
    classes establish only that source and target co-vary and must **not** be imported as
    causal edges (use :func:`physiomap_core.causal_evidence.is_interventional`).

    This distinction is the import gate for externally-sourced edges (gene-regulatory
    networks, whole-cell / ODE models, pathway databases): a co-expression or
    binding-only relation is an *association*, not a cause, and is rejected.
    """

    # --- interventional / mechanistic (admissible as a causal edge) ---
    PERTURBATION = "perturbation"  # KO/KD/CRISPR/RNAi/overexpression of source -> target changes
    PHARMACOLOGICAL = "pharmacological"  # agonist/antagonist/inhibitor of source -> target changes
    GENETIC_LOF_GOF = "genetic_lof_gof"  # human Mendelian loss/gain-of-function -> downstream change
    MENDELIAN_RANDOMIZATION = "mendelian_randomization"  # germline instrument (IV ~ do())
    MECHANISTIC_MODEL = "mechanistic_model"  # sign from a curated mechanistic ODE/Jacobian (causal by construction)
    CURATED_MECHANISTIC = "curated_mechanistic"  # pathway-DB causal statement curated from mechanistic/perturbation evidence
    # --- associational (INADMISSIBLE as a causal edge) ---
    BINDING_ONLY = "binding_only"  # ChIP-seq/motif: physical binding, no demonstrated functional effect
    COEXPRESSION = "coexpression"  # correlation / co-expression inference (ARACNe/GENIE3/WGCNA)
    OBSERVATIONAL_ASSOCIATION = "observational_association"  # epidemiological/GWAS assoc without an instrument
    UNKNOWN = "unknown"  # evidence class not established


class ProductionEvidenceClass(str, Enum):
    """Evidence status for a typed process-output or consumption relation.

    Production is neither material constitution nor an authored SCM causal influence,
    so its evidence vocabulary remains separate from the six interventional promotion
    classes. The explicit legacy value preserves unaudited relations without silently
    treating them as controlled evidence.
    """

    CURATED_SOURCE_STATEMENT = "curated_source_statement"
    EXPERIMENTAL_PERTURBATION = "experimental_perturbation"
    MECHANISTIC_MODEL = "mechanistic_model"
    LEGACY_UNCLASSIFIED = "legacy-evidence-unclassified"


class ContextKind(str, Enum):
    """Kind of steady-state regime in which a causal influence is active.

    Dynamic contexts are recorded explicitly so curators can surface relationships that
    depend on pulse frequency, duration, phase, or another non-steady-state quantity. Such
    records must abstain rather than pretending that a fixed signed edge is available.
    """

    PHYSIOLOGICAL_REGIME = "physiological-regime"
    LIFE_STAGE = "life-stage"
    MODULATOR_REGIME = "modulator-regime"
    SOURCE_REGIME = "source-regime"
    DYNAMIC = "dynamic"


class InfluenceContext(BaseModel):
    """Stable, selectable context attached to a causal influence.

    ``id`` is the runtime selector; ``label`` is explanatory text. A legacy plain string is
    accepted and upgraded deterministically, but new authored data should provide both fields.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    label: str
    kind: ContextKind = ContextKind.PHYSIOLOGICAL_REGIME
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _upgrade_string(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        context_id = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return {"id": context_id, "label": value}

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9]+(?:[-_.][a-z0-9]+)*", value):
            raise ValueError("context id must be a lowercase stable slug")
        return value

    @field_validator("label")
    @classmethod
    def _valid_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("context label must be non-empty")
        return value


def influence_identifier(
    source: str, target: str, sign: Sign, context: InfluenceContext | None = None
) -> str:
    """Return the projection-version-independent identity of an authored influence."""

    sign_name = {Sign.PLUS: "positive", Sign.MINUS: "negative", Sign.UNKNOWN: "unknown"}[sign]
    suffix = f":{context.id}" if context else ""
    return f"influence:{source}:{sign_name}:{target}{suffix}"


def combine_parallel(signs: Iterable[Sign]) -> Sign:
    """Combine signs arriving on parallel paths into one node.

    Agreement yields that sign; an empty input yields ``UNKNOWN``; any disagreement
    (opposing signs, or any ``UNKNOWN``) is a qualitative cancellation -> ``UNKNOWN``.
    """
    distinct = set(signs)
    if not distinct:
        return Sign.UNKNOWN
    if Sign.UNKNOWN in distinct:
        return Sign.UNKNOWN
    if len(distinct) == 1:
        return next(iter(distinct))
    return Sign.UNKNOWN


class Node(BaseModel):
    """A physiological variable: an entity's PATO determinable-quality at a scale."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., description="Unique node identifier (stable key).")
    label: str = Field(..., description="Human-readable label.")
    scale: Scale
    entity_iri: str | None = Field(
        default=None, description="Entity IRI (Uberon/GO/CL/ChEBI). Optional in Phase 1."
    )
    quality_iri: str | None = Field(
        default=None, description="Quality determinable IRI (PATO). Optional in Phase 1."
    )
    bearer_kind: str | None = Field(
        default=None,
        description=(
            "OPTIONAL override of the BFO category of the quality's bearer "
            "(``continuant`` = material entity | ``occurrent`` = process). Normally derived "
            "(``physiomap_core.bfo``): a process quality (rate/flux) or GO-process entity is an "
            "occurrent, else a continuant. Determines constitution admissibility — constitution "
            "is material (continuant↔continuant); a process quality relates to a material one "
            "only through a typed process-output relation (a ``production_edges`` record)."
        ),
    )
    quality_kind: str | None = Field(
        default=None,
        description=(
            "OPTIONAL override of the quality's MEASUREMENT TYPE "
            "(``extensive`` | ``ratio`` | ``rate`` | ``intensive``) used to *derive* the "
            "composition rule of constitutive determination edges into this node "
            "(``physiomap_core.quantity``). Normally left None: the kind is looked up from the "
            "PATO ``quality_iri`` via ``ontology/quality_kinds.yaml`` (default ``intensive``). "
            "Set this only for a misused/ambiguous PATO IRI whose true kind differs."
        ),
    )
    bearer_entity_iri: str | None = Field(
        default=None,
        description=(
            "OPTIONAL anatomical bearer (Uberon/CL) of a molecular/process quality. Most "
            "molecular/subcellular nodes record a *molecular* entity (GO/PR/ChEBI) in "
            "``entity_iri``, so their structural ``part_of`` to a macro entity is "
            "unverifiable. Recording the cell/organ that *bears* the quality here lets the "
            "constitution validator check the structural part_of path via the bearer "
            "(``cardiomyocyte`` Ca²⁺ ▷ cardiac output: bearer = CL:0000746)."
        ),
    )
    exogenous: bool = Field(
        default=False,
        description=(
            "If True, this node is a **forcing / boundary input** whose value is set "
            "outside the modelled system (e.g. dietary ``water_intake`` / ``food_intake``, "
            "ambient challenge). Such a node is legitimately *not* constituted by micro "
            "configuration, so it is excluded from the free-floating-macro grounding gap."
        ),
    )

    @field_validator("id", "label")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be a non-empty string")
        return v


class CausalEdge(BaseModel):
    """A signed, interventionist causal edge (may form cycles).

    Abbreviates a ``quality -> disposition -> process -> quality`` mechanism. A
    self-edge (``source == target``) encodes explicit self-regulation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str | None = Field(
        default=None,
        description=(
            "Stable identity of this particular influence. If omitted, a deterministic ID is "
            "derived from source, target, sign, and context; it does not depend on a projection "
            "registry version."
        ),
    )
    source: str
    target: str
    sign: Sign
    context: InfluenceContext | None = Field(
        default=None,
        description=(
            "Steady-state regime in which this influence is active. Uncontextualized "
            "influences are active in every context slice."
        ),
    )
    mechanism: str | None = Field(
        default=None, description="Optional mechanism reference (e.g. a GO process IRI)."
    )
    evidence: str | None = Field(
        default=None, description="Provenance / literature citation for the sign."
    )
    causal_evidence: CausalEvidenceClass | None = Field(
        default=None,
        description=(
            "Controlled-vocabulary class of the evidence establishing this edge is "
            "**interventional** (``do(source)->Δtarget``), not a mere association. Optional "
            "for hand-curated fragments; **required and gated** for edges imported from "
            "external resources (GRNs, ODE/whole-cell models, pathway DBs) so that "
            "binding-only / co-expression associations are never admitted as causes. See "
            "``physiomap_core.causal_evidence`` and ``scripts/validate_causal_evidence.py``."
        ),
    )
    definitional: bool = Field(
        default=False,
        description=(
            "If True, this edge is part of an *algebraic identity*: the target is a "
            "deterministic function of its (definitional) parents (e.g. MAP = CO x TPR; "
            "pH = Henderson-Hasselbalch(HCO3, pCO2)), not a stochastic mechanism. Such an "
            "edge still carries an interventional sign (comparative statics use it like any "
            "causal edge), but it is flagged so sigma-separation can treat a node ALL of "
            "whose parents are definitional as a deterministic node (Geiger-Verma-Pearl "
            "deterministic closure). Only mark an edge definitional when the target is a "
            "*complete* identity in its definitional parents."
        ),
    )

    @model_validator(mode="after")
    def _identity_and_context_semantics(self) -> "CausalEdge":
        if self.context and self.context.kind is ContextKind.DYNAMIC and self.sign is not Sign.UNKNOWN:
            raise ValueError("a dynamic, out-of-steady-state context must use sign '?' and abstain")
        if self.id is None:
            object.__setattr__(
                self, "id", influence_identifier(self.source, self.target, self.sign, self.context)
            )
        elif not self.id.strip():
            raise ValueError("influence id must be non-empty")
        return self


class ConstitutiveEdge(BaseModel):
    """A cross-scale, **constitutive** (not causal) edge: micro configuration fixes
    a macro quality. Never traversed by the causal separation / solver logic.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    micro: str = Field(..., description="Finer-scale (constituting) node id.")
    macro: str = Field(..., description="Coarser-scale (constituted) node id.")
    relation: str = Field(
        default="part_of+determination",
        description="Constitutive relation label (e.g. 'part_of+determination').",
    )
    sign: Sign = Field(
        default=Sign.PLUS,
        description=(
            "Determination sign: how the micro quality co-varies with the macro quality "
            "it constitutes (default +). NOT a causal sign — used only by the separate "
            "constitutive (determination) propagation, never by the causal solver. For an "
            "``aggregation`` (extensive, same quality on part and whole) the sign is always +; "
            "for a *structural* determination into an intensive macro quality the sign is "
            "asserted from the mechanism. (Ratio qualities are NOT constitution — a concentration "
            "= amount/volume is a ternary :class:`RatioDefinition`, measurement theory, not a "
            "parthood edge.)"
        ),
    )

    @field_validator("relation")
    @classmethod
    def _constitution_relation(cls, value: str) -> str:
        if value == "production":
            raise ValueError(
                "production is not constitution; use the top-level production_edges collection"
            )
        return value


class ProductionEdge(BaseModel):
    """A typed process-output or consumption relation.

    ``+`` means that increasing the source process increases the target pool/output;
    ``-`` means that increasing it consumes or removes the target. Production is
    represented independently from both material constitution and authored causal
    influences. Qualitative reasoning may expose it as an explicitly tagged derived
    shadow edge for backward-compatible sign propagation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str
    target: str
    sign: Sign
    mechanism: str | None = None
    evidence: str | None = None
    production_evidence: ProductionEvidenceClass

    @field_validator("source", "target")
    @classmethod
    def _production_ref_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value

    @model_validator(mode="after")
    def _controlled_provenance(self) -> "ProductionEdge":
        if self.source == self.target:
            raise ValueError("production source and target must differ")
        if self.production_evidence is not ProductionEvidenceClass.LEGACY_UNCLASSIFIED:
            if not self.mechanism or not self.mechanism.strip():
                raise ValueError("controlled production evidence requires a mechanism")
            if not self.evidence or not self.evidence.strip():
                raise ValueError("controlled production evidence requires a traceable source")
        return self


class RatioDefinition(BaseModel):
    """A **ternary** measurement-theoretic identity: a *ratio* quality node equals a numerator
    over a denominator — ``concentration = amount / volume``, ``hematocrit = red-cell volume /
    blood volume``, ``density = mass / volume``.

    This is the case the trait model separates out from constitution: a ratio quality is **not**
    induced by parthood between entities (it is not a 2-node ``part_of`` determination); it is a
    **definitional** relation over **three** trait-nodes — the ratio, its extensive numerator, and
    its extensive denominator — grounded in representational measurement theory (Krantz-Luce-
    Suppes-Tversky Ch.3), not mereology. The ratio node is a Geiger-Verma-Pearl *deterministic*
    node: fixing the numerator and denominator fixes it, with ``d(ratio)/d(numerator) = +`` and
    ``d(ratio)/d(denominator) = -``.

    **Realization** mirrors definitional identities: the solver treats the ratio node as
    deterministic (and marks the ``numerator -> ratio`` / ``denominator -> ratio`` edges
    definitional) **only when those are its sole causal parents**; an over-parented ratio node (an
    extra stochastic parent, like a direct hormonal driver of hematocrit) is left as an ordinary
    causal target, exactly as an entangled definitional identity stays in the causal graph. The
    edges are injected into :meth:`PhysioMap.causal_subgraph` if absent, so a RatioDefinition both
    records the measurement structure and, where clean, contributes the correct signs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ratio: str = Field(..., description="The ratio-quality node (e.g. a concentration/fraction).")
    numerator: str = Field(..., description="The extensive numerator node (amount/count/volume).")
    denominator: str = Field(..., description="The extensive denominator node (volume/duration).")
    mechanism: str | None = Field(
        default=None, description="Optional identity reference (the measurement/definition)."
    )
    evidence: str | None = Field(
        default=None, description="Provenance for the ratio identity."
    )


class QuantitativeArgumentDefinition(BaseModel):
    """One signed argument of a typed quantitative identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    node: str = Field(..., description="Trait node used as an argument of the identity.")
    role: str = Field(
        default="argument",
        description="Semantic role such as numerator, denominator, factor, or summand.",
    )
    derivative_sign: Sign = Field(
        ...,
        description="Sign of the local partial derivative of the result with respect to this argument.",
    )

    @field_validator("node", "role")
    @classmethod
    def _argument_non_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must be a non-empty string")
        return value


class QuantitativeDefinition(BaseModel):
    """A typed algebraic identity kept separate from causal influences.

    The declared derivative signs are comparative statics of the identity.  They may be
    exposed as explicitly tagged, derived shadow edges to qualitative solvers, but they are
    never evidence-bearing causal claims in the authored model or canonical SCM influence list.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal[
        "ratio", "sum", "product", "rate", "aggregation", "structural-function"
    ]
    result: str
    arguments: list[QuantitativeArgumentDefinition]
    mechanism: str | None = None
    evidence: str | None = None

    @model_validator(mode="after")
    def _validate_shape(self) -> "QuantitativeDefinition":
        if not self.arguments:
            raise ValueError("quantitative definition requires at least one argument")
        nodes = [argument.node for argument in self.arguments]
        if len(nodes) != len(set(nodes)):
            raise ValueError("quantitative definition has duplicate arguments")
        if self.result in nodes:
            raise ValueError("quantitative definition cannot use its result as an argument")
        roles = [argument.role for argument in self.arguments]
        signs = [argument.derivative_sign for argument in self.arguments]
        if self.kind in {"ratio", "rate"}:
            if roles != ["numerator", "denominator"] or signs != [Sign.PLUS, Sign.MINUS]:
                raise ValueError(
                    f"{self.kind} requires (+) numerator followed by (-) denominator"
                )
        elif self.kind in {"sum", "aggregation"}:
            if any(role != "summand" for role in roles) or any(sign is not Sign.PLUS for sign in signs):
                raise ValueError(f"{self.kind} requires positive summand arguments")
        elif self.kind == "product":
            if len(self.arguments) < 2:
                raise ValueError("product requires at least two factors")
            if any(role != "factor" for role in roles) or any(sign is not Sign.PLUS for sign in signs):
                raise ValueError("positive-domain product requires positive factor arguments")
        return self


def _ratio_as_quantitative(ratio: dict[str, Any] | RatioDefinition) -> dict[str, Any]:
    value = ratio.model_dump(mode="json", exclude_none=True) if isinstance(
        ratio, RatioDefinition
    ) else dict(ratio)
    return {
        "kind": "ratio",
        "result": value["ratio"],
        "arguments": [
            {"node": value["numerator"], "role": "numerator", "derivative_sign": "+"},
            {"node": value["denominator"], "role": "denominator", "derivative_sign": "-"},
        ],
        **({"mechanism": value["mechanism"]} if value.get("mechanism") else {}),
        **({"evidence": value["evidence"]} if value.get("evidence") else {}),
    }


class ModulationEdge(BaseModel):
    """A **multiplicative** (gain) edge: ``modulator`` scales the *strength* of a causal
    influence identified by ``influence_id`` rather than adding to the target directly.

    Operating-point model: ``edge_target = ... + k(modulator)*edge_source + ...`` with
    ``sign(dk/d modulator) = sign`` (``+`` = raises the gain, ``-`` = lowers it). This is the
    structure George Gkoutos's heart-rate curation surfaced (T3 raises β1-adrenergic
    chronotropic responsiveness, amplifying the ``sympathetic_tone -> heart_rate`` edge).

    Two facts make this tractable in the sign world:

    * **First order** (around a positive operating point) a modulation degenerates to an
      ordinary additive edge ``modulator -> edge_target`` with the same ``sign`` (because
      ``d target/d modulator = k'(modulator)*edge_source`` and ``edge_source > 0``). So a
      modulation whose gain keeps one sign changes **no** node-level sign prediction — the
      additive "shadow" edge carries the main effect and soundness is preserved. (Only when
      ``can_flip_sign`` is True can the modulated edge's sign itself become ``?``.)
    * **Second order** is the genuinely new content: the cross-partial
      ``d^2 target/d(edge_source) d(modulator) = k'(modulator)`` has sign ``sign`` — i.e. it
      answers "does intervening on θ change the *sensitivity* of target to edge_source?".
      Computed by :func:`physiomap_core.modulation.gain_sensitivity`.

    Modulation edges are **not** added to ``causal_subgraph`` (the solver is untouched); they
    are a parallel layer enabling the gain query. The first-order main effect is encoded as a
    normal :class:`CausalEdge` ``modulator -> edge_target`` (the modulation's shadow).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    modulator: str = Field(..., description="Node whose level scales the edge gain.")
    influence_id: str | None = Field(
        default=None,
        description=(
            "Stable ID of the exact causal influence whose gain is modulated. Required in the "
            "canonical model; legacy source/target references are upgraded only when unique."
        ),
    )
    edge_source: str | None = Field(
        default=None,
        description="Compatibility copy of the modulated influence's source.",
    )
    edge_target: str | None = Field(
        default=None,
        description="Compatibility copy of the modulated influence's target.",
    )
    sign: Sign = Field(
        ..., description="Sign of d(gain)/d(modulator): + raises the gain, - lowers it."
    )
    can_flip_sign: bool = Field(
        default=False,
        description=(
            "If True the gain can cross zero, so the modulated edge's own sign is "
            "indeterminate ('?') unless the modulator's level is pinned. Most physiological "
            "gains keep one sign (False)."
        ),
    )
    mechanism: str | None = None
    evidence: str | None = None
    causal_evidence: CausalEvidenceClass | None = None

    @model_validator(mode="after")
    def _has_resolvable_target(self) -> "ModulationEdge":
        if self.influence_id:
            return self
        if self.edge_source and self.edge_target:
            return self
        raise ValueError(
            "modulation requires influence_id, or both legacy edge_source and edge_target"
        )


class PhysioMap(BaseModel):
    """A PhysioMap with separate causal, production, and constitutive layers."""

    model_config = ConfigDict(extra="forbid")

    name: str = "physiomap"
    description: str | None = None
    nodes: list[Node] = Field(default_factory=list)
    causal_edges: list[CausalEdge] = Field(default_factory=list)
    production_edges: list[ProductionEdge] = Field(
        default_factory=list,
        description=(
            "Typed process-output or consumption relations. They are neither material "
            "constitution nor authored SCM causal influences."
        ),
    )
    constitutive_edges: list[ConstitutiveEdge] = Field(default_factory=list)
    modulation_edges: list[ModulationEdge] = Field(
        default_factory=list,
        description=(
            "Multiplicative (gain) edges: a node scales the strength of a causal edge. "
            "Not traversed by the causal solver; queried by physiomap_core.modulation."
        ),
    )
    quantitative_definitions: list[QuantitativeDefinition] = Field(
        default_factory=list,
        description=(
            "Typed algebraic identities (ratio, sum, product, rate, aggregation, or structural "
            "function). These are not causal influences; causal_subgraph exposes only tagged "
            "derived shadows for qualitative compatibility."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_ratio_definitions(cls, data: Any) -> Any:
        """Accept the former ``ratio_definitions`` input as a lossless compatibility alias."""
        if not isinstance(data, dict) or not data.get("ratio_definitions"):
            return data
        upgraded = dict(data)
        definitions = list(upgraded.get("quantitative_definitions") or [])
        definitions.extend(_ratio_as_quantitative(ratio)
                           for ratio in upgraded.pop("ratio_definitions") or [])
        upgraded["quantitative_definitions"] = definitions
        return upgraded

    # --- integrity ------------------------------------------------------------

    @model_validator(mode="after")
    def _check_references(self) -> "PhysioMap":
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("duplicate node ids")
        influence_ids = [e.id for e in self.causal_edges]
        if len(influence_ids) != len(set(influence_ids)):
            raise ValueError("duplicate causal influence ids")
        causal_by_id = {e.id: e for e in self.causal_edges}
        for e in self.causal_edges:
            for ref in (e.source, e.target):
                if ref not in ids:
                    raise ValueError(f"causal edge references unknown node {ref!r}")
        for e in self.production_edges:
            for ref in (e.source, e.target):
                if ref not in ids:
                    raise ValueError(f"production edge references unknown node {ref!r}")
        for e in self.constitutive_edges:
            for ref in (e.micro, e.macro):
                if ref not in ids:
                    raise ValueError(f"constitutive edge references unknown node {ref!r}")
        resolved_modulations: list[ModulationEdge] = []
        for e in self.modulation_edges:
            if e.modulator not in ids:
                raise ValueError(f"modulation edge references unknown node {e.modulator!r}")
            target = causal_by_id.get(e.influence_id) if e.influence_id else None
            if e.influence_id and target is None:
                raise ValueError(
                    f"modulation edge references unknown influence {e.influence_id!r}"
                )
            if target is None:
                candidates = [
                    edge
                    for edge in self.causal_edges
                    if (edge.source, edge.target) == (e.edge_source, e.edge_target)
                ]
                if not candidates:
                    raise ValueError(
                        "modulation edge modulates a non-existent causal edge "
                        f"{e.edge_source!r}->{e.edge_target!r}"
                    )
                if len(candidates) != 1:
                    raise ValueError(
                        "legacy modulation target is ambiguous; supply influence_id for "
                        f"{e.edge_source!r}->{e.edge_target!r}"
                    )
                target = candidates[0]
            if e.edge_source and e.edge_source != target.source:
                raise ValueError(
                    f"modulation source {e.edge_source!r} disagrees with {target.id!r}"
                )
            if e.edge_target and e.edge_target != target.target:
                raise ValueError(
                    f"modulation target {e.edge_target!r} disagrees with {target.id!r}"
                )
            resolved_modulations.append(e.model_copy(update={
                "influence_id": target.id,
                "edge_source": target.source,
                "edge_target": target.target,
            }))
        self.modulation_edges = resolved_modulations
        for definition in self.quantitative_definitions:
            for ref in (definition.result, *(argument.node for argument in definition.arguments)):
                if ref not in ids:
                    raise ValueError(f"quantitative definition references unknown node {ref!r}")
        return self

    # --- accessors ------------------------------------------------------------

    def node(self, node_id: str) -> Node:
        """Return the node with ``node_id`` (raises ``KeyError`` if absent)."""
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise KeyError(node_id)

    def influence(self, influence_id: str) -> CausalEdge:
        """Return the exact causal influence with ``influence_id``."""
        for edge in self.causal_edges:
            if edge.id == influence_id:
                return edge
        raise KeyError(influence_id)

    @property
    def contexts(self) -> list[InfluenceContext]:
        """All selectable contexts, ordered by stable ID."""
        values = {edge.context.id: edge.context for edge in self.causal_edges if edge.context}
        return [values[key] for key in sorted(values)]

    def active_causal_edges(self, contexts: Iterable[str] | None = None) -> list[CausalEdge]:
        """Return influences active in a context slice.

        With no selection all contextual alternatives remain visible and parallel conflicts
        collapse conservatively to ``?`` in :meth:`causal_subgraph`. With a selection,
        uncontextualized influences plus matching contextual influences are active.
        """
        if contexts is None:
            return list(self.causal_edges)
        selected = set(contexts)
        known = {context.id for context in self.contexts}
        unknown = selected - known
        if unknown:
            raise ValueError(f"unknown influence contexts: {sorted(unknown)}")
        return [
            edge
            for edge in self.causal_edges
            if edge.context is None or edge.context.id in selected
        ]

    def context_slice(self, contexts: Iterable[str]) -> "PhysioMap":
        """Return an operational model fixed to the selected steady-state regimes.

        Selected records keep their stable context-derived influence IDs, but their context
        guards are discharged in the returned fixed-regime model. Consequently, ordinary
        solvers can consume the slice without treating its already-selected edges as uncertain.
        """
        causal = self.active_causal_edges(contexts)
        active_ids = {edge.id for edge in causal}
        data = self.model_dump(mode="python")
        data["causal_edges"] = []
        for edge in causal:
            fixed = edge.model_dump(mode="python")
            fixed.pop("context", None)
            data["causal_edges"].append(fixed)
        data["modulation_edges"] = [
            edge.model_dump(mode="python")
            for edge in self.modulation_edges
            if edge.influence_id in active_ids
        ]
        return type(self).model_validate(data)

    @property
    def node_ids(self) -> list[str]:
        return [n.id for n in self.nodes]

    @property
    def ratio_definitions(self) -> list[RatioDefinition]:
        """Deprecated read-only view of generic ratio definitions."""
        ratios: list[RatioDefinition] = []
        for definition in self.quantitative_definitions:
            if definition.kind != "ratio":
                continue
            ratios.append(RatioDefinition(
                ratio=definition.result,
                numerator=definition.arguments[0].node,
                denominator=definition.arguments[1].node,
                mechanism=definition.mechanism,
                evidence=definition.evidence,
            ))
        return ratios

    # --- networkx views -------------------------------------------------------

    @property
    def material_constitutive_edges(self) -> list[ConstitutiveEdge]:
        """Genuine **material** constitution: continuant part_of continuant (aggregation or
        structural ``part_of+determination`` between material entities)."""
        try:
            from physiomap_core.bfo import DeterminationRegime, determination_regime
        except Exception:  # pragma: no cover
            return list(self.constitutive_edges)
        nodes = {n.id: n for n in self.nodes}
        return [
            edge
            for edge in self.constitutive_edges
            if determination_regime(nodes[edge.micro], nodes[edge.macro])
            is DeterminationRegime.MATERIAL
        ]

    @property
    def process_constitutive_edges(self) -> list[ConstitutiveEdge]:
        """Temporal-mereological constitution between two occurrent bearers."""
        try:
            from physiomap_core.bfo import DeterminationRegime, determination_regime
        except Exception:  # pragma: no cover
            return []
        nodes = {n.id: n for n in self.nodes}
        return [
            edge
            for edge in self.constitutive_edges
            if determination_regime(nodes[edge.micro], nodes[edge.macro])
            is DeterminationRegime.PROCESS
        ]

    def causal_subgraph(self, contexts: Iterable[str] | None = None) -> nx.DiGraph:
        """The causal DiGraph plus explicitly tagged compatibility shadows.

        Authored causal influences are included directly. Typed production and quantitative
        records are exposed as ``production-derived`` and ``quantitative-derived`` shadows,
        respectively; constitutive edges are excluded. Parallel authored influences are never
        overwritten: in an explicit context slice only matching records are used. Without an
        explicit slice, context-only records are represented conservatively as ``?`` because
        their regime may be inactive; an unconditional influence remains determinate only when
        every contextual addition agrees with it.

        Nodes carry ``label``/``scale`` attributes; edges carry ``sign``/``mechanism``/
        ``evidence``. This is the graph all causal reasoning operates on.
        """
        g: nx.DiGraph = nx.DiGraph()
        for n in self.nodes:
            g.add_node(n.id, label=n.label, scale=n.scale.value)
        grouped: dict[tuple[str, str], list[CausalEdge]] = {}
        for edge in self.active_causal_edges(contexts):
            grouped.setdefault((edge.source, edge.target), []).append(edge)
        for (source, target), edges in grouped.items():
            sign = combine_parallel(edge.sign for edge in edges)
            context_ambiguous = False
            if contexts is None:
                contextual = [edge for edge in edges if edge.context]
                unconditional = [edge for edge in edges if edge.context is None]
                if contextual:
                    base_sign = combine_parallel(edge.sign for edge in unconditional)
                    if not unconditional or base_sign is Sign.UNKNOWN or any(
                        edge.sign is Sign.UNKNOWN or edge.sign is not base_sign
                        for edge in contextual
                    ):
                        sign = Sign.UNKNOWN
                        context_ambiguous = True
            mechanisms = list(dict.fromkeys(edge.mechanism for edge in edges if edge.mechanism))
            evidence = list(dict.fromkeys(edge.evidence for edge in edges if edge.evidence))
            evidence_classes = {
                edge.causal_evidence.value for edge in edges if edge.causal_evidence
            }
            records = [
                {
                    "id": edge.id,
                    "sign": edge.sign.value,
                    "context": edge.context.model_dump(mode="json") if edge.context else None,
                    "mechanism": edge.mechanism,
                    "evidence": edge.evidence,
                    "causal_evidence": (
                        edge.causal_evidence.value if edge.causal_evidence else None
                    ),
                }
                for edge in edges
            ]
            g.add_edge(
                source,
                target,
                sign=sign.value,
                mechanism=mechanisms[0] if len(mechanisms) == 1 else None,
                evidence=evidence[0] if len(evidence) == 1 else None,
                causal_evidence=(
                    next(iter(evidence_classes)) if len(evidence_classes) == 1 else None
                ),
                definitional=all(edge.definitional for edge in edges),
                edge_kind="causal-influence",
                influence_id=edges[0].id if len(edges) == 1 else None,
                influence_ids=[edge.id for edge in edges],
                contexts=[
                    edge.context.model_dump(mode="json")
                    for edge in edges
                    if edge.context
                ],
                parallel_influences=records,
                context_ambiguous=(
                    context_ambiguous or len({edge.sign for edge in edges}) > 1
                ),
            )
        for e in self.production_edges:
            if not g.has_edge(e.source, e.target):
                g.add_edge(
                    e.source,
                    e.target,
                    sign=e.sign.value,
                    mechanism=e.mechanism,
                    evidence=e.evidence,
                    causal_evidence=None,
                    production_evidence=e.production_evidence.value,
                    definitional=False,
                    edge_kind="production-derived",
                )
        for definition in self.quantitative_definitions:
            for argument in definition.arguments:
                if g.has_edge(argument.node, definition.result):
                    continue
                g.add_edge(
                    argument.node,
                    definition.result,
                    sign=argument.derivative_sign.value,
                    mechanism=definition.mechanism or (
                        f"{definition.kind} identity ({definition.result})"
                    ),
                    evidence=definition.evidence,
                    causal_evidence=None,
                    definitional=True,
                    edge_kind="quantitative-derived",
                    quantitative_kind=definition.kind,
                    quantitative_role=argument.role,
                )
        return g

    def sccs(self) -> list[set[str]]:
        """Strongly connected components of the causal subgraph."""
        return [set(c) for c in nx.strongly_connected_components(self.causal_subgraph())]

    def condensation(self) -> nx.DiGraph:
        """The SCC condensation (DAG of SCCs) of the causal subgraph.

        Delegates to ``networkx.condensation``; each condensation node has a ``members``
        attribute (the set of original node ids), and the graph is a DAG.
        """
        return nx.condensation(self.causal_subgraph())

    # --- (de)serialisation ----------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> "PhysioMap":
        return cls.model_validate(data)

    def to_dict(self) -> dict:
        return self.model_dump(mode="json", exclude_none=True)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PhysioMap":
        """Load a PhysioMap from a YAML file."""
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return cls.from_dict(data or {})

    @classmethod
    def merge(cls, maps: Iterable["PhysioMap"], name: str = "physiomap") -> "PhysioMap":
        """Compose several PhysioMap fragments into one.

        Nodes are unioned by ``id``; a node may be declared in at most one fragment
        (re-declaring the same id with a *different* definition raises). Causal and
        constitutive edges are unioned (exact duplicates collapsed). This lets the
        whole-body map be authored as modular per-system fragments that reference shared
        boundary nodes by id.
        """
        nodes: dict[str, Node] = {}
        for pm in maps:
            for n in pm.nodes:
                if n.id in nodes and nodes[n.id] != n:
                    raise ValueError(
                        f"conflicting definitions for node {n.id!r} across fragments"
                    )
                nodes[n.id] = n
        causal = {e.id: e for pm in maps for e in pm.causal_edges}
        production = {
            (e.source, e.target, e.sign): e for pm in maps for e in pm.production_edges
        }
        const = {
            (e.micro, e.macro, e.relation): e
            for pm in maps
            for e in pm.constitutive_edges
        }
        quantitative = {
            (definition.kind, definition.result,
             tuple((argument.node, argument.role) for argument in definition.arguments)): definition
            for pm in maps
            for definition in pm.quantitative_definitions
        }
        modulation = {
            (edge.modulator, edge.influence_id): edge
            for pm in maps
            for edge in pm.modulation_edges
        }
        return cls(
            name=name,
            nodes=list(nodes.values()),
            causal_edges=list(causal.values()),
            production_edges=list(production.values()),
            constitutive_edges=list(const.values()),
            modulation_edges=list(modulation.values()),
            quantitative_definitions=list(quantitative.values()),
        )

    @classmethod
    def load_composed(
        cls, paths: Iterable[str | Path], name: str = "physiomap"
    ) -> "PhysioMap":
        """Load several YAML fragments and compose them into one validated PhysioMap.

        Fragments are merged at the raw-dict level (so cross-fragment boundary references
        are allowed — a fragment may cite a node owned by another fragment); reference
        integrity is then checked once on the complete merged map. Nodes are unioned by
        ``id`` (a differing re-definition raises); edges are de-duplicated.
        """
        nodes: dict[str, dict] = {}
        causal: dict[tuple, dict] = {}
        production: dict[tuple, dict] = {}
        const: dict[tuple, dict] = {}
        modul: dict[tuple, dict] = {}
        quantitative: dict[tuple, dict] = {}
        for p in paths:
            with open(p, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            for nd in data.get("nodes", []) or []:
                nid = nd["id"]
                if nid in nodes and nodes[nid] != nd:
                    raise ValueError(
                        f"conflicting definitions for node {nid!r} across fragments"
                    )
                nodes[nid] = nd
            for e in data.get("causal_edges", []) or []:
                context = e.get("context")
                context_id = context.get("id") if isinstance(context, dict) else context
                key = e.get("id") or (
                    e["source"], e["target"], e["sign"], context_id
                )
                causal[key] = e
            for e in data.get("production_edges", []) or []:
                production[(e["source"], e["target"], e["sign"])] = e
            for e in data.get("constitutive_edges", []) or []:
                const[(e["micro"], e["macro"], e.get("relation", ""))] = e
            for e in data.get("modulation_edges", []) or []:
                target = e.get("influence_id") or (
                    e.get("edge_source"), e.get("edge_target")
                )
                modul[(e["modulator"], target)] = e
            definitions = list(data.get("quantitative_definitions", []) or [])
            definitions.extend(_ratio_as_quantitative(r)
                               for r in data.get("ratio_definitions", []) or [])
            for definition in definitions:
                key = (definition["kind"], definition["result"], tuple(
                    (argument["node"], argument.get("role", "argument"))
                    for argument in definition["arguments"]
                ))
                quantitative[key] = definition
        return cls.model_validate(
            {
                "name": name,
                "nodes": list(nodes.values()),
                "causal_edges": list(causal.values()),
                "production_edges": list(production.values()),
                "constitutive_edges": list(const.values()),
                "modulation_edges": list(modul.values()),
                "quantitative_definitions": list(quantitative.values()),
            }
        )

    def to_yaml(self, path: str | Path) -> None:
        """Write this PhysioMap to a YAML file."""
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self.to_dict(), fh, sort_keys=False, allow_unicode=True)
