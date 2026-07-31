# Virtual Physiological Human (VPH) & the Physiome Project — Curated Library

Theme folder for the PhysioMap project. PhysioMap is a *qualitative*, cyclic, signed causal
map of human physiology, multi-scale (molecular -> organism), with EQ/ontology-typed nodes —
i.e. a qualitative counterpart to the quantitative multiscale physiology that the
VPH/Physiome community builds. This library collects the vision/strategy papers, the
markup/standards papers, and the Guyton circulation lineage that frame that comparison.

Curator honesty note: entries below are either (a) DOWNLOADED + READ PDFs (page ranges
noted), or (b) STUBS with a verified abstract fetched from PubMed/PMC/publisher and marked
`[NO PDF — stub]`. Nothing here is fabricated. Several seed papers (Guyton 1972 Annu Rev
Physiol; Hunter & Borg 2003 Nat Rev Mol Cell Biol; Lloyd 2004 CellML; Hucka 2003 SBML;
Hunter et al. 2010 Phil Trans A) are paywalled / not in any OA subset reachable from the
sandbox, so they are stubs. Note: the canonical 2010 Phil Trans "vision and strategy" paper
(PMC3342768) resolves on Europe PMC to the *2011 Coveney et al. Interface Focus* introduction
(same DOI cluster); we keep the readable 2011 piece and stub the 2010 Phil Trans paper.

---

## (a) Overview: what the VPH / Physiome Project is

The **Physiome Project** (IUPS, proposed 1993 Glasgow, formally launched ~1997–2000) is a
worldwide public-domain effort to build a quantitative, computational description of human
physiological function across *all* levels of structural and functional integration — from
molecule, through cell, tissue and organ, to the whole organism (and into populations). It
arose from the recognition that the genome/proteome "parts list" delivered by molecular
biology has had limited impact on the practice of medicine because it is not integrated into
*physiology*: phenotype depends on (mathematical) models the way genotype depends on a
nucleotide sequence ("putting Humpty-Dumpty together again").

The **Virtual Physiological Human (VPH)** is the European (EU FP6/FP7/Horizon 2020) clinical
re-framing of the Physiome vision. The term was coined at a Barcelona workshop in May 2005
(White Paper Nov 2005), formalised by the STEP roadmap "Seeding the EuroPhysiome" (2007), and
institutionalised by the VPH Institute. From 2007 the emphasis shifted from a single
"reference Human Physiome" to **patient-specific / problem-specific predictive models** used
as clinical decision-support, plus *in silico* clinical trials. The VPH Institute later
framed three macroscopic targets: **Digital Patient** (modelling for the doctor),
**In silico Clinical Trials** (modelling for industry; reduce/refine/replace animal & human
experimentation), and **Personal Health Forecasting** (subject-specific real-time simulation
for the citizen).

Methodologically, both projects are built **"middle-out"** (Brenner): start at a scale where
data/processes are well understood, then reach *out* to adjacent (higher and lower) scales via
validated mathematics. Regulatory interactions are inherently two-way (feedback loops), so
"higher/lower" denotes spatial scale, not causal priority. The enabling infrastructure is a
set of **markup standards** (CellML for ODE/algebraic cell models; SBML for biochemical
reaction networks; FieldML for spatially-varying fields; SED-ML for simulation protocols;
BioSignalML for time-series; openEHR for clinical records) plus curated, ontology-annotated
**model repositories** (the Physiome Model Repository, PMR). The canonical, longest-running
exemplar is the **cardiac Physiome** (Noble 1962 onward); the canonical *integrative whole-body*
exemplar is the **Guyton circulation model** (1972) and its lineage (HUMAN, QCP, HumMod).

---

## (b) Per-paper entries

### READ (PDF downloaded, verified `%PDF`, read in full)

#### 1. Coveney, Diaz, Hunter, Kohl, Viceconti (2011) — "The Virtual Physiological Human"
- File: `Coveney2011_vph-introduction.pdf` (read pp.1–5, full)
- *Interface Focus* 1(3):281–285. doi:10.1098/rsfs.2011.0020. (Theme-issue introduction, VPH2010.)
- Defines VPH as "systems biology written on the largest of scales": a methodological/
  technological framework to represent the human body as a single coherent dynamical system,
  reaching from genome up to whole human and populations. Distinguishes "physiome" technology
  (mechanistic organ-system modelling, **Popperian** — model predicts, then is tested) from
  data-driven bioinformatics (**Baconian** — data/lookup tables). Stresses **downward
  causation** (Noble) — phenotype-level events often determine genetic behaviour. Surveys the
  VPH2010 cardiovascular-dominated portfolio (patient-specific heart/vessel models, in-stent
  restenosis, nephron multiscale tool, bond-graph formalisation, cancer decision support).
