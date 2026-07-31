# Causal / mechanistic biomedical knowledge graphs — curated library

**Theme:** How causal edges are *represented, extracted, typed, evidenced, and reasoned over* at scale in
biomedical knowledge graphs (KGs), and what PhysioMap should borrow for its `CausalEdge`
(mechanism + evidence/provenance fields), node typing (entity + PATO quality + ontology IRIs), and
qualitative cyclic causal reasoning.

**Curator honesty note.** Every paper below was downloaded as a verified PDF (`%PDF` magic, size
> 30 KB) and *read* via the Read tool over the page ranges noted in each entry. No abstracts were
fabricated; nothing here is a paywalled stub (all 9 targets turned out to be obtainable open-access /
free full text). Page counts are the pages actually read, not the whole article.

---

## (a) Overview

PhysioMap is, structurally, a *signed, cyclic, ontology-typed causal knowledge graph of physiology*: nodes
are `(entity, PATO quality)` pairs with optional Uberon/GO/CL/ChEBI/PATO IRIs; within-scale edges are
signed (`+/-/?`) interventionist causal edges abbreviating a `quality→disposition→process→quality`
mechanism, carrying an optional mechanism ref + evidence/provenance, and may form cycles; cross-scale
edges are constitutive (`part_of` + determination), never causal. That places PhysioMap squarely in the
design space mapped by this literature. The nine papers fall into four functional groups:

1. **Causal-edge representation formalisms** — GO-CAM (activity units linked by signed RO causal
   relations, ECO evidence), INDRA (typed mechanistic Statements + Agents + Evidence + belief), BEL/PyBEL
   (`increases`/`decreases`/`directlyIncreases` causal+correlative relations with full provenance).
   These are the most directly relevant: they show *exactly* how a signed causal edge with a mechanism
   reference and evidence object is modeled.
2. **Schema / typing standards** — Biolink Model (Association = subject–predicate–object core triple +
   provenance/evidence metadata; predicate hierarchy under `related_to` incl. `positively_regulates` /
   `negatively_regulates` / `causes`; `id_prefixes` pin each class to community ontologies). This is a
   ready-made template for typing PhysioMap nodes and edges.
3. **Integrative KGs (typed multi-relational graphs at scale)** — Hetionet (metagraph of 11 node / 24 edge
   types, signed up/down-regulation edges, edge provenance + confidence, metapath reasoning), PrimeKG
   (10 biological scales, ontology-grounded nodes, signed `+/-` disease–phenotype edges, indications /
   contradictions / off-label drug–disease edges, per-node text descriptors), Santos CKG (Neo4j property
   graph, 36 node / 47 relation types, `Publication` nodes = literature provenance).
4. **Extraction + reasoning survey** — Kilicoglu SemMedDB/SemRep (PubMed-scale subject–predicate–object
   predications, UMLS-grounded, explicit causal predicates with per-predicate precision/recall),
   Nicholson & Greene review (rule-based / distant-supervision / supervised relation extraction;
   KG embedding — matrix factorization, TransE-style translational models, node2vec — for link prediction,
   and their limits w.r.t. edge type/direction).

Across all of them the recurring, transferable design pattern is: **a typed (subject, predicate, object)
causal triple, where the predicate carries a sign/direction, the subject/object are grounded in
community ontology IRIs, and a separate evidence/provenance object (source DB or PMID + supporting text +
evidence-type code + optional confidence/belief) hangs off the edge — with the explicit acknowledgement
that the knowledge is incomplete and may be contradictory.**

---

## (b) Per-paper entries

### 1. INDRA — Gyori, Bachman et al. 2017
- **Citation:** Gyori BM, Bachman JA, Subramanian K, Muhlich JL, Galescu L, Sorger PK. *From word models
  to executable models of signaling networks using automated assembly.* Mol Syst Biol. 2017;13(11):954.
  DOI:10.15252/msb.20177651. PMC5731347.
- **File:** `Gyori2017_INDRA.pdf` (26 pp; read pp. 1–12).
- INDRA's central object is the **Statement** — a typed mechanistic assertion (Phosphorylation, Activation,
  Inhibition, IncreaseAmount, DecreaseAmount, …) over **Agent**s. Statements are *signed and directional*:
  the p53 case study encodes literal word models "X **activates** Y" / "X **inactivates** Y" (Fig 5), i.e.
  + and − causal edges, and these models **form feedback cycles** (Mdm2/Wip1/p53 negative feedback giving
  sustained vs. oscillatory dynamics). Agents are **grounded** to HGNC/UniProt/ChEBI/GO/HMDB IRIs.
