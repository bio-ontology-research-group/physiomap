# Mechanism & Ontology Foundations — Curated Library

Theme owner folder: `resources/mechanism-ontology/`
For the PhysioMap project (PI: Robert Hoehndorf). PhysioMap nodes are
(biological entity, PATO determinable-quality) pairs — an EQ model — at a biological
scale, with optional ontology IRIs. Within-scale causal edges ABBREVIATE a
quality->disposition->process->quality mechanism; cross-scale edges are CONSTITUTIVE
(part_of + determination). A later phase adds OWL reasoning (PATO/Uberon/GO/CL/ChEBI
+ OWL API + ELK) to validate EQ node typing.

## (a) Overview
This library assembles the formal-ontology and philosophy-of-mechanism foundations on
which PhysioMap's node model and edge semantics rest:
- **EQ / PATO** (Gkoutos 2005; Mungall 2010; Gkoutos 2018) — the Entity-Quality
  formalism that PhysioMap nodes ARE, including its OWL axiom patterns and reasoning.
- **BFO** (Arp/Smith/Spear 2015, stub) — the upper ontology: continuant/occurrent,
  quality, disposition, process, and the realized_in/inheres_in relations that make
  the "quality->disposition->process->quality" chain precise.
- **Relation Ontology** (Smith 2005; RO causal-relations page) — formally defined
  relations (part_of all-some pattern; the causal family) PhysioMap edges can reuse.
- **OBO Foundry** (Smith 2007) — the coordinated OBO ecosystem and, crucially, the
  BFO continuant/occurrent x granularity grid (organism/cell/molecule) that scaffolds
  PhysioMap's biological scales and constitutive cross-scale links.
- **GO-CAM** (Thomas 2019, stub) — the existing OBO standard for representing a
  causal mechanism as a graph of typed molecular activities; the thing a PhysioMap
  causal edge abbreviates / can expand into.
- **Mechanism philosophy** (Machamer-Darden-Craver 2000, stub) — entities+activities
  account of mechanism; the warrant for abbreviating a regular mechanism as one edge.

Honesty note: 5 items downloaded as verified PDFs and READ; 3 are stubs with
verified abstracts/definitions (GO-CAM, BFO book, MDC) where no verifiable OA PDF was
retrievable in this sandbox. Pages read are noted per entry.

---

## (b) Per-paper entries

### 1. Gkoutos, Green, Mallon, Hancock, Davidson 2005 — "Using ontologies to describe mouse phenotypes"
- File: `Gkoutos2005_mouse-phenotypes-EQ.pdf` (Genome Biol 2005;6(1):R8; DOI
  10.1186/gb-2004-6-1-r8; OA). Pages read: 1-4 (abstract, background, schema, tables).
- Summary: Origin of the compositional EQ approach. Proposes describing a phenotype
  as Entity (from anatomy/GO/etc.) + Attribute (PATO) + Value, plus Assay and
  organism context (Fig. 1 schema: organism `has` phenotypic-character =
  entity `has_attribute` PATO-attribute, `characterized_by` assay, `returned_value`).
  PATO ("phenotypic data = qualifications of descriptive nouns") supplies the
  attributes/values; a meta-ontology relates the imported ontologies. Distinguishes
  ontology (general theory) from knowledge base (instances).
- RELEVANCE: This is the EQ seed PhysioMap nodes inherit. PhysioMap's (entity,
  determinable-quality) pair = (E, PATO attribute); a measured value/state is the
  determinate. Confirms entity drawn from anatomy/GO/chemical ontologies and quality
  from PATO — exactly PhysioMap's IRI sources (Uberon/GO/CL/ChEBI + PATO).

### 2. Mungall, Gkoutos, Smith, Haendel, Lewis, Ashburner 2010 — "Integrating phenotype ontologies across multiple species"
- File: `Mungall2010_integrating-phenotype-ontologies.pdf` (Genome Biol 2010;11(1):R2;
  DOI 10.1186/gb-2010-11-1-r2; OA). Pages read: 1-5 (abstract..EQ syntax + Table 1 +
  Figs 1-3).