- RELEVANCE: gives the crisp framing PhysioMap shares — *whole body as one coherent multi-scale
  causal system*. The Popperian/Baconian contrast maps onto PhysioMap's stance: a curated
  *mechanistic causal* map (Popperian, hypothesis-bearing) rather than a correlational KG.
  "Downward causation" justifies our **cyclic, cross-scale signed edges** (organism->molecule).

#### 2. Kohl & Noble (2009) — "Systems biology and the virtual physiological human"
- File: `KohlNoble2009_systems-biology-vph.pdf` (read pp.1–6, full; CC-BY)
- *Mol Syst Biol* 5:292. doi:10.1038/msb.2009.51.
- Editorial defining systems biology as an **approach** (not a discipline) that consciously
  combines *reductionist* (identify+characterise parts) and *integrationist* (interactions
  among parts and with environment) research to understand maintenance of an entity. Argues
  **no scale has privileged relevance**; systems biology is inherently multi-scale. Uses the
  **virtual heart** as the lead example (50 yr of model–experiment iteration, modularity:
  electrophysiology decouplable from mechanics/metabolism until detail demands cross-talk).
  Box 1 ("general principles from cardiac modelling") is a checklist directly relevant to us:
  Conceptual Duality, Iteration of Theory/Practice, **Structure–Function Relationship**,
  **Multi-Scale** (bridging ~9 spatial and ~17 temporal orders of magnitude), **Multiplicity
  of Models**, Multi-dimensional (0D–3D+t), Multi-physics, **Modularity (define model
  interfaces)**, High-speed sim, Interactivity. Box 2 flags Tools/Standards/Ontologies (cites
  SBML, CellML, FieldML), model curation/preservation, patient-specific treatment.
- RELEVANCE: the "reduce + integrate" diagram (Figs 1–2: Body/Organ/Tissue/Cell/Organelle/
  Network/Transcript/Gene/Molecule stack) is essentially **PhysioMap's scale enum**. The
  modularity / "define model interfaces" principle is exactly our **constitutive cross-scale
  edges** between scale layers. Names Guyton 1972 as the early quantitative circulation model.