- Each Statement carries one or more **Evidence** objects: `source_api` (TRIPS/REACH/BEL/BioPAX), supporting
  `text`, `citation` (PMID), `annotations`, and **epistemics** (assertion vs. hypothesis). INDRA assigns a
  **belief score** aggregating multiple evidences (provenance → confidence). Statements are deliberately
  *underspecified* ("don't know, don't write" / leave fields blank), and are grounded to the Systems
  Biology Ontology (SBO) for participant roles.
- Same Statement is recoverable from NL, BEL (`directlyIncreases`) and BioPAX — i.e. a normalized
  causal-edge schema that ingests heterogeneous sources. Assembly into ODE/rule models is a *separate*
  step; curation of mechanism is decoupled from executable implementation.
- **Relevance to PhysioMap:** The single strongest model for the **evidence/provenance field**: copy the
  Evidence object (source, supporting text, PMID, epistemics) + a **belief/confidence aggregate** over
  multiple evidences. The activates/inactivates duality is exactly PhysioMap's `+/-`; INDRA's explicit
  handling of negative-feedback cycles and the warning that *phrasing/structure changes net dynamics*
  reinforces PhysioMap's choice not to forward-propagate signs through loops. "Don't know, don't write" =
  PhysioMap's `?` / blank-field discipline. Decoupling curation from execution mirrors PhysioMap's
  qualitative-map-vs-ODE separation.

### 2. Hetionet / Project Rephetio — Himmelstein, Baranzini et al. 2017
- **Citation:** Himmelstein DS, Lizee A, Hessler C, et al. *Systematic integration of biomedical knowledge
  prioritizes drugs for repurposing.* eLife. 2017;6:e26726. DOI:10.7554/eLife.26726. PMC5640425.
- **File:** `Himmelstein2017_Hetionet.pdf` (35 pp; read pp. 1–6).
- A **hetnet**: a typed multigraph with a **metagraph schema** — 11 *metanodes* (Anatomy, Gene, BiologicalProcess,
  MolecularFunction, CellularComponent, Pathway, Compound, Disease, …) and **24 *metaedges*** written as
  subject–verb–object: `Compound–downregulates–Gene`, `Anatomy–upregulates–Gene`, `Disease–downregulates–Gene`,
  `Compound–treats–Disease`, etc. Signed up/down-regulation is encoded *in the edge type*. Only
  `Gene–regulates–Gene` is directed; the rest are undirected by design.
- Edges carry attributes including **source databases, license, and confidence scores**, and reference the
  **PMIDs** the relationship was compiled from (provenance as an edge attribute). Distributed as Neo4j +
  JSON + TSV.
- Reasoning is by **metapaths** (typed paths, e.g. Compound–binds–Gene–associates–Disease) scored by the
  degree-weighted path count (DWPC); a permutation null isolates genuine edge-type signal. Typed paths
  *correspond to mechanisms of efficacy*.
- **Relevance to PhysioMap:** The metagraph is a template for a **typed edge ontology** — encode the sign in
  the predicate vocabulary (`upregulates`/`downregulates` ≈ `+`/`-`). Edge-level `sources`/`license`/
  `confidence`/PMID is exactly the provenance bundle PhysioMap's `evidence` field should hold. Metapath
  reasoning over the *condensation of typed edges* is conceptually adjacent to PhysioMap's reasoning over
  the SCC condensation, and DWPC shows how to weight multi-path evidence.

### 3. PyBEL / Biological Expression Language — Hoyt, Konotopez, Ebeling 2018
- **Citation:** Hoyt CT, Konotopez A, Ebeling C. *PyBEL: a computational framework for Biological Expression
  Language.* Bioinformatics. 2018;34(4):703–704. DOI:10.1093/bioinformatics/btx660. PMC5860616.
- **File:** `Hoyt2018_PyBEL.pdf` (2 pp; read in full).
- BEL "assembles **qualitative causal and correlative relations** between biological entities **across
  multiple modes and scales**, with full provenance information including namespace references, relation
  provenance (citation and evidence), and biological context-specific relation metadata (anatomy, cell,
  disease)." Causal predicates: `increases`, `decreases`, `directlyIncreases`, `directlyDecreases` (signed,
  direct vs. indirect). PyBEL realizes a BEL network as a **directed multigraph** (extends NetworkX
  MultiDiGraph); subjects/objects validated against namespace/ontology references; supports **Reverse Causal
  Reasoning** (infer upstream regulator state from downstream expression).
