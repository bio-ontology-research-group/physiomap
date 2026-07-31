"""Curation: validate a proposed contribution with the **same gates we run before deployment**.

The PhysioMap editor lets curators (George, Paul, …) propose new nodes and edges — signed
**causal** influences, typed **production** relations, cross-scale **constitutive** edges, and
**modulation** (gain) edges — with full
provenance. The cardinal rule (see ``CONTRIBUTING.md``) is that *curation must not add an incorrect edge*.
This module is the enforcement: it does **not** re-implement any check — it composes a candidate map
(the committed corpus + the proposed contribution) and runs it through the very functions that gate a
release:

* schema + reference integrity + "a modulation modulates a real causal edge" — ``PhysioMap.model_validate``
* provenance (every causal edge cites evidence) — the ``validate_fragment`` rule
* the causal-evidence interventional gate — ``causal_evidence.admit`` / ``admit_modulation``
* constitution mereology (part_of / aggregation) — ``constitution.validate_constitution``
* cross-scale meta-graph acyclicity — the ``multiscale`` meta-graph DAG check
* ontology-id sanity — format + the verified-id manifest (full OBO check happens at merge)
* (deep) the HPO **soundness regression** — ``scripts.hpo_regression_gate.check`` on the candidate map:
  0 wrong determinate predictions, no backward-diagnosis regression, all references resolve.

A contribution is a dict of the same shape as a fragment::

    {"nodes": [...], "causal_edges": [...], "production_edges": [...],
     "constitutive_edges": [...], "modulation_edges": [...]}

`validate_contribution` returns a structured :class:`CurationReport` (per-gate pass/fail + messages)
so the editor can show exactly why something is rejected — and only a fully green contribution may be
submitted. The submission store (:class:`Submission`) persists proposals with provenance for review.
"""

from __future__ import annotations

import re
import json
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from physiomap_core.causal_evidence import admit, admit_modulation
from physiomap_core.bfo import validate_bearer, validate_bfo
from physiomap_core.constitution import CONSTITUTIVE_KINDS, validate_constitution
from physiomap_core.model import (
    CausalEdge,
    ModulationEdge,
    PhysioMap,
    ProductionEdge,
    ProductionEvidenceClass,
)
from physiomap_core.quantity import validate_quantity

ROOT = Path(__file__).resolve().parent.parent
VERIFIED_IDS = ROOT / "ontology" / "verified_ids.yaml"

#: ontology prefixes admissible for node IRIs (entity from anatomy/cell/molecule, quality from PATO,
#: phenotype from HP, unit from UO, disease from MONDO).
ALLOWED_PREFIXES = {"UBERON", "GO", "CL", "CHEBI", "PR", "PATO", "HP", "UO", "MONDO"}
_IRI_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):([A-Za-z0-9][A-Za-z0-9._-]*)$")

CONTRIBUTION_KEYS = (
    "nodes", "causal_edges", "production_edges", "constitutive_edges", "modulation_edges",
    "quantitative_definitions",
)


# ---------------------------------------------------------------------------
# report types
# ---------------------------------------------------------------------------

class GateResult(BaseModel):
    """Outcome of one validation gate."""

    gate: str
    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    detail: str | None = None


class CurationReport(BaseModel):
    """Aggregate result: a contribution is admissible iff every hard gate passes."""

    ok: bool = False
    gates: list[GateResult] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    summary: str = ""

    @property
    def errors(self) -> list[str]:
        return [f"[{g.gate}] {e}" for g in self.gates for e in g.errors]

    @property
    def warnings(self) -> list[str]:
        return [f"[{g.gate}] {w}" for g in self.gates for w in g.warnings]


# ---------------------------------------------------------------------------
# composing the candidate map
# ---------------------------------------------------------------------------