#### 3. Hester, Brown, Husband, Iliescu, Pruett, Summers, Coleman (2011) — "HumMod"
- File: `Hester2011_HumMod.pdf` (read pp.1–7 of 12; results/discussion examples beyond p.7)
- *Front Physiol* 2:12. doi:10.3389/fphys.2011.00012.
- HumMod = the modern descendant of the Guyton (1972) and Coleman HUMAN models, via QCP. A
  Windows model of integrative human physiology with **~5000 variables** (cardiovascular,
  respiratory, renal, neural, endocrine, skeletal muscle, metabolic), built from peer-reviewed
  empirical data. Crucially: **all physiology is described in XML** (`.DES` "Structure" files;
  ~2900 files); the executable parses the XML, so the model is *declarative and extensible* —
  investigators add/revise XML to add physiology. Each variable carries documentation
  (definition, assumptions, units, **physiologic relationships + references**) in a Zotero-backed
  bibliographic database (5424 records). A **Model Navigator** GUI lets users browse variables
  and their **cause-and-effect** relationships ("Center Area – Details related to cause and
  effect"). Worked examples: renal control of BP, angiotensin II steady state, baroreflex,
  EPO/erythropoiesis, orthostatic hypotension in astronauts.
- RELEVANCE: this is the **canonical integrative model PhysioMap mirrors qualitatively**. HumMod
  already (i) makes physiology a *graph of typed variables with annotated causal/constitutive
  relationships*, (ii) stores per-node provenance/references, (iii) ships a navigator over the
  cause-effect graph. PhysioMap is the *signed-qualitative* projection of exactly this kind of
  structure (drop the kinetics, keep node + sign + cross-scale edge + ontology type +
  reference). Direct lineage to the Guyton fragment we vendored.

#### 4. Viceconti & Hunter (2016) — "The Virtual Physiological Human: Ten Years After"
- File: `Viceconti2016_vph-ten-years.pdf` (read all 18 pp; OA submitted version, White Rose)
- *Annu Rev Biomed Eng* 18:103–123. doi:10.1146/annurev-bioeng-110915-114742.
- The best single synthesis here. Sections: (1) Physiome->VPH history (Bernard -> molecular
  biology divergence -> IUPS Physiome 1993/1997 -> VPH 2005); (2) the vision (Digital Patient /
  In silico Clinical Trials / Personal Health Forecasting + two horizontal themes:
  infrastructure, and epistemology/acceptance of predictive tech); (3) **the methods** — the
  standards stack: **CellML** (declarative XML over MathML for ODE/algebraic models; separates
  *syntax/maths* from *semantics* via **RDF + ontologies**; modular via imports/encapsulation/
  mappings — illustrated with Noble-1962 split into Na/K/leak channel sub-models), **SBML**
  (biochemical reactions), **FieldML** (spatial fields), **SED-ML** (simulation protocols),
  functional curation (Oxford "web lab"), the **Physiome Model Repository** (~600 curated,
  annotated model exposures), VPH-Share cloud, openEHR mapping; (4) clinical targets (cardiac,
  respiratory, musculoskeletal, FFR/HeartFlow FDA approval, aneurysm rupture, osteoporotic
  fracture risk, oncology); (5) two multiscale case studies (cardiac electro-mechanics / LQTS2
  diagnosis from ion channel -> tissue -> torso EKG; respiratory V/Q -> blood-gas lung models);
  (6) remaining challenges — modular models must be *connectable into whole-body integrative
  models*, incentives to use standards, a proposed **Physiome Journal** + whole-body Physiome
  web portal, Technology Readiness Levels (TRL1–9), turn-around time, reduced-order models.
- RELEVANCE: This is the spine of the PhysioMap rationale. (i) The CellML modularity story
  (imports/encapsulation/mappings; semantics via RDF+ontologies) is the *quantitative analogue*
  of PhysioMap's ontology-typed nodes + constitutive cross-scale edges. (ii) The
  "connect independent multiscale modules into whole-body integrative models" challenge is the
  open problem a qualitative causal map can address by providing the *topology/skeleton* into
  which quantitative modules plug. (iii) The cardiac LQTS2 case shows the
  molecule(ion channel)->tissue->organ->body-surface chain PhysioMap encodes as cross-scale edges.

### STUBS (paywalled / not OA-reachable; abstract verified)

#### 5. Guyton, Coleman, Granger (1972) — "Circulation: overall regulation"  `[NO PDF — stub]`
- *Annu Rev Physiol* 34:13–46. doi:10.1146/annurev.ph.34.030172.000305. PMID 4334846.
- PubMed: "No abstract available." Verified via PubMed + Annual Reviews listing + cited in
  KohlNoble2009 and Viceconti2016 reference lists (read here). The first whole-body integrated
  mathematical model of a physiological system; used systems analysis to organise circulatory
  regulation; central to establishing the kidney's role in long-term blood-pressure regulation
  (pressure–natriuresis) and the blood-pressure / sodium-balance relationship. The famous large
  block-diagram of ~150+ interacting variables.
- RELEVANCE: THE canonical integrative, **cyclic, signed** causal model of physiology, and the
  exact model fragment PhysioMap's first slice encodes (we vendored the Guyton-1972 BioModels +
  Physiome CellML versions). Its block diagram *is* a signed causal graph with feedback loops —
  PhysioMap is essentially its qualitative re-typing with ontology nodes.

#### 6. Hunter & Borg (2003) — "Integration from proteins to organs: the Physiome Project"  `[NO PDF — stub]`
- *Nat Rev Mol Cell Biol* 4(3):237–243. doi:10.1038/nrm1054. PMID 12612642. (No PMCID.)
- Abstract (verified, PubMed): "The Physiome Project will provide a framework for modelling the
  human body, using computational methods that incorporate biochemical, biophysical and
  anatomical information on cells, tissues and organs. The main project goals are to use
  computational modelling to analyse integrative biological function and to provide a system
  for hypothesis testing." Introduced the multiscale (~9 spatial / ~17 temporal orders)
  framing and the CellML/anatomical-markup approach.
- RELEVANCE: foundational statement of the molecule->organ integration goal and the
  hypothesis-testing role of models — directly the multiscale axis PhysioMap formalises as a
  scale enum, and the "model as hypothesis-testing instrument" framing.

#### 7. Bassingthwaighte (2000) — "Strategies for the Physiome Project"  `[NO PDF — stub]`
- *Ann Biomed Eng* 28(8):1043–1058. doi:10.1114/1.1313771. (NIH author manuscript PMC3425440,
  but PMC serves a proof-of-work interstitial and the record is *not* in the OA subset, so no PDF.)
