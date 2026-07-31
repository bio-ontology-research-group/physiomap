# Adverse Outcome Pathways (AOPs) — Curated Literature Notes

Theme folder: `resources/adverse-outcome-pathways/`
Curated for the **PhysioMap** project (qualitative, cyclic, signed cross-scale causal map of human physiology).
Compiled 2026-06-02. Only papers downloaded+read or stubbed with a verified abstract are cited below.

---

## (a) Overview of the AOP line of research

The **Adverse Outcome Pathway (AOP)** is a conceptual framework from regulatory/predictive toxicology
that organizes mechanistic knowledge as a **causal chain** running across biological levels of organization:

```
  MIE  --KER-->  KE  --KER-->  KE  --KER-->  ...  --KER-->  AO
 (molecular)   (cellular)   (tissue/organ)        (organism / population)
```

- **MIE (Molecular Initiating Event):** the upstream anchor; the point where a chemical/stressor directly
  perturbs a biomolecule (receptor, enzyme, DNA). By definition at the molecular level.
- **KE (Key Event):** a *measurable change in biological state* that is essential (but not necessarily
  sufficient) for progression toward the AO. **KEs are the nodes.**
- **AO (Adverse Outcome):** the downstream anchor; a change at a level of organization tied to a
  protection goal / apical regulatory endpoint (usually organ level or higher, up to population/ecological).
- **KER (Key Event Relationship):** a *directed* relationship between an upstream and downstream KE.
  **KERs are the edges.** A KER is the unit of inference/extrapolation; its credibility is set by
  **weight of evidence (WoE)** = biological plausibility + empirical support (dose-response, temporal,
  incidence concordance). KERs give an AOP its predictive utility; KEs give it verifiability.

The concept originated with **Ankley et al. 2010** (ecotoxicology), was formalized into development
principles/best-practices by **Villeneuve et al. 2014 (I & II)**, and is governed by OECD guidance (2013/2016)
and the **AOP-Knowledgebase (AOP-KB)** — most actively the open, collaboratively-edited **AOP-Wiki**
(aopwiki.org), plus Effectopedia (quantitative KER data), AOP-Xplorer (network visualization in Cytoscape),
e.AOP.Portal, and an Intermediate Effects Database.

Five core development principles (Villeneuve 2014 I): (1) AOPs are **not chemical-specific** (they describe
biology, not a compound); (2) AOPs are **modular** — KEs and KERs are reusable, shareable building blocks;
(3) an **individual AOP** (single non-branching MIE→AO chain) is the pragmatic unit of development/evaluation;
(4) **AOP networks** (multiple AOPs sharing KEs/KERs) are the functional unit of prediction for real-world
scenarios; (5) AOPs are **living documents** that evolve with evidence.

Maturity ladder: *putative* → *qualitative (formal)* → *quantitative (qAOP)*. A **qAOP** quantifies KERs as
response–response functions so that the magnitude/probability of the AO can be predicted from the degree of
MIE perturbation (Conolly 2017; Spinu 2020). AOP **networks** are analyzed with graph theory / network science
(degree, centrality, critical paths, convergence/divergence, bow-tie motifs) (Knapen 2018; Villeneuve 2018).

Crucial subtlety for our purposes: in an AOP network each KE node encodes a **signed directional state change**
— a *decrease* in a hormone is a different node from an *increase* in that hormone (Villeneuve 2018). The
AOP framework was originally **acyclic** (DAG-like chains), but feedback/feedforward loops and modulating
factors are now handled as **data "layers"** on the network (Knapen 2018; Villeneuve 2018) and explicitly
modeled in qAOPs (Conolly 2017 HPG feedback; Spinu 2020 lists "feedback loops" / "compensatory mechanisms"
as qAOP features).

---

## (b) Per-paper entries

### 1. Ankley et al. 2010 — Conceptual framework  *(stub: `Ankley2010_AOP-conceptual-framework.stub.md`)*
*Environ. Toxicol. Chem.* 29(3):730–741. DOI 10.1002/etc.34. **[NO PDF — stub, verified abstract]**