def normalize_legacy_contribution(contribution: dict) -> dict:
    """Convert accepted legacy contribution aliases into the structured migration shape."""
    raw = dict(contribution or {})
    nodes = []
    for node in raw.get("nodes", []) or []:
        node = dict(node)
        aliases = {"entity": "entity_iri", "quality": "quality_iri", "bearer": "bearer_entity_iri"}
        for old, new in aliases.items():
            if old in node and new not in node:
                node[new] = node.pop(old)
        nodes.append(node)
    causal = []
    for edge in (raw.get("causal_edges") or raw.get("edges") or []):
        edge = dict(edge)
        if "from" in edge and "source" not in edge:
            edge["source"] = edge.pop("from")
        if "to" in edge and "target" not in edge:
            edge["target"] = edge.pop("to")
        if "effect" in edge and "sign" not in edge:
            edge["sign"] = {"increase": "+", "increases": "+", "decrease": "-",
                            "decreases": "-", "unknown": "?"}.get(edge.pop("effect"), "?")
        causal.append(edge)
    quantitative = list(raw.get("quantitative_definitions") or [])
    for ratio in raw.get("ratio_definitions") or []:
        quantitative.append({
            "kind": "ratio",
            "result": ratio["ratio"],
            "arguments": [
                {"node": ratio["numerator"], "role": "numerator", "derivative_sign": "+"},
                {"node": ratio["denominator"], "role": "denominator", "derivative_sign": "-"},
            ],
            **({"mechanism": ratio["mechanism"]} if ratio.get("mechanism") else {}),
            **({"evidence": ratio["evidence"]} if ratio.get("evidence") else {}),
        })
    production = list(raw.get("production_edges") or [])
    constitutive = []
    for edge in raw.get("constitutive_edges") or []:
        if edge.get("relation") == "production":
            production.append({
                "source": edge["micro"],
                "target": edge["macro"],
                "sign": edge.get("sign", "+"),
                "production_evidence": "legacy-evidence-unclassified",
            })
        else:
            constitutive.append(edge)
    return {"nodes": nodes, "causal_edges": causal,
            "production_edges": production,
            "constitutive_edges": constitutive,
            "modulation_edges": list(raw.get("modulation_edges") or []),
            "quantitative_definitions": quantitative}


def _normalise(contribution: dict) -> dict:
    return normalize_legacy_contribution(contribution)


def _causal_key(edge: dict) -> object:
    if edge.get("id"):
        return edge["id"]
    try:
        return CausalEdge.model_validate(edge).id
    except Exception:  # schema gate will report the detailed error later
        pass
    context = edge.get("context")
    context_id = context.get("id") if isinstance(context, dict) else context
    return (
        edge.get("source"), edge.get("target"), edge.get("sign"), context_id
    )


def _modulation_key(edge: dict) -> tuple[object, ...]:
    return (
        edge.get("modulator"),
        edge.get("influence_id")
        or (edge.get("edge_source"), edge.get("edge_target")),
    )


def _modulation_endpoints(edge: dict) -> tuple[str | None, str | None]:
    source, target = edge.get("edge_source"), edge.get("edge_target")
    if source and target:
        return source, target
    parts = str(edge.get("influence_id") or "").split(":")
    if len(parts) >= 4 and parts[0] == "influence":
        return parts[1], parts[3]
    return None, None


