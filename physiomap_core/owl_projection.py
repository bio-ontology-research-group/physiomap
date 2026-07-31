"""Deterministic YAML -> OWL TBox -> SCM projection pipeline."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

import yaml

from physiomap_core import __version__
from physiomap_core.model import PhysioMap, QuantitativeDefinition
from physiomap_core.scm import (ConstitutiveConstraint, Influence, Modulation,
                                ProductionRelation, ProjectionTrace, QuantitativeArgument,
                                QuantitativeExpression, ScmManifest)

BASE = "https://w3id.org/physiomap/"
GENERATOR_VERSION = "1.1.0"
CURIE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(.*)$")
PROJECTION_RECORD_PROPERTY = "scmProjectionRecord"


def _stable(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("\x1f".join(str(x) for x in parts).encode()).hexdigest()[:20]
    return f"{prefix}-{digest}"


def _iri(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return f"<{value}>"
    match = CURIE.match(value)
    if match:
        return f"<http://purl.obolibrary.org/obo/{match[1]}_{match[2]}>"
    return f"<{BASE}{quote(value, safe='_-')}>"


def _trait(node_id: str) -> str:
    # A slash is not legal in a Functional Syntax prefixed local name.
    return f"<{BASE}trait/{quote(node_id, safe='_-')}>"


def _collection(node_id: str) -> str:
    """IRI of the timeless collection of all instances of a trait.

    The collection is named by an opaque digest and linked to its trait by the
    `pm:collectionFor` annotation: like every other PhysioMap IRI it carries no semantics.
    """
    return f"<{BASE}collection/{_stable('collection', node_id)}>"


def _general_quality(entity_iri: str, quality_iri: str) -> str:
    digest = hashlib.sha256(f"{entity_iri}\x1f{quality_iri}".encode()).hexdigest()[:20]
    return f"<{BASE}quality/{digest}>"


def _literal(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _encode_projection_record(record: dict[str, Any]) -> str:
    raw = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_projection_record(value: str) -> dict[str, Any]:
    padded = value + "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded).decode()
        record = json.loads(decoded)
    except Exception as exc:  # noqa: BLE001 - malformed canonical OWL must fail closed
        raise ValueError("invalid embedded SCM projection record") from exc
    if not isinstance(record, dict) or not isinstance(record.get("record_type"), str):
        raise ValueError("embedded SCM projection record lacks record_type")
    return record


def _manifest_projection_records(manifest: ScmManifest) -> list[dict[str, Any]]:
    dumped = manifest.model_dump(mode="json", exclude_none=True)
    collection_fields = {
        "nodes": "node",
        "influences": "influence",
        "production_relations": "production_relation",
        "constitutive_constraints": "constitutive_constraint",
        "quantitative_expressions": "quantitative_expression",
        "modulation": "modulation",
        "projection_traces": "projection_trace",
    }
    metadata = {key: value for key, value in dumped.items() if key not in collection_fields}
    records = [{"record_type": "manifest_metadata", "value": metadata}]
    for field, record_type in collection_fields.items():
        records.extend({"record_type": record_type, "value": value}
                       for value in dumped[field])
    for sequence, record in enumerate(records):
        record["sequence"] = sequence
    return records


def _embed_projection_records(owl: str, manifest: ScmManifest) -> str:
    """Attach every canonical SCM record to the OWL artifact as lossless annotations."""
    lines = owl.rstrip().splitlines()
    if not lines or lines[-1] != ")":
        raise ValueError("cannot embed projection records in malformed Functional Syntax OWL")
    records = _manifest_projection_records(manifest)
    encoded = sorted(_encode_projection_record(record) for record in records)
    additions = [f"Declaration(AnnotationProperty(pm:{PROJECTION_RECORD_PROPERTY}))"]
    for index, payload in enumerate(encoded):
        subject = f"<{BASE}projection-record/{index:05d}>"
        additions.append(
            f"AnnotationAssertion(pm:{PROJECTION_RECORD_PROPERTY} {subject} \"{payload}\")"
        )
    return "\n".join(lines[:-1] + additions + [")"]) + "\n"


def _quantitative_property(kind: str, role: str) -> str:
    if kind == "ratio":
        return "hasNumerator" if role == "numerator" else "hasDenominator"
    if kind == "rate":
        return "hasRateNumerator" if role == "numerator" else "hasRateDenominator"
    if kind == "product":
        return "hasFactor"
    if kind in {"sum", "aggregation"}:
        return "hasSummand"
    return "hasArgument"


def _quantitative_source_axioms(definition: QuantitativeDefinition) -> list[str]:
    return [
        f"{_trait(definition.result)} SubClassOf pm:{_quantitative_property(definition.kind, argument.role)} "
        f"some {_trait(argument.node)}"
        for argument in definition.arguments
    ]


def _quantitative_owl_axioms(definition: QuantitativeDefinition) -> list[str]:
    return [
        f"SubClassOf({_trait(definition.result)} ObjectSomeValuesFrom("
        f"pm:{_quantitative_property(definition.kind, argument.role)} {_trait(argument.node)}))"
        for argument in definition.arguments
    ]


def _quantitative_entailment(definition: QuantitativeDefinition) -> str:
    arguments = ", ".join(argument.node for argument in definition.arguments)
    operator = {
        "ratio": "ratio",
        "rate": "rate",
        "product": "product",
        "sum": "sum",
        "aggregation": "sum",
        "structural-function": "F",
    }[definition.kind]
    return f"{definition.result} = {operator}({arguments})"


@dataclass(frozen=True)
class RegistryTerm:
    identifier: str
    label: str
    synonyms: tuple[str, ...]
    parents: tuple[str, ...]
    obsolete: bool
    replaced_by: str | None
    source: str


def parse_obo(path: Path, wanted: set[str] | None = None) -> dict[str, RegistryTerm]:
    """Parse source term metadata, without loading source ABox assertions."""
    found: dict[str, RegistryTerm] = {}
    stanza: dict[str, list[str]] = {}

    def flush() -> None:
        identifier = (stanza.get("id") or [None])[0]
        if not identifier or (wanted is not None and identifier not in wanted):
            return
        found[identifier] = RegistryTerm(
            identifier=identifier,
            label=(stanza.get("name") or [""])[0],
            synonyms=tuple(v.split('"')[1] for v in stanza.get("synonym", []) if '"' in v),
            parents=tuple(v.split()[0] for v in stanza.get("is_a", [])),
            obsolete=(stanza.get("is_obsolete") or ["false"])[0].lower() == "true",
            replaced_by=(stanza.get("replaced_by") or [None])[0],
            source=path.name,
        )

    with path.open(encoding="utf-8", errors="replace") as handle:
        in_term = False
        for raw in handle:
            line = raw.rstrip("\n")
            if line == "[Term]":
                if in_term:
                    flush()
                stanza, in_term = {}, True
            elif line.startswith("["):
                if in_term:
                    flush()
                stanza, in_term = {}, False
            elif in_term and ": " in line:
                key, value = line.split(": ", 1)
                stanza.setdefault(key, []).append(value)
        if in_term:
            flush()
    return found


def source_registry(cache_dir: Path, identifiers: set[str], registry_cache: Path | None = None
                    ) -> tuple[dict[str, RegistryTerm], dict[str, str], str]:
    by_prefix: dict[str, set[str]] = {}
    for identifier in identifiers:
        if CURIE.match(identifier):
            by_prefix.setdefault(identifier.split(":", 1)[0].upper(), set()).add(identifier)
    registry: dict[str, RegistryTerm] = {}
    checksums: dict[str, str] = {}
    for prefix, wanted in sorted(by_prefix.items()):
        source = cache_dir / f"{prefix}.obo"
        if not source.exists():
            continue
        checksums[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
    if registry_cache and registry_cache.is_file():
        payload = json.loads(registry_cache.read_text(encoding="utf-8"))
        requested = set(payload.get("requested_identifiers", []))
        frozen_checksums = payload.get("checksums", {})
        expected_sources = {f"{prefix}.obo" for prefix in by_prefix}
        sources_absent = not checksums and expected_sources <= set(frozen_checksums)
        sources_match = frozen_checksums == checksums
        if (sources_absent or sources_match) and identifiers <= requested:
            cached = {key: RegistryTerm(**value) for key, value in payload.get("terms", {}).items()}
            return ({key: value for key, value in cached.items() if key in identifiers},
                    frozen_checksums, "checksum-bound-cache")
    for prefix, wanted in sorted(by_prefix.items()):
        source = cache_dir / f"{prefix}.obo"
        if not source.exists():
            continue
        registry.update(parse_obo(source, wanted))
    return registry, checksums, "parsed-source"


def write_source_registry_cache(path: Path, identifiers: set[str],
                                registry: dict[str, RegistryTerm],
                                checksums: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "1.0.0", "checksums": dict(sorted(checksums.items())),
               "requested_identifiers": sorted(identifiers),
               "terms": {key: asdict(value) for key, value in sorted(registry.items())},
               "missing": sorted(identifiers - set(registry))}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class MigrationBuilder:
    def __init__(self, patterns_path: Path, cache_dir: Path | None = None):
        self.patterns_path = patterns_path
        self.patterns = yaml.safe_load(patterns_path.read_text(encoding="utf-8"))
        if not isinstance(self.patterns, dict) or not isinstance(self.patterns.get("patterns"), list):
            raise ValueError("projection registry must contain a patterns list")
        required = {"id", "arity", "owl_template", "direction", "reasoning_mode",
                    "output_kind", "quantitative_semantics", "evidence_requirements",
                    "trace_policy"}
        allowed_modes = {"elk", "hermit-module", "asserted-only", "structural-validator"}
        ids: set[str] = set()
        for pattern in self.patterns["patterns"]:
            missing = required - set(pattern)
            if missing:
                raise ValueError(f"projection pattern is missing fields: {sorted(missing)}")
            if pattern["id"] in ids:
                raise ValueError(f"duplicate projection pattern id {pattern['id']!r}")
            if pattern["reasoning_mode"] not in allowed_modes:
                raise ValueError(f"unsupported reasoning mode {pattern['reasoning_mode']!r}")
            ids.add(pattern["id"])
        expected = {"causal-collection-v2", "production-collection-v2", "constitution-v1",
                    "ratio-v1", "multiplicative-modulation-v2", "aggregation-expression-v1",
                    "structural-function-v1", "product-expression-v1",
                    "sum-expression-v1", "rate-expression-v1"}
        if not expected <= ids:
            raise ValueError(f"projection registry lacks required patterns: {sorted(expected - ids)}")
        self.pattern_version = str(self.patterns["version"])
        self.pattern_by_id = {pattern["id"]: pattern for pattern in self.patterns["patterns"]}
        self.cache_dir = cache_dir
        self.registry_cache = (cache_dir.parent / "registry/used-terms.json") if cache_dir else None

    def build(self, pmap: PhysioMap, source_files: Iterable[str] = ()) -> tuple[str, ScmManifest, dict[str, Any]]:
        legacy_definitional = [
            f"{edge.source}->{edge.target}" for edge in pmap.causal_edges if edge.definitional
        ]
        if legacy_definitional:
            raise ValueError(
                "definitional causal edges are unsupported by projection 1.2; use "
                "quantitative_definitions: " + ", ".join(sorted(legacy_definitional))
            )
        nodes = list(pmap.nodes)
        external = {x for n in nodes for x in (n.entity_iri, n.quality_iri, n.bearer_entity_iri) if x}
        if self.cache_dir:
            registry, checksums, registry_mode = source_registry(
                self.cache_dir, external, self.registry_cache)
        else:
            registry, checksums, registry_mode = {}, {}, "disabled"
        missing = sorted(x for x in external if CURIE.match(x) and x not in registry)
        obsolete = sorted(x for x in external if x in registry and registry[x].obsolete)
        if obsolete:
            raise ValueError(f"obsolete external ontology terms: {obsolete}")

        owl, dl_owl, trait_records, groupings = self._render_owl(pmap, registry, checksums)
        # The DL artifact carries the same content plus the axioms outside OWL 2 EL; it is written
        # by `write_artifacts` and is never the input to the ELK release gate.
        self.dl_owl = dl_owl
        self.groupings = groupings
        traces: list[ProjectionTrace] = []
        influences: list[Influence] = []
        influence_by_id: dict[str, Influence] = {}
        versions = {name: digest for name, digest in sorted(checksums.items())}

        for edge in pmap.causal_edges:
            context = edge.context
            iid = edge.id
            assert iid is not None
            entailment = (f"{_collection(edge.target)} SubClassOf pm:hasMember some "
                          f"(pm:causedBy some {_trait(edge.source)})")
            tid = _stable("trace", iid, entailment)
            traces.append(ProjectionTrace(trace_id=tid, output_id=iid,
                pattern_id="causal-collection-v2", pattern_version=self.pattern_version,
                reasoning_mode="elk", reasoner="ELK (release gate)", entailment=entailment,
                supporting_source_axioms=[entailment], source_ontology_versions=versions))
            item = Influence(id=iid, source=edge.source, target=edge.target, sign=edge.sign.value,
                mechanism=edge.mechanism, evidence=edge.evidence,
                causal_evidence=edge.causal_evidence.value if edge.causal_evidence else None,
                evidence_status=("controlled" if edge.causal_evidence else
                                 "legacy-evidence-unclassified"),
                context=context,
                definitional=edge.definitional, trace_ids=[tid])
            influences.append(item)
            influence_by_id[item.id] = item

        production: list[ProductionRelation] = []
        for edge in pmap.production_edges:
            pid = _stable(
                "production", self.pattern_version, edge.source, edge.target, edge.sign.value
            )
            entailment = (
                f"{_collection(edge.target)} SubClassOf pm:hasMember some "
                f"(pm:producedBy some {_trait(edge.source)})"
            )
            tid = _stable("trace", pid, entailment)
            traces.append(ProjectionTrace(
                trace_id=tid,
                output_id=pid,
                pattern_id="production-collection-v2",
                pattern_version=self.pattern_version,
                reasoning_mode="elk",
                reasoner="ELK (release gate)",
                entailment=entailment,
                supporting_source_axioms=[entailment],
                source_ontology_versions=versions,
            ))
            production.append(ProductionRelation(
                id=pid,
                source=edge.source,
                target=edge.target,
                sign=edge.sign.value,
                mechanism=edge.mechanism,
                evidence=edge.evidence,
                production_evidence=edge.production_evidence.value,
                evidence_status=(
                    "legacy-evidence-unclassified"
                    if edge.production_evidence.value == "legacy-evidence-unclassified"
                    else "controlled"
                ),
                trace_ids=[tid],
            ))

        quantities: list[QuantitativeExpression] = []

        constraints: list[ConstitutiveConstraint] = []
        constraint_trace: dict[tuple[str, str, str], str] = {}
        for edge in pmap.constitutive_edges:
            cid = _stable("constraint", self.pattern_version, edge.micro, edge.macro, edge.relation)
            entailment = f"{_trait(edge.macro)} SubClassOf pm:constitutedBy some {_trait(edge.micro)}"
            tid = _stable("trace", cid, entailment)
            traces.append(ProjectionTrace(trace_id=tid, output_id=cid, pattern_id="constitution-v1",
                pattern_version=self.pattern_version, reasoning_mode="elk", reasoner="ELK (release gate)",
                entailment=entailment, supporting_source_axioms=[entailment], source_ontology_versions=versions))
            constraints.append(ConstitutiveConstraint(id=cid, micro=edge.micro, macro=edge.macro,
                relation=edge.relation, sign=edge.sign.value, trace_ids=[tid]))
            constraint_trace[(edge.micro, edge.macro, edge.relation)] = tid

        for macro in sorted({edge.macro for edge in pmap.constitutive_edges
                             if edge.relation == "aggregation"}):
            parts = [edge for edge in pmap.constitutive_edges
                     if edge.macro == macro and edge.relation == "aggregation"]
            qid = _stable("expression", self.pattern_version, "aggregation", macro,
                          *(edge.micro for edge in parts))
            support_ids = [constraint_trace[(edge.micro, edge.macro, edge.relation)] for edge in parts]
            support = [trace.entailment for trace in traces if trace.trace_id in set(support_ids)]
            tid = _stable("trace", qid, *support)
            traces.append(ProjectionTrace(trace_id=tid, output_id=qid,
                pattern_id="aggregation-expression-v1", pattern_version=self.pattern_version,
                reasoning_mode="structural-validator", reasoner="PhysioMap quantity validator",
                entailment=f"{macro} = sum({', '.join(edge.micro for edge in parts)})",
                supporting_source_axioms=support, source_ontology_versions=versions))
            quantities.append(QuantitativeExpression(id=qid, kind="aggregation", result=macro,
                origin="derived",
                arguments=[QuantitativeArgument(node=edge.micro, role="summand",
                                                derivative_sign="+") for edge in parts],
                trace_ids=[tid]))

        pattern_by_kind = {
            "ratio": "ratio-v1",
            "rate": "rate-expression-v1",
            "product": "product-expression-v1",
            "sum": "sum-expression-v1",
            "aggregation": "aggregation-expression-v1",
            "structural-function": "structural-function-v1",
        }
        for definition in pmap.quantitative_definitions:
            qid = _stable(
                "expression", self.pattern_version, definition.kind, definition.result,
                *((argument.node, argument.role, argument.derivative_sign.value)
                  for argument in definition.arguments),
            )
            support = _quantitative_source_axioms(definition)
            entailment = _quantitative_entailment(definition)
            tid = _stable("trace", qid, entailment, *support)
            pattern_id = pattern_by_kind[definition.kind]
            reasoning_mode = self.pattern_by_id[pattern_id]["reasoning_mode"]
            traces.append(ProjectionTrace(
                trace_id=tid,
                output_id=qid,
                pattern_id=pattern_id,
                pattern_version=self.pattern_version,
                reasoning_mode=reasoning_mode,
                reasoner=("ELK (release gate)" if reasoning_mode == "elk"
                          else "PhysioMap structural validator"),
                entailment=entailment,
                supporting_source_axioms=support,
                source_ontology_versions=versions,
            ))
            quantities.append(QuantitativeExpression(
                id=qid,
                kind=definition.kind,
                origin="authored",
                result=definition.result,
                arguments=[QuantitativeArgument(
                    node=argument.node,
                    role=argument.role,
                    derivative_sign=argument.derivative_sign.value,
                ) for argument in definition.arguments],
                mechanism=definition.mechanism,
                evidence=definition.evidence,
                trace_ids=[tid],
            ))

        modulations: list[Modulation] = []
        for mod in pmap.modulation_edges:
            assert mod.influence_id is not None
            assert mod.edge_source is not None and mod.edge_target is not None
            target = influence_by_id[mod.influence_id]
            mid = _stable("modulation", self.pattern_version, mod.modulator, target.id)
            entailment = (f"{_collection(mod.modulator)} SubClassOf pm:hasMember some "
                          f"(pm:modulates some ({_trait(mod.edge_target)} and pm:causedBy some "
                          f"{_trait(mod.edge_source)}))")
            tid = _stable("trace", mid, entailment)
            traces.append(ProjectionTrace(trace_id=tid, output_id=mid,
                pattern_id="multiplicative-modulation-v2", pattern_version=self.pattern_version,
                reasoning_mode="elk", reasoner="ELK (release gate)", entailment=entailment,
                supporting_source_axioms=[entailment], source_ontology_versions=versions))
            modulations.append(Modulation(id=mid, modulator=mod.modulator, influence_id=target.id,
                sign=mod.sign.value, can_flip_sign=mod.can_flip_sign, mechanism=mod.mechanism,
                evidence=mod.evidence,
                causal_evidence=mod.causal_evidence.value if mod.causal_evidence else None,
                trace_ids=[tid]))

        manifest = ScmManifest(
            physiomap_version=__version__, name=pmap.name, description=pmap.description,
            generator_version=GENERATOR_VERSION, projection_version=self.pattern_version,
            ontology_provenance={"checksums": checksums, "source_files": sorted(source_files),
                                 "primary_kb": "physiomap.owl", "el_artifact": "physiomap-el.owl",
                                 "authority_status": "canonical",
                                 "migration_report_approval": "approved-2026-07-11"},
            reasoning_configuration={"el": "ELK after OWL 2 EL profile check",
                "non_el": "HermiT only for registered bounded locality modules",
                "unsupported_axiom_policy": "fail"},
            nodes=[n.model_dump(mode="json", exclude_none=True) for n in pmap.nodes],
            influences=influences, production_relations=production,
            constitutive_constraints=constraints,
            quantitative_expressions=quantities, modulation=modulations,
            projection_traces=sorted(traces, key=lambda t: t.trace_id))
        report = {"schema_version": "1.0.0", "projection_version": self.pattern_version,
                  "summary": {"traits": len(nodes), "complete_traits": sum(bool(n.entity_iri and n.quality_iri) for n in nodes),
                              "incomplete_traits": sum(not bool(n.entity_iri and n.quality_iri) for n in nodes),
                              "influences": len(influences),
                              "production_relations": len(production),
                              "modulations": len(modulations)},
                  "source_registry": {"mode": registry_mode, "checksums": checksums,
                                      "missing": missing, "obsolete": obsolete,
                                      "replaced": {key: term.replaced_by for key, term in registry.items()
                                                   if term.replaced_by},
                                      "label_mismatches": []},
                  "traits": trait_records, "groupings": groupings}
        pair_signs: dict[tuple[str, str], set[str]] = {}
        for edge in pmap.causal_edges:
            pair_signs.setdefault((edge.source, edge.target), set()).add(edge.sign.value)
        report["causal_policy"] = {
            "total_influences": len(pmap.causal_edges),
            "interventional_class_present": sum(edge.causal_evidence is not None
                                                 for edge in pmap.causal_edges),
            "legacy_without_class": sum(edge.causal_evidence is None for edge in pmap.causal_edges),
            "without_evidence_text": sum(not edge.evidence for edge in pmap.causal_edges),
            "modulations_with_interaction_class": sum(edge.causal_evidence is not None
                                                       for edge in pmap.modulation_edges),
            "modulations_total": len(pmap.modulation_edges),
            "production_relations": len(pmap.production_edges),
            "production_controlled": sum(
                edge.production_evidence.value != "legacy-evidence-unclassified"
                for edge in pmap.production_edges
            ),
            "production_legacy_unclassified": sum(
                edge.production_evidence.value == "legacy-evidence-unclassified"
                for edge in pmap.production_edges
            ),
            "opposing_sign_pairs": [
                {"source": pair[0], "target": pair[1], "signs": sorted(signs)}
                for pair, signs in sorted(pair_signs.items()) if len(signs) > 1
            ],
            "legacy_policy": "evidence-bearing legacy edges remain operational with explicit unclassified status",
            "approved_policy": "legacy evidence is explicitly marked, not bulk reclassified",
            "approval_status": "approved",
            "canonical_source_flip": "approved",
            "opposing_sign_policy": "preserve influences with explicit mechanism contexts",
        }
        owl = _embed_projection_records(owl, manifest)
        projected = self.project_owl(owl)
        if projected != manifest:
            raise ValueError("OWL projection records do not reconstruct the generated SCM exactly")
        return owl, projected, report

    def project_owl(self, source: str | Path) -> ScmManifest:
        """Reconstruct the complete canonical SCM from OWL plus this projection registry.

        The annotations are lossless records attached to the canonical TBox. They are accepted
        only when their pattern versions/modes match the registry and every record has its
        corresponding OWL semantic witness. No YAML or pre-existing SCM is consulted.
        """
        owl = source.read_text(encoding="utf-8") if isinstance(source, Path) else source
        prop = re.escape(f"{BASE}{PROJECTION_RECORD_PROPERTY}")
        pattern = re.compile(
            rf'AnnotationAssertion\((?:pm:{PROJECTION_RECORD_PROPERTY}|<{prop}>)\s+'
            rf'<[^>]+>\s+"([A-Za-z0-9_-]+)"\)'
        )
        encoded = pattern.findall(owl)
        if not encoded:
            raise ValueError("OWL contains no embedded SCM projection records")
        if len(encoded) != len(set(encoded)):
            raise ValueError("OWL contains duplicate SCM projection records")
        records = sorted(
            (_decode_projection_record(value) for value in encoded),
            key=lambda record: record.get("sequence", -1),
        )
        if [record.get("sequence") for record in records] != list(range(len(records))):
            raise ValueError("embedded SCM projection record sequence is incomplete")
        metadata = [record["value"] for record in records
                    if record["record_type"] == "manifest_metadata"]
        if len(metadata) != 1 or not isinstance(metadata[0], dict):
            raise ValueError("OWL must contain exactly one SCM manifest metadata record")
        fields = {
            "node": "nodes",
            "influence": "influences",
            "production_relation": "production_relations",
            "constitutive_constraint": "constitutive_constraints",
            "quantitative_expression": "quantitative_expressions",
            "modulation": "modulation",
            "projection_trace": "projection_traces",
        }
        unknown = sorted({record["record_type"] for record in records}
                         - {"manifest_metadata", *fields})
        if unknown:
            raise ValueError(f"unsupported embedded SCM record types: {unknown}")
        payload = dict(metadata[0])
        for field in fields.values():
            payload[field] = []
        for record in records:
            field = fields.get(record["record_type"])
            if field:
                if not isinstance(record.get("value"), dict):
                    raise ValueError(f"embedded {record['record_type']} value must be an object")
                payload[field].append(record["value"])
        manifest = ScmManifest.model_validate(payload)
        if manifest.projection_version != self.pattern_version:
            raise ValueError(
                "OWL projection version does not match projection registry: "
                f"{manifest.projection_version} != {self.pattern_version}"
            )
        for trace in manifest.projection_traces:
            registered = self.pattern_by_id.get(trace.pattern_id)
            if registered is None:
                raise ValueError(f"projection trace uses unregistered pattern {trace.pattern_id!r}")
            if trace.pattern_version != self.pattern_version:
                raise ValueError(f"projection trace {trace.trace_id} has a stale pattern version")
            if trace.reasoning_mode != registered["reasoning_mode"]:
                raise ValueError(f"projection trace {trace.trace_id} has wrong reasoning mode")
        self._verify_owl_witnesses(owl, manifest)
        return manifest

    @staticmethod
    def _verify_owl_witnesses(owl: str, manifest: ScmManifest) -> None:
        """Fail closed if an embedded record is detached from its asserted OWL pattern."""
        def normalize(value: str) -> str:
            return re.sub(
                rf"<{re.escape(BASE)}([^>]*)>", lambda match: f"pm:{match.group(1)}", value
            )

        normalized_owl = normalize(owl)

        def trait(node_id: str) -> str:
            return normalize(_trait(node_id))

        # Each trait's collection, keyed by the collection IRI, so a collection-scoped mechanism
        # axiom can be read back as a relation between the underlying traits.
        collection_trait = dict(re.findall(
            r"SubClassOf\((pm:collection/[^\s()]+)\s+"
            r"ObjectSomeValuesFrom\(pm:hasMember\s+(pm:trait/[^\s()]+)\)\)",
            normalized_owl,
        ))

        def binary_witnesses(prop: str) -> set[tuple[str, str]]:
            # Return (source, target) pairs. This indexed scan keeps full-corpus OWL-only
            # projection linear rather than rescanning a large ontology for every relation.
            matches = re.findall(
                rf"(pm:trait/[^\s()]+)\s+ObjectSomeValuesFrom\(pm:{prop}\s+"
                rf"(pm:trait/[^\s()]+)\)",
                normalized_owl,
            )
            return {(source, target) for target, source in matches}

        def collection_witnesses(prop: str) -> set[tuple[str, str]]:
            """(source, target) pairs asserted of the target trait's collection."""
            matches = re.findall(
                rf"(pm:collection/[^\s()]+)\s+ObjectSomeValuesFrom\(pm:hasMember\s+"
                rf"ObjectSomeValuesFrom\(pm:{prop}\s+(pm:trait/[^\s()]+)\)\)",
                normalized_owl,
            )
            return {(source, collection_trait[collection])
                    for collection, source in matches if collection in collection_trait}

        node_ids = set(re.findall(
            r'AnnotationAssertion\(pm:nodeId\s+pm:trait/[^\s()]+\s+"([^"]+)"\)',
            normalized_owl,
        ))
        influence_ids = set(re.findall(
            r'Annotation\(pm:influenceId\s+"([^"]+)"\)', normalized_owl
        ))
        context_ids = set(re.findall(
            r'Annotation\(pm:contextId\s+"([^"]+)"\)', normalized_owl
        ))
        causal = collection_witnesses("causedBy")
        production = collection_witnesses("producedBy")
        # Constitution is a genuine universal -- a whole's extensive trait is constituted by its
        # parts' traits in every instance -- so it stays a plain subclass axiom on the trait.
        constitution = binary_witnesses("constitutedBy")
        quantitative = {
            prop: binary_witnesses(prop)
            for prop in (
                "hasNumerator", "hasDenominator", "hasRateNumerator",
                "hasRateDenominator", "hasFactor", "hasSummand", "hasArgument",
            )
        }
        modulation_witnesses = {
            (collection_trait[collection], target, source)
            for collection, target, source in re.findall(
                r"(pm:collection/[^\s()]+)\s+ObjectSomeValuesFrom\(pm:hasMember\s+"
                r"ObjectSomeValuesFrom\(pm:modulates\s+"
                r"ObjectIntersectionOf\((pm:trait/[^\s()]+)\s+"
                r"ObjectSomeValuesFrom\(pm:causedBy\s+(pm:trait/[^\s()]+)\)\)\)\)",
                normalized_owl,
            )
            if collection in collection_trait
        }

        for node in manifest.nodes:
            node_id = node.id
            if node_id not in node_ids:
                raise ValueError(f"node projection record {node_id!r} lacks an OWL witness")
        for edge in manifest.influences:
            if ((trait(edge.source), trait(edge.target)) not in causal
                    or edge.id not in influence_ids):
                raise ValueError(f"influence {edge.id!r} lacks its OWL witness")
            if edge.context and edge.context.id not in context_ids:
                raise ValueError(f"influence {edge.id!r} lacks its OWL context witness")
        for edge in manifest.production_relations:
            if (trait(edge.source), trait(edge.target)) not in production:
                raise ValueError(f"production relation {edge.id!r} lacks its OWL witness")
        for edge in manifest.constitutive_constraints:
            if (trait(edge.micro), trait(edge.macro)) not in constitution:
                raise ValueError(f"constitutive constraint {edge.id!r} lacks its OWL witness")
        for expression in manifest.quantitative_expressions:
            if expression.origin != "authored":
                continue
            for argument in expression.arguments:
                prop = _quantitative_property(expression.kind, argument.role)
                if (trait(argument.node), trait(expression.result)) not in quantitative[prop]:
                    raise ValueError(
                        f"quantitative expression {expression.id!r} lacks an OWL witness"
                    )
        influences = {edge.id: edge for edge in manifest.influences}
        for modulation in manifest.modulation:
            target = influences[modulation.influence_id]
            witness = (trait(modulation.modulator), trait(target.target), trait(target.source))
            if witness not in modulation_witnesses:
                raise ValueError(f"modulation {modulation.id!r} lacks its OWL witness")

    def _render_owl(self, pmap: PhysioMap, registry: dict[str, RegistryTerm],
                    checksums: dict[str, str]) -> tuple[str, list[dict[str, Any]]]:
        lines = ["Prefix(owl:=<http://www.w3.org/2002/07/owl#>)",
                 "Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)",
                 f"Prefix(pm:=<{BASE}>)", f"Ontology(<{BASE}kb/{__version__}>",
                 "Declaration(Class(pm:Trait))", "Declaration(Class(pm:MapVariable))",
                 "Declaration(Class(pm:TraitCollection))",
                 "Declaration(Class(pm:Quality))",
                 "Declaration(Class(pm:ProcessQuality))",
                 "Declaration(Class(pm:ContinuantQuality))",
                 "Declaration(Class(pm:Continuant))", "Declaration(Class(pm:Process))",
                 "Declaration(Class(pm:ContinuantTrait))", "Declaration(Class(pm:ProcessTrait))",
                 "SubClassOf(pm:ContinuantTrait pm:Trait)", "SubClassOf(pm:ProcessTrait pm:Trait)",
                 "SubClassOf(pm:MapVariable pm:Trait)",
                 "SubClassOf(pm:ProcessQuality pm:Quality)",
                 "SubClassOf(pm:ContinuantQuality pm:Quality)",
                 "DisjointClasses(pm:Continuant pm:Process)",
                 "DisjointClasses(pm:ProcessQuality pm:ContinuantQuality)",
                 "DisjointClasses(pm:ContinuantTrait pm:ProcessTrait)"]
        for prop in ("nodeId", "scale", "migrationStatus", "sourceChecksum",
                     "evidenceStatus", "influenceId", "influenceContext", "contextId",
                     "collectionFor"):
            lines.append(f"Declaration(AnnotationProperty(pm:{prop}))")
        properties = (
            "hasPart", "hasContinuantPart", "hasOccurrentPart", "partOf", "contextPartOf",
            "occursIn", "hasQuality", "concerns", "hasNumerator",
            "hasDenominator", "hasRateNumerator", "hasRateDenominator", "hasFactor",
            "hasSummand", "hasArgument", "causedBy", "producedBy", "constitutedBy", "modulates",
            "memberOf", "hasMember",
        )
        for prop in properties:
            lines.append(f"Declaration(ObjectProperty(pm:{prop}))")
        # Phene-pattern mereology. `contextPartOf` is the *localizing* specialization of parthood
        # (a trait's context), kept distinct from the generic `partOf` used by the part-inclusive
        # closure; process traits localize with `occursIn` instead. Both chains are OWL 2 EL.
        lines += ["SubObjectPropertyOf(pm:hasContinuantPart pm:hasPart)",
                  "SubObjectPropertyOf(pm:hasOccurrentPart pm:hasPart)",
                  "SubObjectPropertyOf(pm:contextPartOf pm:partOf)",
                  "TransitiveObjectProperty(pm:partOf)",
                  # A process occurring in a part occurs in the whole. The mirror chain
                  # `hasPart o partOf -> hasPart` is deliberately absent: it is unsound (a part of
                  # my part's whole need not be my part) and, with `partOf` as the inverse of
                  # `hasPart`, it also breaks OWL 2 DL regularity. The part-inclusive closure runs
                  # through the reflexive `partOf` helper classes instead.
                  "SubObjectPropertyOf(ObjectPropertyChain(pm:occursIn pm:partOf) pm:occursIn)",
                  "ObjectPropertyRange(pm:hasQuality pm:Quality)"]
        # Signature-bound source module: TBox declarations, labels, and parent links only.
        # Source individuals are intentionally never copied into the primary KB.
        for identifier, term in sorted(registry.items()):
            lines += [f"Declaration(Class({_iri(identifier)}))",
                      f"AnnotationAssertion(rdfs:label {_iri(identifier)} {_literal(term.label)})"]
            for parent in term.parents:
                if parent in registry:
                    lines.append(f"SubClassOf({_iri(identifier)} {_iri(parent)})")
        records: list[dict[str, Any]] = []
        rendered_qualities: set[str] = set()
        occurrent_traits: set[str] = set()
        for node in sorted(pmap.nodes, key=lambda n: n.id):
            trait = _trait(node.id)
            try:
                from physiomap_core.bfo import BearerKind, bearer_kind
                occurrent = bearer_kind(node) == BearerKind.OCCURRENT
            except Exception:  # pragma: no cover - defensive for standalone artifact builds
                occurrent = (node.entity_iri or "").startswith("GO:")
            bearer_class = "pm:ProcessTrait" if occurrent else "pm:ContinuantTrait"
            if occurrent:
                occurrent_traits.add(node.id)
            collection = _collection(node.id)
            lines += [f"Declaration(Class({trait}))", f"SubClassOf({trait} pm:MapVariable)",
                      f"SubClassOf({trait} {bearer_class})",
                      f"AnnotationAssertion(rdfs:label {trait} {_literal(node.label)})",
                      f"AnnotationAssertion(pm:nodeId {trait} {_literal(node.id)})",
                      f"AnnotationAssertion(pm:scale {trait} {_literal(node.scale.value)})",
                      # The timeless collection of all instances of the trait. Mechanism relations
                      # (causal influence, production, modulation) are type-level capacity claims:
                      # they are asserted of the collection, not of every bearer of the trait.
                      f"Declaration(Class({collection}))",
                      f"SubClassOf({collection} pm:TraitCollection)",
                      f"AnnotationAssertion(rdfs:label {collection} "
                      f"{_literal('collection of all ' + node.label + ' instances')})",
                      f"AnnotationAssertion(pm:collectionFor {collection} {_literal(node.id)})",
                      f"SubClassOf({trait} ObjectSomeValuesFrom(pm:memberOf {collection}))",
                      f"SubClassOf({collection} ObjectSomeValuesFrom(pm:hasMember {trait}))"]
            asserted = [f"{trait} SubClassOf pm:MapVariable", f"{trait} SubClassOf {bearer_class}"]
            verified: list[str] = []
            quality_class = (_general_quality(node.entity_iri, node.quality_iri)
                             if node.entity_iri and node.quality_iri else None)
            if quality_class and quality_class not in rendered_qualities:
                rendered_qualities.add(quality_class)
                lines += [f"Declaration(Class({quality_class}))",
                          f"SubClassOf({quality_class} "
                          f"{'pm:ProcessQuality' if occurrent else 'pm:ContinuantQuality'})",
                          f"SubClassOf({quality_class} {_iri(node.quality_iri)})",
                          f"SubClassOf({quality_class} ObjectSomeValuesFrom(pm:concerns {_iri(node.entity_iri)}))"]
            # Phene pattern: the trait says the organism has a part (a process part, for a process
            # trait) that *is* the characterized entity, sits in the recorded context, and bears the
            # entity-specific quality. Continuant context localizes with `contextPartOf`; a process
            # localizes with `occursIn` -- a process is not a part of an organ.
            part_property = "pm:hasOccurrentPart" if occurrent else "pm:hasContinuantPart"
            context_property = "pm:occursIn" if occurrent else "pm:contextPartOf"
            conjuncts: list[str] = []
            readable: list[str] = []
            for value in (node.entity_iri, node.bearer_entity_iri, node.quality_iri):
                if value:
                    lines.append(f"Declaration(Class({_iri(value)}))")
                    if value in registry:
                        verified.append(value)
            if node.entity_iri:
                conjuncts.append(_iri(node.entity_iri))
                readable.append(node.entity_iri)
            if node.bearer_entity_iri:
                conjuncts.append(
                    f"ObjectSomeValuesFrom({context_property} {_iri(node.bearer_entity_iri)})")
                readable.append(f"{context_property[3:]} some {node.bearer_entity_iri}")
            if node.quality_iri:
                lines.append(f"SubClassOf({_iri(node.quality_iri)} pm:Quality)")
                filler = quality_class or _iri(node.quality_iri)
                conjuncts.append(f"ObjectSomeValuesFrom(pm:hasQuality {filler})")
                readable.append(f"hasQuality some {quality_class or node.quality_iri}")
            if conjuncts:
                inner = (conjuncts[0] if len(conjuncts) == 1
                         else f"ObjectIntersectionOf({' '.join(conjuncts)})")
                lines.append(f"SubClassOf({trait} ObjectSomeValuesFrom({part_property} {inner}))")
                asserted.append(f"{trait} SubClassOf {part_property[3:]} some "
                                f"({' and '.join(readable)})")
            complete = bool(node.entity_iri and node.quality_iri)
            if not complete:
                lines.append(f"AnnotationAssertion(pm:migrationStatus {trait} \"incomplete\")")
            records.append({"node_id": node.id, "trait_iri": f"{BASE}trait/{quote(node.id, safe='_-')}",
                            "quality_class_iri": quality_class[1:-1] if quality_class else None,
                            "source_fields": node.model_dump(mode="json", exclude_none=True),
                            "asserted_axioms": asserted, "inferred_parents": ["pm:Trait"],
                            "satisfiable": True, "verified_terms": verified,
                            "unresolved_information": [] if complete else [
                                name for name, value in (("entity_iri", node.entity_iri),
                                                        ("quality_iri", node.quality_iri)) if not value],
                            "migration_status": "complete" if complete else "incomplete"})
        mereology_lines, groupings = self._mereology(pmap, registry, occurrent_traits)
        lines += mereology_lines
        for edge in sorted(
            pmap.causal_edges,
            key=lambda e: (e.source, e.target, e.sign.value, e.context.id if e.context else ""),
        ):
            status = "controlled" if edge.causal_evidence else "legacy-evidence-unclassified"
            annotations = (
                f"Annotation(pm:evidenceStatus {_literal(status)}) "
                f"Annotation(pm:influenceId {_literal(edge.id or '')})"
            )
            if edge.context:
                annotations += (
                    f" Annotation(pm:contextId {_literal(edge.context.id)})"
                    f" Annotation(pm:influenceContext {_literal(edge.context.label)})"
                )
            # Some member of the target's collection is actually caused by a source instance --
            # the existential witness an intervention supplies. `T_t SubClassOf causedBy some T_s`
            # would instead claim it of every bearer, which any blocked source arm refutes.
            lines.append(f"SubClassOf({annotations} {_collection(edge.target)} "
                         f"ObjectSomeValuesFrom(pm:hasMember "
                         f"ObjectSomeValuesFrom(pm:causedBy {_trait(edge.source)})))")
        for edge in sorted(
            pmap.production_edges, key=lambda e: (e.source, e.target, e.sign.value)
        ):
            status = (
                "legacy-evidence-unclassified"
                if edge.production_evidence.value == "legacy-evidence-unclassified"
                else "controlled"
            )
            lines.append(
                f"SubClassOf(Annotation(pm:evidenceStatus {_literal(status)}) "
                f"{_collection(edge.target)} ObjectSomeValuesFrom(pm:hasMember "
                f"ObjectSomeValuesFrom(pm:producedBy {_trait(edge.source)})))"
            )
        for edge in sorted(pmap.constitutive_edges, key=lambda e: (e.micro, e.macro, e.relation)):
            lines.append(f"SubClassOf({_trait(edge.macro)} ObjectSomeValuesFrom(pm:constitutedBy {_trait(edge.micro)}))")
        for definition in sorted(
            pmap.quantitative_definitions,
            key=lambda item: (item.kind, item.result,
                              tuple(argument.node for argument in item.arguments)),
        ):
            lines.extend(_quantitative_owl_axioms(definition))
        for mod in sorted(pmap.modulation_edges, key=lambda m: (m.modulator, m.edge_source, m.edge_target)):
            filler = f"ObjectIntersectionOf({_trait(mod.edge_target)} ObjectSomeValuesFrom(pm:causedBy {_trait(mod.edge_source)}))"
            lines.append(f"SubClassOf({_collection(mod.modulator)} ObjectSomeValuesFrom(pm:hasMember "
                         f"ObjectSomeValuesFrom(pm:modulates {filler})))")
        for source, checksum in sorted(checksums.items()):
            lines.append(f"AnnotationAssertion(pm:sourceChecksum <{BASE}kb/{__version__}> "
                         f"{_literal(source + ':' + checksum)})")
        dl_lines = lines + _dl_representation_axioms(pmap)
        lines.append(")")
        dl_lines.append(")")
        return ("\n".join(lines) + "\n", "\n".join(dl_lines) + "\n", records, groupings)

    def _mereology(self, pmap: PhysioMap, registry: dict[str, RegistryTerm],
                   occurrent_traits: set[str]) -> tuple[list[str], list[dict[str, Any]]]:
        """Emit the part-of backbone plus the part-inclusive grouping classes.

        Two distinct uses of parthood are kept apart. The *context* of a trait localizes it and is
        asserted per trait (`contextPartOf` / `occursIn`). The *composable* closure below is what
        makes a part's trait inherit to the whole, and it is minted only where the physiology
        licenses it: an extensive quality composes over `part_of` (whole = sum of parts), a process
        rate composes only for the *same* process localized in a part of the same site. Intensive
        qualities (pressure, concentration, pH) get no grouping -- their part/whole composition is
        not fixed by the quality type, so the reasoner must not inherit them.
        """
        from physiomap_core.constitution import is_part_of, load_partof, partof_graph
        from physiomap_core.quantity import QualityKind, load_quality_kinds, quality_kind

        kinds = load_quality_kinds()
        graph = partof_graph(load_partof())
        used = {value for node in pmap.nodes
                for value in (node.entity_iri, node.bearer_entity_iri) if value}
        lines: list[str] = []
        for part in sorted(used & set(graph.nodes)):
            for whole in sorted(graph.successors(part)):
                lines += [f"Declaration(Class({_iri(part)}))", f"Declaration(Class({_iri(whole)}))",
                          f"SubClassOf({_iri(part)} ObjectSomeValuesFrom(pm:partOf {_iri(whole)}))"]

        def label(identifier: str) -> str:
            term = registry.get(identifier)
            return term.label if term else identifier

        composable = {}
        for node in pmap.nodes:
            if not (node.entity_iri and node.quality_iri):
                continue
            kind = quality_kind(node, kinds)
            occurrent = node.id in occurrent_traits
            if occurrent and kind in (QualityKind.EXTENSIVE, QualityKind.RATE):
                composable[node.id] = ("process", node.entity_iri, node.bearer_entity_iri,
                                       node.quality_iri)
            elif not occurrent and kind is QualityKind.EXTENSIVE:
                composable[node.id] = ("continuant", node.entity_iri, None, node.quality_iri)
        groupings: list[dict[str, Any]] = []
        seen: set[tuple[str, ...]] = set()
        for node_id, (mode, entity, context, quality) in sorted(composable.items()):
            whole = context if mode == "process" else entity
            if not whole:
                continue
            key = (mode, entity, whole, quality)
            if key in seen:
                continue
            # Mint only where the closure has a witness: some other trait of the same quality
            # (and, for a process, of the same process) sits on a proper part of this whole.
            subsumed = sorted(
                other for other, value in composable.items()
                if other != node_id and value[0] == mode and value[3] == quality
                and (value[1] == entity if mode == "process" else True)
                and (value[2] if mode == "process" else value[1])
                and (value[2] if mode == "process" else value[1]) != whole
                and is_part_of(graph, (value[2] if mode == "process" else value[1]), whole)
            )
            if not subsumed:
                continue
            seen.add(key)
            identifier = _stable("grouping", *key)
            iri = f"<{BASE}grouping/{identifier}>"
            if mode == "process":
                text = f"{label(quality)} of {label(entity)} occurring in {label(whole)} or its parts"
                inner = (f"ObjectIntersectionOf({_iri(entity)} "
                         f"ObjectSomeValuesFrom(pm:occursIn {_iri(whole)}) "
                         f"ObjectSomeValuesFrom(pm:hasQuality {_iri(quality)}))")
            else:
                helper = f"<{BASE}mereotope/{_stable('partof', whole)}>"
                lines += [f"Declaration(Class({helper}))",
                          f"AnnotationAssertion(rdfs:label {helper} "
                          f"{_literal(label(whole) + ' or part of it')})",
                          f"SubClassOf({_iri(whole)} {helper})",
                          f"SubClassOf(ObjectSomeValuesFrom(pm:partOf {_iri(whole)}) {helper})"]
                text = f"{label(quality)} of {label(whole)} or its parts"
                inner = (f"ObjectIntersectionOf({helper} "
                         f"ObjectSomeValuesFrom(pm:hasQuality {_iri(quality)}))")
            definition = f"ObjectSomeValuesFrom(pm:hasPart {inner})"
            lines += [f"Declaration(Class({iri}))", f"SubClassOf({iri} pm:Trait)",
                      f"AnnotationAssertion(rdfs:label {iri} {_literal(text)})",
                      f"EquivalentClasses({iri} {definition})"]
            groupings.append({"grouping_id": identifier, "grouping_iri": iri[1:-1], "mode": mode,
                              "label": text, "entity_iri": entity, "context_iri": context,
                              "quality_iri": quality, "definition": definition,
                              "expected_members": sorted({node_id, *subsumed})})
        return lines, groupings


