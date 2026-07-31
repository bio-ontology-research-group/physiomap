# E5 (stretch) — population conditional-independence on NHANES  *** DRAFT ***

PhysioMap implies (conditional) independences via **σ-separation** (acyclification + d-separation,
determinism-aware). We test these against the NHANES 2017–2018 population survey: 23 lab analytes +
mean arterial pressure mapped to PhysioMap nodes, **n = 2,154 complete-case adults**, full
partial-correlation matrix (precision-matrix), Fisher-z significance at Bonferroni α.

Reproducible: `scripts/e5_nhanes_ci.py`. Data: NHANES 2017–2018 public XPT (CDC `.../Public/2017/
DataFiles/`), not redistributed.

## Result 1 — σ-separation is uninformative inside the giant SCC (a quantified limitation)
All 24 mapped analytes lie in (or are entangled through) the **~150-node whole-body homeostatic SCC**.
Under acyclification an SCC becomes a bidirected clique, so its members are **mutually inseparable** —
σ-separation therefore implies **0 conditional independences** among these analytes (276/276 pairs
σ-connected). But NHANES shows **215/276 (78%) of pairs are conditionally *independent*** (partial
r ≈ 0). So at the resolution of one giant SCC the model **massively over-predicts dependence**. This is
the same coarseness that makes E3 drug side effects and E4 feedback-core diagnoses abstain — now
**quantified on real population data**, and the strongest empirical case for the SCC-refinement future
work.

## Result 2 — the curated *local* structure does predict conditional dependence
σ-separation given everything is a blunt instrument here, but the graph's local geometry is not. Causal
**graph proximity predicts the magnitude of conditional dependence**:

| causal graph distance | pairs | conditionally dependent | mean \|partial r\| |
|---|---|---|---|
| ≤ 2 (adjacent / 1 intermediate) | 43 | 35% | **0.236** |
| > 2 | 233 | 20% | **0.054** |

Mean partial correlation is **~4× higher** for causally-proximal analyte pairs. The strongest NHANES
partial correlations are exactly the pairs the curated map links directly or by a definitional identity:

| pair | \|partial r\| | graph dist | model relation |
|---|---|---|---|
| total-chol ↔ LDL / HDL / triglycerides | ≈ 1.00 | 2 | **definitional** (Friedewald identity)* |
| hemoglobin ↔ hematocrit | 0.96 | 2 | near-definitional (Hct ≈ 3·Hgb) |
| plasma iron ↔ transferrin saturation | 0.91 | 1 | definitional (TSAT = Fe/TIBC), directly adjacent |
| sodium ↔ chloride / bicarbonate | 0.73 / 0.50 | — | electrolyte/anion coupling |
| chloride ↔ bicarbonate | 0.49 | 1 | directly adjacent (anion balance) |
| creatinine ↔ BUN | 0.48 | 2 | renal clearance |

\* The lipid identities sit at \|r\|=1 partly because NHANES LDL is itself Friedewald-derived from
TC/HDL/TG — so this is a *tautological* data correlation; it confirms the model encodes the right
algebraic relationship (the **deterministic-closure / definitional-edge** machinery) but is not an
independent statistical test. The non-lipid pairs (Hgb–Hct, Fe–TSAT, electrolytes, creatinine–BUN) are
independent corroboration that causal adjacency tracks population conditional dependence.

## Reading
E5 is an honest, mixed result, as befits the stretch experiment. **σ-separation as a whole-SCC CI
oracle fails on this analyte panel** — every analyte is in the one giant homeostatic loop, so the model
implies no independences while the population shows mostly conditional independence. **The curated
edge structure nonetheless aligns with population conditional dependence** (proximal pairs ~4× stronger;
definitional identities recovered at \|r\|≈1). Both halves point to the same fix that E3/E4 identified:
a **finer decomposition of the whole-body SCC** would let σ-separation express the within-core
conditional independences that NHANES actually exhibits. PhysioMap currently buys soundness with a
coarse loop that abstains; population data shows exactly where the loop should be resolved.
