# E9 — the qualitative (sign-only) second-order layer of multiplicative edges  *** DRAFT ***

A multiplicative (gain) edge "modulator `m` scales `s → t`" is intrinsically a **second-derivative**
object: `J_ts = k(x_m) g'(x_s)`, with distinctive content the mixed partial
`∂²t/∂s∂m = k'(x_m) g'(x_s)`. The standard objection is that a *multiplicative* effect needs
magnitudes. E9 shows the opposite for its **sign**: the sign of a second derivative is itself a
qualitative object, so "up/down alone" recovers three useful, falsifiable predicate classes — under
the same calibrated-abstention discipline as the rest of PhysioMap. (A modulation = a Qualitative
Probabilistic Network *additive synergy*, `sign ∂²/∂s∂m`; we instantiate it in the interventional,
cyclic setting.) Reproducible: `python scripts/e9_modulation.py` (committed fixtures only).

Define `μ` = modulation sign (`sign dk/dm`), `σ` = base-edge sign, and the **interaction sign**
`ι = μ·σ` (amplify `+` / dampen–toward-reversal `−`).

## (A) Interaction sign `ι = μ·σ` vs the textbook interaction direction

| | |
|---|---|
| modulation (gain) edges | 15 |
| determinate interaction signs `ι` | **15 / 15** |
| match independent textbook direction | **15 / 15 (100%)** |

`μ` (gain layer) and `σ` (additive causal layer) are curated **separately**, so `ι = μ·σ` matching the
independently-known direction (`benchmarks/human/modulation_validation.yaml`: Bohr effect, glucocorticoid
permissiveness, thyroid β-adrenergic sensitization, adiponectin insulin-sensitization, Ca²⁺ membrane
stabilization, …) is a **joint-consistency check of both curated layers**, not a restatement of one.
Examples: ↑pCO₂ / ↑temperature / ↑2,3-BPG each **dampen** (`−`) the pO₂→Hb-saturation relation (right-shift),
↑pH **amplifies** (`+`) it; cortisol **amplifies** (`+`) the noradrenergic pressor edge.

## (B) Synergy / antagonism for a joint `do(source↑, modulator↑)` — the multi-node payoff

For each gain edge we clamp **both** endpoints up and read the cross term `ι·Δs·Δm` at the target:

| | |
|---|---|
| determinate **cross-term sign** (reinforce ↑ / oppose ↓) | **15 / 15** |
| full **super-/sub-additive** label (synergistic / antagonistic) | **1 / 15** |
| — of which antagonistic (sub-additive) | 1 (`ACh × Ca²⁺ → membrane potential`) |
| reinforces-only (cross signed, additive **net** target `?`) | 14 / 15 |

**The key finding:** the second-order **cross term is sign-determinate in every case (15/15)** — it is a
*local product* `ι·Δs·Δm` that needs no loop inversion — whereas the first-order **net level abstains
14/15** because most modulated targets (heart rate, TPR, sympathetic tone, Hb-saturation, hepatic
glucose…) sit in the whole-body feedback SCC (`−J⁻¹` ambiguous). So *the curvature is more robust than
the level in a feedback system*: even where we cannot sign whether the target rises or falls, we can
determinately sign whether the two interventions **reinforce or oppose** each other's effect on it. The
strict "synergistic/antagonistic" label additionally requires the additive net to be determinate, which
holds only for the one modulated target outside the giant SCC (`ACh × Ca²⁺`, correctly **antagonistic** —
extracellular Ca²⁺ stabilizes the membrane against ACh depolarization). This is exactly the soundness-by-
abstention contract, one order up.

## (C) Sensitization coverage over the monogenic-lesion panel

A single intervention can change a *coupling's gain* without itself being one of its endpoints
(`gain change = μ·sign(Δm)`), a prediction class the additive sign graph cannot express:

| | |
|---|---|
| monogenic lesions evaluated | 183 |
| lesions with ≥1 **determinate** gain change | 6 |
| total determinate gain-change calls | 18 |

e.g. `do(free_T3↑)` determinately **strengthens** the sympathetic→heart-rate, →metabolic-rate and
→contractility couplings and epinephrine→lipolysis; `do(cortisol↑)` strengthens the noradrenergic
pressor edge and the catecholamine metabolic edges (glucocorticoid permissiveness). The number is small
because a gain change is determinate only where the modulator's own response to the lesion is determinate
— it abstains soundly otherwise.

## Reading

Multiplicative edges are **not** dead weight without magnitudes. Sign-only, they deliver: an intrinsic
**interaction direction** (A, 15/15 validated), determinate **reinforce/oppose** verdicts for combined
interventions (B, cross sign 15/15) — sharper than the abstaining level prediction — and a **sensitization**
predicate (C). What genuinely needs numbers is the *threshold* of a sign-flip, the *resolution of an
additive-vs-multiplicative trade-off*, and the *magnitude* of a gain — exactly the targets of the
quantitative-data plan (MR for interaction-sign validation at scale; sign-constrained QPN fits for the
magnitudes within these fixed signs). The qualitative second-order layer is the sound scaffold those
numbers would hang on.
