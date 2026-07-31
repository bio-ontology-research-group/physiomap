# Qualitative Reasoning — Curated Library & Notes

**Theme.** Qualitative reasoning / qualitative physics, qualitative probabilistic networks
(sign propagation), loop analysis, and qualitative comparative statics / sign-solvability.
This is the algorithmic heritage of PhysioMap's qualitative solver.

**PhysioMap solver, restated.** Given a cyclic *signed causal graph* with steady state x*,
predict **sign(∂x*_i/∂θ)** for a parameter θ. Method (decisions already taken):
comparative statics by **Quirk–Maybee / Lancaster sign-solvability** (no Monte Carlo);
ambiguous results returned as **'?'** and logged; **stability assumed** (negative diagonal /
dominant self-regulation); **sign propagation** on acyclic parts, **sign-solving** within
strongly connected components (SCCs).

Everything below is either a PDF I downloaded and read, or a clearly-marked stub built from
verified metadata + abstracts/secondary summaries. Honesty notes are per entry.

---

## (a) The lineage in one paragraph

Modern qualitative reasoning has **two converging roots**. (1) **Qualitative physics /
naive physics** in AI (de Kleer & Brown's *confluences* = qualitative differential
equations; Forbus' *Qualitative Process Theory*; Kuipers' *QSIM* qualitative simulation):
reason about device/physical behavior using sign/order abstractions of ODEs, where
*competing tendencies* yield ambiguous values. Iwasaki & Simon then showed this AI
"qualitative calculus" is the same thing as **comparative statics + causal ordering** from
econometrics/thermodynamics — differentiate the equilibrium equations, replace differentials
by signs, propagate; indeterminacy is expected. (2) The **sign-only matrix-theory** root:
Samuelson's correspondence principle → Lancaster's qualitative linear systems →
Bassett–Maybee–Quirk **sign-solvability / sign-nonsingular matrices**, and in ecology
Levins' **loop analysis** of the signed community matrix. Wellman's **Qualitative
Probabilistic Networks** ported sign propagation to Bayesian networks (acyclic), with the +,
−, 0, ? sign algebra; Druzdzel & Henrion gave the polynomial **local sign-propagation**
algorithm. PhysioMap sits at the intersection: sign propagation on the acyclic part (QPN
lineage), sign-solvability/loop analysis inside cyclic SCCs (Quirk–Maybee + Levins), all
licensed by a stability assumption (the correspondence principle).

---

## (b) Per-paper entries

### 1. de Kleer & Brown 1984 — A Qualitative Physics Based on Confluences
- File: `deKleerBrown1984_confluences.pdf` (77 pp; read: front matter + §§1–3, qualitative
  calculus / confluences / qualitative state, ~pp. 7–30; skimmed feedback sections).
- Citation: de Kleer, J. & Brown, J. S. (1984). *Artificial Intelligence* 24:7–83.
- Summary: A **confluence** is a qualitative differential equation, e.g. `dP + dA − dQ = 0`,
  over the qualitative value space {−,0,+} ([−],[0],[+]). Device behavior is the solution of
  the confluence set under a qualitative calculus; each variable may be pushed by several
  competing tendencies, so a confluence often has **multiple / ambiguous solutions** that
  must be split by region (component states). Causal analysis (ENVISION program) traces how
  a disturbance propagates and identifies **feedback paths**.
- **Relevance:** the qualitative-value algebra (+, −, 0 with ambiguous sums) is the direct
  ancestor of PhysioMap's sign algebra; "competing tendencies → ambiguous sign" is exactly
  PhysioMap's '?'. PhysioMap's signed edges are the linearized analogue of confluences.

### 2. Forbus 1984 — Qualitative Process Theory (QPT)
- File: `Forbus1984_qualitative-process-theory.pdf` (86 pp; read: abstract + §1 concepts;
  influences/quantity-space material).
- Citation: Forbus, K. D. (1984). *Artificial Intelligence* 24:85–168.
- Summary: Models change via **processes**; quantities live in a **quantity space** of
  ordinal inequalities relative to landmarks. Two influence types: **direct influences
  (I+, I−)** (a process directly adds/subtracts to a rate) and **qualitative
  proportionality (∝Q+, ∝Q−)** (monotone functional dependence). Net effect on a quantity =
  sign sum of its influences; when positive and negative influences coexist the result is
  ambiguous unless relative magnitudes are known.
