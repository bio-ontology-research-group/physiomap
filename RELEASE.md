# PhysioMap release v1.1.1

Frozen source and evaluation artifact for the PSB 2027 submission. Built and
refrozen on 2026-07-31 after the approved vascular-effector corrections,
ontology-pattern revision, and expert content review.
Every number in the focused manuscript is regenerated from this artifact by
committed scripts under `scripts/`.
The public release gate is self-contained. When the separate manuscript
checkout is linked at `paper/`, `--require-paper` also makes both LaTeX builds
part of the acceptance contract.

Cite as: PhysioMap v1.1.1.

## Composition

| quantity | value |
|---|---:|
| trait nodes | 1,699 |
| causal influences | 2,270 |
| production relations | 85 |
| constitutive constraints | 4 |
| quantitative expressions | 9 |
| multiplicative modulations | 19 |
| projection traces | 2,387 |
| largest strongly connected component | 213 |

Schema 1.0.0, projection 1.4.0, generator 1.1.0.

## Frozen evaluation inputs

The HPO ontology and gene-to-phenotype annotations used by the rare-disease
evaluation are pinned to the 2026-02-16 release under
`benchmarks/data/hpo-2026-02-16/`. The acceptance contract verifies both
compressed and expanded checksums before evaluation.

## Causal-evidence classes

| class | count | share |
|---|---:|---:|
| `genetic_lof_gof` | 900 | 39.6% |
| `curated_mechanistic` | 544 | 24.0% |
| `pharmacological` | 311 | 13.7% |
| `mechanistic_model` | 206 | 9.1% |
| `perturbation` | 156 | 6.9% |
| unclassified (`legacy-evidence-unclassified`) | 153 | 6.7% |

Interventionally grounded (`genetic_lof_gof`, `pharmacological`,
`perturbation`): 1,367 of 2,270 (60.2%). Mechanistic
(`curated_mechanistic`, `mechanistic_model`): 750 (33.0%). The frozen
621-item review inventory has 470 human-approved resolutions and 151 open
items.

## File checksums (SHA256)

| file | bytes | sha256 |
|---|---:|---|
| `SHA256SUMS` | 1,248 | `7c42bf3ad13217f82399619a776babe1a6827512d704f81309bc2e672e19e426` |
| `legacy-evidence-baseline.json` | 219,966 | `67f7ba9a18e45306b1e5561bdbdf269a926a5c826f804637b5013c5292d0f882` |
| `legacy-evidence-decisions.yaml` | 483,060 | `f1e12188404b1e987d15383aeb590a0463bb1489f7ac9556b1a78f3d60548fa1` |
| `legacy-evidence-worklist.json` | 180,895 | `e2e175ffeeba8ff28354c0691c06251739d90628244e6c76a2080bb3eaf794d4` |
| `legacy-evidence-worklist.tsv` | 73,753 | `08064f082b21f506ae2cf4ff3eebb85a1a137b5093180f505c590fc501680421` |
| `migration-report.json` | 2,205,604 | `b13c9a4d8d0659fca6ec9ba351ba914d82cdccecad8b2c7b3742760d6c615528` |
| `patterns.yaml` | 3,448 | `d6c083b2e7feb6333cdf62e1ba255d7746bee5bad609b7c96904fe1fcc0fa6aa` |
| `physiomap-dl.owl` | 5,887,065 | `3a899cddd64fd0945020680e508d7f0483a1b6ef9fe232902e90678f3b176922` |
| `physiomap-el.owl` | 12,967,268 | `6ea278f96d46a85bae3619b55a5cd6d7a85cea28fa074ef408ba585b08a17543` |
| `physiomap-scm.json` | 5,923,844 | `9e4ff3dba9c9c5754c38f4cf7c71188c6c628ccdc5fbe10a5514e7fa6d165afa` |
| `physiomap-scm.schema.json` | 19,288 | `7d2b96f4a77d0a5509297c858ab8cb4d81dd3c30415f788587175d269e2334ff` |
| `physiomap.owl` | 29,859,999 | `7e061dc61c4649a151b25e3ca9375f54959ca6dea1a8fbb10d33fda60d4640c6` |
| `projection-entailments.tsv` | 149,335 | `65fd497171675ef760fc4a5fce71d1997fbfca1e187e89c692ced70b50586091` |
| `projection-traces.json` | 2,977,879 | `c56320154eabf7810fe249678d72798686b873d8703cc70d8d043340b5b46e55` |
| `trait-classification.tsv` | 240,920 | `7a205fdce96d79b5a522c6010eaa08ab076d34965b87838cba6c36fdeff0079c` |

## Minting a DOI

`.zenodo.json` is prepared at the repository root. After the final review and
commit, publish with:

```bash
git tag -a v1.1.1 -m "PhysioMap 1.1.1 (PSB 2027 submission artifact)"
git push origin v1.1.1
```

Then create the Zenodo release from the GitHub integration and record the DOI
here and in the manuscript. These external publication steps have not been run.
