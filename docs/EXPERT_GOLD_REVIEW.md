# Stratified expert content review

## Purpose

This review assesses the released content of PhysioMap v1.1.1 across all five
relation types. It complements the earlier curator audit, which evaluated
enrichment among low- and medium-confidence causal proposals rather than a
sample of released content.

The historical filenames contain `expert_gold`, but the returned judgments are
not treated as an infallible gold standard. They are the judgments of one
physiology expert and identify both accepted relations and relations requiring
correction or further investigation.

## Sampling design

`scripts/build_expert_gold_sample.py` drew a fixed-seed stratified sample from
the archived v1.1.1 SCM export. The sampling seed was `20260728`.

| relation type | reviewed | sampling frame | selection |
|---|---:|---:|---|
| causal influence | 50 | 2,270 | stratified by evidence class |
| production | 10 | 85 | simple random sample |
| modulation | 10 | 19 | simple random sample |
| constitution | 4 | 4 | complete stratum |
| quantitative identity | 9 | 9 | complete stratum |
| **Total** | **83** | **2,387** | |

The 50 causal influences comprised 18 genetic loss- or gain-of-function, 11
curated mechanistic, 6 pharmacological, 5 mechanistic-model, 5 perturbation,
and 5 unclassified assertions. The allocation was approximately proportional
to evidence-class size, with a minimum of five assertions for each class
containing at least five assertions.

The relation types were sampled at different rates. Consequently, the
unweighted overall counts below describe the reviewed sample and are not a
map-wide accuracy estimate.

## Review procedure and interpretation

The workbook showed each relation, its sign where applicable, its evidence
class, and any mechanism and evidence text. Paul N. Schofield reviewed the
relation content against his physiological knowledge and optionally supplied a
comment. The review was therefore not blinded to the map's supporting
information.

Verdicts are normalized as follows:

| workbook value | interpretation |
|---|---|
| `TRUE` | accepted |
| `FALSE?` | flagged for further review or investigation because it may be false or was not immediately verifiable |
| `FALSE` | rejected as false |

In particular, a flagged assertion was not counted as rejected.

## Results

All 83 assertions received a verdict, and 39 received a comment.

| relation type | accepted | flagged | rejected | reviewed |
|---|---:|---:|---:|---:|
| causal influence | 42 | 6 | 2 | 50 |
| production | 8 | 2 | 0 | 10 |
| constitution | 4 | 0 | 0 | 4 |
| quantitative identity | 8 | 1 | 0 | 9 |
| modulation | 7 | 3 | 0 | 10 |
| **Total** | **69** | **12** | **2** | **83** |

The comments identify actionable issues involving variable scope, conflated
processes, context-dependent direction, indirectness, and the representation
of curve shifts as local slope modulation. These comments should guide
targeted curation; they do not alter the meaning of the three verdict classes.

## Provenance and integrity

The template was sent to Paul N. Schofield on 2026-07-28. His completed
workbook was returned on 2026-07-30 in email
`290B9FDD-7683-4E05-A9F0-32AB06C3A10A@cam.ac.uk`.

| artifact | SHA-256 |
|---|---|
| decompressed v1.1.1 sampling frame | `9e4ff3dba9c9c5754c38f4cf7c71188c6c628ccdc5fbe10a5514e7fa6d165afa` |
| compressed sampling-frame archive | `5a3d55fd1934b694cc9b8555be194b4e19ddc77afcc285bd20573d4a048b8d68` |
| workbook sent | `dcd85e0d02cd3ddeb570d50eaaa5b6aa479d16fcac46774b9696c80266e4e06f` |
| workbook returned | `21a629623ad21d54964d42265270241ef49910ab4df17af89fdd6c63aecb9a05` |

The importer verifies that the returned workbook contains the same 83 review
identifiers and unchanged relation, sign, evidence-class, mechanism, and
evidence cells as the sent workbook. It also verifies that all 83 verdicts can
be normalized. The attached prose digest was generated after the review and
is not used as an input.

## Archived artifacts

| file | role |
|---|---|
| `benchmarks/data/physiomap-scm-expert-review-2026-07-28.json.gz` | exact sampling frame |
| `scripts/build_expert_gold_sample.py` | fixed-seed sampler |
| `benchmarks/results/expert_gold_sample.tsv` | sampled rows, with missing cells encoded as `\N` |
| `benchmarks/results/expert_gold_sample.json` | sampled rows in JSON |
| `docs/physiomap_expert_gold_review_2026-07-28.xlsx` | exact workbook sent |
| `docs/physiomap_expert_gold_review_returned_2026-07-30.xlsx` | exact workbook returned |
| `scripts/import_expert_gold_review.py` | integrity checks and verdict normalization |
| `benchmarks/results/expert_gold_review.tsv` | complete row-level judgments, with comment line breaks escaped |
| `benchmarks/results/expert_gold_review.json` | complete judgments and provenance, preserving reviewer text |
| `benchmarks/results/expert_gold_review_summary.json` | aggregate results and provenance |
| `docs/generated/expert-gold-review-macros.tex` | generated manuscript counts |
| `docs/generated/expert-gold-review-by-type.tex` | generated manuscript table |

Reproduce the sample and verify all derived review artifacts with:

```bash
python3 scripts/build_expert_gold_sample.py --seed 20260728
python3 scripts/import_expert_gold_review.py --check
```

The second command fails if the sent or returned workbook has changed, an
identity cell differs, a verdict is unrecognized, or a derived artifact is
stale.