- BEL `SET`-statement annotations attach **context** (organism, disease, cell, anatomy) to each relation —
  i.e. relation-scoped provenance + context, not just node attributes. Trend noted toward OWL namespaces.
- **Relevance to PhysioMap:** BEL is the closest *qualitative, multi-scale, signed-causal* prior art to
  PhysioMap and explicitly separates **direct vs. indirect** causal links (cf. PhysioMap's
  edge-abbreviates-mechanism). Adopt BEL's pattern of **relation-scoped context+provenance** (citation,
  evidence text, anatomical/cell/disease context) as fields on `CausalEdge`. The directed-multigraph
  realization and Reverse Causal Reasoning (reasoning *backward* along signed edges) are directly relevant
  to PhysioMap's interventionist semantics.

### 4. SemMedDB / SemRep — Kilicoglu, Shin, Fiszman, Rosemblat, Rindflesch 2012
- **Citation:** Kilicoglu H, Shin D, Fiszman M, Rosemblat G, Rindflesch TC. *SemMedDB: a PubMed-scale
  repository of biomedical semantic predications.* Bioinformatics. 2012;28(23):3158–3160.
  DOI:10.1093/bioinformatics/bts591. PMC3509487.
- **File:** `Kilicoglu2012_SemMedDB.pdf` (3 pp; read in full).
- **Semantic predications** = subject–predicate–object triples extracted from *all* PubMed titles+abstracts by
  SemRep (rule-based semantic interpreter). Subject/object are **UMLS Metathesaurus concepts**; predicate is
  one of ~30 types in an extended UMLS semantic network. **Causal/influence predicates** include `CAUSES`,
  `PREDISPOSES`, `STIMULATES`, `INHIBITS`, `AFFECTS`, `AUGMENTS`, `DISRUPTS`, `INTERACTS_WITH`. ~57.6M
  predications from 21M citations.
- Provenance is the **source sentence + PMID** (SENTENCE_PREDICATION table). Extraction quality is
  **reported per relation class** as precision/recall (e.g. gene–disease 76% P; pharmacogenomics 73% P /
  55% R) — i.e. confidence is predicate-type-specific.
- **Relevance to PhysioMap:** The canonical *causal-relation-extraction* resource and a source of candidate
  PhysioMap edges (CAUSES/STIMULATES/INHIBITS ≈ signed causal links). Two lessons: (i) ground subject/object
  to a controlled vocabulary (UMLS there ↔ Uberon/GO/CL/ChEBI/PATO here); (ii) record provenance as
  *source-sentence + citation*, and treat extraction confidence as **predicate-specific** — useful for a
  per-edge confidence/quality field and for honest `?` flagging when extraction precision is low.

### 5. Biolink Model — Unni, Moxon et al. 2022
- **Citation:** Unni DR, Moxon SAT, Bada M, et al. *Biolink Model: A universal schema for knowledge graphs in
  clinical, biomedical, and translational science.* Clin Transl Sci. 2022;15(8):1848–1855.
  DOI:10.1111/cts.13302. (arXiv:2203.13906, read).
- **File:** `Unni2022_Biolink.pdf` (12 pp; read pp. 1–7).
- The model's unit is the **Association** = a *core triple* (subject Class — predicate — object Class) **plus
  metadata slots**, "primarily information about the **provenance and evidence** supporting the assertion"
  (`has_evidence`, `publications`). Classes (Gene, Disease, Chemical, AnatomicalStructure, Phenotype, …) form
  a hierarchy; **predicates form a hierarchy descending from `related_to`**, including
  `positively_regulates`, `negatively_regulates`, `entity_regulates_entity`, `affects`, `causes`,
  `genetically_interacts_with` — so **sign and causal direction are first-class, hierarchical predicate
  semantics** (query at any granularity). Classes carry **`id_prefixes`** specifying the preferred ontology
  (Mondo, HGNC, ChEBI, HPO, UBERON…) → ontology typing baked in. Distributed via LinkML in YAML/JSON-Schema/
  SQL-DDL/Python/RDF; an Association is **equivalent to an OWL Axiom / `rdf:Statement`**.
