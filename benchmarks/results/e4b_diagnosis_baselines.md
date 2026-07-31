# E4b - inverse-task comparators

External reference: HPOA `hp/releases/2026-02-16`. Closed pool of 175 single-lesion hypotheses; the true lesion is always present. Scoring, tie handling, and metrics are identical across arms; only the rule producing each candidate's predicted profile differs.

| inference rule | unique top-1 | top-3 | top-10 | MRR | median rank |
|---|---:|---:|---:|---:|---:|
| comparative static | 40/163 | 127/163 | 161/163 | 0.707 | 1 |
| shortest signed path | 30/163 | 94/163 | 105/163 | 0.535 | 2 |
| signed diffusion (alpha=0.85) | 30/163 | 99/163 | 110/163 | 0.558 | 2 |
| chance | 1/163 | 3/163 | 9/163 | 0.033 | 88 |