def _dl_representation_axioms(pmap: PhysioMap) -> list[str]:
    """Axioms PhysioMap *represents* but does not reason over.

    ELK answers every released query, so the EL artifact carries only EL-expressible axioms. The
    ontology's actual commitments are wider: parthood has inverses, and PATO's constraint that a
    process quality can only be a quality *of* a process is a universal restriction. Both are OWL 2
    DL, so they live in the DL artifact, which also types every external entity as continuant or
    occurrent so that the universal restrictions have something to bite on.
    """
    from physiomap_core.bfo import _isa_ancestors

    lines = ["Declaration(ObjectProperty(pm:qualityOf))",
             "Declaration(ObjectProperty(pm:continuantPartOf))",
             "Declaration(ObjectProperty(pm:occurrentPartOf))",
             "Declaration(ObjectProperty(pm:siteOfProcess))",
             "InverseObjectProperties(pm:hasMember pm:memberOf)",
             "InverseObjectProperties(pm:hasPart pm:partOf)",
             "InverseObjectProperties(pm:hasContinuantPart pm:continuantPartOf)",
             "InverseObjectProperties(pm:hasOccurrentPart pm:occurrentPartOf)",
             "InverseObjectProperties(pm:hasQuality pm:qualityOf)",
             "InverseObjectProperties(pm:occursIn pm:siteOfProcess)",
             "SubObjectPropertyOf(pm:continuantPartOf pm:partOf)",
             "SubObjectPropertyOf(pm:occurrentPartOf pm:partOf)",
             "ObjectPropertyDomain(pm:occursIn pm:Process)",
             "ObjectPropertyRange(pm:occursIn pm:Continuant)",
             "ObjectPropertyDomain(pm:contextPartOf pm:Continuant)",
             "ObjectPropertyRange(pm:contextPartOf pm:Continuant)",
             # PATO: a process quality inheres only in processes; a physical-object quality only
             # in continuants. This is what makes a rate borne by an organ a modelling error.
             "SubClassOf(pm:ProcessQuality ObjectAllValuesFrom(pm:qualityOf pm:Process))",
             "SubClassOf(pm:ContinuantQuality ObjectAllValuesFrom(pm:qualityOf pm:Continuant))"]
    # A trait collection is homogeneous (only instances of its trait) and is the *one* such
    # collection. Neither axiom is in OWL 2 EL, and neither is needed for the released
    # entailments, so both are represented here and never reasoned over.
    for node in sorted(pmap.nodes, key=lambda n: n.id):
        collection = _collection(node.id)
        individual = f"<{BASE}collection/{_stable('collection-individual', node.id)}>"
        lines += [f"Declaration(NamedIndividual({individual}))",
                  f"SubClassOf({collection} ObjectAllValuesFrom(pm:hasMember {_trait(node.id)}))",
                  f"EquivalentClasses({collection} ObjectOneOf({individual}))"]
    used = {value for node in pmap.nodes
            for value in (node.entity_iri, node.bearer_entity_iri) if value}
    for identifier in sorted(used):
        prefix = identifier.split(":")[0]
        if prefix == "GO":
            ancestors = _isa_ancestors("GO", identifier) | {identifier}
            if "GO:0008150" in ancestors:
                lines.append(f"SubClassOf({_iri(identifier)} pm:Process)")
            elif "GO:0005575" in ancestors:
                lines.append(f"SubClassOf({_iri(identifier)} pm:Continuant)")
        elif prefix in {"UBERON", "CL", "CHEBI", "PR", "FMA", "CLO"}:
            lines.append(f"SubClassOf({_iri(identifier)} pm:Continuant)")
    return lines