- **Relevance to PhysioMap:** The most reusable *schema blueprint*. PhysioMap's `CausalEdge` ≈ a Biolink
  Association: subject/object = `(entity, quality)` nodes with `id_prefixes`-style ontology pinning;
  predicate from a small signed-causal hierarchy (positively/negatively_regulates ↔ `+`/`-`, a generic
  `regulates`/`affects` ↔ `?`); evidence/provenance carried as Association metadata. The Association ≡ OWL
  Axiom equivalence is the bridge to PhysioMap's planned OWL reasoning phase. Hierarchical predicates let
  PhysioMap reason at the abstract `regulates` level when the sign is unknown.

### 6. GO-CAM — Thomas, Hill, Mi et al. 2019
- **Citation:** Thomas PD, Hill DP, Mi H, et al. *Gene Ontology Causal Activity Modeling (GO-CAM) moves
  beyond GO annotations to structured descriptions of biological functions and systems.* Nat Genet.
  2019;51:1429–1433. DOI:10.1038/s41588-019-0500-1. (OSTI 1581368 full text, read).
- **File:** `Thomas2019_GOCAM.pdf` (15 pp; read pp. 1–8).
- The **closest conceptual analog to PhysioMap.** Unit = an **activity unit**: a GO *molecular function*
  (`enabled_by` a gene product) occurring in a *cellular component* **location**, *part_of* a *biological
  process* **program** — i.e. a multi-aspect, ontology-typed node, much like PhysioMap's `(entity, quality)`
  with scale. Activity units are linked by **causal relations drawn from the Relations Ontology (RO)**:
  `directly positively regulates`, `directly negatively regulates`, `positively/negatively regulates`,
  `causally upstream of` — **causal relations carry a positive or negative direction of effect**, and chains
  of them build **causal pathways of arbitrary size and branching** (Wnt signaling example, with feedback
  via beta-catenin destruction). "Direct" relations mean regulation via direct physical interaction.
- Every triple is **supported by evidence using the Evidence and Conclusion Ontology (ECO)**; a triple may
  have **multiple evidences**; **contradictory / alternative models are allowed to coexist** and be revised
  as evidence accrues. GO-CAM is explicitly a framework for **qualitative, causal models** that *omits
  stoichiometry and kinetics*. Formally expressed in **RDF/OWL**; curated in Noctua; exportable to SIF
  (lossy) for network tools.