def compose_candidate(base: PhysioMap, contribution: dict) -> PhysioMap:
    """The committed map with the contribution merged in (dict-level union, then validated).

    Mirrors :meth:`PhysioMap.load_composed`: nodes union by id (a *differing* re-definition of an
    existing id raises — you cannot silently overwrite a node), edges de-duplicated. Raises
    ``ValueError`` / pydantic ``ValidationError`` on any schema or reference problem.
    """
    contribution = _normalise(contribution)
    base_d = base.to_dict()
    nodes: dict[str, dict] = {n["id"]: n for n in base_d.get("nodes", [])}
    for nd in contribution["nodes"]:
        nid = nd["id"]
        if nid in nodes and nodes[nid] != nd:
            raise ValueError(
                f"node {nid!r} already exists with a different definition — editing existing "
                f"nodes is not supported via curation (propose edges referencing it instead)"
            )
        nodes[nid] = nd
    causal = {_causal_key(e): e for e in base_d.get("causal_edges", [])}
    for e in contribution["causal_edges"]:
        causal[_causal_key(e)] = e
    production = {
        (e["source"], e["target"], e["sign"]): e
        for e in base_d.get("production_edges", [])
    }
    for e in contribution["production_edges"]:
        production[(e["source"], e["target"], e["sign"])] = e
    const = {(e["micro"], e["macro"], e.get("relation", "")): e
             for e in base_d.get("constitutive_edges", [])}
    for e in contribution["constitutive_edges"]:
        const[(e["micro"], e["macro"], e.get("relation", ""))] = e
    modul = {_modulation_key(e): e for e in base_d.get("modulation_edges", [])}
    for e in contribution["modulation_edges"]:
        modul[_modulation_key(e)] = e
    quantitative = {
        (e["kind"], e["result"], tuple(
            (argument["node"], argument.get("role", "argument"))
            for argument in e["arguments"]
        )): e
        for e in base_d.get("quantitative_definitions", [])
    }
    for e in contribution["quantitative_definitions"]:
        key = (e["kind"], e["result"], tuple(
            (argument["node"], argument.get("role", "argument"))
            for argument in e["arguments"]
        ))
        quantitative[key] = e
    return PhysioMap.model_validate({
        "name": "candidate",
        "nodes": list(nodes.values()),
        "causal_edges": list(causal.values()),
        "production_edges": list(production.values()),
        "constitutive_edges": list(const.values()),
        "modulation_edges": list(modul.values()),
        "quantitative_definitions": list(quantitative.values()),
    })


# ---------------------------------------------------------------------------
# individual gates (each reuses the deployment-grade check)
# ---------------------------------------------------------------------------

def _gate_schema(base: PhysioMap, contribution: dict) -> tuple[GateResult, PhysioMap | None]:
    """Schema + reference integrity + modulation-modulates-a-real-edge, via the real validator."""
    try:
        cand = compose_candidate(base, contribution)
        quantity = validate_quantity(cand)
        new_quantity_errors = sorted(set(quantity.errors) - set(validate_quantity(base).errors))
        if new_quantity_errors:
            raise ValueError("; ".join(new_quantity_errors))
    except Exception as exc:  # noqa: BLE001 - surface the validator's message verbatim
        return GateResult(gate="schema", ok=False, errors=[str(exc)]), None
    return GateResult(gate="schema", ok=True,
                      detail="parses against the pydantic model; all references resolve"), cand


def _gate_provenance(contribution: dict) -> GateResult:
    """Every NEW causal edge must cite evidence; mechanism strongly recommended. New nodes should
    carry entity + quality IRIs (the EQ pair we want to keep)."""
    c = _normalise(contribution)
    errors, warnings = [], []
    for i, e in enumerate(c["causal_edges"]):
        tag = f"{e.get('source')}->{e.get('target')}"
        if not (e.get("evidence") or "").strip():
            errors.append(f"causal edge {tag}: MISSING evidence (provenance is required)")
        if not (e.get("mechanism") or "").strip():
            warnings.append(f"causal edge {tag}: no mechanism described")
    for edge in c["production_edges"]:
        tag = f"{edge.get('source')}->{edge.get('target')}"
        if not (edge.get("evidence") or "").strip():
            errors.append(f"production edge {tag}: MISSING evidence")
        if not (edge.get("mechanism") or "").strip():
            errors.append(f"production edge {tag}: MISSING mechanism")
    for i, m in enumerate(c["modulation_edges"]):
        source, target = _modulation_endpoints(m)
        tag = f"{m.get('modulator')} scales {m.get('influence_id') or f'({source}->{target})'}"
        if not (m.get("evidence") or "").strip():
            errors.append(f"modulation {tag}: MISSING evidence")
    for definition in c["quantitative_definitions"]:
        tag = f"{definition.get('kind')}:{definition.get('result')}"
        if not (definition.get("evidence") or "").strip():
            errors.append(f"quantitative definition {tag}: MISSING evidence")
        if not (definition.get("mechanism") or "").strip():
            errors.append(f"quantitative definition {tag}: MISSING mechanism/equation")
    for n in c["nodes"]:
        miss = [f for f in ("entity_iri", "quality_iri") if not (n.get(f) or "").strip()]
        if miss:
            warnings.append(f"node {n.get('id')}: no {', '.join(miss)} (EQ grounding recommended)")
    return GateResult(gate="provenance", ok=not errors, errors=errors, warnings=warnings)