def write_artifacts(output_dir: Path, owl: str, manifest: ScmManifest,
                    report: dict[str, Any], dl_owl: str | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "physiomap.owl").write_text(owl, encoding="utf-8")
    (output_dir / "physiomap-el.owl").write_text(owl, encoding="utf-8")
    (output_dir / "physiomap-dl.owl").write_text(dl_owl or owl, encoding="utf-8")
    manifest.write_json(output_dir / "physiomap-scm.json")
    (output_dir / "projection-traces.json").write_text(json.dumps(
        [t.model_dump(mode="json") for t in manifest.projection_traces], indent=2, sort_keys=True) + "\n")
    (output_dir / "migration-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def verify_elk_projection(path: Path, manifest: ScmManifest) -> dict[str, int]:
    """Require ELK's registered entailments to equal the generated SCM projection.

    Multiple legacy influences may deliberately share one OWL witness (for example, distinct
    mechanism/context discriminators), so comparison is over unique instantiated patterns while
    the manifest retains every contextual influence and its trace.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "pattern_id\targ1\targ2\targ3":
        raise ValueError("invalid ELK projection-entailment header")
    actual = {tuple((line.split("\t") + [""] * 4)[:4]) for line in lines[1:] if line}
    expected: set[tuple[str, str, str, str]] = set()
    expected.update(("causal-collection-v2", e.source, e.target, "")
                    for e in manifest.influences)
    expected.update(("production-collection-v2", e.source, e.target, "")
                    for e in manifest.production_relations)
    expected.update(("constitution-v1", e.micro, e.macro, "")
                    for e in manifest.constitutive_constraints)
    expected.update(("ratio-v1", q.result, q.arguments[0].node, q.arguments[1].node)
                    for q in manifest.quantitative_expressions if q.kind == "ratio")
    influence = {e.id: e for e in manifest.influences}
    expected.update(("multiplicative-modulation-v2", h.modulator,
                     influence[h.influence_id].source, influence[h.influence_id].target)
                    for h in manifest.modulation)
    missing, extra = sorted(expected - actual), sorted(actual - expected)
    if missing or extra:
        preview = f"missing={missing[:5]}, extra={extra[:5]}"
        raise ValueError(f"ELK/SCM projection mismatch ({preview})")
    counts: dict[str, int] = {}
    for row in actual:
        counts[row[0]] = counts.get(row[0], 0) + 1
    return dict(sorted(counts.items()))