- Abstract (verified via PMC HTML): the *physiome* = comprehensive quantitative description of
  organism function in normal+disease states, built on the *morphome* (anatomy + biochemical
  composition). The Project requires: databasing experimental observations, building quantitative
  integrative models molecule->organism, and international collaboration. Key challenges:
  many interconnected nonlinear pathways, computational demands, and gaps in kinetic/dynamic
  data. Provides scientific basis for genome–phenotype–physiome relationships. (Sections:
  Simplicity/Complexity of Biology; The Physiome and Project; Databases; Modeling genome->human
  or vice versa or middle; Management; a Cardiome example; Next steps.)
- RELEVANCE: articulates the *morphome -> physiome* layering and the database+model+collaboration
  triad. PhysioMap's typed nodes (anatomy/EQ) + signed causal edges are a qualitative "physiome
  database" in this sense; the "middle-out" modelling question recurs in our scale design.

#### 8. Lloyd, Halstead, Nielsen (2004) — "CellML: its future, present and past"  `[NO PDF — stub]`
- *Prog Biophys Mol Biol* 85(2–3):433–450. doi:10.1016/j.pbiomolbio.2004.01.004. PMID 15142756.
- Abstract (verified, PubMed): standards are needed so cell models can be exchanged over the web
  and read into simulation software consistently, and to eliminate publication errors. "CellML is
  a free, open-source, eXtensible markup language based standard for defining mathematical models
  of cellular function." Summarises CellML structure, current uses (biological-pathway and
  electrophysiological models), and future development — toolsets and **integration of ontologies**.
- RELEVANCE: the markup standard that encodes the quantitative models PhysioMap shadows. The
  "integration of ontologies" thread is precisely PhysioMap's *ontology-typed nodes*; CellML's
  modular import structure parallels our cross-scale constitutive edges.

#### 9. Hucka et al. (2003) — "The systems biology markup language (SBML)"  `[NO PDF — stub]`
- *Bioinformatics* 19(4):524–531. doi:10.1093/bioinformatics/btg015. PMID 12611808.
  (OUP paywalled; OA SBML spec PDFs exist on sbml.org but are the *specification*, not this paper.)
- Abstract (verified, PubMed/repositories): SBML is "a free, open, XML-based format for
  representing biochemical reaction networks," a machine-readable medium for representing and
  exchanging models, supported by many simulation/analysis tools; describes SBML Level 1.
- RELEVANCE: the biochemical-network counterpart to CellML; defines the molecular-scale models
  PhysioMap's lowest scale layer references. Standardised, exchangeable, ontology-annotatable
  model encodings are the substrate a qualitative causal layer sits on top of.

---

## (c) Synthesis & relevance to PhysioMap

1. **PhysioMap = a qualitative VPH.** The VPH/Physiome program builds the human body as one
   coherent multi-scale *quantitative* dynamical system (Coveney 2011; Viceconti 2016). PhysioMap
   keeps the same object — multi-scale, whole-body, causal — but projects it to the *qualitative,
   signed* level: nodes (EQ/ontology-typed) and signed causal/constitutive edges, no kinetics.
   It is the topology/skeleton of a VPH model.

2. **Guyton 1972 is the canonical cyclic, signed, integrative model — and our first slice.**
   Guyton's circulation block diagram is literally a signed causal graph of ~150 variables with
   feedback loops (Guyton 1972; reaffirmed as the founding integrative model by KohlNoble2009 and
   Viceconti2016). PhysioMap's Guyton cardiovascular fragment is its qualitative re-typing; the
   vendored BioModels/CellML versions give the quantitative ground truth to validate signs/loops.

3. **HumMod shows the bridge is real and already half-built.** HumMod (Hester 2011), the Guyton
   lineage descendant, encodes ~5000 variables as *declarative XML with per-variable
   cause-and-effect relationships, ontology-like documentation, and literature provenance*, browsed
   via a cause-effect navigator. PhysioMap is the signed-qualitative abstraction of precisely this
   structure: keep node + sign + cross-scale edge + ontology type + reference; drop the equations.

4. **The scale enum comes straight from the community's stack.** KohlNoble2009 Fig 2 lays out
   Body/Organ/Tissue/Cell/Organelle/Network/Transcript/Gene/Molecule with Time/Function/Structure
   axes; Hunter&Borg 2003 quantify it as ~9 spatial / ~17 temporal orders of magnitude. This is the
   blueprint for PhysioMap's scale enumeration.

5. **Constitutive cross-scale edges = the standards' modularity made qualitative.** CellML's
   imports/encapsulation/mappings (Viceconti2016 Fig 1: Noble-1962 split into Na/K/leak channels)
   and the systems-biology "define model interfaces" principle (KohlNoble2009 Box 1) are the
   quantitative version of PhysioMap's cross-scale edges that bind a lower-scale entity into a
   higher-scale one. PhysioMap edges are where, in a VPH, a CellML/SBML module would plug in.