def _gate_causal_evidence(contribution: dict) -> GateResult:
    """New causal, production, and modulation records require controlled evidence classes."""
    c = _normalise(contribution)
    errors = []
    for e in c["causal_edges"]:
        if e.get("source") == e.get("target"):
            continue
        try:
            edge = CausalEdge.model_validate(e)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{e.get('source')}->{e.get('target')}: invalid ({exc})")
            continue
        ok, reason = admit(edge)
        if not ok:
            errors.append(f"{e.get('source')}->{e.get('target')}: {reason}")
    for m in c["modulation_edges"]:
        try:
            mod = ModulationEdge.model_validate(m)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"modulation {m.get('modulator')}: invalid ({exc})")
            continue
        ok, reason = admit_modulation(mod)
        if not ok:
            errors.append(
                f"modulation {m.get('modulator')} scales "
                f"{m.get('influence_id') or _modulation_endpoints(m)}: {reason}")
    for raw in c["production_edges"]:
        tag = f"{raw.get('source')}->{raw.get('target')}"
        try:
            edge = ProductionEdge.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"production {tag}: invalid ({exc})")
            continue
        if edge.production_evidence is ProductionEvidenceClass.LEGACY_UNCLASSIFIED:
            errors.append(
                f"production {tag}: new curation cannot use legacy-evidence-unclassified"
            )
    return GateResult(gate="causal_evidence", ok=not errors, errors=errors,
                      detail=(
                          "interventional class required for causal/modulation records; "
                          "controlled production provenance required for process outputs"
                      ))


def _gate_constitution(base: PhysioMap, cand: PhysioMap, contribution: dict) -> GateResult:
    """Constitutive edges obey the part_of / aggregation mereology.

    Runs the real :func:`validate_constitution` on the candidate map and reports only violations
    that involve a NEW constitutive edge (the base map already passes)."""
    c = _normalise(contribution)
    if not c["constitutive_edges"]:
        return GateResult(gate="constitution", ok=True, detail="no constitutive edges proposed")
    new_pairs = {(e.get("micro"), e.get("macro")) for e in c["constitutive_edges"]}
    try:
        report = validate_constitution(cand)
    except Exception as exc:  # noqa: BLE001
        return GateResult(gate="constitution", ok=False, errors=[f"validate_constitution: {exc}"])
    # only errors that involve a NEW constitutive edge gate; pre-existing ones (if any) are notes
    errors = [v for v in report.errors if any(m in v and M in v for (m, M) in new_pairs)]
    warnings = [v for v in report.errors if v not in errors]
    warnings += [v for v in report.notes if any(m in v and M in v for (m, M) in new_pairs)]
    return GateResult(gate="constitution", ok=not errors, errors=errors, warnings=warnings,
                      detail=f"{report.n_constitutive} constitutive edges checked vs "
                             "ontology/partof.yaml")


