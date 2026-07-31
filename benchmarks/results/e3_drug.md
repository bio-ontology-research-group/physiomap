# E3 — Drug-effect forward eval: ChEMBL MoA target clamp vs established biomarkers + SIDEKICK  *** DRAFT ***

A drug is a **pharmacological `do()`**: its ChEMBL mechanism-of-action target is clamped by action
direction (inhibitor/antagonist/blocker → `-`; agonist/activator/potentiator → `+`), and the
comparative-statics solver predicts the directional downstream phenotypes. This is the *second,
independent* perturbation class after the monogenic `do()` of E1, and it reuses the **same**
enzyme-activity nodes + reaction edges (an enzyme inhibitor is the same clamp as the Mendelian LoF
of that enzyme).

Reproducible: `scripts/e3_chembl_fetch.py` (+ `e3_chembl_fetch2.py`, targets-first) →
`scripts/e3_sidekick_extract.py` → `scripts/e3_drug_eval.py`. Data: ChEMBL MoA (7,561 drug-mechanism
rows), SIDEKICK (Zenodo 10.5281/zenodo.17779317), `benchmarks/hpo/drug_biomarkers.yaml`.

## Resolution
ChEMBL gives 7,561 drug→target mechanisms. PhysioMap's interventional **protein-node** coverage
(450 PR-grounded nodes → 65 drug-target UniProt accessions) resolves **53 single-target drugs** to an
enzyme/channel activity-node clamp (gene→UniProt→PR→node, same resolver as E1). PhysioMap encodes most
**receptors implicitly** (it has `aldosterone`, `angiotensin_II` as nodes, not the mineralocorticoid
receptor or ACE proteins), so receptor-targeted cardiovascular drugs do not auto-resolve — a coverage
limit, not an error.

## Part A — determinate on-target biomarker predictions (the useful result)
For 35 of the resolved drugs the clamp's target enzyme/channel maps to an **established clinical
biomarker** with a known direction (`benchmarks/hpo/drug_biomarkers.yaml`, every direction verified
against primary literature / FDA labels). The solver's determinate predictions:

| | |
|---|---|
| drugs | 35 (7 mechanism classes) |
| determinate biomarker predictions | **40** |
| **correct** | **40** |
| **wrong** | **0** |
| abstain | 0 |

**40/40 = 100%, 0 wrong.** Examples (all match established pharmacology):

- **Statins** (atorvastatin, simvastatin, rosuvastatin, pravastatin, pitavastatin, lovastatin,
  fluvastatin, cerivastatin) — `hmg_coa_reductase_activity ↓` → **LDL cholesterol ↓** ✓
- **CFTR potentiators/correctors** (ivacaftor, elexacaftor, tezacaftor, deutivacaftor, +6) —
  `cftr_activity ↑` → **sweat chloride ↓** ✓ — a **gain-of-function** clamp that **inverts** the
  cystic-fibrosis loss-of-function direction; the **CFTR inhibitors** (crofelemer, iowh-032)
  correctly give **sweat chloride ↑** (opposite sign, same node).
- **ADA inhibitor** pentostatin/coformycin → **deoxyadenosine ↑**; **PNP inhibitors**
  forodesine/ulodesine → **inosine ↑, guanosine ↑** — pharmacological **phenocopies** of ADA- and
  PNP-deficiency (the same clamp as the genetic IEM).
- **DPD inhibitors** (eniluracil, gimeracil) → **plasma uracil ↑**.
- **COMT inhibitors** (entacapone, opicapone, tolcapone, nebicapone) → **metanephrine ↓**.
- **Peripheral AADC inhibitors** (carbidopa, benserazide, foscarbidopa) → **plasma L-DOPA ↑,
  urinary dopamine ↓** (both directions on the FDA carbidopa-levodopa label).

This shows **usefulness across a second perturbation class**: directional drug-effect predictions that
match established biomarkers, including a GoF potentiator whose sign inverts the disease, with zero
wrong calls — and it reuses the E1 reaction-edge layer (drug inhibition ≡ genetic LoF of the same
enzyme), so the two evaluations corroborate each other.

## Part B — feedback-mediated side effects (SIDEKICK): sound abstention
Scored against the directional abnormal-quantity side-effect terms SIDEKICK records (single-ingredient
drugs; 10 of the resolved drugs cross-reference, 52 documented single-direction (drug, side-effect-node)
pairs):

| | |
|---|---|
| determinate predictions on documented side-effect nodes | 0 |
| **contradictions (predicted opposite of documented)** | **0** |
| **abstained** | **52 / 52 = 100%** |

Drug side effects are overwhelmingly **feedback-mediated** electrolyte / glucose / urate disturbances
(e.g. statin → hyperglycemia, COMT-inhibitor → blood-pressure changes) whose nodes sit in the
**~150-node whole-body homeostatic SCC**. There the solver uses the conservative loop engine
(`SCC_EXACT_MAX = 16`) and **abstains rather than guess** — exactly the E2 *calibrated-abstention*
boundary, now at the pharmacological scale, with **zero contradictions**. The solver does **not**
fabricate feedback side-effect directions it cannot determine.

## Reading
E3 is the same story as E1/E2 in a second perturbation class: **determinate where the network
determines the sign** (40/40 on-target biomarkers, including a sign-inverting GoF), **sound abstention
where feedback does not** (100% on deep-SCC side effects, 0 contradictions). The concrete, localized
next step is a **finer SCC decomposition** (the exact sign-solver is capped at SCC ≤ 16): it would
convert the Part-B abstentions into determinate feedback-side-effect predictions — the
spironolactone→K⁺ / ACE-inhibitor→K⁺ class — which currently abstain because `aldosterone`, `renin`,
and `plasma_potassium` are entangled in the giant SCC.
