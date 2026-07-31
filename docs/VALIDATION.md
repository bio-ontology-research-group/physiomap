# PhysioMap v1.1.1 validation

This document states what the released evaluations test and what their results
support. Every value below is regenerated from the committed source and fixed
evaluation inputs.

## Release acceptance contract

Run the complete repository-owned acceptance contract with:

```bash
uv run python scripts/owl_scm_release_gate.py
```

The command verifies and expands the pinned HPO evaluation inputs, rebuilds the
OWL knowledge base and structural causal model, checks OWL-only reconstruction
and ontology reasoning, validates the schema and quantitative constraints,
regenerates the web data and evaluations, runs the Python and ontology test
suites, renders the website in a headless browser, and compares two
independent builds byte for byte.

When the separate manuscript repository is linked at `paper/`, submission
maintainers can also require both LaTeX documents to compile:

```bash
uv run python scripts/owl_scm_release_gate.py --require-paper
```

## Rare-disease application

The fixed benchmark contains 866 directional gene-phenotype pairs for 167 of
183 mapped genes associated with inborn errors of metabolism. The full
row-level mapping is
[`e1b_forward_pairs.tsv`](../benchmarks/results/e1b_forward_pairs.tsv).

| Evaluation | Result | Interpretation |
|---|---:|---|
| comparative-static forward inference | 171 correct, 0 wrong, 695 abstentions | All determinate calls agreed with the adjudicated HPO-derived reference. This is selective directional accuracy, not recall or independent clinical validation. |
| leakage-controlled forward inference | 151 correct, 0 wrong, 657 abstentions | Removing disease-specific authored relations did not introduce a wrong determinate call in the controlled subset. |
| naive forward propagation | 186 correct, 5 wrong, 675 abstentions | Greater coverage came with five incorrect determinate calls. |
| naive shortest signed path | 292 correct, 83 wrong, 491 abstentions | Path reachability alone did not preserve directional precision under feedback. |

The complete forward results are
[`e1b_forward.json`](../benchmarks/results/e1b_forward.json) and
[`e2_baseline.json`](../benchmarks/results/e2_baseline.json). The
precision-coverage analysis is
[`e2c_risk_coverage.csv`](../benchmarks/results/e2c_risk_coverage.csv).

For inverse inference, 163 lesions were ranked against a fixed pool of 175
candidates. PhysioMap placed 40 lesions first, 127 in the top three, and 161
in the top ten, with mean reciprocal rank 0.707. The signed shortest-path and
signed-diffusion comparisons had mean reciprocal ranks of 0.535 and 0.558,
respectively. These results measure recovery within the fixed candidate pool.
They do not establish diagnostic performance in an open clinical setting.

The inverse results are
[`e4_diagnosis.json`](../benchmarks/results/e4_diagnosis.json) and
[`e4b_diagnosis_baselines.json`](../benchmarks/results/e4b_diagnosis_baselines.json).

## Relation-layer sensitivity

The cumulative relation-layer analysis is a sensitivity diagnostic, not
evidence that each typed layer improves this particular application. Relative
to the complete evaluated fragment, causal influence alone changed four of 866
forward outcomes and 12 of 163 inverse ranks. Adding production left one
forward difference and no inverse-rank differences. Adding quantitative
identity removed the remaining difference. Constitution produced no further
change in this benchmark, and modulation was not an input to the first-order
endpoint solver.

The result supports semantic separation of the relation types, but the rare
disease tasks provide little empirical leverage for estimating the added
application value of the sparse non-causal layers. See
[`e5_typed_layer_ablation.json`](../benchmarks/results/e5_typed_layer_ablation.json).

## Expert content review

A fixed-seed stratified sample covered all five released relation types. One
physiology expert accepted 69 of 83 sampled relations, flagged 12 for further
review or investigation, and rejected 2. `FALSE?` was normalized to
`flagged`; only `FALSE` was normalized to `rejected`.

This review strengthens the claim that the release has received cross-type
expert scrutiny. It does not provide a map-wide accuracy estimate because the
relation types were sampled at different rates and the judgments came from one
reviewer. The sample, original and returned workbooks, normalized rows,
checksums, and interpretation are in
[`EXPERT_GOLD_REVIEW.md`](EXPERT_GOLD_REVIEW.md).