- Summary: Defines the EQ model precisely: a phenotype = Q (PATO quality) + E (entity
  bearing the quality) + optional E2 (additional/relational entity) + M (modifier).
  Translates EQ to OWL/OBO via the `inheres_in` relation: phenotype 'femur shape' =
  `intersection_of: PATO:0000052 (shape); inheres_in some MA:0001359 (femur)` — i.e.
  `<Q that inheres_in E>`. These logical definitions ("XP"/cross-product ontologies,
  e.g. MP-XP-MA) let an automated reasoner classify pre-composed phenotype ontologies
  (Fig. 2: inferred MP `is_a` links) and enable cross-species queries when combined
  with a multi-species anatomy ontology (Uberon). Fig. 1 shows the OBO physical-scale
  grid (FMA/MA/Uberon anatomical -> CL cellular -> GO-CC/PRO sub-cellular ->
  ChEBI molecular).
- RELEVANCE: The authoritative E/Q/E2/M decomposition and the `inheres_in` axiom are
  the OWL realization of PhysioMap node typing. The XP/cross-product + reasoner story
  is exactly PhysioMap's planned OWL/ELK validation phase. Relational qualities (E2
  via `towards`) cover qualities-of-two-entities (e.g. sensitivity_toward oxygen),
  relevant to cross-entity PhysioMap nodes.

### 3. Gkoutos, Schofield, Hoehndorf 2018 — "The anatomy of phenotype ontologies: principles, properties and applications"
- File: `Gkoutos2018_anatomy-of-phenotype-ontologies.pdf` (Brief Bioinform
  2018;19(5):1008-1021; DOI 10.1093/bib/bbx035; OA; **Hoehndorf is corresponding
  author / PI**). Pages read: 1-8 (intro, landscape, PATO framework, EQ axiom
  patterns, ontology-based analysis).
- Summary: Authoritative review of the PATO/EQ framework by the PhysioMap PI. Key
  technical content:
  - PATO structure: attributes vs values (value subclasses of attribute class, via
    'attribute'/'value' slims); scalar vs non-scalar attributes; unary vs
    **relational qualities** (relational qualities use a `towards` relation to their
    2nd..nth argument); opposite-of axioms between values.
  - **EQ axiom patterns** (the OWL the reasoning phase needs):
    - quality-as-classifier: `P EquivalentTo: 'has part' some (Q and 'inheres in'
      some E)`.
    - entity-as-classifier alt: `P EquivalentTo: has-part some (E and has-quality
      some Q)`.
    - 'inheres in' is functional (a quality inheres in exactly one entity).
    - parthood propagation via `inheres_in_part_of`
      (= `inheres_in o part_of`), giving inferred phenotype taxonomies from anatomy
      part_of (e.g. 'abnormal left ventricle' is_a 'abnormal heart').
    - **Absence** modeled via negation: `absence of E` = `not ('has part' some
      ('part of' some E))`.
    - Uses **OWL 2 EL** profile (polynomial-time reasoning; supports the equivalent/
      subclass/intersection/existential axioms above) — i.e. ELK-compatible.
  - Direct vs comparative phenotype statements (wild-type reference -> abnormal/
    divergent quality); PATO can auto-generate a phenotype backbone taxonomy from
    anatomy/physiology + GO function.
  - **Key claim for PhysioMap**: "similarity between phenotypes provides information
    about the underlying **mechanisms** leading to the phenotype" — phenotype
    similarity is used to infer shared mechanism (disease-gene prioritization,
    PhenomeNET/Monarch).
- RELEVANCE: This is the single most directly applicable paper. Its EQ axiom patterns,
  `inheres_in`/`inheres_in_part_of`, functionality of inheres_in, absence-by-negation,
  and OWL 2 EL choice are a ready specification for PhysioMap's node-typing validation.
  The mechanism-from-similarity framing aligns with PhysioMap edges carrying mechanism
  refs + evidence.

### 4. Smith, Ceusters, Klagges, Köhler, Kumar, Lomax, Mungall, Neuhaus, Rector, Rosse 2005 — "Relations in biomedical ontologies"
- File: `Smith2005_relations-in-biomedical-ontologies.pdf` (Genome Biol 2005;6(5):R46;
  DOI 10.1186/gb-2005-6-5-r46; OA). Pages read: 1-3 (abstract, problem, theory of
  classes/instances, types of relations).
