# ODE-Causality / Cyclic SCMs / Sigma-Separation — Reading Notes

Curated library for the PhysioMap theme: **Causality and the equilibrium of ODE
systems; cyclic SCMs; sigma-separation.** This is the theoretical backbone of
PhysioMap: a within-scale signed causal map with feedback **cycles**, where a
Guyton-style steady state is the equilibrium of an implied ODE system = a
**cyclic structural causal model (SCM)**; causal reasoning under cycles uses
**sigma-separation**; intervention predictions are **qualitative comparative
statics** sign(dx*/dθ) at that steady state.

All papers below were downloaded and read (page ranges noted). Honesty note:
definitions in the "precise definitions" sections are transcribed faithfully
from the PDFs; where I paraphrase or reconstruct (e.g. the comparative-statics
formula, which is not stated verbatim in any seed paper) I flag it explicitly.

---

## (a) Overview of this line of work

This literature (almost entirely from the Amsterdam / Tübingen group around
Joris Mooij, with Forré, Bongers, Blom, Rubenstein, Janzing, Schölkopf, plus the
Copenhagen Hansen–Sokol SDE strand) answers two linked questions:

1. **Where do (cyclic) SCMs come from?** They arise as the *equilibrium*
   description of a dynamical system (ODE/SDE). A first-order ODE system
   `Ẋ_i = f_i(X_pa(i))` at steady state (`Ẋ=0`) yields equilibrium equations
   `0 = f_i(X_pa(i))`, which — after *labeling* which equation belongs to which
   variable — become the structural equations of an SCM. Feedback loops in the
   ODE become **directed cycles** in the SCM graph. (Mooij 2013; Rubenstein 2018
   for the time-dependent generalization; Hansen–Sokol 2014 for the stochastic
   SDE analogue; Blom 2019 for cases where the SCM is *not* expressive enough.)