def _gate_bearer_bfo(base: PhysioMap, cand: PhysioMap) -> GateResult:
    """Reject new bearer mismatches and malformed cross-BFO relation typing."""
    base_bearer = set(validate_bearer(base, strict=True).errors)
    candidate_bearer = set(validate_bearer(cand, strict=True).errors)
    new_bearer = sorted(candidate_bearer - base_bearer)
    bfo = validate_bfo(cand)
    errors = sorted(set(bfo.errors) | set(new_bearer))
    return GateResult(
        gate="bearer_bfo",
        ok=not errors,
        errors=errors,
        warnings=bfo.notes,
        detail=(
            f"{len(candidate_bearer)} known bearer mismatches baselined; "
            "new mismatches and cross-category constitution are forbidden"
        ),
    )


def _gate_acyclicity(cand: PhysioMap) -> GateResult:
    """The combined causal+constitutive meta-graph must stay acyclic (no cross-scale cycle)."""
    import networkx as nx

    from physiomap_core.multiscale import constitutive_graph
    try:
        g = cand.causal_subgraph()
        cg = constitutive_graph(cand)
        cond = nx.condensation(g)
        comp_of = {n: c for c in cond.nodes for n in cond.nodes[c]["members"]}
        meta = nx.DiGraph()
        meta.add_nodes_from(cond.nodes)
        meta.add_edges_from(cond.edges)
        for micro, macro in cg.edges:
            cm, cM = comp_of[micro], comp_of[macro]
            if cm != cM:
                meta.add_edge(cm, cM)
        if not nx.is_directed_acyclic_graph(meta):
            return GateResult(gate="acyclicity", ok=False, errors=[
                "the contribution creates a cross-scale cycle in the causal+constitutive "
                "meta-graph (a constitutive determination plus a causal return path forms an "
                "unsupported mixed-relation loop)"])
    except ValueError as exc:  # constitutive_graph itself cyclic
        return GateResult(gate="acyclicity", ok=False, errors=[str(exc)])
    return GateResult(gate="acyclicity", ok=True,
                      detail="meta-graph (SCC condensation + constitutive lifts) is a DAG")


def _verified_ids() -> dict[str, str]:
    if not VERIFIED_IDS.exists():
        return {}
    return (yaml.safe_load(VERIFIED_IDS.read_text()) or {}).get("ids", {}) or {}


def _gate_ontology(contribution: dict) -> GateResult:
    """New node IRIs are well-formed and (if known) carry their verified label.

    The *authoritative* OBO check (every used ID present + non-obsolete) runs at merge time via
    ``scripts/verify_ontology_ids.py`` — that gate refuses to deploy on a bad ID. Here we do the
    fast live check: prefix in the allowed set + legal CURIE local id, and confirm against the verified
    manifest where possible (so a curator immediately sees the term label they picked)."""
    c = _normalise(contribution)
    verified = _verified_ids()
    errors, warnings = [], []
    for n in c["nodes"]:
        for field in ("entity_iri", "quality_iri", "bearer_entity_iri"):
            iri = (n.get(field) or "").strip()
            if not iri:
                continue
            m = _IRI_RE.match(iri)
            if not m:
                errors.append(
                    f"node {n.get('id')}.{field}: {iri!r} is not a CURIE PREFIX:LOCAL_ID"
                )
                continue
            pfx = m.group(1).upper()
            if pfx not in ALLOWED_PREFIXES:
                errors.append(f"node {n.get('id')}.{field}: prefix {pfx!r} not allowed "
                              f"({sorted(ALLOWED_PREFIXES)})")
                continue
            if field == "quality_iri" and pfx != "PATO":
                warnings.append(f"node {n.get('id')}.quality_iri: {iri} is not a PATO term "
                                "(qualities are normally PATO determinables)")
            if iri in verified:
                warnings.append(f"node {n.get('id')}.{field}: {iri} ✓ verified = {verified[iri]!r}")
            else:
                warnings.append(f"node {n.get('id')}.{field}: {iri} format OK — will be "
                                "OBO-verified before deployment (not yet in the verified manifest)")
    return GateResult(gate="ontology", ok=not errors, errors=errors, warnings=warnings,
                      detail="format + verified-id manifest (full OBO verification at merge)")