- Summary: Founding Relation Ontology (RO) paper. Insists relations be defined at the
  **instance** level then lifted to classes; distinguishes three binary relation
  kinds: `<class,class>` (is_a), `<instance,class>` (instance_of), `<instance,
  instance>` (e.g. an individual nucleus part_of an individual cell). Provides the
  **all-some** semantics for class-level part_of: 'C part_of D' means every instance
  of C stands in instance-part_of to *some* instance of D. Defines ~10 core relations
  (is_a, part_of, located_in, has_participant, derives_from, transformation_of, etc.),
  with consistent textual+formal definitions, to fix the ambiguities of pre-2004 GO.
- RELEVANCE: PhysioMap must commit to RO-style all-some semantics for its `part_of`
  (used by constitutive cross-scale edges) and for any class-level relation, so the
  OWL reasoning phase is sound. The instance-vs-class care directly informs how
  PhysioMap node *types* (classes) relate to specific *instances* (a particular
  organism's heart at a time).

### 5. Smith, Ashburner, Rosse, ... Lewis 2007 — "The OBO Foundry: coordinated evolution of ontologies..."
- File: `Smith2007_OBO-Foundry.pdf` (Nat Biotechnol 2007;25(11):1251-1255; DOI
  10.1038/nbt1346; PMC2814061 manuscript; downloaded from SIG eprint). Pages read:
  1-4 (full Perspective + Tables 1-2).
- Summary: The OBO Foundry principles (open, common syntax, orthogonality, shared
  relations via RO, unique IDs, textual definitions, collaborative governance) and the
  ecosystem of orthogonal ontologies. **Table 1 (load-bearing for PhysioMap)** is a
  grid: rows = granularity (organism / cell+cellular-component / molecule) x columns =
  BFO top categories (Continuant {Independent: organism, anatomical entity (FMA/CARO),
  cell (CL/FMA), molecule (ChEBI/SO/PRO); Dependent: organ function, cellular function,
  molecular function (GO); **Phenotypic quality (PATO)** spanning all granularities} |
  Occurrent: organism-/cellular-/molecular **process** (GO)). RO provides the "glue"
  relations for cross-products; PATO supplies quality templates; FMA genus-differentia
  definitions anchored in is_a.
- RELEVANCE: Table 1 IS the PhysioMap scale-x-category scaffold. PhysioMap "scales"
  ≈ the granularity rows; ENTITY ≈ independent continuant cell/anatomy/molecule
  columns (Uberon/CL/ChEBI); QUALITY ≈ the PATO dependent-continuant column; the
  abbreviated mechanism's process ≈ the GO occurrent column. Confirms PhysioMap should
  draw entity IRIs from exactly these OBO ontologies and reuse RO relations.

### 6. Thomas, Hill, Mi, ... Mungall 2019 — GO-CAM
- Stub: `Thomas2019_GO-CAM.stub.md` (Nat Genet 2019;51(10):1429-1433; DOI
  10.1038/s41588-019-0500-1; PMID 31548717). **[NO PDF — paywalled; abstract +
  metadata verified via PubMed/nature.com WebFetch.]**
- Summary + RELEVANCE: see stub. GO-CAM = causal graph of GO-MF activities
  (enabled_by gene product, occurs_in CL/Uberon, has_input/output ChEBI) linked by RO
  causal relations and grouped into GO Biological Processes. It is the concrete
  artifact a PhysioMap within-scale causal edge abbreviates and could expand into
  during the OWL phase.

### 7. Arp, Smith, Spear 2015 — Building Ontologies with BFO
- Stub: `ArpSmithSpear2015_BFO.stub.md` (MIT Press; ISBN 9780262527811; +BFO 2.0 /
  ISO 21838-2). **[NO PDF — book; definitions captured from BFO 2.0 spec, verified.]**
- Summary + RELEVANCE: see stub. Supplies continuant/occurrent, quality vs realizable
  entity (role/disposition/function), process, and the inheres_in / realized_in /
  bearer_of / has_realization relations — the precise vocabulary for PhysioMap's node
  typing (entity=independent continuant, quality=BFO quality/PATO determinable) and
  for the disposition->process realization chain a causal edge abbreviates.

### 8. Machamer, Darden, Craver 2000 — "Thinking about Mechanisms"
- Stub: `MachamerDardenCraver2000_mechanisms.stub.md` (Philos Sci 2000;67(1):1-25;
  DOI 10.1086/392759). **[NO PDF — definition captured verbatim from SEP, verified.]**
- Summary + RELEVANCE: see stub. "Mechanisms are entities and activities organized
  such that they are productive of regular changes from start or set-up to finish or
  termination conditions." Entities≈BFO continuants, activities≈BFO processes;
  regularity warrants abbreviating a recurring mechanism as a single causal edge;
  multilevel constitution underwrites constitutive cross-scale edges.

### (supporting) RO Causal Relations — oborel.github.io/obo-relations/causal-relations
- Not a paper; the RO causal-relations documentation (content captured via WebFetch).
- The causal family PhysioMap can reuse for edges:
  - `causally upstream of` (RO:0002411), `immediately causally upstream of`
    (RO:0002412), `causally upstream of or within` (RO:0002418).
  - `causally upstream of, positive effect` (RO:0002304) / `negative effect`
    (RO:0002305).
  - `regulates` (RO:0002211): "p regulates q iff p is causally upstream of q, the
    execution of p is not constant and varies according to specific conditions, and p
    influences the rate or magnitude of execution of q due to an effect on some
    enabler of q (or of a part of q)." `positively/negatively regulates`
    (RO:0002213/RO:0002212); `directly regulates`; `provides input for`.
  - Causal algebra distinguishes **regulatory** vs **non-regulatory** influence;
    "regulation is infectious" (any regulatory link makes the whole chain regulatory).

---

## (c) EQ model + BFO realization chain + constitutive relations

### EQ → PATO node typing
A PhysioMap node = (biological entity E, PATO determinable quality Q).
- In EQ/OWL terms (Mungall 2010; Gkoutos 2018), the node corresponds to a phenotype
  class `P EquivalentTo: 'has part' some (Q and 'inheres in' some E)`, or the
  quality-bearer reading `Q that inheres_in E`.
- E is an OWL class from Uberon/CL/GO-CC/ChEBI (BFO **independent continuant /
  material entity**); Q is a PATO class (BFO **quality**, a specifically dependent
  continuant). A *determinate* value (e.g. a specific blood-pressure magnitude) is a
  subclass of the determinable Q (PATO models values as subclasses of attribute
  classes; scalar values via increased/decreased-relative-to axioms).
- OWL-phase validation: with BFO as upper ontology + ELK (OWL 2 EL, which Gkoutos
  2018 confirms PATO/EQ targets), check that (i) E classifies under material entity,
  (ii) Q classifies under quality, (iii) `inheres_in` is functional (Q has exactly one
  bearer), and (iv) inferred phenotype taxonomy via `inheres_in_part_of` (=
  inheres_in o part_of) matches anatomy part_of. Absence nodes use negation
  (`not ('has part' some ('part of' some E))`).

### Causal edge abbreviates quality → disposition → process → quality
A within-scale causal edge A->B (A, B both quality-nodes on the same entity/scale)
COMPRESSES a BFO realization chain (Arp/Smith/Spear; MDC):
1. Quality A (a configuration of the bearer) **grounds** a **disposition** d of the
   bearer (BFO: disposition is realized in virtue of the bearer's physical make-up).
2. d is **realized_in** a **process** p (BFO `realized_in`; MDC: activities of
   entities productive of change).
3. p **brings about / changes** quality B (the termination condition; the process's
   output quality).
So edge A->B = "A grounds-disposition realized-in process producing B."
- Store as the edge's **mechanism ref**: the disposition + process (ideally a GO-CAM
  model: GO-MF activity enabled_by a gene product, occurs_in the entity, has_input/
  output ChEBI), plus evidence. The single edge is sound because mechanisms are
  **regular** (MDC) — a recurring entities+activities organization can be summarized.
- Relation typing of the edge: reuse RO causal relations — default
  `causally upstream of` (+ positive/negative effect for sign), or `regulates`
  (positively/negatively) when A modulates the *rate/magnitude* of B's process via an
  enabler (RO:0002211 definition). This distinguishes productive ("provides input
  for"/upstream) from regulatory edges in PhysioMap exactly as the RO causal algebra
  does.

### part_of + determination underpins CONSTITUTIVE cross-scale edges
A cross-scale edge links a MICRO node (entity e_micro, quality q_micro) to a MACRO
node (entity e_macro, quality q_macro) where e_micro is `part_of` e_macro.
- Both endpoints are **continuants** (entities + their qualities), so the relation is
  among continuants — distinct from the occurrent-grounded within-scale causal edge.
- **part_of**: use RO all-some semantics (Smith 2005): every e_micro instance is
  part_of some e_macro instance; PhysioMap should commit to this for soundness and use
  `inheres_in_part_of` to propagate quality classification up the part hierarchy.
- **determination**: the configuration of micro qualities {q_micro} FIXES the macro
  quality q_macro (constitutive relevance, Craver/MDC multilevel mechanisms). This is
  *constitutive*, not causal — synchronic, not productive-over-time. PhysioMap should
  represent it as a determination/constitution relation (candidate: a
  `determined_by`/`has_determinant` relation, or RO's mereological + a custom
  constitution property), NOT as a causal_upstream relation.
- BFO grounding: macro quality is a quality of the macro material entity; the macro
  entity's parts (micro entities) and their qualities are what the macro quality
  *supervenes on / is determined by*. This is the "micro configuration fixes macro
  quality" claim made formal.

### RO causal relations we could reuse (summary)
- Productive / pathway-flow edges: `causally upstream of` (RO:0002411),
  `immediately causally upstream of` (RO:0002412), `provides input for`,
  `causally upstream of or within` (RO:0002418); sign via
  `..., positive/negative effect` (RO:0002304/RO:0002305).
- Regulatory edges: `regulates` (RO:0002211), `positively regulates` (RO:0002213),
  `negatively regulates` (RO:0002212), `directly regulates`.
- Mereological / constitutive: `part_of` (RO:0000050) + `has part` (RO:0000051);
  `inheres_in` (RO:0000052) + `inheres_in_part_of` for quality propagation;
  `realized_in` (BFO) for the disposition->process step inside a mechanism ref.

---

## (d) Cross-links (causal KGs, AOPs, VPH)
- **GO-CAM / Noctua** — concrete causal-activity models; PhysioMap edge mechanism refs
  can point at GO-CAM models (entry 6 / stub).
- **Adverse Outcome Pathways (AOP / AOP-Wiki, OECD)** — Molecular Initiating Event ->
  Key Events -> Adverse Outcome, with "Key Event Relationships" that are essentially
  cross-scale causal/constitutive links across biological levels; directly analogous
  to PhysioMap's within- and cross-scale edges. (Not in this library; flag for the
  causal-modeling theme.)
- **Virtual Physiological Human (VPH) / Physiome / multiscale modeling** — the
  quantitative multiscale-physiology program PhysioMap qualitatively abstracts; SBML/
  CellML + the Physiome project are the mechanistic substrates a causal edge could
  reference. (Not in this library; flag.)
- **Monarch Initiative / PhenomeNET / Uberon / uPheno** — the EQ-based cross-species
  phenotype integration that uses exactly the Mungall 2010 / Gkoutos 2018 machinery;
  source of entity IRIs and of the phenotype-similarity-implies-shared-mechanism idea.
- **Biolink Model** — reuses RO causal relations in a property graph; a precedent for
  PhysioMap mapping its edge types onto RO.

---

## Files in this folder
- Gkoutos2005_mouse-phenotypes-EQ.pdf            (READ pp.1-4)
- Mungall2010_integrating-phenotype-ontologies.pdf (READ pp.1-5)
- Gkoutos2018_anatomy-of-phenotype-ontologies.pdf  (READ pp.1-8)
- Smith2005_relations-in-biomedical-ontologies.pdf (READ pp.1-3)
- Smith2007_OBO-Foundry.pdf                        (READ pp.1-4)
- Thomas2019_GO-CAM.stub.md                        (stub; verified abstract)
- ArpSmithSpear2015_BFO.stub.md                    (stub; verified definitions)
- MachamerDardenCraver2000_mechanisms.stub.md      (stub; verified definition)
