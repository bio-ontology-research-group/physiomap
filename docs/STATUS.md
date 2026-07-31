# PhysioMap v1.1.1 status

PhysioMap v1.1.1 is the frozen resource and evaluation artifact prepared for
the PSB 2027 submission.

## Canonical representation

The authoritative release consists of:

```text
release/owl-scm/physiomap.owl
        + projection/patterns.yaml
        -> release/owl-scm/physiomap-scm.json
```

The OWL knowledge base and versioned projection registry reconstruct the
complete typed structural causal model without consulting the legacy YAML
curation inputs. The JSON model is the canonical solver input.

| content | count |
|---|---:|
| physiological traits | 1,699 |
| causal influences | 2,270 |
| production relations | 85 |
| constitutive constraints | 4 |
| quantitative identities | 9 |
| modulations | 19 |
| projected relation instances | 2,387 |
| largest causal feedback component | 213 traits |

## Evidence and review

Every projected axiom carries evidence and provenance. Of the 2,270 causal
influences, 1,367 have interventional evidence, 750 have mechanistic evidence,
and 153 remain explicitly marked as legacy-evidence-unclassified.

The frozen 621-item evidence-migration inventory contains 470 human-approved
resolutions and 151 open items. This admission metadata is distinct from the
five content relation types and is not read by the solver.

A fixed-seed expert review sampled 83 projected relations across all five
content types. The reviewer accepted 69, flagged 12 for further investigation,
and rejected 2. The workbooks and machine-readable audit are retained under
`docs/` and `docs/generated/`.

## Evaluation

The rare-disease benchmark contains 866 directional gene-phenotype pairs for
167 of 183 mapped inborn-error genes. The first-order solver made 171
determinate predictions and all 171 agreed with the adjudicated HPO-derived
reference. The remaining 695 predictions were explicit abstentions.

The full row-level benchmark is
`benchmarks/results/e1b_forward_pairs.tsv`. Comparative baselines and inverse
lesion-ranking results are under `benchmarks/results/`.

## Verification

The release gate rebuilds the ontology, projection, canonical model, web
payload, evaluations, generated result files, and checksums. It also runs the
Python and ontology test suites, browser smoke tests, and two byte-identical
builds:

```bash
uv run python scripts/owl_scm_release_gate.py
```

When a separate manuscript checkout is linked at `paper/`,
`--require-paper` also requires the main paper and supplementary material to
compile.

The verified release runs the complete Python and ontology test suites, web
rendering checks, and deterministic rebuild checks.

## Known boundary

The first-order solver uses derivative signs at a locally stable equilibrium.
It does not supply missing quantitative functions, parameters, exogenous
distributions, effect sizes, penetrance, thresholds, or dynamics. Exact
determinant expansion defaults to feedback components of at most 16 traits;
larger components use a conservative approximation. The limit is
configurable and has no semantic significance.
