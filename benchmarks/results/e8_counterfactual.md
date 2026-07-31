# E8 — rung-three qualitative counterfactuals: necessity + abduction information gain  *** DRAFT ***

The comparative-statics solver is a rung-two (interventional) engine; backward diagnosis is the
abduction step of rung-three reasoning. E8 implements the full counterfactual
(abduction $\to$ action $\to$ prediction) on the sign-SCM (`physiomap_core/counterfactual.py`) and
reports three things. Reproducible: `scripts/e8_counterfactual.py` (needs clingo; committed data only).

## (D) Probability-of-necessity attribution over the catalogue
For each (disorder lesion, observed phenotype), the qualitative **probability of necessity** PN asks:
would the phenotype be at baseline had the lesion been absent? For a single lesion the "lesion-absent"
world *is* the baseline, so PN is determinate iff the factual change is determinate.

| | |
|---|---|
| observed (disorder, phenotype) pairs | 866 |
| **necessarily attributable** (determinate but-for) | **166 (19%)** |
| abstained (PN undetermined, feedback core) | 700 (81%) |
| disorders with ≥1 determinate attribution | 97 |

**Honest note:** single-lesion PN equals forward determinacy (E1b); this is the rung-three *framing*
(mechanistic attribution: "this phenotype is necessarily caused by the lesion") of the rung-two result,
not new computation. It is the right object for a clinician asking *which* phenotypes a variant explains.

## (A) Worked but-for vignette — hereditary hemochromatosis
`do(hepcidin−)` (HFE loss of function):

| node | factual | counterfactual (no lesion) | PN |
|---|---|---|---|
| plasma iron | `+` | `0` | **necessary** |
| transferrin saturation | `+` | `0` | **necessary** |

"Had the lesion been absent, transferrin saturation would be normal" — a determinate qualitative
necessity, matching the textbook iron-overload mechanism (low hepcidin → ferroportin up → iron up).

## (B) Abduction information gain — the genuine rung-three content
Does conditioning on the patient's *other* observed phenotypes (the abduction step, encoded as ASP
integrity constraints — no surgery) resolve a sign the **marginal** `do(lesion)` query leaves `?`?

| | |
|---|---|
| disorders with ≥2 observed phenotypes tested | 153 |
| **SCC signs resolved by abduction** (`?` → determinate) | **139** |

Examples: under ACADVL, conditioning resolves `skin_blood_flow −`, `sweating −`, `shivering +`; under
APRT/ASL, `baroreceptor_firing_rate +`, `parasympathetic_tone +`, `renal_perfusion_pressure +`.

**This is the information gain that distinguishes rung-three from rung-two:** the lesion alone leaves
these feedback-core signs undetermined, but conditioning on the co-observed phenotypes pins them down.
**Sound by construction:** conditioning only *shrinks* the answer-set family, and the true world
satisfies the observations and lies in the (superset) family, so any cautious consequence under the
observations holds in the true world. These are therefore sound, patient-specific determinate
predictions for *unmeasured* phenotypes — the same calibrated-abstention discipline, now conditioned.

## Reading
Pure single-lesion but-for counterfactuals collapse to forward determinacy (D, A) — the cross-world
link is the magnitude background the sign abstraction discards. But the **abduction step is genuinely
informative** (B): observing part of a patient's phenotype determinately resolves other feedback-core
signs the intervention alone cannot, recovering 139 determinate calls. Rung-three reasoning in
PhysioMap is therefore real and useful precisely through abduction/conditioning, and it inherits the
soundness guarantee.