def _gate_soundness(cand: PhysioMap) -> GateResult:
    """Deep gate: the HPO soundness regression on the candidate map (0 wrong determinate, etc.)."""
    try:
        from scripts.hpo_regression_gate import check
    except Exception as exc:  # noqa: BLE001 - scripts may be unavailable in some installs
        return GateResult(gate="soundness", ok=False, errors=[f"cannot import gate: {exc}"])
    ok, violations = check(quiet=True, pmap=cand)
    return GateResult(gate="soundness", ok=ok, errors=violations,
                      detail="HPO forward 0-wrong + backward + referential integrity (deep)")


def _gate_projection(cand: PhysioMap) -> GateResult:
    """Build the candidate OWL/SCM artifacts and run quantitative structural validation."""
    try:
        from physiomap_core.owl_projection import MigrationBuilder
        from physiomap_core.quantitative_validation import validate_quantitative_manifest
        builder = MigrationBuilder(ROOT / "projection/patterns.yaml", ROOT / "ontology/.obo_cache")
        _, manifest, migration = builder.build(cand)
        if migration["source_registry"]["missing"] or migration["source_registry"]["obsolete"]:
            return GateResult(gate="owl_projection", ok=False, errors=[
                f"source terms missing={migration['source_registry']['missing']} "
                f"obsolete={migration['source_registry']['obsolete']}"])
        quantitative = validate_quantitative_manifest(manifest, trials=4)
        if not quantitative.ok:
            return GateResult(gate="owl_projection", ok=False, errors=quantitative.errors)
        return GateResult(gate="owl_projection", ok=True,
                          detail=f"{len(manifest.influences)} influences; "
                                 f"{quantitative.exact_rules_checked} derivative rules realized")
    except Exception as exc:  # noqa: BLE001
        return GateResult(gate="owl_projection", ok=False, errors=[str(exc)])


# ---------------------------------------------------------------------------
# the public entry point
# ---------------------------------------------------------------------------

def validate_contribution(base: PhysioMap, contribution: dict, *, deep: bool = False) -> CurationReport:
    """Run every live gate (and, if ``deep``, the soundness regression) on a proposed contribution.

    Returns a :class:`CurationReport`. ``report.ok`` is True iff every *hard* gate passes; warnings
    (e.g. a missing mechanism, or an as-yet-unverified-but-well-formed IRI) never block submission.
    """
    c = _normalise(contribution)
    gates: list[GateResult] = []

    schema, cand = _gate_schema(base, contribution)
    gates.append(schema)
    gates.append(_gate_provenance(contribution))
    gates.append(_gate_causal_evidence(contribution))
    gates.append(_gate_ontology(contribution))
    if cand is not None:
        gates.append(_gate_constitution(base, cand, contribution))
        gates.append(_gate_bearer_bfo(base, cand))
        gates.append(_gate_acyclicity(cand))
        if deep:
            gates.append(_gate_projection(cand))
            gates.append(_gate_soundness(cand))
    else:
        # schema failed: downstream structural gates can't run meaningfully
        gates.append(GateResult(gate="constitution", ok=False,
                                errors=["skipped — fix the schema error first"]))
        gates.append(GateResult(gate="bearer_bfo", ok=False,
                                errors=["skipped — fix the schema error first"]))
        gates.append(GateResult(gate="acyclicity", ok=False,
                                errors=["skipped — fix the schema error first"]))

    ok = all(g.ok for g in gates)
    counts = {k: len(c[k]) for k in CONTRIBUTION_KEYS}
    n = sum(counts.values())
    passed = sum(1 for g in gates if g.ok)
    summary = (f"{'ADMISSIBLE' if ok else 'REJECTED'}: {passed}/{len(gates)} gates pass · "
               f"{counts['nodes']} nodes, {counts['causal_edges']} causal, "
               f"{counts['production_edges']} production, "
               f"{counts['constitutive_edges']} constitutive, {counts['modulation_edges']} "
               f"modulation, {counts['quantitative_definitions']} quantitative definition(s)" +
               ("" if n else " · empty contribution"))
    if not n:
        ok = False
    return CurationReport(ok=ok, gates=gates, counts=counts, summary=summary)


