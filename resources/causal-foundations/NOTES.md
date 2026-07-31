# Causal-Foundations — Curated Library Notes

**Theme.** Foundations of causal inference: structural causal models (SCMs), the
do-operator / interventions, d-separation, causal discovery, and the interventionist
theory of causation. This is the conceptual backbone for PhysioMap.

**Why this matters for PhysioMap.** PhysioMap edges have *interventionist* semantics and
the map instantiates a (possibly **cyclic**) structural causal model. Causal reasoning
under cycles uses **σ-separation**, which **reduces to d-separation in the acyclic case**.
So this library pins down, from the classical literature: (i) the precise semantics of
the do-operator / intervention, (ii) the d-separation criterion that σ-separation must
reduce to, and (iii) the interventionist (Woodward) account of "X causes Y" that
justifies our edge semantics. Cross-links to the project's ODE-causality and Mendelian
Randomization (MR) themes are given at the end.

---

## (a) Overview

The modern foundation is the **Structural Causal Model (SCM)** — a set of structural
assignments Xⱼ := fⱼ(PAⱼ, Nⱼ) with jointly independent noise — which simultaneously
defines (1) an observational distribution, (2) a family of *intervention*
distributions, and (3) counterfactuals. An SCM induces a directed graph; in the acyclic
(Markovian) case the induced distribution factorizes over the graph and satisfies the
**Markov property**, so conditional independencies can be read off graphically via
**d-separation**. Interventions are modeled by the **do-operator**, which surgically
replaces a variable's structural assignment by a constant (or new mechanism), leaving
the rest of the model intact; this is the formal counterpart of Woodward's
"arrow-breaking" **intervention**. **Causal discovery** (SGS/PC/FCI, LiNGaM, additive
noise models, SAT-based methods) infers structure from data under bridge assumptions
(Causal Markov + Faithfulness, ± causal sufficiency, ± acyclicity). Cyclic/feedback
models — PhysioMap's regime — are a recognized generalization where the equilibrium of a
dynamical (e.g. ODE) system is described by an SCM whose acyclic separation theory
(d-separation) generalizes to σ-separation.

Library contents (5 read PDFs/essays + 2 stubs):

| Item | Type | File |
|---|---|---|
| Pearl 2009, Causal inference in statistics: an overview | PDF (read) | `Pearl2009_causal-inference-overview.pdf` |
| Peters, Janzing & Schölkopf 2017, Elements of Causal Inference | PDF book (key chs read) | `PetersJanzingScholkopf2017_elements-causal-inference.pdf` |
| Pearl 1995, Causal diagrams for empirical research | PDF (read, partial) | `Pearl1995_causal-diagrams.pdf` |
| Eberhardt 2017, Introduction to the foundations of causal discovery | PDF (read in full) | `Eberhardt2017_foundations-causal-discovery.pdf` |
| Spirtes, Glymour & Scheines 2000, Causation, Prediction, and Search | stub | `SpirtesGlymourScheines2000_..._STUB.md` |
| Woodward 2003, Making Things Happen | stub | `Woodward2003_making-things-happen_STUB.md` |
| (Woodward, "Causation with a Human Face" essay) | read as cross-check for Woodward defs | — (not retained) |

---

## (b) Per-item entries