The founding paper. Introduces AOP as the linkage between a direct MIE and an AO at a regulatorily relevant
level of biological organization, with KEs as intermediate measurable responses. Argues the abstraction
improves cross-species extrapolation, chemical category formation, mixture-effect forecasting, and use of
molecular biomarkers to predict organism/population effects. (Read via verified PubMed abstract; full text paywalled.)

**Relevance to PhysioMap:** The progenitor of the cross-scale signed causal-pathway idea. KE ≈ (entity, quality)
node typed by scale; KER ≈ directed causal edge; MIE/AO ≈ scale-anchored boundary nodes. Confirms the design
choice that physiology/toxicology can be encoded as chains of measurable state-changes linked by causation
across levels of organization.

### 2. Villeneuve et al. 2014 (I) — Strategies and Principles  *(`Villeneuve2014_AOP-development-strategies.pdf`, read pp. 1–9 / full)*
*Toxicol. Sci.* 142(2):312–320. DOI 10.1093/toxsci/kfu199. **OA (US Gov public domain).**

Lays out the five core principles (above) and five development strategies (top-down, bottom-up, middle-out,
case-study, by-analogy, data-mining). Table 1 is the canonical KE/KER/MIE/AO definition set; explicitly states
"in a graph theory context, KEs represent nodes and KERs represent edges." KEs are state measurements (give
verifiability); KERs are units of inference defined by biological plausibility + WoE (give predictive utility).
Introduces the 3-phase maturity ladder (putative/qualitative/quantitative) and the AOP-Wiki/AOP-KB model of
modular reusable pages. Notes that AOPs deliberately collapse complex systems-biology crosstalk into single
chains for tractability, with networks recovering the complexity.

**Relevance to PhysioMap:** The single most directly applicable methodological paper. (i) Node=KE / edge=KER
graph semantics is exactly PhysioMap's data model. (ii) **Modularity + reusability** = PhysioMap nodes/edges
as shared, individually-curated, IRI-addressable units that compose into larger maps — argues for a
knowledgebase architecture (AOP-Wiki as a template). (iii) The pragmatic single-chain vs. network distinction
maps to PhysioMap's choice to represent feedback explicitly (cycles) rather than collapse them. (iv) Maturity
ladder mirrors PhysioMap's qualitative-now / quantitative-later trajectory.

### 3. Vinken/Leonard et al. 2018 — A concise introduction for toxicologists  *(`Leonard2018_AOP-concise-introduction.pdf`, read pp. 1–6)*
(Vinken, Knapen, Vergauwen, Hengstler, Angrish, Whelan) *Arch. Toxicol.* 91(11):3697–3707, 2017. DOI 10.1007/s00204-017-2020-z. **OA author manuscript.**

A clean "helicopter view." Distinguishes AOP from the older **Mode-of-Action** concept: MoA is chemical-specific
and includes kinetics (ADME); AOP is **chemical-agnostic**, describing the toxicodynamic process purely
biologically, and can extend up to population/ecological levels. ADME/kinetics enter only at the *application*
phase to connect external exposure to internal dose at the MIE. Recaps the AOP-KB modules, the five principles,
the tailored Bradford-Hill WoE assessment, and applications (IATA, chemical categories, prioritization, assay
development). Two case studies: skin sensitization (human) and aromatase inhibition (fish).

**Relevance to PhysioMap:** The MoA-vs-AOP distinction clarifies PhysioMap's stance: PhysioMap edges should be
**mechanism/intervention statements about biology** (chemical-agnostic, like AOPs), with perturbations
(theta) and kinetics layered on at "application" time — paralleling sign(dx*/dθ). Reinforces that the same
causal backbone serves both human and comparative physiology.

### 4. Wittwehr et al. 2017 — AOPs for computational prediction models  *(`Wittwehr2017_AOP-computational-prediction.pdf`, read pp. 1–6)*
*Toxicol. Sci.* 155(2):326–336. DOI 10.1093/toxsci/kfw207. **OA (CC BY-NC).**

