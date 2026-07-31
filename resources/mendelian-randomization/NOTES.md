# Mendelian Randomization — Curated Read Library

Theme curator notes for the **PhysioMap** project (qualitative, cyclic, signed causal
map of human physiology). This folder collects the seminal and most PhysioMap-relevant
literature on **Mendelian randomization (MR)** and its connection to causal inference,
instrumental variables (IV), and signed/mechanistic causal edges.

All PDFs listed below were **downloaded and read** (page counts noted per entry). One
paywalled paper (Lawlor 2008) is captured as a verified-abstract stub. No citations,
DOIs, or findings here are fabricated.

---

## (a) Overview of the MR line of research

Mendelian randomization is a strategy for **causal inference from observational data**
that exploits a natural experiment: because alleles are assorted approximately at random
from parents to offspring at conception, germline genetic variants associated with a
modifiable exposure act as **instrumental variables (IVs)** for that exposure. By
analogy with the random treatment allocation in a randomized controlled trial (RCT), a
genetic variant divides the population into subgroups that differ in long-term average
exposure but not (in principle) in confounders, so the variant→outcome association can be
used to test, and sometimes estimate, the **causal effect** of the exposure on the
outcome free of unmeasured confounding and reverse causation. The framework was named and
popularized by Davey Smith & Ebrahim (2003) as a response to the repeated failure of
conventional observational epidemiology (e.g. β-carotene, vitamin E, HDL-cholesterol,
HRT) to predict RCT results. It rests on three core IV conditions — **relevance** (the
variant is associated with the exposure), **exclusion restriction** (the variant affects
the outcome only through the exposure), and **independence/exchangeability** (the variant
is independent of confounders) — plus, for point estimation, a fourth point-estimate-
identifying condition (e.g. homogeneity / no effect modification) and, for most methods, a
**linearity** assumption. The field has since elaborated a large methodological toolkit:
two-sample MR (using two GWAS), MR-Egger and other pleiotropy-robust estimators, network
and multivariable MR (MVMR) for mediation and direct/indirect effects, bidirectional MR
and Steiger filtering for causal direction, two-step (epigenetic) MR, factorial MR, and
platforms such as MR-Base/TwoSampleMR that automate phenome-wide causal scans over
billions of GWAS associations. The central threat throughout is **horizontal
pleiotropy** (a variant affecting the outcome through a path other than the exposure),
which is exactly an exclusion-restriction violation; much of the methodology is dedicated
to detecting and correcting it.

---

## (b) Per-paper entries

### 1. Davey Smith & Ebrahim 2003 — the founding paper
- **Citation:** Davey Smith G, Ebrahim S. (2003) "'Mendelian randomization': can genetic
  epidemiology contribute to understanding environmental determinants of disease?"
  *International Journal of Epidemiology* 32(1): 1–22. DOI: 10.1093/ije/dyg070.
- **File:** `DaveySmith2003_MR_genetic_epidemiology.pdf` — read pp. 1–3 of 22 (abstract,
  intro, concept-of-MR section; the conceptual core).
- **Problem:** Observational epidemiology produces non-replicable, confounded
  associations that RCTs later overturn (β-carotene/lung cancer, vitamin C/CHD).
- **Method/idea:** Use the random assortment of genes at conception as a natural
  randomization device; a polymorphism that "mimics the biological link" of a proposed
  exposure is largely immune to reverse causation and to the social/behavioural
  confounding that vitiates conventional exposure measurements.
- **Key result:** Articulates and names the MR paradigm; catalogues its limitations up
  front — LD-confounding, **pleiotropy**, lack of suitable polymorphisms, and
  **canalization** (developmental buffering of genetic perturbations).
- **Relevance to PhysioMap:** This is the conceptual root for treating an *intervention on
  one variable* as the identifying device for a causal edge. The named limitations
  (pleiotropy, canalization/compensation) are exactly the failure modes a signed
  physiological causal map must reason about: a "+" edge can be masked by homeostatic
  compensation, which is the biological analogue of a feedback loop damping a perturbation.

### 2. Lawlor et al. 2008 — MR as instrumental-variable analysis  [STUB, no PDF]
- **Citation:** Lawlor DA, Harbord RM, Sterne JAC, Timpson N, Davey Smith G. (2008)
  "Mendelian randomization: using genes as instruments for making causal inferences in
  epidemiology." *Statistics in Medicine* 27(8): 1133–1163. DOI: 10.1002/sim.3034.
- **File:** `Lawlor2008_genes_as_instruments.stub.md` — paywalled (Wiley); verified
  abstract only.
