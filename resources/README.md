# PhysioMap — literature base & lines of research

A curated, **read** library underpinning PhysioMap (a qualitative, cyclic, signed causal
map of human physiology). 49 open-access PDFs + 11 verified-abstract stubs across eight
lines of research, each with its own `NOTES.md` (overview, per-paper summaries with pages
read, theme synthesis, cross-links). This file is the cross-cutting synthesis and index.

> Honesty: every PDF here was downloaded and verified (`%PDF`, >30 KB) and read at the
> page counts recorded in each `NOTES.md`. Items marked **stub** are paywalled/book
> sources captured as full citation + a verified abstract/definition (no PDF). Nothing is
> fabricated. The standard comparative-statics Jacobian identity (below) is textbook, not
> quoted from a seed paper — flagged as such in `ode-causality/NOTES.md`.

## The eight lines of research

Each links to its folder's `NOTES.md` for detail.

### 1. ODE-equilibrium causality & cyclic SCMs — [`ode-causality/`](ode-causality/NOTES.md)
**The theoretical backbone.** The equilibrium of an ODE system *is* a structural causal
model, generically **cyclic**; feedback loops become directed cycles. Mooij–Janzing–
Schölkopf (2013) make the ODE→SCM construction precise (set `Ẋ=0`, keep a *labelled*
equilibrium equation per variable; `do()` overwrites the label) and show, under structural
stability, that intervention commutes with equilibration. Bongers et al. (2021, *Ann.
Statist.*) give the measure-theoretic foundations and the "simple SCM" regime in which
interventions and a Markov property are well-defined. Forré & Mooij (2017) define
**σ-separation** and the **acyclification** that reduces it to ordinary d-separation;
Forré & Mooij (2018) build cyclic causal *discovery* on it; Rubenstein et al. (2018)
extend to time-varying interventions (dynamic SCMs); Blom et al. (2019) mark the boundary
where conservation laws break the SCM picture (use Causal Constraints Models). This line
justifies PhysioMap's central modelling claim: **an intervention's qualitative prediction
is the sign of the steady-state comparative static `sign(dx*/dθ)`, computed over a cyclic
SCM whose Markov property is σ-separation.**

### 2. Causal-inference foundations — [`causal-foundations/`](causal-foundations/NOTES.md)
The classical backbone PhysioMap instantiates: SCMs, the **do-operator** (surgical,
modular replacement of one variable's assignment), **d-separation** (the acyclic criterion
σ-separation must reduce to), and the **interventionist theory of causation** (Woodward:
`X→Y` means *some possible intervention on X changes Y with all else held fixed* — exactly
Pearl's do-surgery). Pearl (2009, OA) and Peters–Janzing–Schölkopf (2017, OA book, Ch. 6
gives cyclic SCMs *and* the SCM↔ODE bridge) are the load-bearing reads; Eberhardt (2017)
maps the discovery-assumption lattice and names the cycle-capable methods (CCD, SAT-based).

### 3. Qualitative reasoning & sign-solving — [`qualitative-reasoning/`](qualitative-reasoning/NOTES.md)
The algorithmic heritage of `qualitative.py`. Qualitative physics (de Kleer & Brown
confluences = qualitative ODEs; Forbus QPT influences; Kuipers QSIM) and **qualitative
probabilistic networks** (Wellman 1990: the sign algebra `{+,−,0,?}` with chain ⊗ and
parallel ⊕, where **`+ ⊕ − = ?`**; Druzdzel & Henrion 1993: an O(|V|²) local sign-
propagation with '?' absorbing). Iwasaki & Simon (1986) bridge to **comparative statics**:
differentiate the equilibrium equations, replace differentials by signs, solve SCCs
simultaneously. The cyclic/feedback case is **loop analysis** (Levins) and the determinacy
question is **sign-solvability** (Maybee–Quirk, Lancaster): `sign(dx*)` is determined iff
the relevant signed determinants are *sign-nonsingular* (every term in the signed expansion
agrees) — otherwise `?`. The assumed stability + dominant negative diagonal fixes
`sign(det J)` and is precisely the "correspondence principle" licensing the sign-only method.