How AOPs guide building computational/in-silico prediction models. Key insight: the AOP **bounds the modeling
problem** — the box-and-arrow diagram defines which biological pathways, compartments, and **scales** a model
(or series of linked models) must operate at; it "provides a road map of the biological scales." KE descriptions
suggest modeling formalism (enzyme inhibition→kinetics; cell proliferation→agent-based; risk→probabilistic);
KER descriptions define **input→output (response–response) relationships**, ideally with functional form
(linear/sigmoidal/Bayesian), uncertainty bounds, and **time-scale of coupling** between KE_up and KE_down.
Four worked case examples: aromatase/reproduction in fish (multi-scale model chain, molecular→population),
skin sensitization (Bayesian network), thyroid-hormone disruption (convergent AOP network), ERα activation.

**Relevance to PhysioMap:** Directly addresses cross-scale model composition. The notion that the qualitative
AOP graph *specifies the scales and coupling/timescales* a dynamical model must respect is precisely
PhysioMap's intended use: the signed cyclic causal map as the skeleton onto which quantitative comparative
statics / dynamics are hung. The KER "response–response with uncertainty and timescale" annotation is the
quantitative refinement of PhysioMap's +/-/? edge labels.

### 5. Knapen et al. 2018 — AOP Networks I: Development and Applications  *(`Knapen2018_AOP-networks-I.pdf`, read pp. 1–6)*
*Environ. Toxicol. Chem.* 37(6):1723–1733. DOI 10.1002/etc.4125. **OA (EPA author manuscript).**

Defines an **AOP network** = assembly of ≥2 AOPs sharing ≥1 KE (incl. shared MIE or AO). Distinguishes
*network-guided AOP development* (intentionally sharing KE/KER pages so networks emerge by default in the
AOP-Wiki) from *AOP network derivation* (extracting + linking existing AOP-KB content into a "primary network").
Networks are refined for a given question via **filters** (taxonomic / life-stage / sex / biological-level /
network-metric / confidence filters) and enriched via **data layers**. Critically, this is where **feedback
loops, feedforward loops, and modulating factors** are reintroduced — as layers on top of the basic acyclic
framework — so the core AOP stays simple while dynamics are captured.

**Relevance to PhysioMap:** The networks-from-modules story is PhysioMap's composition model. The **filter/layer**
mechanism is a concrete pattern for PhysioMap: keep one canonical signed causal graph, then derive
context-specific subgraphs (e.g., a specific organ system, scale band, or the Guyton CV fragment) via
structured filters, and overlay dynamic information (feedback signs, modulators) as layers. Confirms that the
toxicology community had to *bolt cycles onto* an acyclic base — PhysioMap's decision to make **cycles
first-class** is a principled improvement for physiology, where feedback is the norm.

### 6. Villeneuve et al. 2018 — AOP Networks II: Network Analytics  *(`Villeneuve2018_AOP-networks-II-analytics.pdf`, read pp. 2–6)*
*Environ. Toxicol. Chem.* 37(6):1734–1748. DOI 10.1002/etc.4124. **OA (EPA author manuscript).**

Applies graph theory / network science to AOP networks. Three points especially load-bearing for us:
(1) **Each KE node is a signed directional state change** — a decrease in a hormone/enzyme-activity/heart-rate
is a *distinct node* from an increase; (2) AOP networks, unlike most biological networks, **span multiple
levels of organization** and prioritize **predictive utility over biological fidelity** (KEs may be the minimal
set needed for inference); (3) network topology analyses — degree, in/out-degree, centrality, **critical paths**,
**convergence/divergence points**, and **bow-tie motifs** (a convergent "knot" KE that fans out) — identify
integrative control points and pleiotropic hubs. Caveats: networks reflect only what's been curated; high
connectivity ≠ biological importance; AOP-Wiki has limited formal QA.

**Relevance to PhysioMap:** The most technically aligned paper. **Signed directional nodes** validate
PhysioMap's (entity, PATO quality) node design where the *direction/quality* matters (increase vs decrease).
Multi-scale spanning + predictive-over-fidelity matches PhysioMap exactly. Bow-tie/convergence/centrality
analyses are ready-made tools for analyzing PhysioMap's cyclic signed graph (e.g., finding control hubs in the
Guyton fragment). The QA caveat is a direct lesson: PhysioMap must attach provenance/WoE to every edge.

