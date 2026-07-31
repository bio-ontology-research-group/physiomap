# E2c — risk–coverage: is the abstention just "answering the easy ones"?  *** DRAFT ***

The sharpest reviewer objection to calibrated abstention: 100% precision at 19% coverage may be gamed,
since *any* method restricted to its most-confident 19% might also be ~100%. We test this with a
selective-prediction (risk–coverage) sweep on the 866 forward E1b pairs, thresholding the signed-
diffusion baseline by its confidence |r_v| and comparing to PhysioMap's single determinate/abstain
operating point. Reproducible: `scripts/e2c_risk_coverage.py` (map + committed HPOA).

## Result
PhysioMap operating point: **coverage 19.2% (166/866), precision 100.0%**.

Signed-diffusion, thresholded by |r| (selective prediction):

| coverage | precision | threshold |
|---|---|---|
| 2.3% | 100.0% | top 5% by \|r\| |
| 5.1% | 100.0% | top 10% |
| **10.3%** | 97.8% | top 19% |
| 13.7% | 97.5% | top 30% |
| **20.8%** | **95.6%** | top 50% |
| 33.3% | 83.0% | top 80% |
| 41.7% | 75.9% | all |

## Reading
At **matched coverage (~19–21%)** PhysioMap is **100%** while the confidence-thresholded diffusion
baseline is **~95.6%** — it still makes errors among its most-confident calls. Diffusion reaches 100%
only by collapsing to **~5% coverage** (≈4× less than PhysioMap). So the abstention is a **calibrated
boundary**, not cherry-picking the easy pairs: PhysioMap's determinacy test is a sharper confidence
signal than diffusion magnitude, dominating the baseline's entire risk–coverage frontier at and above
its own operating coverage. (Honest nuance: a baseline *can* hit 100% at very low coverage, so the
claim is matched-coverage dominance, not that no baseline is ever 100% anywhere.)