- **Problem/method:** The formal biostatistics treatment that recasts MR explicitly as IV
  analysis (relevance, exclusion restriction, independence-of-confounders), drawing the
  RCT analogy and importing econometric two-stage least-squares (2SLS) machinery.
- **Relevance to PhysioMap:** Canonical bridge between genetic-epidemiology MR and the
  formal IV/2SLS framework. Its content is faithfully reproduced in the OA Sanderson 2022
  Primer and Davey Smith & Hemani 2014 review, both held here.

### 3. Bowden, Davey Smith & Burgess 2015 — MR-Egger
- **Citation:** Bowden J, Davey Smith G, Burgess S. (2015) "Mendelian randomization with
  invalid instruments: effect estimation and bias detection through Egger regression."
  *International Journal of Epidemiology* 44(2): 512–525. DOI: 10.1093/ije/dyv080.
- **File:** `Bowden2015_MR_Egger.pdf` — read pp. 1–4 of ~14 (abstract, key messages,
  intro, model setup with IV1/IV2/IV3).
- **Problem:** With many genetic instruments, some are likely **invalid** due to
  horizontal pleiotropy, biasing the standard inverse-variance-weighted (IVW)/2SLS
  estimate.
- **Method:** View multi-instrument MR as a **meta-analysis**; pleiotropy bias is
  analogous to small-study bias, visible as asymmetry in a funnel plot. Adapt **Egger
  regression**: the intercept tests for directional pleiotropy and the slope gives a
  causal estimate that remains consistent even if *all* instruments are invalid, under the
  **InSIDE** assumption (instrument strength independent of direct effect).
- **Key result:** MR-Egger is a sensitivity analysis that can detect and correct
  directional pleiotropy at the cost of power.
- **Relevance to PhysioMap:** Formalizes "an edge that looks causal may be a confounded /
  side-channel association." The decomposition of each variant's total effect into a direct
  (pleiotropic) effect α_j plus an indirect (via-exposure) effect βγ_j is precisely the
  total = direct + indirect decomposition PhysioMap needs when an edge is mediated vs
  direct.

### 4. Davey Smith & Hemani 2014 — genetic anchors; the extensions review
- **Citation:** Davey Smith G, Hemani G. (2014) "Mendelian randomization: genetic anchors
  for causal inference in epidemiological studies." *Human Molecular Genetics* 23(R1):
  R89–R98. DOI: 10.1093/hmg/ddu328.
- **File:** `DaveySmithHemani2014_genetic_anchors.pdf` — read all 10 pages (full text +
  Boxes 1–4 + tables).
- **Problem/method:** A compact, conceptually rich review of MR foundations and its
  family of extensions.
- **Key content:** Box 1 = IV conditions + 2SLS; Box 2 = the **type-I (biological) vs
  type-II (mediated/"vertical") pleiotropy** distinction — type II *is the essence* of MR,
  type I is the threat; Box 3 = "complexity of associations" (circulating vs in-situ
  marker levels can invert the sign of an effect); Box 4 = two-step epigenetic MR. Covers
  **bidirectional MR** (instruments for both traits to resolve direction), **network MR**,
  **mediation/two-step**, factorial and multiphenotype MR, and hypothesis-free MR.
- **Relevance to PhysioMap (high):** The single best map of how MR maps onto causal
  *graphs*. Network MR ≈ "causal dissection of networks of gene interactions"; mediation
  (BMI→BP→CHD) is exactly a signed path through PhysioMap nodes; bidirectional MR addresses
  the direction of an edge — the core problem when a cyclic map allows A→B and B→A.

### 5. Burgess et al. 2015 — Network Mendelian randomization (mediation)
- **Citation:** Burgess S, Daniel RM, Butterworth AS, Thompson SG; EPIC-InterAct
  Consortium. (2015) "Network Mendelian randomization: using genetic variants as
  instrumental variables to investigate mediation in causal pathways." *International
  Journal of Epidemiology* 44(2): 484–495. DOI: 10.1093/ije/dyu176.
- **File:** `Burgess2015_network_MR.pdf` — read pp. 1–6 of 12 (abstract, key messages,
  methods, DAGs, regression-based + SEM estimators, direction-of-effect / reciprocal MR,
  technical issues).
- **Problem:** Decompose the effect of an exposure X on outcome Y into a **direct** effect
  and an **indirect** effect through a mediator Z, under unmeasured confounding.
- **Method:** Give X and Z each their own genetic IV (G_X, G_Z); estimate direct/indirect
  effects via repeated ratio/2SLS or via **structural equation models (SEMs)** on the DAG.
  Direction between X and Z is verified by "reciprocal MR."