def ontology_lookup(query: str, limit: int = 20) -> list[dict[str, str]]:
    """Search the checksum-bound local source registry by identifier, label, or synonym."""
    path = ROOT / "ontology/registry/used-terms.json"
    if not path.is_file() or not query.strip():
        return []
    terms = json.loads(path.read_text(encoding="utf-8"))["terms"]
    needle = query.casefold().strip()
    matches = []
    for identifier, term in terms.items():
        text = " ".join([identifier, term["label"], *term.get("synonyms", [])]).casefold()
        if needle in text:
            matches.append({"id": identifier, "label": term["label"], "source": term["source"],
                            "obsolete": str(term["obsolete"]).lower()})
    return sorted(matches, key=lambda item: (not item["id"].casefold().startswith(needle),
                                              item["label"], item["id"]))[:limit]


def axiom_preview(contribution: dict) -> list[str]:
    """Render the ordinary OWL axiom templates that a legacy or structured proposal creates."""
    c = _normalise(contribution)
    trait = lambda value: f"<https://w3id.org/physiomap/trait/{value}>"
    # A mechanism relation is a type-level capacity claim, so it is asserted of the trait's
    # timeless collection rather than of every bearer of the trait (`_collection` in
    # owl_projection mints the real IRI; the preview names it readably).
    collection = lambda value: f"<https://w3id.org/physiomap/collection/{value}>"
    axioms = []
    for node in c["nodes"]:
        axioms.extend([f"Declaration(Class({trait(node['id'])}))",
                       f"SubClassOf({trait(node['id'])} pm:MapVariable)",
                       f"SubClassOf({trait(node['id'])} pm:memberOf some {collection(node['id'])})",
                       f"SubClassOf({collection(node['id'])} pm:hasMember some {trait(node['id'])})"])
        conjuncts = []
        if node.get("entity_iri"):
            conjuncts.append(node["entity_iri"])
        if node.get("bearer_entity_iri"):
            process = str(node.get("entity_iri") or "").startswith("GO:")
            relation = "occursIn" if process else "contextPartOf"
            conjuncts.append(f"pm:{relation} some {node['bearer_entity_iri']}")
        if node.get("quality_iri"):
            conjuncts.append(f"pm:hasQuality some {node['quality_iri']}")
        if conjuncts:
            axioms.append(f"SubClassOf({trait(node['id'])} pm:hasPart some "
                          f"({' and '.join(conjuncts)}))")
    for edge in c["causal_edges"]:
        axioms.append(f"SubClassOf({collection(edge['target'])} pm:hasMember some "
                      f"(pm:causedBy some {trait(edge['source'])}))")
    for edge in c["production_edges"]:
        axioms.append(
            f"SubClassOf({collection(edge['target'])} pm:hasMember some "
            f"(pm:producedBy some {trait(edge['source'])}))"
        )
    for edge in c["constitutive_edges"]:
        axioms.append(f"SubClassOf({trait(edge['macro'])} pm:constitutedBy some {trait(edge['micro'])})")
    for edge in c["modulation_edges"]:
        source, target = _modulation_endpoints(edge)
        if source and target:
            axioms.append(f"SubClassOf({collection(edge['modulator'])} pm:hasMember some "
                          f"(pm:modulates some ({trait(target)} and pm:causedBy some "
                          f"{trait(source)})))")
    properties = {
        "ratio": {"numerator": "hasNumerator", "denominator": "hasDenominator"},
        "rate": {"numerator": "hasRateNumerator", "denominator": "hasRateDenominator"},
        "product": {"factor": "hasFactor"},
        "sum": {"summand": "hasSummand"},
        "aggregation": {"summand": "hasSummand"},
        "structural-function": {"argument": "hasArgument"},
    }
    for definition in c["quantitative_definitions"]:
        for argument in definition["arguments"]:
            prop = properties[definition["kind"]][argument["role"]]
            axioms.append(f"SubClassOf({trait(definition['result'])} pm:{prop} some "
                          f"{trait(argument['node'])})")
    return axioms


