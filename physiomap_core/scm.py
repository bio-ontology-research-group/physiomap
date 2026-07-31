"""Typed OWL-projected structural causal model manifest.

The YAML model remains the authoring format during migration.  This module is the
compatibility boundary: generated manifests carry ontology/projection metadata,
while :meth:`ScmManifest.to_physiomap` recreates the existing public model exactly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from physiomap_core.model import InfluenceContext, Node, PhysioMap


class ProjectionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trace_id: str
    output_id: str
    pattern_id: str
    pattern_version: str
    reasoning_mode: Literal["elk", "hermit-module", "asserted-only", "structural-validator"]
    reasoner: str
    entailment: str
    supporting_source_axioms: list[str]
    source_ontology_versions: dict[str, str] = Field(default_factory=dict)


class Influence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    source: str
    target: str
    sign: Literal["+", "-", "?"]
    mechanism: str | None = None
    evidence: str | None = None
    causal_evidence: str | None = None
    evidence_status: Literal["controlled", "legacy-evidence-unclassified"]
    context: InfluenceContext | None = None
    definitional: bool = False
    trace_ids: list[str]


class ConstitutiveConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    micro: str
    macro: str
    relation: str
    sign: Literal["+", "-", "?"]
    trace_ids: list[str]


class ProductionRelation(BaseModel):
    """Projected typed process-output / consumption relation (not an influence)."""

    model_config = ConfigDict(extra="forbid")
    id: str
    source: str
    target: str
    sign: Literal["+", "-", "?"]
    mechanism: str | None = None
    evidence: str | None = None
    production_evidence: Literal[
        "curated_source_statement",
        "experimental_perturbation",
        "mechanistic_model",
        "legacy-evidence-unclassified",
    ]
    evidence_status: Literal["controlled", "legacy-evidence-unclassified"]
    trace_ids: list[str]


class QuantitativeArgument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node: str
    role: str
    derivative_sign: Literal["+", "-", "?"]


class QuantitativeExpression(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: Literal["ratio", "sum", "product", "rate", "aggregation", "structural-function"]
    origin: Literal["authored", "derived"]
    result: str
    arguments: list[QuantitativeArgument]
    mechanism: str | None = None
    evidence: str | None = None
    trace_ids: list[str]

    @model_validator(mode="before")
    @classmethod
    def _upgrade_pre_origin_manifest(cls, data: Any) -> Any:
        if isinstance(data, dict) and "origin" not in data:
            upgraded = dict(data)
            # Before projection 1.2, ratios were authored while all other quantitative
            # expressions were inferred from causal/constitutive records.
            upgraded["origin"] = "authored" if data.get("kind") == "ratio" else "derived"
            return upgraded
        return data


class Modulation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    modulator: str
    influence_id: str
    sign: Literal["+", "-"]
    can_flip_sign: bool = False
    mechanism: str | None = None
    evidence: str | None = None
    causal_evidence: str | None = None
    trace_ids: list[str]


class ScmManifest(BaseModel):
    """Canonical generated representation of ``M=(V,E,H,F,tau)``."""

    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1.0.0"
    physiomap_version: str
    name: str
    description: str | None = None
    generator_version: str
    projection_version: str
    ontology_provenance: dict[str, Any]
    reasoning_configuration: dict[str, Any]
    nodes: list[Node]
    influences: list[Influence]
    production_relations: list[ProductionRelation] = Field(default_factory=list)
    constitutive_constraints: list[ConstitutiveConstraint]
    quantitative_expressions: list[QuantitativeExpression]
    modulation: list[Modulation]
    projection_traces: list[ProjectionTrace]

    @model_validator(mode="after")
    def _integrity(self) -> "ScmManifest":
        node_ids = [n.id for n in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("duplicate SCM node ids")
        known = set(node_ids)
        trace_ids = {t.trace_id for t in self.projection_traces}
        influence_ids = {e.id for e in self.influences}
        if len(influence_ids) != len(self.influences):
            raise ValueError("duplicate influence ids")
        for e in self.influences:
            if e.source not in known or e.target not in known:
                raise ValueError(f"unresolved influence reference {e.source}->{e.target}")
            if not set(e.trace_ids) <= trace_ids:
                raise ValueError(f"influence {e.id} has unresolved trace")
            expected_status = "controlled" if e.causal_evidence else "legacy-evidence-unclassified"
            if e.evidence_status != expected_status:
                raise ValueError(f"influence {e.id} has inconsistent evidence status")
        production_ids = {edge.id for edge in self.production_relations}
        if len(production_ids) != len(self.production_relations):
            raise ValueError("duplicate production relation ids")
        for edge in self.production_relations:
            if edge.source not in known or edge.target not in known:
                raise ValueError(
                    f"unresolved production reference {edge.source}->{edge.target}"
                )
            if not set(edge.trace_ids) <= trace_ids:
                raise ValueError(f"production relation {edge.id} has unresolved trace")
            expected_status = (
                "legacy-evidence-unclassified"
                if edge.production_evidence == "legacy-evidence-unclassified"
                else "controlled"
            )
            if edge.evidence_status != expected_status:
                raise ValueError(
                    f"production relation {edge.id} has inconsistent evidence status"
                )
        insulin_vldl = [e for e in self.influences
                        if (e.source, e.target) == ("plasma_insulin", "vldl_secretion")]
        if ({e.sign for e in insulin_vldl} == {"+", "-"}
                and (any(not e.context for e in insulin_vldl)
                     or len({e.context.id for e in insulin_vldl if e.context})
                     != len(insulin_vldl))):
            raise ValueError("insulin/VLDL opposing influences require distinct approved contexts")
        for h in self.modulation:
            if h.modulator not in known or h.influence_id not in influence_ids:
                raise ValueError(f"invalid modulation target in {h.id}")
            if not set(h.trace_ids) <= trace_ids:
                raise ValueError(f"modulation {h.id} has unresolved trace")
        for q in self.quantitative_expressions:
            if q.result not in known or not q.arguments or any(a.node not in known for a in q.arguments):
                raise ValueError(f"invalid quantitative expression {q.id}")
            if not set(q.trace_ids) <= trace_ids:
                raise ValueError(f"quantitative expression {q.id} has unresolved trace")
        quantitative_pairs = {
            (argument.node, q.result)
            for q in self.quantitative_expressions
            if q.origin == "authored"
            for argument in q.arguments
        }
        causal_pairs = {(edge.source, edge.target) for edge in self.influences}
        projection_tuple = tuple(int(part) for part in self.projection_version.split("."))
        if projection_tuple >= (1, 2, 0) and quantitative_pairs & causal_pairs:
            raise ValueError("authored quantitative arguments also occur as causal influences")
        return self

    def to_physiomap(self) -> PhysioMap:
        """Return the legacy model without leaking generated metadata into it."""
        edge_by_id = {e.id: e for e in self.influences}
        causal_pairs = {(edge.source, edge.target) for edge in self.influences}
        projection_tuple = tuple(int(part) for part in self.projection_version.split("."))
        legacy_production = [
            constraint
            for constraint in self.constitutive_constraints
            if constraint.relation == "production"
        ]
        return PhysioMap.model_validate({
            "name": self.name,
            "description": self.description,
            "nodes": self.nodes,
            "causal_edges": [{"id": e.id, "source": e.source, "target": e.target,
                               "sign": e.sign,
                               **({"context": e.context.model_dump(mode="json")}
                                  if e.context else {}),
                               **({"mechanism": e.mechanism} if e.mechanism else {}),
                               **({"evidence": e.evidence} if e.evidence else {}),
                               **({"causal_evidence": e.causal_evidence}
                                  if e.causal_evidence else {}),
                               "definitional": e.definitional}
                             for e in self.influences],
            "production_edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "sign": edge.sign,
                    "production_evidence": edge.production_evidence,
                    **({"mechanism": edge.mechanism} if edge.mechanism else {}),
                    **({"evidence": edge.evidence} if edge.evidence else {}),
                }
                for edge in self.production_relations
            ] + [
                {
                    "source": edge.micro,
                    "target": edge.macro,
                    "sign": edge.sign,
                    "production_evidence": "legacy-evidence-unclassified",
                }
                for edge in legacy_production
            ],
            "constitutive_edges": [
                c.model_dump(exclude={"id", "trace_ids"})
                for c in self.constitutive_constraints
                if c.relation != "production"
            ],
            "modulation_edges": [
                {
                    "modulator": h.modulator,
                    "influence_id": h.influence_id,
                    "edge_source": edge_by_id[h.influence_id].source,
                    "edge_target": edge_by_id[h.influence_id].target,
                    "sign": h.sign,
                    "can_flip_sign": h.can_flip_sign,
                    **({"mechanism": h.mechanism} if h.mechanism else {}),
                    **({"evidence": h.evidence} if h.evidence else {}),
                    **({"causal_evidence": h.causal_evidence} if h.causal_evidence else {}),
                } for h in self.modulation
            ],
            "quantitative_definitions": [
                {
                    "kind": q.kind,
                    "result": q.result,
                    "arguments": [argument.model_dump(mode="json") for argument in q.arguments],
                    **({"mechanism": q.mechanism} if q.mechanism else {}),
                    **({"evidence": q.evidence} if q.evidence else {}),
                } for q in self.quantitative_expressions
                if q.origin == "authored" and (
                    projection_tuple >= (1, 2, 0)
                    or not any((argument.node, q.result) in causal_pairs for argument in q.arguments)
                )
            ],
        })

    @classmethod
    def from_json(cls, path: str | Path) -> "ScmManifest":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def write_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.model_dump(mode="json", exclude_none=True),
                                         indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_scm(path: str | Path) -> PhysioMap:
    """Compatibility loader for callers that only need the legacy ``PhysioMap`` API."""
    return ScmManifest.from_json(path).to_physiomap()


def canonical_scm_path() -> Path:
    """Return the approved canonical release SCM, with an explicit deployment override."""
    configured = os.environ.get("PHYSIOMAP_SCM_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent.parent / "release/owl-scm/physiomap-scm.json"


def load_canonical_scm() -> ScmManifest:
    """Load the complete typed canonical SCM without discarding projected information."""
    path = canonical_scm_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"canonical PhysioMap SCM is missing at {path}; run the OWL/SCM release build")
    return ScmManifest.from_json(path)


def load_canonical_physiomap() -> PhysioMap:
    """Load the canonical SCM through the legacy solver-shaped ``PhysioMap`` adapter."""
    return load_canonical_scm().to_physiomap()