- **Key result:** Estimators are consistent under IV conditions **plus linearity and
  homogeneity (no interaction)**; simulations show robustness to random heterogeneity.
- **Relevance to PhysioMap (very high):** Explicitly builds **causal networks** with IVs
  and SEM, decomposing total into direct+indirect effects — the qualitative skeleton of
  PhysioMap. Crucially it states a key limitation: MR estimates are **long-term/lifetime
  ("at conception")** relationships, and **changes over time and feedback between exposure
  and mediator cannot be addressed** by conventional MR. This is the explicit boundary
  between MR's acyclic-DAG assumptions and PhysioMap's *cyclic* feedback structure.

### 6. Hemani et al. 2018 — MR-Base / TwoSampleMR platform
- **Citation:** Hemani G, Zheng J, Elsworth B, ... Davey Smith G, Gaunt TR, Haycock PC.
  (2018) "The MR-Base platform supports systematic causal inference across the human
  phenome." *eLife* 7: e34408. DOI: 10.7554/eLife.34408.
- **File:** `Hemani2018_MRBase_TwoSampleMR.pdf` — read pp. 1–3 of 29 (abstract, eLife
  digest, MR principles, model setup).
- **Problem:** GWAS summary data are scattered and uncurated; 2SMR methods evolve fast and
  are hard for non-specialists.
- **Method:** A curated database (then ~11 billion SNP–trait associations from 1673 GWAS)
  + R packages (TwoSampleMR, MRInstruments) + web UI that automate harmonization,
  two-sample MR, and a suite of pleiotropy sensitivity analyses; enables phenome-wide and
  hypothesis-free causal scans.
- **Key result:** Demonstrates systematic, scalable causal inference (LDL→CHD example,
  PheWAS for pleiotropy detection).
- **Relevance to PhysioMap:** The practical engine for **populating edges at scale** —
  any candidate signed edge in a physiological map (exposure→quality) can in principle be
  queried/sign-checked against MR-Base. Reinforces vertical (mediating) vs horizontal
  (off-path) pleiotropy as the edge-validity criterion.

### 7. Sanderson et al. 2019 — multivariable MR (single- and two-sample)
- **Citation:** Sanderson E, Davey Smith G, Windmeijer F, Bowden J. (2019) "An
  examination of multivariable Mendelian randomization in the single-sample and two-sample
  summary data settings." *International Journal of Epidemiology* 48(3): 713–727. DOI:
  10.1093/ije/dyy262.
- **File:** `Sanderson2019_MVMR.pdf` — read pp. 1–3 of ~15 (abstract, key messages,
  intro, IV conditions, MVMR setup).
- **Problem:** Estimate the effect of **two or more correlated exposures** on one outcome;
  clarify what is estimated when a secondary exposure is a confounder, mediator,
  pleiotropic pathway, or collider.
- **Method:** Multivariable 2SLS (individual data) / multivariable IVW (summary data);
  instrument strength + validity assessed via the **Sanderson–Windmeijer conditional
  F-statistic** and the Sargan / generalized Cochran's Q tests.
- **Key result (load-bearing):** **MR estimates the *total* causal effect of an exposure;
  MVMR estimates the *direct* causal effect** of each exposure conditional on the others.
- **Relevance to PhysioMap (very high):** This total-vs-direct distinction is the
  qualitative comparative-statics question PhysioMap asks — `sign(dx*/dθ)` differs
  depending on which other nodes are held fixed (conditioned on). It also enumerates the
  four roles a third variable can play (confounder/mediator/pleiotropic-pathway/collider),
  which is the typology of graph motifs PhysioMap edges must be disambiguated against
  (esp. **collider bias** when conditioning).

### 8. Sanderson 2021 — Multivariable MR and Mediation
- **Citation:** Sanderson E. (2021) "Multivariable Mendelian Randomization and Mediation."
  *Cold Spring Harbor Perspectives in Medicine* 11(2): a038984. DOI:
  10.1101/cshperspect.a038984.
- **File:** `Sanderson2021_MVMR_mediation.pdf` — read pp. 1–4 of ~12 (abstract, intro,
  mediation framing, MVMR setup, MV-IV1/2/3 conditions).
- **Problem/method:** Connects MVMR to **counterfactual mediation analysis**: total =
  direct + indirect; proportion mediated = indirect/total; with explicit treatment of
  natural vs controlled direct/indirect effects (per VanderWeele/MacKinnon).
- **Key result:** MVMR (and network MR / two-step MR) can recover mediated effects under
  IV assumptions plus no-unobserved-confounding *of the mediator–outcome relationship* and
  no measurement error in exposure/mediator; restated MV-IV conditions require exposures be
  strongly predicted *conditional on the other exposures* (else multicollinearity → weak
  instruments).