# ---------------------------------------------------------------------------
# submission store (proposals persisted with provenance, for review)
# ---------------------------------------------------------------------------

_ID_SAFE = re.compile(r"[^a-z0-9]+")


class Submission(BaseModel):
    """A curator's proposed contribution, persisted for review with provenance."""

    id: str
    curator: str
    created: str                      # ISO-8601 timestamp (supplied by the caller; no wall clock here)
    status: str = "pending"           # pending | validated | approved | merged | rejected
    title: str = ""
    note: str | None = None
    contribution: dict = Field(default_factory=dict)
    report: CurationReport | None = None
    review_note: str | None = None


def make_submission_id(curator: str, created: str, title: str = "") -> str:
    """A filesystem-safe, human-readable id from curator + timestamp (+ optional title)."""
    stamp = _ID_SAFE.sub("", created.replace("T", "").replace(":", "").replace("-", ""))[:14]
    who = _ID_SAFE.sub("-", curator.lower()).strip("-")[:20] or "anon"
    slug = _ID_SAFE.sub("-", title.lower()).strip("-")[:24]
    return "-".join(p for p in (stamp, who, slug) if p)


class SubmissionStore:
    """Directory-backed store of :class:`Submission` records (one YAML per submission)."""

    def __init__(self, directory: str | Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, sub_id: str) -> Path:
        if _ID_SAFE.sub("", sub_id.replace("-", "")) != sub_id.replace("-", ""):
            raise ValueError(f"unsafe submission id {sub_id!r}")
        return self.dir / f"{sub_id}.yaml"

    def save(self, sub: Submission) -> Submission:
        self._path(sub.id).write_text(
            yaml.safe_dump(sub.model_dump(mode="json", exclude_none=True),
                           sort_keys=False, allow_unicode=True))
        return sub

    def load(self, sub_id: str) -> Submission:
        return Submission.model_validate(yaml.safe_load(self._path(sub_id).read_text()))

    def list(self) -> list[Submission]:
        out = []
        for f in sorted(self.dir.glob("*.yaml")):
            try:
                out.append(Submission.model_validate(yaml.safe_load(f.read_text())))
            except Exception:  # noqa: BLE001 - skip a corrupt record rather than fail the list
                continue
        return sorted(out, key=lambda s: s.created, reverse=True)

    def update(self, sub_id: str, **changes) -> Submission:
        sub = self.load(sub_id)
        sub = sub.model_copy(update=changes)
        return self.save(sub)


def contribution_to_fragment(sub: Submission) -> str:
    """Render a submission's contribution as a fragment YAML ready to commit under ``benchmarks/``.

    Adds a provenance header (curator, date, submission id, validation summary) so the merged
    fragment carries who proposed it and that it passed the gates. The maintainer still runs the
    full pre-deploy suite (OBO id verification + soundness + tests) before committing.
    """
    c = _normalise(sub.contribution)
    body = {"name": make_submission_id(sub.curator, sub.created, sub.title) or sub.id}
    for k in CONTRIBUTION_KEYS:
        if c[k]:
            body[k] = c[k]
    header = (f"# PhysioMap curation contribution — DRAFT FOR DOMAIN REVIEW\n"
              f"# submitted by: {sub.curator}\n# date: {sub.created}\n"
              f"# submission id: {sub.id}\n# title: {sub.title}\n"
              f"# live-gate result: {sub.report.summary if sub.report else 'not validated'}\n"
              f"# NB: run scripts/verify_ontology_ids.py + scripts/hpo_regression_gate.py + the test "
              f"suite before committing.\n")
    return header + yaml.safe_dump(body, sort_keys=False, allow_unicode=True)