- **Relevance to PhysioMap:** Adopt GO-CAM almost wholesale as the causal-edge template: (i) **typed,
  ontology-grounded activity-like nodes** (function/process/location ↔ entity/quality/scale); (ii) **signed
  causal predicates from RO** (`directly_positively_regulates`/`directly_negatively_regulates`/
  `causally_upstream_of, positive/negative effect`) as the controlled vocabulary for PhysioMap's `+/-` —
  these are the exact IRIs to put in the `mechanism`/predicate slot; (iii) **ECO evidence codes** for the
  evidence field; (iv) the principle that **qualitative causal models legitimately omit kinetics** and that
  **incomplete/contradictory knowledge is first-class** (PhysioMap's `?`). GO-CAM's RO causal-relation set
  and ECO are the concrete ontologies PhysioMap should reuse.

### 7. PrimeKG — Chandak, Huang, Zitnik 2023
- **Citation:** Chandak P, Huang K, Zitnik M. *Building a knowledge graph to enable precision medicine.* Sci
  Data. 2023;10:67. DOI:10.1038/s41597-023-01960-3. PMC9893183.
- **File:** `Chandak2023_PrimeKG.pdf` (16 pp; read pp. 1–5).
- A multimodal KG over **ten biological scales** (~129k nodes, ~4M relationships) with node types Disease,
  Protein/Gene, Drug, Phenotype, Anatomy, BiologicalProcess, MolecularFunction, CellularComponent, Pathway,
  Exposure — each **grounded in a community ontology** (MONDO, GO, **UBERON** for anatomy, HPO, Reactome,
  DrugBank, UMLS). Relations include **signed `+/-` disease–phenotype associations**, and notably rich
  **drug–disease edges typed as `indication` / `contraindication` / `off-label`** (sign/polarity of a
  therapeutic relationship). Each disease/drug node is augmented with **free-text descriptors** (Mayo Clinic /
  DrugCentral) for multimodal use.
- Construction = per-source parsers + ID harmonization (e.g. UniProt→HGNC) to map heterogeneous resources
  onto typed nodes/edges; explicitly motivated by *ontology heterogeneity* and *disease entity resolution*.
- **Relevance to PhysioMap:** Demonstrates **cross-scale, ontology-typed node design at scale** with the
  same ontologies PhysioMap targets (UBERON anatomy, GO process/function, HPO phenotype). The signed `+/-`
  associations and polarized indication/contradiction edges validate encoding **sign in the edge type**. The
  per-node text descriptors suggest a (entity, quality) node could also carry a human-readable description.
  ID-harmonization machinery is the practical answer to PhysioMap's "optional IRIs from multiple ontologies."

### 8. Clinical Knowledge Graph (CKG) — Santos, Colaço et al. 2022
- **Citation:** Santos A, Colaço AR, Nielsen AB, et al. *A knowledge graph to interpret clinical proteomics
  data.* Nat Biotechnol. 2022;40:692–702. DOI:10.1038/s41587-021-01145-6. PMC9110295.
- **File:** `Santos2022_CKG.pdf` (17 pp; read pp. 1–4).
- A **Neo4j property graph**: ~20M nodes / 220M relationships, **36 node labels and 47 relationship types**
  (HAS_PARENT, ASSOCIATED_WITH, ACTS_ON, CURATED_TARGETS, CURATED_AFFECTS_INTERACTION_WITH,
  HAS_QUANTIFIED_PROTEIN, MENTIONED_IN_PUBLICATION, …). Built by **per-resource parsers with config files
  that specify how each ontology/DB is interpreted** into nodes/relations. Over 50M relationships involve
  **`Publication` nodes** linking statements to **PMIDs** (provenance as a first-class node), populated from
  NER over ~7M abstracts/full-texts. Edge attributes include **FC (fold change)** and **Src (source)**.
  Supports graph algorithms (NetworkX/Neo4j) and **graph representation learning for link prediction**.
- **Relevance to PhysioMap:** A worked **property-graph + provenance** engineering pattern: provenance modeled
  *both* as edge attributes (Src) *and* as dedicated `Publication`/PMID nodes — PhysioMap can do the same for
  `evidence` (lightweight inline ref + optional first-class evidence node). The parser-config approach to
  ontology mapping is reusable for ingesting legacy MSPML/RAAS fixtures. Confirms link-prediction over a
  typed causal graph as a downstream reasoning mode.

### 9. Constructing knowledge graphs and their biomedical applications — Nicholson & Greene 2020
- **Citation:** Nicholson DN, Greene CS. *Constructing knowledge graphs and their biomedical applications.*
  Comput Struct Biotechnol J. 2020;18:1414–1428. DOI:10.1016/j.csbj.2020.05.017. PMC7327409.
- **File:** `NicholsonGreene2020_KGreview.pdf` (15 pp; read pp. 1–4, 6–9).
- A **review** covering (a) KG construction — manual curation vs. text mining; relation-extraction methods:
  **rule-based** (grammatical/dependency-parse patterns), **distant/weak supervision** (DB-mention pairs as
  noisy labels), **supervised** (CNN/LSTM); notes the recall–precision tradeoff (manual = high precision/low
  recall; automated = scalable but noisier). (b) **Representational learning for reasoning** — matrix
  factorization (SVD/Laplacian), **translational distance models (TransE/TransH:** `h + r ≈ t`), neural
  (node2vec/DeepWalk/autoencoders/graph-attention) — used for **link prediction / node classification** in
  drug repurposing, drug–drug interaction, gene–disease, patient diagnosis.
- **Key caveats it flags (directly load-bearing for PhysioMap):** baseline embeddings "**ignore information
  such as edge type and node type**"; TransE "**forces relationships to be a one-to-one mapping, which may
  not be appropriate for all relationship types**"; future models *should incorporate edge confidence
  scores, textual info, and edge-type information.* It also notes most KGs treat edges as **mostly
  unidirectional but some bidirectional** (treats vs. resembles).
- **Relevance to PhysioMap:** The map of the whole field. It tells PhysioMap (i) where its curated edges can
  come from (rule-based/distant-supervision over SemMedDB-style triples) and the *honesty* implication of
  predicate-specific extraction noise; (ii) a clear warning that **off-the-shelf KG embeddings flatten edge
  sign/type/direction and cyclic structure** — so PhysioMap's reasoning must stay *symbolic/qualitative*
  (σ-separation + sign-solvability) rather than naive embedding, and any future embedding must be
  type/sign/direction-aware. Reuse its taxonomy when documenting PhysioMap's provenance/extraction pipeline.

---

## (c) Synthesis & relevance to PhysioMap

**What to borrow for the `CausalEdge` (mechanism + evidence/provenance), node typing, and reasoning:**

1. **Model the edge as a typed triple, not a bare arrow.** Every formalism here (GO-CAM, INDRA, BEL,
   Biolink, Hetionet, SemMedDB, CKG) represents a causal edge as `(subject, predicate, object)` where the
   **predicate is a named relation from a controlled vocabulary**. PhysioMap's `+/-/?` should be backed by an
   explicit predicate IRI, not just a glyph.

2. **Put the sign *in* the predicate, drawn from the Relations Ontology, and make predicates hierarchical.**
   GO-CAM's RO relations (`directly_positively_regulates`, `directly_negatively_regulates`,
   `causally_upstream_of {positive,negative} effect`) and Biolink's `positively_regulates` /
   `negatively_regulates` under a generic `regulates`/`related_to` are the exact vocabulary. Map: `+` →
   `…positively_regulates`, `-` → `…negatively_regulates`, `?` → generic `regulates`/`affects`. The
   hierarchy lets PhysioMap reason at the unsigned `regulates` level when the sign is genuinely `?`.