- **Relevance:** Wellman explicitly equates his qualitative influence S+ with Forbus' ∝Q
  (an inequality on partial derivatives). PhysioMap edges = ∝Q-style monotone signed
  dependencies; multiple influences into one node combine by **sign sum** — and stall to '?'
  on conflict. This is the per-node combination rule used in sign propagation.

### 3. Kuipers 1986 — Qualitative Simulation (QSIM)
- File: `Kuipers1986_qualitative-simulation.pdf` (50 pp; read: abstract + §§1–3 qualitative
  state / constraints, ~pp. 289–305).
- Citation: Kuipers, B. (1986). *Artificial Intelligence* 29:289–338.
- Summary: From a **qualitative differential equation** (constraints among variables, with
  monotonic-function constraints M+/M− that fix only the sign of a relationship), QSIM
  generates the tree of possible qualitative states (qval = ordinal value vs landmarks,
  qdir ∈ {inc, std, dec}) and transitions. Known limitation: may emit **spurious behaviors**
  not realizable by any real ODE — the price of dropping magnitudes.
- **Relevance:** confirms the general principle PhysioMap relies on — sign/order abstraction
  of an ODE is sound-but-incomplete; the analogue of QSIM's spurious branches is PhysioMap's
  '?'. PhysioMap deliberately solves only for steady-state sign(∂x*/∂θ) rather than
  simulating trajectories, sidestepping QSIM's branching/spuriousness.

### 4. Iwasaki & Simon 1986 — Causality in Device Behavior  ★ central
- File: `IwasakiSimon1986_causality-device-behavior.pdf` (16 pp; **read in full**, esp.
  §§4.1–4.2, pp. 18–19, "positivity/negativity of causal effects" & "minimal complete
  subsets").
- Citation: Iwasaki, Y. & Simon, H. A. (1986). *Artificial Intelligence* 29:3–32.
- Summary: Shows de Kleer & Brown's qualitative causal calculus **is** the classical method
  of **comparative statics + causal ordering**. Procedure: a device sits at equilibrium
  satisfying a self-contained equation system; differentiate w.r.t. a perturbed parameter;
  **replace differentials by their signs**; propagate signs through the equations to find
  signs of other variables. Indeterminacy ("dz = dx − dy = 0" with dx<0, dy>0 → sign(dz)
  unknown) is **normal, not pathological** — "countervailing forces" (the CO₂/greenhouse
  example). Sets of equations that cannot be ordered one-by-one form **minimal complete
  subsets** that must be **solved simultaneously**. Crucially: when feedback is present, the
  **conditions for stability of the equilibrium supply the signs of the partial
  derivatives** needed to make the propagation determinate.
- **Relevance (this is the PhysioMap blueprint):**
  - "Differentiate equilibrium system, replace differentials by signs, propagate" = exactly
    PhysioMap's comparative-statics step.
  - "Minimal complete subsets solved simultaneously" = PhysioMap's **SCCs**; acyclic remainder
    = one-by-one **sign propagation**. This justifies the SCC/condensation split.
  - "Countervailing forces → indeterminate sign" = PhysioMap's **'?'**, explicitly endorsed.
  - "Stability conditions supply the signs of partial derivatives" = PhysioMap's
    **stability / dominant-diagonal assumption**; it is what makes sign-solving possible.

### 5. Wellman 1990 — Fundamental Concepts of Qualitative Probabilistic Networks  ★ central
- File: `Wellman1990_qualitative-probabilistic-networks.pdf` (47 pp; read: §§1–4 in detail,
  pp. 257–270 — definitions, FSD/MLRP, sign operators, reduction/reversal; skimmed synergy
  §7).
- Citation: Wellman, M. P. (1990). *Artificial Intelligence* 44(3):257–303.
- Summary: A **QPN** = (V, Q) with **qualitative influences** S^δ(a,b), δ ∈ {+,−,0,?}, and
  **qualitative synergies** (interactions among influences). S+ formalized as **first-order
  stochastic dominance** of b's CDF as a increases, equivalently the **Monotone Likelihood
  Ratio Property** — a probabilistic monotonicity = an inequality on (partial) derivatives,
  the stochastic analogue of Forbus' ∝Q. Inference combines influences by **sign
  multiplication ⊗** (along a chain) and **sign addition ⊕** (parallel paths), via graph
  **reduction** and arc **reversal**. The **canonical direction** `dir(a,b)` collapses to ?
  when both + and − are derivable. **QPN graphs must be acyclic w.r.t. influence edges.**
- **Relevance:** defines PhysioMap's **sign algebra** (the ⊗ / ⊕ tables, the +/−/0/? lattice
  with "0 preferred, then +/−, then ?"). The transitivity (S+∘S+ ⇒ S+) is chain sign
  propagation on acyclic parts. **Key gap to bridge:** QPNs are *acyclic*; PhysioMap is
  *cyclic*, so within SCCs Wellman's reduce/reverse is replaced by sign-solvability /
  loop analysis (entries 7–8).