### 1. Pearl (2009) — "Causal inference in statistics: An overview". *Statistics Surveys* 3:96–146. DOI 10.1214/09-SS057. [OPEN ACCESS]
**File:** `Pearl2009_causal-inference-overview.pdf` (UCLA tech report R-350; %PDF, 580 KB).
**Pages read:** 1–15 (Abstract, §1–§3.2.3, through Theorem 1 / Causal Markov Condition;
includes the do-operator definition, d-separation Definition 1, identifiability).
**Summary.** The canonical accessible synthesis of the SCM framework. Establishes the
association-vs-causation distinction ("behind every causal conclusion there must lie some
causal assumption not testable in observational studies"). Introduces SCMs as
nonparametric structural equations z=f_Z(u_Z), x=f_X(z,u_X), y=f_Y(x,u_Y); defines the
**do-operator** as a model mutilation: do(X=x₀) replaces the equation for X with the
constant x₀, yielding the post-intervention distribution P(y|do(x₀)) := P_{M_x}(y) (Eq. 7).
Gives the **d-separation Definition 1** (the blocking criterion — see §(c)), **Theorem 1
(Causal Markov factorization)**, **Definition 2 (identifiability)**, the back-door
criterion for confounder selection, and the instrumental-variable analysis (§3.5) used
to bound effects under noncompliance. Notes that causal effects are identifiable
whenever the model is Markovian (acyclic + independent errors).
**Relevance to PhysioMap.** Primary source for do-operator semantics and the
d-separation criterion. The do(X=x₀) "surgery" is exactly PhysioMap's intervention
semantics. The IV section directly underpins the MR cross-link. The
Markovian/acyclic conditions clarify *what changes* in the cyclic case PhysioMap targets.

### 2. Peters, Janzing & Schölkopf (2017) — *Elements of Causal Inference*. MIT Press. ISBN 9780262037310. [OPEN ACCESS]
**File:** `PetersJanzingScholkopf2017_elements-causal-inference.pdf` (author-hosted KU
copy; %PDF, 22 MB).
**Pages read:** Front matter/Preface; Ch. 6 core — book pp. 82–106 and 121–123 (the most
PhysioMap-relevant): d-separation (Def 6.1), SCM (Def 6.2), entailed distribution
(Prop 6.3), **cyclic SCMs** (Eq. 6.2–6.4 and Remark 6.5), **Remark 6.7 relating SCMs to
ODEs**, interventions (Def 6.8) incl. atomic/imperfect/stochastic/soft, total causal
effect (Def 6.12 + Prop 6.13–6.14), the augmented-graph "intervention variable"
formulation, counterfactuals (Def 6.17), Markov property (Def 6.21) + equivalence,
Markov blanket, Reichenbach's principle (Prop 6.28), faithfulness/causal minimality
(§6.5), causal graphical models (Def 6.32), SCMs-imply-Markov (Prop 6.31).
**Summary.** Rigorous modern textbook. SCM C := (S, P_N) with assignments
Xⱼ := fⱼ(PAⱼ, Nⱼ), N jointly independent; entails a unique observational distribution,
plus intervention distributions and counterfactuals. **Crucially for PhysioMap it treats
cyclic structure head-on:** a linear assignment X := BX + N has the unique solution
X = (I−B)⁻¹N (Eq. 6.2) when I−B is invertible, with an **equilibrium-of-iteration**
interpretation X^t := BX^{t−1} + N (Eq. 6.3) converging when B's eigenvalues lie in the
unit circle. **Remark 6.7** makes the ODE connection explicit: an ODE system Ẋ = f(X)
can be represented by the assignment X_{t+Δt} := X_t + Δt·f(X_t), so an SCM describes how
the *equilibrium states* react to interventions (forcing terms) — "the framework is in
principle also applicable to cyclic structures." Intervention distribution (Def 6.8)
replaces structural assignment(s) and re-derives the entailed distribution; atomic
intervention = point mass do(X=a). The global Markov property is *defined via
d-separation*; faithfulness is the converse (independence ⇒ d-separation) and is an
assumption about the world (unlike structural minimality).
**Relevance to PhysioMap.** Best single reference for cyclic SCMs + the SCM↔ODE bridge
that PhysioMap's ODE-causality theme relies on. Its definition of the global Markov
property *as d-separation* is the exact acyclic statement σ-separation generalizes.

### 3. Pearl (1995) — "Causal diagrams for empirical research". *Biometrika* 82(4):669–710.
**File:** `Pearl1995_causal-diagrams.pdf` (%PDF, 2.5 MB; tech report R-218-B).
**Pages read:** 1–3 (Summary, §1 eelworm example, §2.1 d-separation Definition 1).
**Summary.** The historical introduction of causal diagrams as a query language. Shows
how a DAG encodes the qualitative assumptions (missing arrows = absence of causal
influence) and how to read off whether a causal effect is *identifiable* from
nonexperimental data. Introduces the do/x̌ ("x-check") intervention notation
pr(y|x̌); the **back-door criterion** (shown equivalent to Rosenbaum–Rubin ignorability)
and the **front-door criterion**; and the **do-calculus** as a symbolic calculus for
stepwise derivation of causal-effect formulas. Gives d-separation as Definition 1
(same blocking criterion as Pearl 2009).
**Relevance to PhysioMap.** Foundational source for do-calculus / identifiability and the
back-door & front-door criteria — the machinery for deciding when a PhysioMap-encoded
causal effect can be estimated from observational data.

### 4. Eberhardt (2017) — "Introduction to the foundations of causal discovery". *Int. J. Data Science and Analytics* 3:81–91. DOI 10.1007/s41060-016-0038-6.
**File:** `Eberhardt2017_foundations-causal-discovery.pdf` (Caltech author copy; %PDF,
596 KB). **Pages read:** all 11.
**Summary.** Organizes causal discovery by the *assumptions* methods require. Sets up
causal graphs (edge X→Y = X is a direct cause relative to V; intervention = remove all
edges into X), distinguishes P(Y|X) (observational) from P(Y|do(X)) (interventional).
States the two bridge principles: **Causal Markov** (X ⊥ NonDesc(X) | Pa(X)) and **Causal
Faithfulness** (independence ⇒ d-separation), which together give d-sep ⟺ conditional
independence. Defines **d-connection/d-separation** via colliders. Reviews what is
learnable: constraint-based PC recovers only the **Markov equivalence class** (Thm:
Markov completeness for linear-Gaussian/multinomial); stronger parametric assumptions
escape this — **LiNGaM** (linear non-Gaussian, Thm 2, via Darmois–Skitovich) and
**nonlinear additive-noise models** (Thm 4, Hoyer condition) give *full* identifiability.
Covers FCI (drops causal sufficiency), and **SAT/constraint-based methods that drop both
sufficiency AND acyclicity (CCD), explicitly handling feedback/cycles.** Footnote 5
flags the subtleties of allowing causal cycles and points to cyclic-model references.
**Relevance to PhysioMap.** The "which assumptions buy which identifiability" map for any
data-driven inference of PhysioMap structure; importantly it names the cyclic/feedback
discovery methods (CCD, SAT-based) relevant to PhysioMap's cyclic SCM.

### 5. Spirtes, Glymour & Scheines (2000) — *Causation, Prediction, and Search* (2nd ed.). MIT Press. [STUB]
**File:** `SpirtesGlymourScheines2000_causation-prediction-search_STUB.md`. Not OA; no PDF.
**Summary / relevance:** see stub. Canonical source for Causal Markov + Faithfulness and
the PC/FCI constraint-based discovery algorithms; the acyclic d-separation framework
σ-separation reduces to.

### 6. Woodward (2003) — *Making Things Happen*. Oxford UP. [STUB]
**File:** `Woodward2003_making-things-happen_STUB.md`. Paywalled; no PDF. The verbatim
interventionist definitions (I1–I4 intervention variable; (M) direct cause; contributing
cause) are captured precisely in the stub and reproduced in §(c) below. Cross-checked
against Woodward's essay "Causation with a Human Face" (read locally).
**Relevance:** the philosophical justification for PhysioMap's interventionist edge
semantics; (M) is precisely what a PhysioMap edge asserts.

---

## (c) SCMs, interventions, and d-separation (anchor for our formalism)

### Structural Causal Model (SCM)
An SCM C := (S, P_N) is a set of d structural assignments
> **Xⱼ := fⱼ(PAⱼ, Nⱼ)**, j = 1,…,d, with noise variables N = (N₁,…,N_d) jointly independent.
PAⱼ ("parents" / **direct causes**) are the arguments of fⱼ; the induced graph G has an
edge from each member of PAⱼ to Xⱼ. In the **acyclic (Markovian)** case the SCM entails a
unique observational distribution that **factorizes** over G:
> P(x₁,…,x_d) = ∏ⱼ P(xⱼ | pa_j)   (Causal Markov factorization; Pearl 2009 Thm 1).
In the **cyclic** linear case X := BX + N, the entailed distribution is
X = (I−B)⁻¹N (when I−B invertible), interpretable as the **equilibrium** of the iteration
X^t := BX^{t−1} + N (Peters et al. Eq. 6.2–6.4). An SCM can approximate an **ODE system**
Ẋ = f(X) via X_{t+Δt} := X_t + Δt·f(X_t), so the SCM describes how the system's
*equilibrium* responds to interventions (Peters et al. Remark 6.7).

### The do-operator / intervention semantics
An intervention **replaces** one or more structural assignments and re-derives the
entailed distribution of the *new* SCM:
> **do(Xₖ = a):** replace `Xₖ := fₖ(PAₖ, Nₖ)` by `Xₖ := a` (an **atomic** intervention,
> point mass). The post-intervention distribution is
> **P_M(y | do(X=x)) := P_{M_x}(y)** (Pearl 2009 Eq. 7).
The rest of the mechanisms (the other fⱼ and the noise) are left untouched — the
intervention is *surgical / modular*. Generalizations: **imperfect/soft** (new parents
or a new mechanism rather than a constant), **stochastic** (set X to a distribution).
Intervening is generally **≠** conditioning: P(y | do(x)) ≠ P(y | x) in general.
A **total causal effect** from X to Y exists iff X ⫫̸ Y in P^{do(X:=Ñ_X)} for some Ñ_X
(Peters et al. Def 6.12).

### d-separation (the criterion σ-separation must reduce to)
**Definition (Pearl 1995 Def 1 / 2009 Def 1; Peters et al. Def 6.1).** In a DAG G, a path
p between two nodes is **blocked** by a set S iff there is an intermediate node w on p
such that *either*
- (i) w is a **non-collider** (chain `→ w →` or fork `← w →`) and w ∈ S; *or*
- (ii) w is a **collider** (`→ w ←`) and *neither* w *nor any descendant of w* is in S.

S **d-separates** disjoint sets A and B (written **A ⫫_G B | S**) iff S blocks *every*
path between a node in A and a node in B. The bridge to probability:
> **Global Markov property:** A ⫫_G B | C  ⇒  A ⫫ B | C in P (holds for any P entailed by
> an SCM with graph G; Peters et al. Def 6.21, Prop 6.31).
> **Faithfulness** (an assumption about the world): the converse, A ⫫ B | C ⇒ A ⫫_G B | C.
Markov + Faithfulness ⇒ **d-separation ⟺ conditional independence** (Eberhardt 2017
Eq. 1; SGS). Two DAGs are **Markov equivalent** iff they share the same skeleton and
v-structures (immoralities), equivalently entail the same d-separations.

> **PhysioMap check.** Because PhysioMap is cyclic, the relevant separation criterion is
> **σ-separation**, which is *defined to coincide with d-separation when the graph is
> acyclic*. The Definition above is therefore the exact target the project's
> σ-separation reduction must hit: in the acyclic limit, σ-separation collapses to the
> collider/non-collider blocking rule stated here, and the global Markov property recovers
> the standard d-separation ⇒ independence statement.

### Interventionist account of causation (Woodward 2003 — justifies our edge semantics)
- **Intervention variable** I for X w.r.t. Y satisfies **(I1)** I causes X; **(I2)** I is a
  *switch* that breaks all other arrows into X (X then depends only on I); **(I3)** every
  directed path from I to Y passes through X; **(I4)** I is independent of any cause Z of Y
  off the X-path. *(This is exactly Pearl's do-surgery: I2 = "delete the equation for X".)*
- **(M) Direct cause:** X is a **direct cause** of Y (relative to variable set V) iff there
  is a **possible intervention on X that changes Y (or its distribution) while all other
  variables in V are held fixed by interventions.**
- **Contributing/total cause:** X is a contributing cause of Y iff some intervention on X
  changes Y along a directed path, holding off-path variables fixed.

> **PhysioMap check.** A PhysioMap edge X→Y *means* exactly (M): a surgical intervention
> on X would change Y with the rest held fixed. Woodward's interventionist content and
> Pearl's do-operator are two formulations of the same operation, which is why
> instantiating an SCM endows PhysioMap edges with genuine (not merely associational)
> causal meaning — and why it remains well-defined under feedback/cycles.

---

## (d) Cross-links to other PhysioMap themes

- **ODE-causality.** Peters et al. **Remark 6.7** gives the SCM↔ODE bridge: an SCM is the
  equilibrium-level causal description of a dynamical (ODE) system, and works for cyclic
  structure. The separation theory generalizes: **σ-separation (Forré & Mooij; Bongers et
  al.) generalizes d-separation** to cyclic/feedback SCMs and reduces to d-separation in
  the acyclic case — the central formal fact PhysioMap relies on. (See the ODE-causality
  folder for σ-separation / cyclic-SCM primary sources.)
- **Mendelian Randomization (MR).** Pearl 2009 §3.5 and Pearl 1995 formalize
  **instrumental variables** as a way to identify/bound *interventional* effects
  P(Y|do(X)) when X is confounded. MR uses genetic variants as IVs; the IV graph is
  precisely Woodward's I1–I4 intervention-variable structure (I→X→Y with I independent of
  confounders). So MR estimates the very do(X) quantity that PhysioMap edges assert. (See
  the MR folder.)
- **Causal discovery → PhysioMap structure.** Eberhardt 2017 + SGS give the assumption
  lattice (Markov, Faithfulness, sufficiency, acyclicity) and algorithms (PC, FCI, LiNGaM,
  ANM, **CCD/SAT for cycles**) for inferring PhysioMap-style structure from data; the
  cyclic methods are the ones compatible with PhysioMap's feedback regime.

---

## Provenance / honesty notes
- Downloaded + verified (`%PDF`, >30 KB) and READ: Pearl 2009 (pp. 1–15), Peters–Janzing–
  Schölkopf 2017 (Ch. 6 core: book pp. 82–106, 121–123, + front matter), Pearl 1995
  (pp. 1–3), Eberhardt 2017 (all 11 pp.).
- Stubs (paywalled/not OA, no PDF): SGS 2000, Woodward 2003 — abstracts/definitions
  verified via publisher pages and Woodward's own restated definitions (I1–I4, (M)),
  cross-checked against the locally-read essay "Causation with a Human Face".
- No source was cited that was not downloaded+read or stubbed with a verified
  abstract/definition. Nothing fabricated.
