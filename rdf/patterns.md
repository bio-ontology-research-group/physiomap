# PhysioMap modelling patterns

The RDF/OWL representation ([`physiomap.ttl`](physiomap.ttl)) is built from a small, fixed set of
**modelling patterns**. Each pattern names the intent, the triple template, the reused vocabulary
(OBO Relation Ontology / BFO / PATO and the Semanticscience Integrated Ontology, SIO, as the upper
ontology), and the SHACL shape in [`shapes.ttl`](shapes.ttl) that machine-checks conformance.

Prefixes: `pmv:` `…/node/`, `pme:` `…/edge/`, `pmo:` `…/ontology#`, `obo:` `purl.obolibrary.org/obo/`,
`sio:` `semanticscience.org/resource/`.

---

## P1 — Physiological variable (entity–quality pattern)

**Intent.** A node is a physiological variable: a PATO determinable quality borne by an OBO entity
at a biological scale (a concentration, rate, pressure, activity…).

```turtle
pmv:plasma_glucose_concentration
    a pmo:Variable, obo:PATO_0000033 ;          # the PATO quality (concentration)
    rdfs:label "plasma glucose concentration" ;
    pmo:scale "organ_system" ;
    obo:RO_0000052 obo:CHEBI_17234 ;            # inheres in glucose            (BFO/RO)
    sio:SIO_000011 obo:CHEBI_17234 .            # is attribute of glucose       (SIO)
```

**SIO alignment.** `pmo:Variable rdfs:subClassOf sio:SIO_000614` (*attribute*); the variable
`sio:SIO_000011` (*is attribute of*) its entity. **OBO alignment.** the variable is typed as its
PATO quality and `RO:0000052` (*inheres in*) its entity; an optional anatomical bearer uses
`pmo:hasBearer ⊑ RO:0000052`. **Shape:** `pmo:VariableShape`.

## P2 — Signed causal relation (first-order, rung 2)

**Intent.** A within-scale interventional edge `do(source) → Δtarget`, carrying a *sign* (direction
of effect) and provenance. Represented twice: a **direct signed triple** (for reasoning/SPARQL) and
a **reified edge resource with its own IRI** (so the relation is a first-class, citable, annotatable
object).

```turtle
pmv:hfe_activity obo:RO_0002305 pmv:plasma_hepcidin_concentration .   # neg: causally upstream of, negative effect

<…/edge/causal/hfe_activity--neg--plasma_hepcidin_concentration>
    a pmo:CausalRelation ;
    pmo:hasSource pmv:hfe_activity ; pmo:hasTarget pmv:plasma_hepcidin_concentration ;
    pmo:sign "-" ;
    pmo:causalEvidence "genetic_lof_gof" ;                            # P5
    dcterms:source "…provenance / PMID…" ;                           # P5
    pmo:mechanism "…" .
```

**Vocabulary.** `RO:0002304` (*causally upstream of, positive effect*), `RO:0002305` (*negative
effect*), `RO:0002411` (*causally upstream of*, for an undetermined `?` sign). **Shape:**
`pmo:CausalRelationShape`.

## P3 — Constitutive (cross-scale) relation

**Intent.** A finer-scale variable helps *determine* a coarser-scale variable. This is
**constitution, not causation**, and is never traversed by causal reasoning; the meta-graph of
scales stays acyclic.

```turtle
pmv:beta_cell_insulin_secretion_rate pmo:constitutesByProduction pmv:plasma_insulin_concentration .
# aggregation additionally asserts obo:BFO_0000051 (has part); part_of+determination asserts obo:BFO_0000050 (part of)

<…/edge/constitutive/12>
    a pmo:ConstitutiveRelation ;
    pmo:hasSource pmv:beta_cell_insulin_secretion_rate ;
    pmo:hasTarget pmv:plasma_insulin_concentration ;
    pmo:sign "+" ; rdfs:label "production" .
```

**Vocabulary.** `pmo:constitutes` with sub-properties `constitutesByProduction` /
`constitutesByAggregation` / `constitutesByPartOfDetermination`; `BFO:0000050`/`0000051`. **Shape:**
`pmo:ConstitutiveRelationShape`.

## P4 — Second-order (gain / multiplicative) relation — attaches to a triple, not a node

**Intent (the critical pattern).** A multiplicative edge says a *modulator* scales the **strength**
of a causal edge. Its content is the mixed second derivative
`∂²target / ∂source ∂modulator` — it is a statement **about a causal edge**, so it must attach to
the causal **edge (triple)**, never appear as a peer node in the graph.

```turtle
# gain annotates the causal EDGE resource of P2 (edge-level reification):
<…/edge/causal/baroreflex_sympathetic_outflow--pos--heart_rate>
    pmo:gainModulatedBy pmv:cardiac_beta1_adrenergic_chronotropic_responsiveness ;
    pmo:gainSign "+" .

# RDF-star equivalent (for stores that support it):
# << pmv:baroreflex_sympathetic_outflow obo:RO_0002304 pmv:heart_rate >>
#     pmo:gainModulatedBy pmv:cardiac_beta1_adrenergic_chronotropic_responsiveness ; pmo:gainSign "+" .
```

The canonical file uses edge-level reification (`pmo:gainModulatedBy` on the causal-edge resource)
for universal tooling compatibility; the RDF-star form is the semantically identical modern
serialization. **Vocabulary.** `pmo:gainModulatedBy` (domain `pmo:CausalRelation`), `pmo:gainSign`,
`pmo:gainCanFlip`. **Shape:** `pmo:GainAnnotationShape`.

## P5 — Interventional evidence & provenance

**Intent.** Every causal relation records the interventional-evidence class that admits it (the
causal-evidence gate) and a provenance string. This is what makes the graph a *causal* KG rather
than an association network.

```turtle
<…/edge/causal/…> pmo:causalEvidence "pharmacological" ; dcterms:source "…citation…" .
```

**Admissible classes** (controlled vocabulary): `perturbation`, `pharmacological`,
`genetic_lof_gof`, `mendelian_randomization`, `mechanistic_model`, `curated_mechanistic`.
Associational classes (`binding_only`, `coexpression`, `observational_association`) are rejected at
curation and never appear. **Shape:** carried by `pmo:CausalRelationShape`.