3. **Direct vs. indirect is a real distinction PhysioMap already needs.** BEL (`increases` vs.
   `directlyIncreases`) and GO-CAM ("direct" = via physical interaction) both separate a one-step mechanism
   from an abbreviated multi-step path. This *is* PhysioMap's "edge abbreviates a
   `quality→disposition→process→quality` mechanism" — record a flag/relation for whether the edge is direct or
   a mechanism-collapsing shortcut, and let the `mechanism` ref point at the collapsed process (a GO process
   IRI, as in PhysioMap's RAAS GO-term fixtures).

4. **Make evidence/provenance a structured object on the edge, with multiple evidences and a confidence
   aggregate.** Converging best practice: INDRA Evidence (source_api, supporting text, PMID, epistemics) +
   **belief score**; GO-CAM (multiple **ECO** evidence codes per triple); Hetionet (sources, license,
   confidence, PMIDs as edge attributes); BEL (citation + evidence text + anatomy/cell/disease context);
   CKG (`Publication`/PMID provenance + `Src`). PhysioMap's `evidence` field should hold a *list* of
   `{source, supporting_text, citation(PMID/DOI), evidence_code(ECO), context}` plus an optional aggregate
   **confidence/belief**. Provenance can be inline *and/or* a first-class evidence node (CKG pattern).

5. **Ground every node in community ontologies and harmonize IDs.** Biolink `id_prefixes`, PrimeKG
   (MONDO/GO/UBERON/HPO/DrugBank), CKG parser-config, INDRA grounding, SemMedDB UMLS — all pin entities to
   IRIs and run ID normalization. PhysioMap's `(entity from Uberon/GO/CL/ChEBI, quality from PATO)` already
   matches this; add a lightweight ID-harmonization step (à la CKG/PrimeKG parsers) when importing.

6. **Adopt the GO-CAM activity-unit pattern for multi-aspect, cross-scale node typing.** A GO-CAM node =
   function × location × process; PhysioMap node = entity × PATO quality × scale. GO-CAM's `part_of` to a
   biological-process program and `enabled_by` to a gene product is a precedent for PhysioMap's
   **constitutive cross-scale `part_of` edges kept separate from causal edges** — GO-CAM likewise keeps
   structural/`part_of` relations distinct from RO *causal* relations.

7. **Embrace incompleteness and contradiction as first-class.** INDRA "don't know, don't write"; GO-CAM
   allows coexisting contradictory models revised by evidence; SemMedDB reports predicate-specific
   precision. This validates PhysioMap's discipline of flagging ambiguous signs as `?`, never fabricating,
   and logging — and suggests allowing competing/contradictory edges distinguished by their evidence/belief.

8. **Reason symbolically over typed paths / the condensation — do NOT lean on naive embeddings.** Hetionet's
   metapath/DWPC over typed edges and BEL's Reverse Causal Reasoning are symbolic, type-aware path reasoning,
   adjacent to PhysioMap's SCC-condensation + σ-separation + sign-solvability. Nicholson & Greene explicitly
   warn that standard KG embeddings (TransE/node2vec) **ignore edge type/sign/direction and force
   one-to-one relations** — i.e. they would destroy exactly the signed, cyclic, typed structure PhysioMap
   depends on. Keep reasoning qualitative/symbolic; any future ML must be sign/type/direction-aware.

9. **Keep curation decoupled from execution.** INDRA separates mechanistic Statements from the assembled
   executable model; GO-CAM separates qualitative causal models from kinetics. This mirrors PhysioMap's
   split between the qualitative causal map and any downstream ODE/comparative-statics machinery — the map
   is the durable knowledge artifact; execution policies are layered on top.

10. **Provide a serialization with an OWL bridge.** Biolink Association ≡ OWL Axiom / `rdf:Statement`; GO-CAM
    is native RDF/OWL; BEL is moving to OWL namespaces. PhysioMap already plans an OWL phase — design the
    `CausalEdge` so it can serialize to a reified `rdf:Statement` (subject, signed-RO predicate, object) with
    evidence as annotations, matching Biolink/GO-CAM, so PhysioMap interoperates with these KGs.

---

## (d) Cross-links to sibling resource folders

- **`mechanism-ontology/`** — GO-CAM's use of the **Relations Ontology (RO)** causal relations and **ECO**
  evidence codes, and Biolink's predicate hierarchy / SBO grounding (INDRA), are the concrete mechanism /
  relation / evidence ontologies PhysioMap should reuse for its predicate and `mechanism` slots. Cross-read
  with that folder.
- **`adverse-outcome-pathways/`** — AOPs are signed, directed, qualitative causal chains
  (molecular-initiating-event → key events → adverse outcome) with weight-of-evidence — structurally the same
  signed-causal-path + evidence pattern seen in GO-CAM / Hetionet metapaths; compare evidence/confidence
  schemes.
- **`causal-foundations/`** — The interventionist semantics underlying INDRA's activate/inactivate and
  PhysioMap's edges, and the σ-separation / cyclic-SCM reasoning (Forré & Mooij; Bongers et al.) that
  motivates *symbolic* rather than embedding-based reasoning (per Nicholson & Greene's caveats), live there.
- **`qualitative-reasoning/` & `ode-causality/`** — GO-CAM's and INDRA's "qualitative causal model that omits
  kinetics, then optionally assemble to ODEs" maps onto PhysioMap's qualitative-map ↔ Guyton-ODE /
  comparative-statics split.
- **`virtual-physiological-human/`** — cross-scale constitutive (`part_of`) vs. causal edge distinction
  (GO-CAM activity-unit `part_of` program) connects to multi-scale physiological modeling there.

---

## Files saved (all verified `%PDF`, > 30 KB)

| File | Pages | 1-line relevance |
|------|-------|------------------|
| `Gyori2017_INDRA.pdf` | 26 | Typed mechanistic Statements + Agents + **Evidence object + belief score**; signed activate/inactivate edges forming feedback cycles. |
| `Himmelstein2017_Hetionet.pdf` | 35 | Metagraph of typed metaedges (signed up/down-regulation); edge **provenance+confidence**; metapath reasoning. |
| `Hoyt2018_PyBEL.pdf` | 2 | BEL = qualitative signed causal/correlative relations across scales with **relation-scoped provenance+context**; direct vs. indirect. |
| `Kilicoglu2012_SemMedDB.pdf` | 3 | PubMed-scale UMLS-grounded causal predications (CAUSES/STIMULATES/INHIBITS); sentence+PMID provenance; predicate-specific precision. |
| `Unni2022_Biolink.pdf` | 12 | Association = causal **core triple + evidence/provenance metadata**; hierarchical signed predicates; `id_prefixes` ontology typing; ≡ OWL Axiom. |
| `Thomas2019_GOCAM.pdf` | 15 | **Closest analog**: activity-unit nodes + **RO signed causal relations** + **ECO evidence**; qualitative, contradiction-tolerant, RDF/OWL. |
| `Chandak2023_PrimeKG.pdf` | 16 | 10-scale ontology-typed nodes (UBERON/GO/HPO/MONDO); signed `+/-` and indication/contradiction edges; per-node text. |
| `Santos2022_CKG.pdf` | 17 | Neo4j property graph; 47 typed relations; **`Publication`/PMID provenance nodes**; parser-config ontology mapping; link prediction. |
| `NicholsonGreene2020_KGreview.pdf` | 15 | Survey of causal relation extraction + KG embeddings; **warns embeddings flatten edge type/sign/direction** → keep reasoning symbolic. |