### 7. Spinu et al. 2020 — Quantitative AOP (qAOP) models for toxicity prediction  *(`Spinu2020_qAOP-models.pdf`, read pp. 1–7)*
*Arch. Toxicol.* 94(5):1497–1510. DOI 10.1007/s00204-020-02774-7. **OA (CC BY).**

Systematic review proposing five **common features** of a qAOP (problem formulation; mechanistic knowledge+data;
quantitative approach; regulatory applicability; additional considerations) and surveying 5 probabilistic
(Bayesian network) + 10 mechanistic qAOP models. Distinguishes three qAOP classes: semi-quantitative WoE,
probabilistic (Bayesian-network), and mechanistic (ODE/compartment) qAOPs. OECD definition of qAOP = KEs with
measurable accuracy/precision + KERs with quantitative understanding of *what magnitude/duration of change in
KE_up evokes what magnitude of change in KE_down*. The feature tables explicitly track **feedback loops,
compensatory mechanisms, modulating factors, kinetics, dose/concentration-response (D/C–R), time-response (T–R),
cross-species extrapolation, sensitivity analysis, and uncertainty** across models — and note ODE-based models
produce linear/sigmoidal/Gaussian response shapes.

**Relevance to PhysioMap:** The bridge from qualitative signed edges to quantitative dynamics. The qAOP
class taxonomy (WoE / Bayesian / mechanistic-ODE) is a roadmap for how a PhysioMap edge could be progressively
quantified. The feature checklist (feedback loops, compensation, D/C-R, T-R, sensitivity, uncertainty) is a
strong candidate **annotation schema for PhysioMap edges**. Confirms that mechanistic qAOPs are ODE/SCM-like
systems whose steady states give the comparative-statics predictions PhysioMap targets, and that feedback +
compensation are explicitly representable.

### 8. Conolly et al. 2017 — Quantitative AOPs & predictive toxicology  *(stub: `Conolly2017_qAOP-predictive-toxicology.stub.md`)*
*Environ. Sci. Technol.* 51(8):4661–4672. DOI 10.1021/acs.est.6b06230. **[NO PDF — stub, verified abstract]**
(PMC author manuscript PMC6134852 is gated behind an NCBI JavaScript proof-of-work challenge; ACS source paywalled.)

The flagship mechanistic qAOP: aromatase (CYP19) inhibition → reproductive failure → population decline in
fathead minnow (AOP:25), built from four linked sub-models — a mechanistic **HPG (hypothalamus–pituitary–gonad)
feedback model**, a vitellogenin liver compartment model, a statistical VTG→fecundity model, and a
density-dependent population matrix model — spanning molecular→cellular→organ→organism→population.

**Relevance to PhysioMap:** Demonstrates a qualitative cross-scale causal pathway promoted to a coupled
dynamical model with an **explicit endocrine feedback (cyclic) subsystem** — the closest toxicology analogue
to PhysioMap's cyclic signed maps and the Guyton CV feedback fragment. The molecular→population model chain is
PhysioMap's cross-scale composition; its steady states are the equilibria from which sign(dx*/dθ) is read.
(See Wittwehr 2017 Case Example 1 for the diagram, which we *did* read in full.)

### 9. Becker et al. 2015 — Tailored Bradford-Hill / weight of evidence  *(stub: `Becker2015_AOP-Bradford-Hill-WoE.stub.md`)*
*Regul. Toxicol. Pharmacol.* 72(3):514–537. DOI 10.1016/j.yrtph.2015.04.004. **[NO PDF — stub, verified abstract]** (ScienceDirect paywalled, 403)

The canonical AOP weight-of-evidence method: **tailored Bradford-Hill considerations** — biological plausibility,
**essentiality** of KEs, and empirical support (dose-response, temporal, incidence concordance) — each scored
high/moderate/low for every KE, KER, and the AOP overall; plus a prototype MCDA confidence model. (Heavily
referenced by Villeneuve 2014, Wittwehr 2017, Leonard 2018, and Spinu 2020, all of which we read.)