- **Relevance to PhysioMap (high):** The cleanest statement of mediation in MR terms and
  its assumptions. The natural/controlled-direct-effect distinction is directly relevant
  to PhysioMap's interventionist semantics (hold-mediator-fixed = controlled direct
  effect). Also flags that mediation/MVMR currently does **not** handle interaction or
  feedback well — again the cyclic-map boundary.

### 9. Sanderson et al. 2022 — Nature Reviews Methods Primers
- **Citation:** Sanderson E, Glymour MM, Holmes MV, Kang H, Morrison J, Munafò MR, Palmer
  T, Schooling CM, Wallace C, Zhao Q, Davey Smith G. (2022) "Mendelian randomization."
  *Nature Reviews Methods Primers* 2: 6. DOI: 10.1038/s43586-021-00092-5.
  (Europe PMC author manuscript, PMC7614635.)
- **File:** `Sanderson2022_MR_primer.pdf` — read pp. 1–13 of ~30 (abstract through the
  full Experimentation / Conditions / Data / Results methods sections; the methodological
  core, incl. IVW, weak-instrument F>10, pleiotropy-robust methods, Steiger filtering).
- **Problem/method:** The authoritative modern primer: principles, the **four** MR
  conditions (3 IV + 1 point-estimate-identifying), individual- vs summary-level
  estimation (2SLS, allele scores, IVW), assessment of conditions, and a catalogue of
  pleiotropy-robust estimators (MR-Egger/InSIDE, weighted median/mode, MR-PRESSO, MR-RAPS,
  MR-CAUSE, sisVIME, MVMR), plus MR-GxE/MR-GENIUS, **nonlinear MR**, and **Steiger
  filtering** for misspecified/wrong-direction SNPs.
- **Key result:** Frames MR as one leg of **triangulation** — valuable precisely because
  its biases are *different from and uncorrelated with* those of other observational
  designs.
- **Relevance to PhysioMap (must-read):** The reference glossary for every assumption a
  causal-edge curator must respect. Especially: the **linearity assumption** (most MR is
  linear; nonlinear MR is the exception) — PhysioMap's *qualitative/sign* edges are a
  graceful way to sidestep functional-form commitments; **gene–environment equivalence**
  (MR speaks to *lifetime* effects of the variant, not a one-off intervention); and
  **triangulation** as the epistemic stance for combining MR-derived edges with
  ODE/mechanistic and KG-derived edges.

---

## (c) Synthesis & relevance to PhysioMap

1. **MR is interventionist causation made operational.** A genetic instrument is a
   `do()`-like perturbation of one node; the variant→outcome association identifies a
   causal edge under the IV conditions. This is the same interventionist semantics
   PhysioMap uses for within-scale signed edges — MR supplies an empirical, genetics-based
   way to *test the sign and existence* of such an edge from human population data.

2. **Total vs direct effect = the comparative-statics question.** MR gives the *total*
   effect of an exposure; MVMR/network MR give the *direct* effect conditional on
   mediators (Sanderson 2019/2021; Burgess 2015). PhysioMap's `sign(dx*/dθ)` predictions
   are exactly this total-vs-direct distinction made qualitative; the choice of what to
   condition on changes the predicted sign.

3. **Pleiotropy is confounding/off-path leakage of an edge.** Horizontal (type-I)
   pleiotropy = exclusion-restriction violation = a spurious or contaminated edge; vertical
   (type-II) pleiotropy = legitimate mediation through the node. PhysioMap edge curation
   must make the same distinction: is an observed dependency a true within-scale causal
   edge or a side-channel through another node/scale?

4. **Mediation decomposes a path; PhysioMap is built of such paths.** total = direct +
   indirect and "proportion mediated" (Burgess 2015; Sanderson 2021) give the quantitative
   logic behind PhysioMap's qualitative signed *paths*; natural vs controlled direct
   effects map onto "hold the mediator fixed" interventions.

5. **Direction of an edge is itself an MR question.** Bidirectional MR and Steiger
   filtering (Davey Smith & Hemani 2014; Sanderson 2022) attack exactly the A→B vs B→A
   ambiguity that PhysioMap confronts wherever reciprocal/feedback edges are allowed.

6. **The cyclic-feedback boundary is explicit in the MR literature.** Burgess (2015)
   states plainly that conventional MR cannot handle *time-varying effects or feedback
   between exposure and mediator* — its estimands are long-term/lifetime quantities on an
   acyclic DAG. PhysioMap's defining commitment to **cycles** is therefore *beyond* what
   standard MR identifies; MR informs the edges, but the cyclic-SCM / σ-separation
   machinery is PhysioMap's own contribution.