2. **How do you reason causally on a graph with cycles (and latent
   confounders)?** Ordinary d-separation / the usual Markov property *fail* in
   the cyclic non-linear case (Spirtes' counterexample). Forré & Mooij 2017
   repair this by defining **σ-separation** on directed graphs with hyperedges
   (HEDGes) and proving a directed global Markov property for general structural
   equation models w.r.t. σ-separation. Bongers et al. 2021 give the measure-
   theoretic foundations (solvability, simple SCMs, marginalization, the causal
   interpretation), and Forré & Mooij 2018 turn σ-separation into a constraint-
   based causal-discovery algorithm.

The key technical bridge — and the highest-value output for our `sigma.py` — is
that **σ-separation in a graph G reduces to ordinary d-separation in the
*acyclification* G^acy of G**, and to plain d-separation in the acyclic case.

---

## (b) Per-paper entries

### 1. Mooij, Janzing & Schölkopf 2013 — "From Ordinary Differential Equations to Structural Causal Models: the deterministic case"
- **arXiv:** 1304.7920 (UAI 2013). **File:** `Mooij2013_ODE-to-SCM.pdf` (~204KB, 8pp; read pp.1–8 = essentially the whole paper).
- **Summary:** Shows how the equilibrium states of a first-order deterministic
  ODE `Ẋ_i = f_i(X_pa(i))` can be described by a deterministic SCM
  `X_i = h_i(X_pa(i))`. The construction goes via an intermediate object, the
  **Labeled Equilibrium Equations (LEE)** `E_i: 0 = g_i(X_pa(i))`, where the
  *label* records which variable's dynamical equation `Ẋ_i = …` each equilibrium
  equation came from (this label is exactly the information an intervention
  do(X_i=ξ_i) replaces, and it is lost if you treat the equilibrium equations as
  an unlabeled set). Perfect intervention do(X_I=ξ_I) is realized at the ODE
  level by adding a strong feedback term κ(ξ_i − X_i) and letting κ→∞; this
  reduces the equilibrium equation `0 = f_i(...)+κ(ξ_i−X_i)` to `0 = X_i − ξ_i`.
  Under **stability** assumptions (Def. 1: unique globally attracting
  equilibrium; Def. 10: *structural* stability = stable w.r.t. the relevant
  interventions) the whole diagram ODE → LEE → SCM **commutes with
  intervention** (Theorem 1, Theorem 2): intervening then equilibrating = 
  equilibrating then intervening. Worked examples: Lotka–Volterra (unstable, a
  caution), damped coupled harmonic oscillators (stable → clean cyclic SCM,
  e.g. final SCM graph X1↔X2↔X3↔X4 with self-consistent equations
  `Q_i = [k_i(Q_{i+1}−l_i)+k_{i−1}(Q_{i−1}+l_{i−1})]/(k_i+k_{i+1})`).
  Self-loops in the ODE (X_i depends on itself) generically do NOT survive into
  the SCM, but structural stability secretly relies on them for uniqueness.
- **RELEVANCE to PhysioMap (HIGH — core):** This is *the* formal justification
  for treating a Guyton steady-state physiology diagram as a cyclic SCM. It tells
  us (i) the steady state of the implied ODE = solution of an SCM with cycles;
  (ii) interventions = do() on that SCM, valid *only under stability*; (iii) the
  "label" caveat = which mechanism/equation a node owns is causally load-bearing
  and must be preserved (analogous to "which physiological control loop sets a
  variable"). Read pp.6–8 (equilibrium eqns, LEE, SCM construction, Thm 1/2).

### 2. Rubenstein, Bongers, Schölkopf & Mooij 2018 — "From Deterministic ODEs to Dynamic Structural Causal Models"
- **arXiv:** 1608.08028 (UAI 2018). **File:** `Rubenstein2018_ODE-to-dynamic-SCM.pdf` (~670KB; read pp.1–4 = abstract, intro, ODE setup, interventions).
- **Summary:** Generalizes Mooij 2013 from *static equilibrium* under *constant*
  interventions to *asymptotic dynamics* under *time-varying* interventions.
  Interventions become forcing of a *trajectory* `do(X_I = ζ_I)` with
  `ζ_I: R_≥0 → ∏R_i`; two trajectories are equivalent if they agree
  asymptotically. Under regularity/modularity conditions on the dynamical system
  and on the admitted **set of interventions** (Dyn_I must be *modular*,
  Def. 1 — single-variable trajectories combine freely), the asymptotic behaviour
  is captured by a **Dynamic SCM (DSCM)**. Static equilibrium (Mooij 2013) is the
  special case where the intervention set is the constant trajectories.
- **RELEVANCE (MEDIUM):** Confirms the ODE→SCM bridge is robust and clarifies
  that the SCM is an abstraction valid *relative to a declared class of
  interventions*. For PhysioMap, which mostly reasons about steady-state
  comparative statics, the static special case (= Mooij 2013) is what we use, but
  this paper bounds when the static picture is legitimate and flags oscillatory
  regimes (where no static equilibrium exists) as out of scope.

### 3. Bongers, Forré, Peters & Mooij 2021 — "Foundations of Structural Causal Models with Cycles and Latent Variables"
- **arXiv:** 1611.06221 (Annals of Statistics 2021). **File:** `Bongers2021_cyclic-latent-SCM.pdf` (~1.0MB, long; read pp.1–5 = abstract, intro, Fig.1 overview, SCM definition 2.1/2.2).
- **Summary:** The measure-theoretic foundations for SCMs *with cycles and latent
  confounders*. Defines an SCM as a tuple `M = ⟨I, J, X, E, f, P_E⟩` (endogenous
  index I, exogenous index J, domains, measurable mechanism f: X×E→X, product
  exogenous law P_E). Cycles break almost every nice property of acyclic SCMs:
  no guaranteed (unique) solution; no guaranteed unique observational/
  interventional/counterfactual distribution; marginalization may not exist or
  respect latent projection; the usual Markov property fails; the graph can be
  inconsistent with causal semantics. Each property is *recovered* under
  **solvability** conditions. Introduces **simple SCMs** = uniquely solvable
  w.r.t. *every* subset of variables; simple SCMs retain (almost) all the good
  acyclic properties, are closed under intervention and marginalization, and obey
  a directed global Markov property — the *general* one via **σ-separation**, the
  *stronger* d-separation one in special cases (acyclic, linear, discrete).
  Fig. 1 is the master diagram tying SCM → acyclified SCM → (augmented) graph →
  acyclified graph → d-/σ-separations.
- **RELEVANCE (HIGH):** This is the rigorous "is our cyclic SCM well-defined?"
  reference. PhysioMap should aim for the **simple SCM** regime (unique solution
  under all the interventions we ask about) — that is exactly the assumption that
  makes sign(dx*/dθ) well-defined and the σ-separation Markov property valid. Cite
  for: solvability, simple SCMs, the d-vs-σ separation dichotomy.

### 4. Forré & Mooij 2017 — "Markov Properties for Graphical Models with Cycles and Latent Variables"  ★ DEFINES σ-SEPARATION
- **arXiv:** 1710.08775 (unpublished long manuscript, 131pp). **File:** `Forre2017_sigma-separation-Markov.pdf` (~1.3MB; read pp.1–6 intro, pp.16–19 graph notation/d-sep, pp.44–53 acyclification + σ-separation + the Theorem 2.8.3/2.8.4 equivalences).
- **Summary:** Introduces **directed graphs with hyperedges (HEDGes)**,
  unifying mDAGs (latents-as-hyperedges) and DMGs (cycles). Defines the
  **acyclification** G^acy (§2.7) and **σ-separation** (§2.8), and proves the
  central equivalence: **σ-separation in G ⇔ d-separation in G^acy** (Cor. 2.8.4),
  and that σ-separation **implies** d-separation in G itself (Thm 2.8.2 with
  G'=G). σ-separation is the criterion for the general directed global Markov
  property (gdGMP) satisfied by structural-equation models in the presence of
  cycles + latents; it is stable under marginalization (Cor. 2.8.5); and on mDAGs
  (incl. ADMGs/DAGs) σ-separation and d-separation coincide.
- **RELEVANCE (HIGHEST — drives `sigma.py`):** This is the algorithm spec.
  Exact transcriptions in section (c) below.

### 5. Forré & Mooij 2018 — "Constraint-based Causal Discovery for Non-Linear Structural Causal Models with Cycles and Latent Confounders"
- **arXiv:** 1807.03024 (UAI 2018). **File:** `Forre2018_cyclic-causal-discovery.pdf` (~5.3MB; read pp.1–3 = abstract, intro, theory §2.1/2.2 mSCM + loops + σ-sep restated).
- **Summary:** Builds on **modular SCMs (mSCMs)** and gives a *simplified but
  equivalent* presentation of σ-separation directly on directed graphs (without
  the full HEDG machinery), under weaker assumptions. Extends σ-separation to
  mixed graphs (bi-/undirected edges) = **σ-connection graphs (σ-CG)**, proves
  closedness under marginalization/conditioning, and uses an **answer-set-
  programming (ASP) / weighted-SAT** solver to find the σ-CG most compatible with
  the conditional (in)dependences in data — the first constraint-based discovery
  algorithm handling non-linearity + cycles + latent confounders + multiple
  interventional datasets at once (assuming no selection bias, σ-faithfulness).
  Useful cleaner restatements: **loops** L(G); **strongly connected component**
  `Sc^G(v) := Anc^G(v) ∩ Desc^G(v)`; mSCM definition (Def. 2.4). The "gear
  analogy" (Fig. 1) illustrates that with cycles, *local* mechanism compatibility
  does not imply *global* compatibility — global compatibility must be assumed.
- **RELEVANCE (MEDIUM–HIGH):** (i) Cleaner, implementation-friendly statement of
  the same Sc^G / σ-separation objects we code. (ii) If PhysioMap ever moves from
  hand-curation to *learning/validating* edges from data, this is the discovery
  algorithm to use. (iii) The gear analogy is a good intuition for why a curated
  cyclic map needs a global-compatibility (solvability) assumption.

### 6. Blom, Bongers & Mooij 2019 — "Beyond Structural Causal Models: Causal Constraints Models"
- **arXiv:** 1805.06539. **File:** `Blom2019_causal-constraints-models.pdf` (~509KB; read pp.1–4 = abstract, intro, SCM/dynamical-system setup, basic enzyme reaction example).
- **Summary:** Shows SCMs are **not always expressive enough** to capture the
  causal semantics of dynamical systems at equilibrium — specifically when the
  equilibrium depends on the **initial condition** (e.g. via *conservation
  laws / constants of motion*, as in the basic enzyme reaction where
  `C(t)+E(t)=c_0+e_0` is invariant). Proposes **Causal Constraints Models (CCMs)**:
  a causal model specified by a family of *constraints* (equations that hold and
  are invariant under interventions that don't target their variables) rather
  than by per-variable structural assignments. CCMs subsume SCMs, correctly
  handle functional laws (e.g. ideal gas law) and non-globally-stable systems.
  Theorem 1: the stationary behaviour of the basic enzyme reaction *cannot* be
  fully represented by an SCM on the natural endogenous variables.
- **RELEVANCE (MEDIUM — a caveat/boundary):** Tells us when the clean ODE→SCM
  story (Mooij 2013) breaks: **conservation laws and non-unique equilibria**.
  Human physiology is full of conserved quantities (total body water/sodium,
  mass balance). Where PhysioMap relies on such balances, the SCM abstraction may
  be incomplete and a constraint may be the more honest representation. Flag in
  the modelling guidelines; not needed for the core sigma.py.

### 7. Sokol & Hansen 2014 — "Causal Interpretation of Stochastic Differential Equations"
- **arXiv:** 1304.0217 (Electronic Journal of Probability 19, 2014). **File:** `HansenSokol2014_SDE-causal-interpretation.pdf` (~355KB; read pp.1–3 = abstract, intro, contributions). [Primarily measure-theoretic SDE work; read for context/abstract.]
- **Summary:** The stochastic analogue of the ODE→SCM strand. Defines the
  **post-intervention SDE** for a perfect intervention on an SDE coordinate, and
  shows (under Lipschitz conditions) that its solution is the uniform-in-
  probability limit of post-intervention SEMs built from the Euler scheme of the
  original SDE — i.e. interventions on SDEs ≈ interventions on the corresponding
  discrete-time SCM. For Lévy-driven SDEs the post-intervention distribution is
  *identifiable from the generator* (a stronger result than the DAG case, where
  intervention effects are generally not identifiable from observation). Also:
  weak conditional local independence ≈ "locally unaffected by intervention".
- **RELEVANCE (LOW–MEDIUM — context):** Establishes that the ODE→SCM bridge
  generalizes to noise/stochasticity. PhysioMap is qualitative/deterministic at
  the structural level, so this is background that legitimizes ignoring noise for
  the structural reasoning while knowing a stochastic version exists.

---

## (c) Sigma-separation & acyclification — PRECISE DEFINITIONS  ★ (drives sigma.py)

All transcribed from **Forré & Mooij 2017 (arXiv:1710.08775)**. Notation from §2.1.
Where a symbol is ASCII-ized I keep the paper's meaning.

### Graph notation (Forré–Mooij 2017 §2.1; also Forré–Mooij 2018 Def. 2.2)
- `Pa^G(w) := {v | v→w ∈ E}` parents; `Ch^G(v) := {w | v→w ∈ E}` children.
- A **path** (Def. 2.1.1.5) is a sequence of n≥1 nodes with an edge chosen at each
  position; nodes may repeat. Trivial path = single node.
- **directed path** `v → v₂ → ⋯ → w`: all arrowheads point the same way.
- **Ancestors / descendants** (2.1.1.7):
  `Anc^G(w) := {v | ∃ directed path v→⋯→w}`,
  `Desc^G(v) := {w | ∃ directed path v→⋯→w}`. Both reflexive
  (`{w} ⊆ Anc^G(w)`, `{v} ⊆ Desc^G(v)`). Lifted to sets by union.
- **Strongly connected component** (2.1.1.10 / 2.1.2):
  **`Sc^G(v) := Anc^G(v) ∩ Desc^G(v)`**  — the set of nodes that are both
  ancestor and descendant of v (i.e. lie on a common directed cycle with v, or
  = v itself). These are the equivalence classes of `v ~ w :⇔ w ∈ Sc^G(v)`.
  NOTE: `v ∈ Sc^G(v)` always (a singleton SCC is just {v}).
- `S(G)` = the DAG of strongly connected components (2.1.2.3, Lemma 2.1.3:
  it IS a DAG).

### d-separation (Def. 2.1.4, for ordinary directed graphs — the reduction target)
A path `v₁ … vₙ` (n≥1) is **Z-blocked** iff
- (a) an endnode v₁ or vₙ ∈ Z, OR
- (b) two adjacent edges form one of:
  - non-collider `→ vᵢ →` with vᵢ ∈ Z, or
  - non-collider `← vᵢ ←` with vᵢ ∈ Z, or
  - non-collider `← vᵢ →` with vᵢ ∈ Z, or
  - **collider** `→ vᵢ ←` with **vᵢ ∉ Anc^G(Z)**.
Otherwise the path is **Z-open**. `X ⊥d_G Y | Z` iff every path from X to Y is
Z-blocked. (Remark 2.1.5: it suffices to check paths with no repeated node.)

### ACYCLIFICATION (Definition 2.7.1) — the construction `sigma.py` should build
Given a directed graph (HEDG) `G = (V, E, H)`, the **acyclification**
`G^acy = (V^acy, E^acy, H^acy)` is:
1. `V^acy := V`  (same nodes).
2. Put **`v → w ∈ E^acy`  iff  `v ∉ Sc^G(w)`  AND there exists a node
   `w' ∈ Sc^G(w)` with `v → w' ∈ E`.**
3. `H^acy := { F' ⊆ ⋃_{v∈F} Sc^G(v) | F ∈ H }`  (each hyperedge is extended to
   cover the union of the SCCs of its nodes).

In words (paper's own gloss): *"draw edges from a node v to all nodes of a
strongly connected component S if there was at least one edge from v to a node
of S; all edges between nodes of a strongly connected component are erased; and
hyperedges are extended to cover the union of the strongly connected components
of their nodes."*

- **Lemma 2.7.2:** `G^acy` is an mDAG — its underlying directed graph
  `(V, E^acy)` is acyclic. (Because SCCs form a DAG and E^acy only goes along it.)
- **Lemma 2.7.4:** every pseudo-topological order of G is a topological order of
  G^acy (since `Pa^{G^acy}(v) ⊆ Anc^G(v) \ Sc^G(v)`).

**Algorithmic recipe for `sigma.py` (no-latent case = our PhysioMap default):**
For an ordinary signed directed graph G (no hyperedges):
1. Compute SCCs of G (e.g. Tarjan / Kosaraju). `Sc(w)` = SCC containing w.
2. Build G^acy on the same nodes: for each original edge `u → w'`, and for every
   `w` in the same SCC as w' with `u ∉ Sc(w)` (equivalently `u`'s SCC ≠ `w`'s
   SCC), add `u → w`. Concretely: contract each SCC; for each inter-SCC edge from
   SCC A to SCC B in the condensation, add edges `u → w` for every u∈A, w∈B.
   Erase all intra-SCC edges. Result is a DAG.
3. To test `X ⊥σ_G Y | Z`, run **ordinary d-separation on G^acy** with the SAME
   X, Y, Z (Corollary 2.8.4, case G'=G^acy: `X ⊥σ_G Y | Z ⇔ X ⊥d_{G^acy} Y | Z`).
   This is the recommended implementation path: it lets us reuse a standard
   d-separation routine. Signs on edges are irrelevant to separation (they matter
   only for the comparative-statics sign computation, section (d)).

### σ-SEPARATION (Definition 2.8.1, "segment version") — the native criterion
Operates directly on G using **segments**. Given a path
`v₁ ⇄→← ⋯ ⇄→← vₙ` (n≥1):
1. **Segments.** Partition the path uniquely by SCCs: a maximal run of
   consecutive nodes `vᵢ,…,v_k` all lying in the *same* SCC `Sc^G(vᵢ)` (with the
   bordering nodes `v_{i−1}, v_{k+1} ∉ Sc^G(vᵢ)`) is a **segment** σ_j. Write its
   left/right endnodes `σ_{j,l}:=vᵢ`, `σ_{j,r}:=v_k`. Path = `σ₁ ⇄→← ⋯ ⇄→← σ_m`;
   σ₁, σ_m are the **end-segments**.
2. **The path is Z-σ-blocked (σ-blocked by Z) iff at least one of:**
   - **(a)** an endnode `v₁ = σ_{1,l}` or `vₙ = σ_{m,r}` is in Z; or
   - **(b)** there is a segment σ_j with an **outgoing directed edge** in the path
     (i.e. `← σ_j ⋯` or `⋯ σ_j →`) **AND its corresponding endnode**
     (σ_{j,l} or σ_{j,r} respectively) **lies in Z**; or
   - **(c)** there is a segment σ_j with two adjacent (hyper)edges forming a
     **collider** `→ σ_j ←` (arrowheads into the segment from both sides) **AND
     `Sc^G(σ_j) ∩ Anc^G(Z) = ∅`**.
   If none holds, the path is **Z-σ-open / Z-σ-active**.
   (Footnote 17: with repeated nodes allowed one may relax the collider condition
   to `Sc^G(σ_j)∩Z=∅` or `σ_j∩Anc^G(Z)=∅` or `σ_j∩Z=∅`, but then fix one
   consistent choice per path.)
3. **`X ⊥σ_G Y | Z`** iff every path with one endnode in X and one in Y is
   σ-blocked by Z.

**Reading of (b) vs (c):** A *non-collider* segment blocks if (the relevant
endnode of) it is conditioned on — analogous to a chain/fork mid-node in Z. A
*collider* segment blocks UNLESS the whole SCC of the segment has an ancestor in
Z (i.e. the collider is "opened" by conditioning on the segment or any of its
descendants/SCC-ancestors-of-Z). The crucial cyclic twist vs d-separation: the
unit that gets blocked/opened is the **whole strongly connected segment**, not a
single node.

### THE EQUIVALENCES (Theorems 2.8.2–2.8.4, Corollary 2.8.4)
- **Thm 2.8.2:** for suitable G' (e.g. G'=G), `X ⊥σ_G Y | Z ⇒ X ⊥d_{G'} Y | Z`.
  In particular with G'=G: **σ-separation implies d-separation**. (So σ-sep is
  *strictly stronger / more conservative*: fewer independences are claimed.)
- **Thm 2.8.3:** under stated edge-replacement conditions, `X ⊥d_{G'} Y | Z ⇒
  X ⊥σ_G Y | Z`.
- **Corollary 2.8.4 (THE one we implement):** both directions hold — hence
  **`X ⊥σ_G Y | Z ⇔ X ⊥d_{G'} Y | Z`** — for, among others:
  1. **`G' = G^acy`** (the acyclification),
  2. `G' = (V, E^acy ∪ E^sc, H^acy)` with `E^sc := {v→w | ∀ v∈V, w∈Sc^G(v)}`,
  3. `G' = G^c = (V, E, H^c)`, `H^c := H ∪ {F ⊆ Sc^G(v) | ∀ v∈V}`,
  4. `G' = G₂^c` (hyperedges of size ≤2),
  5. the **collapsed graph** `G^col = (V, E^acy ∪ E^sc_<, H₁)` of Spirtes (1994)
     for a pseudo-topological order <,
  6. `G' = (V, E^acy ∪ E^sc, H₁)`.
  **Furthermore, if `G₂ = G₂'` then σ-separation in G and d-separation in G
  coincide** — i.e. in the acyclic / no-relevant-cycle case σ-sep degenerates to
  d-sep (matches PhysioMap requirement "reduces to d-separation when acyclic").
- **Corollary 2.8.5:** σ-separation is **stable under marginalization**:
  `X ⊥σ_G Y | Z ⇔ X ⊥σ_{G^{mar\W}} Y | Z` for W disjoint from X∪Y∪Z. (Lets us
  reason on a sub-map after projecting out latent/uninstrumented variables.)

**Implementation decision for `sigma.py`:** implement Corollary 2.8.4 case (1):
build `G^acy` once (SCC condensation + edge lifting per Def. 2.7.1), then answer
every σ-separation query by standard d-separation on `G^acy`. This is exact,
reuses well-tested d-sep code, and automatically gives the acyclic→d-sep
reduction for free. (Optionally cross-check against the native segment criterion
2.8.1 on small graphs as a unit test.)

---

## (d) ODE equilibrium = cyclic SCM; comparative statics = causal effect

### The formal chain (Mooij 2013, made precise; Rubenstein 2018 generalization)
1. **Dynamical system / ODE** `D`:  `Ẋ_i(t) = f_i(X_pa(i)(t))`, `i ∈ I={1,…,D}`,
   parents `pa(i) ⊆ I` (j∈pa(i) iff f_i genuinely depends on X_j). Graph `G_D`:
   node per variable, edge `X_j → X_i` iff X_i's rate depends on X_j. **Feedback
   loops in physiology ⇒ directed cycles in G_D.**
2. **Equilibrium** (steady state): set `Ẋ=0`. **Equilibrium equations**
   `0 = f_i(X_pa(i))`, ∀i (Mooij 2013 eqn (6)). Under **stability** (Def. 1:
   unique globally attracting X*), this system has a unique solution X*.
3. **Labeled equilibrium equations (LEE)** `E_i: 0 = g_i(X_pa(i))`: keep the label
   i = "this equation governs X_i". This label is exactly what perfect
   intervention do(X_I=ξ_I) overwrites (replace `E_i` by `0 = X_i − ξ_i` for i∈I).
4. **SCM** `M`: under (structural) solvability solve each labeled equation for its
   owned variable, `X_i = h_i(X_pa_M(i))` (Mooij 2013 Def. 6, §4.4). Cyclic G_D ⇒
   cyclic SCM. **Theorem 2:** if D and the intervened ODE are structurally stable,
   the ODE→LEE→SCM diagram commutes with intervention. ⇒ **the Guyton-style steady
   state is the solution of a cyclic SCM, and do() on that SCM = the steady state
   of the intervened ODE.**

### Comparative statics = causal effect  (FLAG: formula reconstructed, see below)
At a stable equilibrium the equilibrium equations define `x*` implicitly as a
function of parameters/interventions θ:
        `F(x*, θ) = 0`,   where  `F_i(x,θ) = f_i(x; θ)`  (stacked).
By the **Implicit Function Theorem**, *provided the Jacobian
`J := ∂F/∂x = ∂f/∂x` evaluated at (x*,θ) is invertible* (which is implied by the
hyperbolic-stability condition that J has no zero/imaginary-axis eigenvalues —
for an asymptotically stable equilibrium of `Ẋ=f`, the dynamical Jacobian
`∂f/∂x` has all eigenvalues with negative real part, hence is nonsingular), the
equilibrium response to an infinitesimal parameter change is

   **dx*/dθ  =  − (∂F/∂x)^{-1} · ∂F/∂θ  =  − (∂f/∂x)^{-1} · ∂f/∂θ .**

The **qualitative comparative static** PhysioMap predicts is
   **sign(dx*_k/dθ)** for the variable(s) k of interest.
This is the steady-state **causal effect** of an intervention/parameter on the
SCM solution — i.e. the do()-effect in the cyclic SCM of Mooij 2013, restricted
to its sign. For a single perfect intervention do(X_j = θ) on a target node, the
relevant `∂f/∂θ` column is the way θ enters the j-th (replaced) equation.

**HONESTY FLAG:** The closed-form `dx*/dθ = −(∂F/∂x)^{-1} ∂F/∂θ` is the standard
implicit-function-theorem / comparative-statics identity and is the correct
formalization of "intervention prediction at the steady state of the cyclic
SCM," but it is **NOT written verbatim** in any of the seven seed PDFs. Mooij
2013 gives the qualitative ODE→equilibrium→SCM construction and the stability
condition; the explicit Jacobian-inverse formula is my (standard, textbook)
reconstruction connecting their framework to "qualitative comparative statics."
Treat the formula as load-bearing-but-derived, not as a paper quotation.

### When is it valid? (stability conditions, from the papers)
- **Mooij 2013 Def. 1 / Def. 10:** need a **unique (locally) attracting
  equilibrium**, and *structural* stability = stability also holds for the
  intervened systems do(X_I=ξ_I) you intend to reason about. Without this the SCM
  / comparative static is undefined or non-unique. The Lotka–Volterra example is
  the explicit warning (unstable / oscillatory → no static SCM).
- **Bongers 2021:** the corresponding SCM should be in the **simple SCM** regime
  (uniquely solvable w.r.t. every intervention subset) for the do()-effects and
  the σ-separation Markov property to be well-defined.
- **Blom 2019 caveat:** if the equilibrium depends on **initial conditions**
  (conservation laws / constants of motion / non-unique equilibria), an SCM is
  *not expressive enough* — use a Causal Constraints Model instead, and
  comparative statics on a single x* is ill-posed.
- **Rubenstein 2018 caveat:** if the system does not settle to a static
  equilibrium (sustained oscillation), use the dynamic-SCM picture; static
  comparative statics does not apply.

Practical PhysioMap reading: comparative-statics sign predictions are valid
exactly where the relevant physiological subsystem has a **unique, locally
asymptotically stable steady state that persists under the modelled
intervention**, and no binding conservation law pins the equilibrium to initial
conditions. Where loop gain flips a system to instability/oscillation, or a
conservation law binds, flag the prediction as out of the SCM's validity.

---

## (e) Cross-links

- **resources/causal-foundations/** — Pearl do-calculus, SCMs, d-separation: the
  acyclic baseline that σ-separation generalizes; Mooij 2013 Defs 6–8 follow
  Pearl. d-separation routine there is reused by our acyclification approach.
- **resources/qualitative-reasoning/** — sign(dx*/dθ) is the quantitative-free
  comparative static; QR / signed-influence and loop-gain analysis are the
  qualitative-dynamics counterpart to the stability conditions in (d). The
  σ-segment = SCC unit mirrors QR's treatment of feedback loops as units.
- **resources/virtual-physiological-human/** (Guyton, VPH) — the *source* of the
  ODE systems: Guyton's circulatory/renal steady-state model is precisely a large
  coupled ODE whose equilibrium Mooij 2013 turns into a cyclic SCM. The whole
  PhysioMap "Guyton steady state = cyclic SCM" claim rests on §(d) above.
- **resources/mendelian-randomization/** & **causal-knowledge-graphs/** —
  downstream consumers: MR is an instrument-based effect estimator that assumes a
  (usually acyclic) causal graph; σ-separation tells us which conditional
  independences (hence which MR/identification arguments) survive in the cyclic
  physiological setting. Forré–Mooij 2018 is the discovery-side bridge to KGs.

---

## File inventory (all verified `%PDF`, size > 30KB)
| File | arXiv | Pages read | Tier |
|---|---|---|---|
| `Mooij2013_ODE-to-SCM.pdf` | 1304.7920 | 1–8 (full) | core |
| `Rubenstein2018_ODE-to-dynamic-SCM.pdf` | 1608.08028 | 1–4 | support |
| `Bongers2021_cyclic-latent-SCM.pdf` | 1611.06221 | 1–5 | core |
| `Forre2017_sigma-separation-Markov.pdf` | 1710.08775 | 1–6, 16–19, 44–53 | ★ highest |
| `Forre2018_cyclic-causal-discovery.pdf` | 1807.03024 | 1–3 | support |
| `Blom2019_causal-constraints-models.pdf` | 1805.06539 | 1–4 | caveat |
| `HansenSokol2014_SDE-causal-interpretation.pdf` | 1304.0217 | 1–3 | context |

## Must-read flags
1. **Forré & Mooij 2017 §2.7–2.8 (pp.44–53)** — acyclification + σ-separation;
   this *is* the sigma.py spec. Read before writing any separation code.
2. **Mooij 2013 §3–4 (pp.6–8)** — ODE→LEE→SCM and Theorem 1/2; the formal
   licence for "Guyton steady state = cyclic SCM."
3. **Bongers 2021 (intro + simple SCMs)** — solvability / simple-SCM regime that
   makes our do()-effects and Markov property well-defined.
4. **Blom 2019 (basic enzyme example, Thm 1)** — the conservation-law boundary
   where the SCM abstraction (and hence comparative statics) fails.