6. **Standards (CellML/SBML/FieldML/SED-ML) are the quantitative substrate PhysioMap annotates.**
   These XML standards separate maths from *semantics encoded via RDF + ontologies* (Viceconti2016;
   Lloyd 2004; Hucka 2003). PhysioMap's ontology-typed nodes are the same semantic layer, and a
   PhysioMap node can carry pointers to the CellML/SBML model(s) realising it quantitatively.

7. **The unsolved VPH problem is exactly what a causal map helps with.** Viceconti2016's "remaining
   challenges" name the open problem: *connecting independently developed, validated multiscale
   modules into whole-body integrative models*. A curated qualitative causal map provides the
   integrative wiring diagram (which variable drives which, with what sign, across which scale
   boundary) into which quantitative modules can be slotted and consistency-checked.

8. **Popperian, mechanistic, hypothesis-bearing — not Baconian/correlational.** Coveney2011 frames
   physiome modelling as Popperian (mechanistic models that predict and are tested) vs Baconian
   data-mining. PhysioMap inherits this: it is a *mechanism* graph for hypothesis testing and
   qualitative simulation (sign propagation around loops), not a statistical association KG.

9. **Downward causation / cyclicity is a feature, not a bug.** KohlNoble2009 and Coveney2011 insist
   regulatory interactions are two-way and that "higher/lower" is spatial, not causal-priority.
   This licenses PhysioMap's *cyclic* graph with feedback loops and organism->molecule edges,
   distinguishing it from acyclic causal-DAG formalisms.

10. **Curation + provenance are first-class.** Across HumMod (Zotero-backed per-variable refs), PMR
    (~600 curated annotated exposures), and the proposed Physiome Journal, the community treats
    annotated, referenced, reusable models as the deliverable. PhysioMap should likewise attach a
    reference + ontology annotation to every node and edge.

---

## (d) Cross-links to sibling resource folders

- **`ode-causality/`** — Guyton/HumMod are ODE systems; a signed causal edge in PhysioMap is the
  qualitative abstraction of a partial-derivative sign (∂(target rate)/∂(source) ≷ 0) of the
  underlying ODE. The CellML/SBML models give the ODEs from which PhysioMap's signs can be derived
  and validated. See ode-causality notes for the formal ODE->causal-graph mapping.
- **`mechanism-ontology/`** — VPH semantics are RDF + bio-ontology annotations on CellML/SBML terms
  (Lloyd 2004; Viceconti2016). PhysioMap's EQ/ontology-typed nodes are the same idea; mechanism
  ontologies (process, participant, regulation) supply the edge *types* (constitutive vs causal vs
  regulatory) we need beyond a bare sign.
- **`causal-knowledge-graphs/`** — PhysioMap is a causal KG, but mechanistic/Popperian (per
  Coveney2011) rather than correlational; HumMod's navigable cause-effect graph and the Guyton
  block diagram are the physiological-domain priors. Contrast acyclic statistical KGs with our
  cyclic signed map.
- **`qualitative-reasoning/`** — sign propagation around Guyton's feedback loops is qualitative
  (QSIM/QPT-style) reasoning over the VPH quantitative model; this folder is the natural home for
  the inference engine that runs over PhysioMap.
- **`causal-foundations/` & `mendelian-randomization/`** — relevant to whether/when the signed,
  cyclic, downward-causation graph admits interventionist (do-calculus) or equilibrium-causal
  semantics; VPH's two-way regulatory loops are the stress test for those foundations.
- **`adverse-outcome-pathways/`** — AOPs are signed, multi-scale (molecular initiating event ->
  organism outcome) causal chains, i.e. a domain-specific qualitative VPH fragment; a useful
  template for PhysioMap edge typing and cross-scale chaining.

---

## Files in this folder

| File | Status | Pages read |
|------|--------|-----------|
| `Coveney2011_vph-introduction.pdf` | READ | 1–5 (full) |
| `KohlNoble2009_systems-biology-vph.pdf` | READ | 1–6 (full) |
| `Hester2011_HumMod.pdf` | READ | 1–7 of 12 (core) |
| `Viceconti2016_vph-ten-years.pdf` | READ | 1–18 (full) |
| Guyton 1972 | STUB | — |
| Hunter & Borg 2003 | STUB | — |
| Bassingthwaighte 2000 | STUB | — |
| Lloyd (CellML) 2004 | STUB | — |
| Hucka (SBML) 2003 | STUB | — |