### 4. Mendelian randomization — [`mendelian-randomization/`](mendelian-randomization/NOTES.md)
How signed causal edges get *identified from data*. A genetic instrument is a `do()`-like
natural experiment satisfying Woodward's I1–I4; MR estimates the **total** effect, MVMR the
**direct** effect — the very total-vs-direct (comparative-statics) distinction PhysioMap's
`sign(dx*/dθ)` makes, where the conditioning choice can flip the sign. Vertical pleiotropy =
legitimate mediation through a node; horizontal pleiotropy = an off-path/confounded edge
(exclusion-restriction violation) — PhysioMap's edge-validity criterion. Crucially, the MR
literature states its own boundary: standard MR assumes an acyclic DAG and lifetime
estimands and **cannot represent feedback or dynamics** (Burgess network MR) — exactly the
regime PhysioMap's cyclic SCM + σ-separation is built for. MR is one leg of triangulation.

### 5. Adverse Outcome Pathways — [`adverse-outcome-pathways/`](adverse-outcome-pathways/NOTES.md)
PhysioMap's closest applied structural twin. An AOP is a qualitative, cross-scale causal
pathway: Molecular Initiating Event → Key Events → Adverse Outcome, with **Key Event =
node, Key Event Relationship = directed causal edge** (stated verbatim, Villeneuve 2014).
AOPs separate biology (chemical-agnostic) from perturbation, climb a putative→qualitative→
**quantitative (qAOP)** ladder mirroring PhysioMap's "signs now, dynamics later", and attach
**weight-of-evidence** to each KER (Bradford-Hill + KE **essentiality** ≈ the interventionist
criterion). They make "increase X"/"decrease X" *separate nodes*; PhysioMap compresses that
onto edge signs. The base AOP graph is acyclic and bolts feedback on as "layers" — PhysioMap
making cycles + the within-scale-causal vs cross-scale-constitutive split first-class is the
principled refinement. AOP-Wiki is the open, IRI-addressable knowledgebase to emulate (and
its thin formal QA is a cautionary tale: make per-edge provenance mandatory).

### 6. Causal knowledge graphs — [`causal-knowledge-graphs/`](causal-knowledge-graphs/NOTES.md)
How to represent, evidence and reason over causal edges at scale. Converging practice:
model an edge as a **typed triple** with the predicate from a controlled vocabulary
(GO-CAM and Biolink use the **Relations Ontology** `positively/negatively_regulates` under a
generic `regulates`; `?` → the unsigned parent, so reasoning degrades gracefully);
distinguish **direct vs indirect** (BEL `increases` vs `directlyIncreases`; PhysioMap's "edge
abbreviates a mechanism"); make **evidence a structured list + confidence** (INDRA
Evidence+belief, GO-CAM ECO codes, Hetionet provenance); **ground nodes in ontologies**
(PrimeKG: UBERON/GO/HPO/MONDO). Reason **symbolically** (Hetionet metapaths, BEL reverse
causal reasoning) — Nicholson & Greene warn that KG embeddings flatten edge sign/type/
direction, which would destroy PhysioMap's signed/cyclic/typed structure. GO-CAM is the
closest analog and the concrete shape a `mechanism` reference should expand into.

