# E2b — a stronger baseline: signed diffusion / random-walk-with-restart  *** DRAFT ***

A network-medicine reviewer would object that the E2 baselines (shortest signed path, forward-path
consensus) are both *path-product* propagators, while the field's actual workhorse for "signed
effect through a directed network" is **diffusion / random-walk-with-restart** (Cowen et al. 2017)
and SPIA-style perturbation-factor accumulation (Tarca et al. 2009). E2b adds that stronger baseline
on the **identical** signed causal graph and scores it on the **same** 866 (gene, phenotype) pairs.

Method: signed RWR `r = (1-α)(I-αS)^{-1} e_θ` on the do-surgered graph (`S` = sign-carrying,
out-magnitude-normalized transition; seed `e_θ` at the clamp), `sign(r_v)` = prediction, `|r_v|≤ε`
→ abstain. Reproducible: `scripts/e2b_diffusion_baseline.py` (α=0.85). No map mutation.

## Result
| method | determinate | correct | wrong | precision |
|---|---|---|---|---|
| **PhysioMap (comparative statics)** | 166 | 166 | **0** | **100.0%** |
| naive shortest signed path | 359 | 278 | 81 | 77.4% |
| naive forward-path consensus | 185 | 179 | 6 | 96.8% |
| **signed diffusion / RWR (α=0.85)** | **357** | 274 | **83** | **76.8%** |

- Where **CS abstains but diffusion commits** (191 pairs): diffusion accuracy **108/191 = 56.5% ≈ chance**.
- Head-to-head where **both** commit and **differ**: **0** — CS never directly contradicts the diffusion
  baseline; all 83 of diffusion's errors fall in the region where CS abstains.

## Reading
The stronger, field-standard propagator behaves exactly like the naive path-product baselines:
it commits ~2.2× more widely than PhysioMap (357 vs 166) at ~chance-grade precision inside the
feedback region, because `(I-αS)^{-1} = Σ αⁿSⁿ` sums signed walks of all lengths with a fixed scalar
`α` in place of the per-node dissipation that makes `∂F/∂x` Hurwitz, and never tests sign-solvability.
This converts the paper's claim from "we beat two naive baselines" into the stronger and more general
**"every additive signed propagator — path-product *or* diffusion — is unsound under physiological
feedback; soundness requires the comparative-static plus the sign-solvability test."** CARNIVAL/COSMOS
(signed-causal ILP contextualization, Liu 2019 / Dugourd 2021) are mentioned in prose as the
causal-ILP family but are not a fair per-pair sign comparator (they solve subnetwork identification
from a measured downstream footprint we do not have per HPO pair).