7. **Collider bias and conditioning.** MVMR's enumeration of a third variable as
   confounder/mediator/pleiotropic-pathway/**collider** (Sanderson 2019) is a direct
   warning for PhysioMap: conditioning on the wrong node (a collider/descendant) opens
   spurious associations — relevant to how σ-separation must treat conditioning sets in a
   cyclic graph.

8. **Qualitative/sign edges sidestep MR's linearity commitment.** Almost all MR assumes a
   linear, homogeneous, no-interaction exposure→outcome relationship (Sanderson 2022;
   Burgess 2015). PhysioMap's choice to record only edge *signs* (+/-/?) is a principled
   way to use MR evidence for *direction of effect* without inheriting its strong
   functional-form assumptions.

9. **Scale matters: MR is within-population, lifetime, cross-individual.** MR effects are
   long-run averages across individuals at the organism scale. This is consistent with
   PhysioMap treating MR-derived edges as *within-scale* (organism/physiology) causal
   edges — not as the constitutive cross-scale (part_of) edges, which MR says nothing
   about.

10. **Triangulation is the integration principle.** Sanderson 2022 frames MR as one
    evidence stream whose biases are uncorrelated with others. PhysioMap should treat
    MR-derived signs as one input to be triangulated with ODE/mechanistic models and
    causal knowledge graphs, not as ground truth.

11. **Tooling exists to populate edges at scale.** MR-Base/TwoSampleMR (Hemani 2018) makes
    it feasible to query candidate edges phenome-wide; a Guyton-cardiovascular slice
    (BMI→BP, BP→CHD, lipids→CHD, urate→BP, CRP non-causality) has direct MR evidence in
    these very papers.

---

## (d) Cross-links to other PhysioMap themes

- **Causal foundations (interventionist causation, do-operator, SCMs):** MR is the
  empirical instantiation of `do()` via a randomized instrument; the IV conditions are the
  identifiability conditions for an edge. MR's acyclic-DAG estimands contrast with
  PhysioMap's cyclic SCM + σ-separation — see the causal-foundations theme for the formal
  cyclic-SCM and σ-separation references that *extend beyond* what MR identifies
  (Burgess 2015 explicitly marks this boundary).
- **ODE / dynamical-systems causality:** MR estimates *steady-state, lifetime* effects;
  Burgess (2015) notes MR cannot capture feedback/time-varying dynamics. This is the
  precise complement to ODE-based causality (e.g. the Guyton cardiovascular model), which
  encodes the dynamics MR averages over. PhysioMap's qualitative comparative statics at the
  steady state of a cyclic SCM is the conceptual meeting point of the two.
- **Causal knowledge graphs (causal KGs):** MR-Base (Hemani 2018) is effectively a
  large-scale, machine-readable causal KG of signed exposure→outcome edges with sensitivity
  metadata; the type-I/type-II pleiotropy distinction is the edge-validity schema a KG
  curator needs. Ontology IRIs on PhysioMap nodes can be linked to GWAS trait/exposure
  identifiers used in MR-Base.
- **Mediation / network causality:** Network MR (Burgess 2015) and MVMR-mediation
  (Sanderson 2021) provide the direct/indirect decomposition that any path-based causal KG
  or signed map relies on.

---

## Inventory / provenance

| File | Pages read | Verified |
|------|-----------|----------|
| DaveySmith2003_MR_genetic_epidemiology.pdf | 1–3 / 22 | %PDF, 384 KB |
| Lawlor2008_genes_as_instruments.stub.md | abstract only (paywalled) | PubMed-verified |
| Bowden2015_MR_Egger.pdf | 1–4 / ~14 | %PDF, 757 KB |
| DaveySmithHemani2014_genetic_anchors.pdf | 1–10 / 10 (full) | %PDF, 472 KB |
| Burgess2015_network_MR.pdf | 1–6 / 12 | %PDF, 459 KB |
| Hemani2018_MRBase_TwoSampleMR.pdf | 1–3 / 29 | %PDF, 2.26 MB |
| Sanderson2019_MVMR.pdf | 1–3 / ~15 | %PDF, 634 KB |
| Sanderson2021_MVMR_mediation.pdf | 1–4 / ~12 | %PDF, 810 KB |
| Sanderson2022_MR_primer.pdf | 1–13 / ~30 | %PDF, 484 KB |

8 PDFs downloaded, verified (`head -c 5` = `%PDF`, all > 30 KB) and read; 1 paywalled
paper captured as a verified-abstract stub. Total: 9 curated items.