**Relevance to PhysioMap:** The provenance/confidence layer PhysioMap edges need. Each signed causal edge can
carry a structured WoE record: biological plausibility + empirical support (dose-response, temporal, incidence
concordance), and node **essentiality** ≈ the interventionist test (does perturbing/knocking out the node change
the downstream variable?) — the empirical grounding for an interventionist causal edge. Dose-response +
temporal concordance are the data that justify the **sign** (+/−) and rule out spurious edges (?).

---

## (c) Synthesis & relevance to PhysioMap

1. **AOPs are PhysioMap's exact structural twin from toxicology.** KE = (biological entity, quality/state)
   node typed by biological scale (molecular→population); KER = directed causal edge; MIE/AO = scale-anchored
   boundary nodes. The "KE = node, KER = edge" graph semantics is stated verbatim in Villeneuve 2014.
   PhysioMap's main additions are (i) PATO qualities + ontology IRIs as the formal node typing, and
   (ii) making **feedback cycles first-class** rather than a bolt-on layer.

2. **Signed directional nodes are validated.** Villeneuve 2018 makes "increase in X" and "decrease in X"
   *separate nodes*. PhysioMap instead pushes direction onto **edge signs (+/−/?)** with a single
   (entity, quality) node — a more compact encoding, but the AOP precedent confirms that direction of change is
   the load-bearing information and must be represented somewhere.

3. **The qualitative→quantitative ladder mirrors PhysioMap's plan.** putative → qualitative(formal) → qAOP
   (Villeneuve 2014; Spinu 2020) parallels PhysioMap's "signs now, dynamics later." A KER refined into a
   **response–response function with sign, shape, uncertainty, and timescale** (Wittwehr 2017; Spinu 2020) is
   the quantitative version of a PhysioMap signed edge; sign(dx*/dθ) is its qualitative limit.

4. **KERs already carry the evidence/WoE machinery PhysioMap needs.** Becker 2015's tailored Bradford-Hill
   (biological plausibility + dose-response/temporal/incidence concordance + KE essentiality) is a ready-made
   schema for per-edge confidence and provenance. **Essentiality ≈ the interventionist criterion** underpinning
   PhysioMap's interventionist causal edges; dose-response/temporal concordance justify the edge **sign**.

5. **Feedback and cycles: AOPs reveal a gap PhysioMap fills.** The AOP base framework is acyclic; loops,
   feedforward, compensation, and modulators are handled as **data layers** (Knapen 2018; Villeneuve 2018) or
   only inside qAOPs (Conolly 2017's HPG loop; Spinu 2020's "feedback loops/compensatory mechanisms" feature).
   PhysioMap's native cyclic SCM + σ-separation reasoning is the principled answer for physiology, where
   feedback (e.g., Guyton CV regulation) is the rule.

6. **Cross-scale links: AOP KERs blur causal and constitutive — PhysioMap must keep them distinct.** AOPs
   chain KEs across levels of organization with a single edge type (KER). PhysioMap's discipline of
   **within-scale = signed causal** vs **cross-scale = constitutive (part_of + determination, non-causal)** is
   a sharper ontology. The AOP literature (Wittwehr 2017: "AOP provides a road map of the biological scales")
   supports treating scale as explicit, but does not separate causal from constitutive — a PhysioMap refinement.

7. **AOP networks = composition + analysis toolkit, ready to reuse.** Modular reusable nodes/edges (Villeneuve
   2014), filters/layers to derive context-specific subgraphs (Knapen 2018), and graph-theoretic analytics —
   degree, centrality, critical paths, convergence/divergence, **bow-tie motifs** (Villeneuve 2018) — are
   directly applicable to analyzing PhysioMap's cyclic signed graph and extracting fragments like the Guyton
   slice. Bow-tie "knot" KEs are candidate physiological control hubs.

