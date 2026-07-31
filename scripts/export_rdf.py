#!/usr/bin/env python3
"""Export PhysioMap as FAIR linked data (RDF/Turtle + OWL schema).

Mints resolvable IRIs under ``https://w3id.org/physiomap/`` for **variables and for the
relations between them** (the point of a causal knowledge graph: relations are first-class,
identified resources), grounds entities/qualities in OBO Foundry IRIs, types the relations with
the Relation Ontology's *signed* causal relations, and aligns the schema to the Semanticscience
Integrated Ontology (SIO, primary) plus BFO/RO (secondary).

Vocabulary (all verified):
  * variable  = a physiological (entity, PATO quality) attribute at a scale
      pmv:<id> a pmo:Variable, obo:PATO_xxxx ;  RO:0000052 (inheres in) obo:<entity> ;
               sio:SIO_000011 (is attribute of) obo:<entity>            [SIO alignment]
      pmo:Variable rdfs:subClassOf sio:SIO_000614 (attribute)           [SIO alignment]
  * signed causal edge (direct, for reasoning/SPARQL):
      pmv:<src> RO:0002304 pmv:<tgt>   (+, causally upstream of, positive effect)
      pmv:<src> RO:0002305 pmv:<tgt>   (-, causally upstream of, negative effect)
      pmv:<src> RO:0002411 pmv:<tgt>   (?, causally upstream of)
  * reified causal edge (for identity + provenance):
      pme:causal/... a pmo:CausalRelation ; pmo:hasSource ; pmo:hasTarget ; pmo:sign ;
               pmo:causalEvidence ; pmo:mechanism ; dcterms:source (provenance)
  * constitutive edge: pmo:constitutes (+ BFO part_of / has_part); reified pmo:ConstitutiveRelation
  * quantitative definition: reified pmo:QuantitativeDefinition with typed, signed argument
    records; these are identities, not authored causal edges
  * modulation (gain, second-order) edge: a multiplicative edge is the mixed second derivative
    d2(target)/d(source)d(modulator); it is a statement ABOUT a causal edge, so it attaches to the
    causal EDGE resource (the triple), NOT a separate node:
      <causal edge> pmo:gainModulatedBy <modulator> ; pmo:gainSign "+" .
    (In RDF-star this is << src RO_rel tgt >> pmo:gainModulatedBy modulator; the canonical file
    uses edge-level reification for universal tooling compatibility.)

Writes ``rdf/physiomap.ttl`` (self-contained: OWL schema + data). Dependency-free (emits Turtle
directly). Validate with any RDF tool, e.g. ``python -c "import rdflib; rdflib.Graph().parse('rdf/physiomap.ttl')"``.

Run:  uv run python scripts/export_rdf.py
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from physiomap_core.model import Sign
from physiomap_core.scm import ScmManifest, canonical_scm_path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "rdf" / "physiomap.ttl"

BASE = "https://w3id.org/physiomap/"
PREFIXES = {
    "physiomap": BASE,
    "pmv": BASE + "node/",
    "pme": BASE + "edge/",
    "pmo": BASE + "ontology#",
    "obo": "http://purl.obolibrary.org/obo/",
    "sio": "http://semanticscience.org/resource/",
    "dcterms": "http://purl.org/dc/terms/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}

# Relation Ontology / BFO / SIO terms used (obo: and sio: CURIEs)
RO_POS, RO_NEG, RO_ANY = "obo:RO_0002304", "obo:RO_0002305", "obo:RO_0002411"
RO_INHERES_IN = "obo:RO_0000052"
BFO_PART_OF, BFO_HAS_PART = "obo:BFO_0000050", "obo:BFO_0000051"
SIO_ATTRIBUTE, SIO_IS_ATTR_OF = "sio:SIO_000614", "sio:SIO_000011"

SIGN_REL = {Sign.PLUS: RO_POS, Sign.MINUS: RO_NEG, Sign.UNKNOWN: RO_ANY}


def esc(s: str) -> str:
    """Escape a Turtle string literal body."""
    return (
        s.replace("\\", "\\\\").replace('"', '\\"')
        .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    )


def lit(s: str) -> str:
    return '"' + esc(s) + '"'


def loc(s: str) -> str:
    """IRI-safe local name (keep readable snake_case; percent-encode the rest)."""
    return quote(s, safe="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")


def curie_to_obo(curie: str | None) -> str | None:
    """'CHEBI:17234' -> 'obo:CHEBI_17234'; pass through anything already a CURIE/IRI-looking."""
    if not curie:
        return None
    curie = curie.strip()
    if curie.startswith("http"):
        return "<" + curie + ">"
    if ":" in curie:
        pre, _, local = curie.partition(":")
        return f"obo:{pre}_{local}"
    return None


def sign_abbr(s: Sign) -> str:
    return {Sign.PLUS: "pos", Sign.MINUS: "neg", Sign.UNKNOWN: "unk"}[s]


def nref(nid: str) -> str:
    """Full node IRI (angle-bracket form; always valid regardless of local-name rules)."""
    return f"<{BASE}node/{loc(nid)}>"


def emit(pm, quantitative_expressions=None) -> str:
    L: list[str] = []
    for p, u in PREFIXES.items():
        L.append(f"@prefix {p}: <{u}> .")
    L.append("")

    # ---- OWL ontology header + schema (TBox) --------------------------------
    L += [
        "physiomap: a owl:Ontology ;",
        '    dcterms:title "PhysioMap: a signed, multi-scale causal knowledge graph of human physiology" ;',
        '    dcterms:description "A causal knowledge graph of human physiology. Nodes are (entity, PATO quality, scale) variables; signed causal influences, process-output relations, and cross-scale constitution are represented as separate typed layers." ;',
        '    dcterms:license <https://creativecommons.org/licenses/by/4.0/> ;',
        "    rdfs:seeAlso <https://github.com/bio-ontology-research-group/physiomap> ,",
        "        <https://bio2vec.net/physiomap/> .",
        "",
        "# ---- schema (classes) ----",
        f'pmo:Variable a owl:Class ; rdfs:label "physiological variable" ; rdfs:subClassOf {SIO_ATTRIBUTE} ;',
        '    rdfs:comment "An (entity, PATO determinable-quality) pair borne at a biological scale (a concentration, rate, pressure, activity, and so on)." .',
        'pmo:CausalRelation a owl:Class ; rdfs:label "signed causal relation" ;',
        '    rdfs:comment "A reified interventional causal influence do(source)->delta(target), carrying its sign, evidence class, mechanism, and provenance." .',
        'pmo:ProductionRelation a owl:Class ; rdfs:label "production relation" ;',
        '    rdfs:comment "A typed process-output or consumption relation, distinct from both material constitution and an authored causal influence." .',
        'pmo:ConstitutiveRelation a owl:Class ; rdfs:label "constitutive relation" ;',
        '    rdfs:comment "A reified cross-scale aggregation or part-of determination; never a causal relation." .',
        'pmo:QuantitativeDefinition a owl:Class ; rdfs:label "quantitative definition" ;',
        '    rdfs:comment "A typed algebraic identity whose signed arguments are distinct from authored causal influences." .',
        'pmo:QuantitativeArgument a owl:Class ; rdfs:label "quantitative argument" .',
        '# multiplicative (gain) edges are SECOND-ORDER: they annotate a causal edge (see pmo:gainModulatedBy below), not a node.',
        "",
        "# ---- schema (properties) ----",
        'pmo:hasSource a owl:ObjectProperty ; rdfs:label "has source" ; rdfs:range pmo:Variable .',
        'pmo:hasTarget a owl:ObjectProperty ; rdfs:label "has target" ; rdfs:range pmo:Variable .',
        'pmo:hasResult a owl:ObjectProperty ; rdfs:label "has result" ; rdfs:range pmo:Variable .',
        'pmo:hasArgument a owl:ObjectProperty ; rdfs:label "has quantitative argument" ; rdfs:range pmo:QuantitativeArgument .',
        'pmo:hasVariable a owl:ObjectProperty ; rdfs:label "has argument variable" ; rdfs:range pmo:Variable .',
        'pmo:gainModulatedBy a owl:ObjectProperty ; rdfs:label "gain modulated by" ; rdfs:domain pmo:CausalRelation ; rdfs:range pmo:Variable ;',
        '    rdfs:comment "Second-order (multiplicative) relation attached to a causal edge: the modulator scales the strength (gain) of that edge. Its content is the mixed second derivative d2(target)/d(source)d(modulator), so it annotates the causal EDGE (triple), not a separate node." .',
        'pmo:gainSign a owl:DatatypeProperty ; rdfs:label "gain sign" ; rdfs:comment "Sign of d(gain)/d(modulator): + raises, - lowers the edge strength." .',
        'pmo:gainCanFlip a owl:DatatypeProperty ; rdfs:label "gain can flip sign" .',
        f'pmo:hasBearer a owl:ObjectProperty ; rdfs:label "has anatomical bearer" ; rdfs:subPropertyOf {RO_INHERES_IN} .',
        'pmo:constitutes a owl:ObjectProperty ; rdfs:label "constitutes" ;',
        '    rdfs:comment "A finer-scale variable helps determine a coarser-scale variable (constitutive, not causal)." .',
        'pmo:produces a owl:ObjectProperty ; rdfs:label "produces or consumes" ;',
        '    rdfs:comment "A signed process-output relation; a negative sign denotes consumption or removal." .',
        "pmo:constitutesByAggregation rdfs:subPropertyOf pmo:constitutes .",
        "pmo:constitutesByPartOfDetermination rdfs:subPropertyOf pmo:constitutes .",
        'pmo:sign a owl:DatatypeProperty ; rdfs:label "sign" ; rdfs:comment "+ / - / ? : the direction of the interventional (or gain/determination) effect." .',
        'pmo:scale a owl:DatatypeProperty ; rdfs:label "biological scale" .',
        'pmo:causalEvidence a owl:DatatypeProperty ; rdfs:label "causal-evidence class" ; rdfs:comment "Controlled vocabulary (perturbation, pharmacological, genetic_lof_gof, mendelian_randomization, mechanistic_model, curated_mechanistic) establishing the interventional claim." .',
        'pmo:productionEvidence a owl:DatatypeProperty ; rdfs:label "production-evidence class" .',
        'pmo:quantitativeKind a owl:DatatypeProperty ; rdfs:label "quantitative-expression kind" .',
        'pmo:expressionOrigin a owl:DatatypeProperty ; rdfs:label "expression origin" .',
        'pmo:argumentRole a owl:DatatypeProperty ; rdfs:label "quantitative argument role" .',
        'pmo:derivativeSign a owl:DatatypeProperty ; rdfs:label "partial-derivative sign" .',
        'pmo:mechanism a owl:DatatypeProperty ; rdfs:label "mechanism" .',
        'pmo:definitional a owl:DatatypeProperty ; rdfs:label "definitional (algebraic identity) edge" .',
        "",
        "# ==== data (ABox) ====",
        "",
    ]

    # ---- nodes --------------------------------------------------------------
    for n in pm.nodes:
        s = nref(n.id)
        types = ["pmo:Variable"]
        q = curie_to_obo(n.quality_iri)
        if q:
            types.append(q)  # the variable IS an instance of its PATO determinable quality
        L.append(f"{s} a {', '.join(types)} ;")
        L.append(f"    rdfs:label {lit(n.label)} ;")
        L.append(f"    pmo:scale {lit(n.scale.value)}")
        ent = curie_to_obo(n.entity_iri)
        if ent:
            L.append(f"    ; {RO_INHERES_IN} {ent} ; {SIO_IS_ATTR_OF} {ent}")
        bearer = curie_to_obo(n.bearer_entity_iri)
        if bearer:
            L.append(f"    ; pmo:hasBearer {bearer}")
        L.append("    .")

    L.append("")
    # ---- causal edges -------------------------------------------------------
    by_influence_id: dict[str, str] = {}
    for e in pm.causal_edges:
        rel = SIGN_REL[e.sign]
        src, tgt = nref(e.source), nref(e.target)
        eid = f"<{BASE}edge/causal/{loc(e.id or '')}>"
        by_influence_id[e.id or ""] = eid
        # direct signed triple (RO)
        L.append(f"{src} {rel} {tgt} .")
        # reified relation carrying identity + metadata
        L.append(f"{eid} a pmo:CausalRelation ; pmo:hasSource {src} ; pmo:hasTarget {tgt} ; pmo:sign {lit(e.sign.value)}")
        if e.causal_evidence:
            L.append(f"    ; pmo:causalEvidence {lit(e.causal_evidence.value)}")
        if e.evidence:
            L.append(f"    ; dcterms:source {lit(e.evidence)}")
        if e.mechanism:
            L.append(f"    ; pmo:mechanism {lit(e.mechanism)}")
        if e.context:
            L.append(
                f"    ; pmo:contextId {lit(e.context.id)} ; "
                f"pmo:contextLabel {lit(e.context.label)}"
            )
        if e.definitional:
            L.append('    ; pmo:definitional "true"^^xsd:boolean')
        L.append("    .")

    L.append("")
    # ---- production/process-output relations -------------------------------
    for i, edge in enumerate(pm.production_edges):
        source, target = nref(edge.source), nref(edge.target)
        pid = f"<{BASE}edge/production/{i}>"
        L.append(f"{source} pmo:produces {target} .")
        L.append(
            f"{pid} a pmo:ProductionRelation ; pmo:hasSource {source} ; "
            f"pmo:hasTarget {target} ; pmo:sign {lit(edge.sign.value)} ; "
            f"pmo:productionEvidence {lit(edge.production_evidence.value)}"
        )
        if edge.evidence:
            L.append(f"    ; dcterms:source {lit(edge.evidence)}")
        if edge.mechanism:
            L.append(f"    ; pmo:mechanism {lit(edge.mechanism)}")
        L.append("    .")

    L.append("")
    # ---- constitutive edges -------------------------------------------------
    REL_ABBR = {"aggregation": "constitutesByAggregation"}
    for i, c in enumerate(pm.constitutive_edges):
        micro, macro = nref(c.micro), nref(c.macro)
        sub = REL_ABBR.get(c.relation, "constitutesByPartOfDetermination")
        L.append(f"{micro} pmo:{sub} {macro} .")
        if c.relation == "aggregation":
            L.append(f"{macro} {BFO_HAS_PART} {micro} .")
        elif "part_of" in c.relation:
            L.append(f"{micro} {BFO_PART_OF} {macro} .")
        cid = f"<{BASE}edge/constitutive/{i}>"
        L.append(f"{cid} a pmo:ConstitutiveRelation ; pmo:hasSource {micro} ; pmo:hasTarget {macro} ; pmo:sign {lit(c.sign.value)} ; rdfs:label {lit(c.relation)} .")

    L.append("")
    # ---- typed quantitative definitions -------------------------------------
    expressions = (
        list(quantitative_expressions)
        if quantitative_expressions is not None
        else list(pm.quantitative_definitions)
    )
    for i, definition in enumerate(expressions):
        local_id = getattr(definition, "id", f"definition-{i}")
        qid = f"<{BASE}quantitative/{loc(local_id)}>"
        origin = getattr(definition, "origin", "authored")
        argument_ids = [
            f"<{BASE}quantitative/{loc(local_id)}/argument/{j}>"
            for j in range(len(definition.arguments))
        ]
        L.append(
            f"{qid} a pmo:QuantitativeDefinition ; "
            f"pmo:hasResult {nref(definition.result)} ; "
            f"pmo:quantitativeKind {lit(definition.kind)} ; "
            f"pmo:expressionOrigin {lit(origin)}"
        )
        if definition.evidence:
            L.append(f"    ; dcterms:source {lit(definition.evidence)}")
        if definition.mechanism:
            L.append(f"    ; pmo:mechanism {lit(definition.mechanism)}")
        for aid in argument_ids:
            L.append(f"    ; pmo:hasArgument {aid}")
        L.append("    .")
        for aid, argument in zip(argument_ids, definition.arguments, strict=True):
            derivative_sign = getattr(
                argument.derivative_sign, "value", argument.derivative_sign
            )
            L.append(
                f"{aid} a pmo:QuantitativeArgument ; "
                f"pmo:hasVariable {nref(argument.node)} ; "
                f"pmo:argumentRole {lit(argument.role)} ; "
                f"pmo:derivativeSign {lit(derivative_sign)} ."
            )

    L.append("")
    # ---- modulation (gain, second-order) edges ------------------------------
    # A multiplicative edge is a statement ABOUT a causal edge (its gain), so it attaches to the
    # causal EDGE resource (the triple), not a separate node.
    for mo in pm.modulation_edges:
        edge_iri = by_influence_id.get(mo.influence_id or "")
        if not edge_iri:
            continue  # the model validator guarantees the modulated causal edge exists
        extra = ' ; pmo:gainCanFlip "true"^^xsd:boolean' if mo.can_flip_sign else ""
        L.append(f"{edge_iri} pmo:gainModulatedBy {nref(mo.modulator)} ; pmo:gainSign {lit(mo.sign.value)}{extra} .")

    return "\n".join(L) + "\n"


def main() -> int:
    scm = ScmManifest.from_json(canonical_scm_path())
    pm = scm.to_physiomap()
    OUT.parent.mkdir(exist_ok=True)
    ttl = emit(pm, scm.quantitative_expressions)
    OUT.write_text(ttl, encoding="utf-8")
    print(f"wrote {OUT} ({len(ttl):,} bytes)")
    print(f"  {len(pm.nodes)} variables, {len(pm.causal_edges)} causal, "
          f"{len(pm.production_edges)} production, {len(pm.constitutive_edges)} constitutive, "
          f"{len(scm.quantitative_expressions)} quantitative, "
          f"{len(pm.modulation_edges)} modulation edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