### 6. Druzdzel & Henrion 1993 — Efficient Reasoning in QPNs  ★ central (implementation)
- File: `DruzdzelHenrion1993_efficient-QPN-reasoning.pdf` (6 pp; **read in full**).
- Citation: Druzdzel, M. J. & Henrion, M. (1993). *Proc. AAAI-93*, 548–553.
- Summary: A **polynomial-time local sign-propagation** algorithm (Fig. 3). Each node holds
  a sign (init 0; evidence node set to +). Messages carry `sign := sign ⊗ link-sign`; a node
  updates `node.sign := node.sign ⊕ message.sign` and forwards to unvisited active neighbors.
  **Termination/complexity:** by the ⊕ table a node's sign can change **at most twice**
  (0 → {+,−,?} → ? only); ? is absorbing → **O(|V|²)**. Preserves graph structure (unlike
  graph-reduction), so it labels *all* nodes and supports explanation. Adds **product
  synergy / intercausal** ("explaining away") for instantiated colliders. Authors note that
  in **loops**, the common negative product synergy often **conflicts with positive links →
  '?'**, and the algorithm can then do meta-level reasoning about *which paths conflict*.
- **Relevance (directly drives `qualitative.py`):**
  - The message-passing loop with `node.sign = ⊕(node.sign, ⊗(incoming, edge))` is the
    reference implementation for PhysioMap's **acyclic sign propagation**.
  - **'?' is absorbing** — once ambiguous, stays ambiguous: a clean monotone fixpoint that
    guarantees termination. Adopt this invariant.
  - On a path each node updates ≤ twice ⇒ cheap; log *which trails* produced the conflicting
    signs to explain a '?' (PhysioMap's logging requirement).

### 7. Levins 1974 — Qualitative Analysis of Partially Specified Systems  (STUB)
- Stub: `Levins1974_loop-analysis_STUB.md` (+ Puccia & Levins 1985 book). **No PDF**
  (Wiley paywall, HTTP 402). Summary reconstructed from verified metadata + loop-analysis
  tutorials/`LoopAnalyst` docs — see stub for honesty note.
- Citation: Levins, R. (1974). *Ann. N.Y. Acad. Sci.* 231(1):123–138.
- Summary / relevance: **Loop analysis** of the signed **community matrix** (= Jacobian sign
  pattern) of a *cyclic* system. Press-perturbation response ∂x*_i/∂c_h = signed sum of
  (path h→i) × (complementary feedback) ÷ overall feedback F_n — the **adjugate/Cramer**
  structure. Stability needs every feedback level F_k < 0 (Routh–Hurwitz, qualitative).
  This is PhysioMap's exact setting: **sign(∂x*/∂θ) on a cyclic graph from sign pattern +
  stability**, with conflicting loop contributions → '?'. Best source for *explaining* a '?'
  (which loops disagree). See entry §(c).

### 8. Maybee & Quirk 1969 + sign-solvability classics  (STUB)  ★ the named method
- Stub: `MaybeeQuirk_sign-solvability_STUB.md` (Maybee–Quirk 1969 SIAM Rev;
  Bassett–Maybee–Quirk 1968 Econometrica; Lancaster 1962/1965; Samuelson 1947;
  Brualdi & Shader 1995). **No PDF** (SIAM/Econometrica/CUP paywalls, 402/403). Definitions
  reconstructed from verified search summaries incl. Brualdi's preface — see stub honesty
  note.
- Summary / relevance: **Sign-solvability** — Ax=b is sign-solvable iff sign(x) is fixed by
  sign patterns of A,b alone. **Sign-nonsingular (SNS)** matrix = every term of det A's
  expansion has the same sign (no cancellation). This is **the** named method PhysioMap
  adopted. See entry §(c) for the criterion as PhysioMap should implement it.

---

## (c) Sign propagation, ambiguity, and sign-solvability for comparative statics
### (the section that drives `qualitative.py`)

**Setup.** Steady state f(x*, θ) = 0. Implicit differentiation:
J · dx* = − (∂f/∂θ) dθ, where **J = ∂f/∂x** is the Jacobian (the signed community matrix).
So **dx* = − J⁻¹ b**, with b = (∂f/∂θ) dθ. We want **sign(dx*)** from sign(J), sign(b) only.

### Sign algebra (Wellman / Forbus / de Kleer–Brown)
Values {+, −, 0, ?}. Two operators:
- **⊗ (multiply, along a chain / serial edges):** sign product; anything ⊗ ? = ? (except
  0 ⊗ ? = 0).
- **⊕ (add, parallel paths / multiple influences):** + ⊕ + = +; − ⊕ − = −; x ⊕ 0 = x;
  **+ ⊕ − = ?** (the canonical ambiguity); ? ⊕ anything = ?.
- Lattice preference: 0 ≻ {+,−} ≻ ?. Prefer the strongest (most specific) derivable sign.

### Sign propagation on the ACYCLIC part (Druzdzel–Henrion algorithm)
For DAG regions / the condensation DAG of SCCs:
1. Init every node sign 0; set perturbed source to sign(dθ) (e.g. +).
2. Message passing: `msg.sign = src.sign ⊗ edge.sign`; on receipt
   `node.sign = node.sign ⊕ msg.sign`; forward to unvisited active neighbors.
3. **'?' is absorbing**; each node changes sign ≤ twice ⇒ **O(|V|²)** and guaranteed to
   terminate. Log the contributing trails so a '?' is explainable (which paths conflicted).

### **Where '?' legitimately arises** (collect & log all four)
1. **Parallel paths of opposite sign** (+ ⊕ − = ?) — Iwasaki–Simon's "countervailing
   forces"; Forbus' opposing influences; de Kleer–Brown's competing tendencies.
2. **Feedback loops with conflicting sign** — Druzdzel–Henrion note negative product
   synergy vs positive links in a loop → '?'; Levins: opposing loop products.
3. **Determinant cancellation inside an SCC** — the numerator/denominator sign-determinant
   has terms of both signs (not sign-determinate). This is the genuine sign-solvability '?'.
4. **Unknown sign(det J)** if stability is *not* assumed. PhysioMap assumes stability, which
   removes this case (see below) — so in practice '?' should come from 1–3, and that is what
   to log.

### Sign-solving WITHIN an SCC (Quirk–Maybee / Lancaster sign-solvability) ★
Inside a strongly connected component the variables are mutually dependent (Iwasaki–Simon's
"minimal complete subset") and must be solved **simultaneously**, not propagated. Use Cramer:

  **dx*_i = det( J with column i replaced by −b ) / det( J ).**

**Determinacy criterion (the rule to implement):**
- A determinant is **sign-determinate** iff, in its signed permutation expansion
  det = Σ_σ sgn(σ) Π a_{i,σ(i)}, **every nonzero term carries the same sign** (the
  sign-nonsingular / SNS condition — no cancellation between opposing terms).
- `sign(dx*_i)` is determined iff **both** det(J) and the replaced-column determinant are
  sign-determinate; then `sign(dx*_i) = sign(num) ⊗ sign(1/det J)`.
- **Otherwise return '?'** (and log which opposing terms/loops caused it). Equivalently, in
  loop-analysis language (Levins): determinate iff all path×complementary-feedback
  contributions to the (i,θ) response share one sign.

**Practical algorithm for an SCC:**
1. Form J restricted to the SCC; b = the (signed) inflow from already-resolved upstream
   nodes ⊗ edge signs (this couples SCC-solving with the outer propagation).
2. Fix `sign(det J)` from stability (below).
3. For each target i, expand the column-replaced determinant **symbolically over signs**;
   if all terms agree → that sign; if they conflict → '?'.
4. For larger SCCs, use the signed-digraph / bipartite-matching characterizations of
   sign-nonsingularity (Brualdi–Shader) instead of brute-force expansion.

### How stability / dominant diagonal buys determinacy (correspondence principle)
- **Samuelson's correspondence principle** (formalized by Bassett–Maybee–Quirk): assuming
  the equilibrium is **dynamically stable** supplies sign information otherwise missing.
- For a stable n×n system, **sign(det J) = (−1)ⁿ** — so the *denominator* in Cramer is
  sign-fixed *for free* (removes '?' case #4 above). PhysioMap's "negative diagonal /
  dominant self-regulation" is the structural sufficient condition (diagonally dominant with
  negative diagonal ⇒ stable, and ⇒ many minors sign-determinate).
- **Dominant self-regulation** also tends to make the diagonal term dominate each minor's
  sign expansion, so numerators are more often sign-determinate → fewer '?'. This is why
  PhysioMap *assumes* stability rather than checking it: it is the enabling assumption of the
  whole sign-only method.

### Implementation checklist for `qualitative.py`
- [ ] Sign type {+,−,0,?} with ⊗ and ⊕ tables exactly as Wellman Fig. 3; **'?' absorbing**.
- [ ] Condense graph into SCCs; topological order on the condensation DAG.
- [ ] **Acyclic edges:** Druzdzel–Henrion message passing (node.sign updated ≤ twice).
- [ ] **SCCs:** sign-solvability — Cramer determinants, sign-determinate test (all expansion
      terms same sign), `sign(det J) = (−1)^|SCC|` from assumed stability.
- [ ] On any conflict, emit **'?'** and **log the conflicting paths/loops/terms**.
- [ ] (Optional) loop-analysis view (Levins) for human-readable explanations of each '?'.

---

## (d) Cross-links to sibling resource folders
- **`../ode-causality/`** — Iwasaki–Simon (this folder) is the bridge: it equates the AI
  qualitative calculus with comparative statics on the equilibrium of an ODE system; the
  SCM-from-ODE papers there (Mooij 2013, Rubenstein 2018, Bongers 2021 cyclic SCM,
  Blom 2019 causal-constraints) formalize the *cyclic equilibrium → causal model* step that
  PhysioMap linearizes into a signed Jacobian.
- **`../causal-foundations/`** — d-separation / collider ("explaining away") used by Wellman
  and Druzdzel–Henrion for intercausal sign reasoning is the same machinery as causal-graph
  separation; PhysioMap's signed graph is a causal diagram with sign-annotated edges.
- **`../causal-knowledge-graphs/` & `../adverse-outcome-pathways/`** — sources of the signed
  causal edges PhysioMap consumes; sign propagation (this folder) is how predictions are
  computed over them.

---

## Files in this folder
| File | Type | Pages read |
|---|---|---|
| `deKleerBrown1984_confluences.pdf` | PDF | front matter + §§1–3 (~7–30) |
| `Forbus1984_qualitative-process-theory.pdf` | PDF | abstract + §1 |
| `Kuipers1986_qualitative-simulation.pdf` | PDF | abstract + §§1–3 (~289–305) |
| `IwasakiSimon1986_causality-device-behavior.pdf` | PDF | **full** (16 pp) |
| `Wellman1990_qualitative-probabilistic-networks.pdf` | PDF | §§1–4 (257–270) + §7 skim |
| `DruzdzelHenrion1993_efficient-QPN-reasoning.pdf` | PDF | **full** (6 pp) |
| `Levins1974_loop-analysis_STUB.md` | stub | metadata + secondary |
| `MaybeeQuirk_sign-solvability_STUB.md` | stub | metadata + secondary |

8 items: 6 read PDFs + 2 grounded stubs (each bundling several classics).
