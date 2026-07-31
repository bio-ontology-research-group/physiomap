# Connecting phenotype nodes to core physiology — multi-agent literature fan-out  *** DRAFT FOR REVIEW ***

Two coordinated multi-agent literature fan-outs that (1) connect previously-orphan HPO
phenotype/analyte nodes to the core physiology by specific mechanisms, and (2) add the
multiplicative (gain) **modulation** edges those connections surface — following George Gkoutos's
heart-rate template (`benchmarks/human/systems/george_heart_rate.yaml`). Everything here is a
**draft for domain review**.

## Motivation

Of the composed human/HPO map's 1555 nodes, **270 HPO-mapped phenotype nodes were causal ROOTS**
— no upstream parent, so no intervention could ever reach them (they abstain by default). The HPO
gap-fill (v0.8.0) deliberately added them node-first/edge-conservative; this pass adds the
*mechanistic edges* where a real, literature-grounded physiological controller exists — and only
there.

## Pipeline

**Part 1 — phenotype connections.** 270 roots grouped into 18 themes (by analyte class). Per theme:
a **connect** agent literature-searches each analyte's physiological regulation and proposes signed,
cited mechanism edges; an independent **adversarial verify** agent re-checks every sign, citation,
scale, and direction. 18 + 18 = 36 agents.

**Part 2 — modulation (gain) edges.** 6 gain domains (glucocorticoid permissiveness, thyroid
β-adrenergic sensitization, Bohr/O₂-haemoglobin affinity, calcium/vitamin-D/PTH gain, insulin
counter-regulatory gain, autonomic/renal permissive). Per domain: a **propose** agent + an
**adversarial verify** agent. 6 + 6 = 12 agents.

## Discipline (the hard rules, enforced)

- **Honest connect-vs-abstain.** Connect an analyte only where a genuine physiological mechanism
  regulates it from a core variable. Pure gene-product analytes (most lysosomal/mitochondrial/muscle
  enzyme *activities*, idiosyncratic organic acids) have no upstream physiological controller —
  **76 were left as sound-abstaining roots, not fabricated** (a parentless node can never give a
  wrong sign; an invented edge can).
- **Backward-safe direction.** Prefer `core_node → analyte` (analyte = downstream **sink**): it
  makes the analyte forward-predictable without creating new explanatory paths through the
  feedback-dense diagnostic core.
- **Verified citations.** Every PMID/DOI web-checked or replaced by a textbook anchor (the project
  has been burned by fabricated PMIDs). Adversarial verifiers corrected unverifiable citations
  (e.g. one gain's "Endocrine Reviews 2026" → the canonical Exton et al. *J Biol Chem* 1972,
  PMID 4337859).
- **Modulation edges gated harder.** A gain is admitted only with **interventional interaction
  evidence** (a two-factor `do()` whose slope changes with the modulator, or a mechanistic cross
  term); the modulated base edge must already exist. Enforced by `validate_causal_evidence.py`.

## Yield (integrated, behind the gates)

- **`benchmarks/human/systems/phenotype_connections.yaml`** — **43 within-scale signed causal edges
  + 2 new nodes** (`plasma_riboflavin`, `hepatocellular_injury`), connecting **38 orphan phenotype
  nodes** (270 → 232 HPO-mapped roots). Examples: `cortisol →(−) plasma_tryptophan` (hepatic TDO
  induction), `il6 →(+) plasma_alpha1_antitrypsin` / `plasma_ca125` (acute-phase), `plasma_insulin
  →(−) plasma_apolipoprotein_c3`, `hepatocellular_injury →(+) plasma_alt/ast`, `cellular_cobalamin_uptake
  →(+) methylmalonyl_coa_mutase_activity`, `adipose_tissue_mass →(−) plasma_25oh_vitamin_d`.
- **`benchmarks/human/systems/modulation_gains.yaml`** — **14 multiplicative (gain) modulation
  edges** (composed map: 1 → **15** modulation edges). Each scales an *existing* causal edge and
  carries interventional interaction evidence:
  - **Glucocorticoid permissiveness** — cortisol scales `norepinephrine → total_peripheral_resistance`
    (Pirpiris *Hypertension* 1992), `epinephrine → lipolysis_rate`, `plasma_glucagon →
    hepatic_glucose_production` and `epinephrine → hepatic_glycogenolysis` (Exton 1972; Chan 1984).
  - **Thyroid β-adrenergic sensitization** — free T3 scales `sympathetic_tone →
    myocardial_contractility` (Carvalho-Bianco *Mol Endocrinol* 2004), `→ metabolic_rate`, and
    `epinephrine → lipolysis_rate`.
  - **Bohr effect** — pCO₂, temperature, 2,3-BPG each *lower* the gain of `arterial_po2 →
    hemoglobin_o2_saturation`; arterial pH *raises* it (right/left shift of the O₂-Hb curve).
  - **Other** — plasma Ca²⁺ scales `synaptic_acetylcholine → postsynaptic_membrane_potential`;
    adiponectin scales `plasma_insulin → peripheral_glucose_uptake`; angiotensin II modulates
    `baroreceptor_firing_rate → sympathetic_tone` (baroreflex gain).

  Modulation edges sit in a **parallel layer** (not in `causal_subgraph`), so they change **no**
  node-level sign prediction — they only enable the gain-sensitivity query, e.g.
  `python -m physiomap_core.modulation free_t3 + sympathetic_tone myocardial_contractility` → gain
  `+`. 10 of the 14 already have their first-order additive shadow edge present (fully consistent);
  the other 4 are flagged (sound: the gain query is represented even where the additive shadow is not).

## Deferred (held for review) → `benchmarks/results/phenotype_connections_deferred.yaml`

**7 forward-sound, sign-verified causal edges** held out:
- **5** would form a cross-scale meta-graph cycle (the sink target has an existing constitutive lift
  / downstream edge back into the core) — e.g. `il6/tnf_alpha → csf_chi3l1`, `pituitary_gh →
  plasma_mbl`, `gfr → plasma_folate`, `extracellular_fluid_volume → urinary_pge2`.
- **1** couples the delicate FGF23-klotho SCC (`calcitriol → plasma_osteocalcin`) — costs X-linked
  hypophosphatemic rickets its unique top-1 backward recovery (consistent with the existing
  FGF23-klotho abstention note).
- **1** references a `benchmarks/multiscale/` node outside the human/systems composition
  (`erythroblast_proliferation → erythrocyte_pyruvate_kinase_activity`).

Plus the **76 honestly-abstained analytes** (with per-analyte reasons) recorded in the same file.

## Soundness & gating (all green)

- **Meta-graph acyclicity** preserved (the 5 cycle-forming edges deferred by bisection).
- **Forward soundness:** REAL-HPO **23/23 determinate correct, 0 wrong**; curated pilot **18/18, 0
  wrong**. **Backward top-3 20/20**, and **fgf23 unique top-1 preserved** (the 1 axis edge deferred
  by bisection).
- **Ontology IDs:** `verify_ontology_ids.py` — **999/999 OK** (manifest regenerated). **Causal
  evidence:** 43/43 causal edges + 14/14 modulation edges admitted (interventional/interaction).
- **Full test suite green.**

Composed human/HPO map: **1557 nodes / 1756 causal edges / 15 modulation edges** (was 1555 / 1713 / 1).