### 7. Virtual Physiological Human & the Physiome — [`virtual-physiological-human/`](virtual-physiological-human/NOTES.md)
PhysioMap is, in effect, a **qualitative VPH**: the multi-scale whole-body causal object the
VPH/Physiome community models quantitatively, projected onto signed, ontology-typed edges
with the kinetics dropped — the topology a quantitative model plugs into. The scale enum
comes from this community's own stack (Kohl & Noble; Hunter & Borg's ~9 spatial orders of
magnitude); constitutive cross-scale edges correspond to **CellML modularity** (imports/
encapsulation/mappings); CellML/SBML separate maths from an RDF+ontology semantic layer
(the layer PhysioMap's typed nodes live in). HumMod (the Guyton lineage) already encodes
physiology as declarative XML with per-variable cause→effect relations + literature
provenance — PhysioMap is the signed-qualitative abstraction of exactly that, and the Guyton
1972 model we vendored is literally a signed, cyclic, integrative causal graph.

### 8. Mechanism & ontology (EQ / PATO / BFO / RO / GO-CAM) — [`mechanism-ontology/`](mechanism-ontology/NOTES.md)
The formal grounding of nodes and edges. A node `(E, Q)` is an OWL **EQ class** — `Q that
inheres_in E` (Mungall 2010; Gkoutos–Schofield–Hoehndorf 2018) — with E a BFO independent
continuant (Uberon/CL/GO-CC/ChEBI) and Q a BFO quality (PATO); **determinable/determinate**
is native to PATO (attribute class vs value subclass). Node typing is checkable in OWL 2 EL
with ELK (`inheres_in_part_of` propagates classification up anatomy `part_of`). A **causal
edge abbreviates the BFO realization chain** quality → disposition → `realized_in` process →
quality (Arp/Smith/Spear; Machamer-Darden-Craver mechanisms), so the edge's `mechanism` ref
should be **GO-CAM-shaped**; type causal edges with **RO** (`causally_upstream_of` +
positive/negative variants; `regulates` family). **Cross-scale constitutive edges are
continuant-only** (`part_of` + a synchronic determination relation) and must never reuse the
occurrent-grounded causal relations — the formal basis for PhysioMap's hard causal/
constitutive separation.

## Cross-cutting synthesis: what the literature tells PhysioMap to do

**Node model.** Adopt the EQ pattern verbatim (`Q inheres_in E`); E/Q from Uberon/GO/CL/
ChEBI + PATO; determinable = PATO attribute, determinate/signed-change = value subclass;
validate in OWL 2 EL / ELK (line 8). The scale enum is the community's spatial granularity
stack (line 7). [✓ already in `model.py`: optional `entity_iri`/`quality_iri`, `Scale`.]

**Edge model.** A causal edge is a typed triple, not a bare arrow: back the `+/−/?` with an
**RO predicate** (`positively/negatively_regulates`; `?` → generic `regulates`/
`causally_upstream_of`); record **direct vs indirect**; point `mechanism` at a GO-CAM-shaped
activity graph (the abbreviated quality→disposition→process→quality chain); make `evidence`
a **structured list with confidence** following INDRA/GO-CAM/Hetionet, and adopt AOP
weight-of-evidence (Bradford-Hill + essentiality) as the per-edge confidence schema (lines
5, 6, 8). [→ a near-term refinement of `CausalEdge.mechanism`/`evidence`.]

**Constitutive (cross-scale) edges.** Continuant-only `part_of` + determination; never
causal; never traversed by σ-separation. Strongly licensed by BFO/RO (line 8) and matches
CellML modular interfaces (line 7). [✓ already a separate `ConstitutiveEdge` class.]

**σ-separation (sigma.py).** Implement via **acyclification → d-separation** as the source
of truth; it is exact, reduces to plain d-separation on a DAG, and σ-sep is the correct
cyclic Markov property (lines 1, 2). Precise recipe below.

**Qualitative solver (qualitative.py).** Sign algebra `{+,−,0,?}` with ⊗/⊕ and `+⊕−=?`;
O(|V|²) acyclic sign propagation with '?' absorbing (Druzdzel–Henrion); within an SCC do
**comparative statics by sign-solvability** — `sign(dx*)` determined iff the signed
determinants are sign-nonsingular, else `?`; stability + negative diagonal fixes
`sign(det J)` (lines 1, 3). Log every `?` with *which* loops/paths/terms conflict (Levins).
[✓ matches design decisions D2/D3.]

**Identification & validation (later).** Edges can be tested against data via MR (IV =
do()-like instrument; total vs direct effect = our comparative static; pleiotropy diagnoses
edge validity) and triangulated with mechanistic (ODE/Guyton) and KG evidence — independent
bias structures (lines 4, 1, 6).

## Key technical results to carry into the implementation

**σ-separation criterion + acyclification** (Forré & Mooij 2017; `Sc(v)` = SCC of `v`):
- *Acyclification* `G^acy`: condense each SCC; lift every inter-SCC edge to all node-pairs
  across the two SCCs (`v→w` iff `v∉Sc(w)` and `∃ w'∈Sc(w): v→w'`); erase all intra-SCC
  edges. Result is a DAG.
- *Equivalence* (Cor. 2.8.4): `X ⊥σ_G Y | Z  ⇔  X ⊥d_{G^acy} Y | Z`. So `sigma.py`:
  compute SCCs → build `G^acy` once → answer every query by d-separation on `G^acy`.
  Degenerates to plain d-separation when `G` is acyclic (the PhysioMap anchor).
- The direct σ-walk (our oracle) blocks/opens on **whole SCC segments**, not single nodes:
  a collider-segment opens iff its SCC intersects `An(Z)`; a non-collider segment with an
  outgoing path-edge blocks iff the relevant boundary node is in `Z`.

**ODE → SCM → comparative statics.** At a stable equilibrium `F(x*,θ)=0`, the implicit
function theorem gives `dx*/dθ = −(∂F/∂x)⁻¹ (∂F/∂θ)`, valid when `∂F/∂x` is nonsingular —
guaranteed at an asymptotically stable hyperbolic equilibrium. PhysioMap reports
`sign(dx*ₖ/dθ)`. Requires a unique locally stable equilibrium persisting under the
intervention, the simple-SCM regime, and **no binding conservation law** (else use a Causal
Constraints Model / dynamic SCM).

**Sign-solvability determinacy.** `dx*_i = det(J with col i ← −b)/det(J)`; a determinant's
sign is determined iff its signed expansion has no term-cancellation (sign-nonsingular).
Both numerator and denominator must be determinate, else `?`. Stability ⇒
`sign(det J)=(−1)^{|SCC|}` for free; dominant negative diagonal makes minors determinate.

**Interventionist edge semantics & do-operator.** `do(Xₖ=a)` replaces `Xₖ`'s assignment by
the constant `a`, leaving all other mechanisms intact; `X→Y` means a possible intervention
on `X` changes `Y` with all other variables held fixed (Woodward (M) ≡ Pearl do-surgery).

## Index

| # | Line of research | folder | PDFs | stubs |
|---|------------------|--------|------|-------|
| 1 | ODE-equilibrium causality, cyclic SCMs, σ-separation | `ode-causality/` | 7 | 0 |
| 2 | Causal-inference foundations (SCM/do/d-sep/interventionism) | `causal-foundations/` | 4 | 2 |
| 3 | Qualitative reasoning, QPNs, loop analysis, sign-solvability | `qualitative-reasoning/` | 6 | 2 |
| 4 | Mendelian randomization | `mendelian-randomization/` | 8 | 1 |
| 5 | Adverse Outcome Pathways (incl. qAOP, AOP networks) | `adverse-outcome-pathways/` | 6 | 3 |
| 6 | Causal knowledge graphs (INDRA/Hetionet/BEL/GO-CAM/Biolink…) | `causal-knowledge-graphs/` | 9 | 0 |
| 7 | Virtual Physiological Human & the Physiome | `virtual-physiological-human/` | 4 | 0 |
| 8 | Mechanism & ontology (EQ/PATO/BFO/RO/GO-CAM) | `mechanism-ontology/` | 5 | 3 |
| | **total** | | **49** | **11** |

Common paywall note across themes: NCBI/PMC now serves a JavaScript proof-of-work
interstitial that blocks scripted PDF fetches, and Annual Reviews / OUP / Nature / Elsevier
/ ACS / SIAM / Wiley are hard paywalls — hence the stubs (Guyton 1972, Ankley 2010, Conolly
2017, Becker 2015, Lawlor 2008, Levins 1974, Maybee–Quirk, Spirtes–Glymour–Scheines 2000,
Woodward 2003, GO-CAM, BFO, Machamer-Darden-Craver). Each stub carries a verified abstract
or captured definitions.