8. **AOP-Wiki is the model knowledgebase to emulate.** Open, collaborative, modular pages for each KE and KER,
   structured + free-text fields, OECD review for endorsed AOPs, network derivation tooling (AOP-Xplorer in
   Cytoscape), and quantitative KER data (Effectopedia). PhysioMap should adopt this architecture: IRI-addressable
   node/edge records with structured provenance, supporting both manual curation and programmatic network
   derivation. **Caveat (Villeneuve 2018): the AOP-Wiki has limited formal QA** — PhysioMap should make
   per-edge WoE/provenance mandatory to avoid the "high connectivity mistaken for importance" trap.

9. **Predictive utility over biological fidelity.** AOPs deliberately collapse systems-biology complexity to the
   minimal node set that supports inference (Villeneuve 2014, 2018). This justifies PhysioMap being a
   *qualitative comparative-statics* tool rather than a full mechanistic simulation — abstraction is a feature.

---

## (d) Cross-links to other PhysioMap resource themes

- **mechanism-ontology / `../mechanism-ontology/`:** KE/KER ↔ entity+quality and causal-relation ontology
  patterns; AOP-Wiki's structured KE/KER fields and OECD event/relationship ontology terms are precedent for
  PhysioMap's PATO-qualities + IRI typing of nodes and the within-scale-causal / cross-scale-constitutive split.
- **causal-knowledge-graphs / `../causal-knowledge-graphs/`:** AOP networks ARE causal KGs (signed, directed,
  multi-scale). Network derivation + filters/layers (Knapen 2018) and topology analytics (Villeneuve 2018) are
  reusable KG-construction and KG-analysis methods. WoE (Becker 2015) is the edge-provenance/confidence model.
- **causal-foundations / ode-causality / `../causal-foundations/`, `../ode-causality/`:** qAOPs as mechanistic
  ODE/Bayesian SCMs (Conolly 2017; Spinu 2020) connect AOP edges to the steady-state cyclic-SCM semantics and
  comparative statics sign(dx*/dθ) that PhysioMap uses; the HPG feedback loop is a concrete cyclic-SCM example.
- **qualitative-reasoning / `../qualitative-reasoning/`:** the qualitative AOP (signs, monotone response shapes,
  feedback layers) is qualitative reasoning over a physiological/toxicological causal graph.
- **virtual-physiological-human / `../virtual-physiological-human/`:** Wittwehr 2017's multi-scale model
  composition (molecular→population) and the AOP-as-scale-roadmap idea connect AOPs to VPH-style multi-scale
  modeling; AOPs supply the qualitative causal skeleton VPH models can be hung on.
- **mendelian-randomization / `../mendelian-randomization/`:** KE **essentiality** (Becker 2015) is an
  interventionist/instrumental test of a causal edge — conceptually adjacent to MR's use of instruments to
  establish causal direction and sign.

---

## File inventory

| File | Status | Pages read |
|---|---|---|
| `Villeneuve2014_AOP-development-strategies.pdf` | PDF (OA, 278 KB) | full, pp.1–9 |
| `Leonard2018_AOP-concise-introduction.pdf` (Vinken et al.) | PDF (OA, 964 KB) | pp.1–6 |
| `Wittwehr2017_AOP-computational-prediction.pdf` | PDF (OA, 580 KB) | pp.1–6 |
| `Knapen2018_AOP-networks-I.pdf` | PDF (OA, 658 KB) | pp.1–6 |
| `Villeneuve2018_AOP-networks-II-analytics.pdf` | PDF (OA, 941 KB) | pp.2–6 |
| `Spinu2020_qAOP-models.pdf` | PDF (OA, 898 KB) | pp.1–7 |
| `Ankley2010_AOP-conceptual-framework.stub.md` | stub (paywalled) | verified abstract |
| `Conolly2017_qAOP-predictive-toxicology.stub.md` | stub (PMC PoW-gated) | verified abstract + Wittwehr Case 1 |
| `Becker2015_AOP-Bradford-Hill-WoE.stub.md` | stub (paywalled, 403) | verified abstract |

**6 PDFs read + 3 verified stubs = 9 papers.**
