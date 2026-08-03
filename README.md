# PhysioMap

PhysioMap is an ontology-grounded causal knowledge graph of human physiology.
It represents physiological traits across molecular, cellular, tissue, organ,
and whole-body scales and gives each relation type an explicit structural
causal model semantics.

[![Release v1.1.1](https://img.shields.io/badge/release-v1.1.1-356b9f.svg)](https://github.com/bio-ontology-research-group/physiomap/releases/tag/v1.1.1)
[![Code license: BSD 3-Clause](https://img.shields.io/badge/code-BSD--3--Clause-blue.svg)](LICENSE)
[![Data license: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey.svg)](LICENSE-DATA)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](pyproject.toml)
[![Live viewer](https://img.shields.io/badge/viewer-bio2vec.net%2Fphysiomap-3b7d6b.svg)](https://bio2vec.net/physiomap/)

The current release is **PhysioMap v1.1.1**. The release fixes the knowledge
base, projection registry, causal model, evaluation inputs, generated results,
and provenance needed to reproduce the accompanying paper.

## Representation

The authoritative resource has three versioned parts:

```text
OWL knowledge base + projection registry -> typed structural causal model
```

- [`release/owl-scm/physiomap.owl`](release/owl-scm/physiomap.owl) is the
  authoritative OWL 2 knowledge base.
- [`projection/patterns.yaml`](projection/patterns.yaml) defines which
  entailed ontology patterns project to causal-model constructs.
- [`release/owl-scm/physiomap-scm.json`](release/owl-scm/physiomap-scm.json)
  is the canonical typed causal model used by the software.

PhysioMap traits denote quantitative random variables. Its five content
relation types constrain structural functions in different ways:

| relation type | structural causal model interpretation |
|---|---|
| causal influence | a source variable enters a target mechanism as a non-constant direct dependence |
| production | a process contributes an output term to the mechanism of its product |
| constitution | constituent variables determine a variable of the whole through a constitutive map |
| quantitative identity | a named variable equals a specified function of other variables |
| modulation | a modulator changes the derivative of one variable with respect to another |

Derivative signs form a separate abstraction of these quantitative
constraints. The implemented first-order solver uses this abstraction to
compute the sign of a steady-state response after an intervention. It returns
`+` or `-` only when the available signs determine the response and returns `?`
otherwise. A separate gain-sensitivity query uses modulation relations.

Evidence and provenance are not PhysioMap content types and are not solver
inputs. They document why each axiom was admitted, where it came from, and how
it was reviewed. The distinction between content and construction evidence is
described in [`docs/MULTISCALE.md`](docs/MULTISCALE.md). The released content
review is documented in
[`docs/EXPERT_GOLD_REVIEW.md`](docs/EXPERT_GOLD_REVIEW.md).

## Current release

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

The fixed-seed expert content review examined 83 projected relations across all
five relation types. The reviewer accepted 69, flagged 12 for further
investigation, and rejected 2. These counts describe the reviewed sample, not
a map-wide accuracy estimate.

In the rare metabolic disease evaluation, the first-order solver made 171
determinate predictions among 866 directional gene-phenotype pairs, all
concordant with the literature-adjudicated HPO-derived reference. The
evaluation measures selective directional prediction and ranking within a
closed lesion pool. It is not an independent clinical validation.
The complete adjudicated pair set, including the primary intervention and
supporting HPO classes for every row, is
[`benchmarks/results/e1b_forward_pairs.tsv`](benchmarks/results/e1b_forward_pairs.tsv).
The gene-stratified conditional randomization analysis of whether abstention
tracks shortest-path errors is archived at immutable revision
[`79ff2fb`](https://github.com/bio-ontology-research-group/physiomap/tree/79ff2fb).
That revision contains the exact
[`scripts/e2_baseline.py`](scripts/e2_baseline.py) implementation and its
[human-readable](benchmarks/results/e2_baseline.md) and
[machine-readable](benchmarks/results/e2_baseline.json) results.

## Install

```bash
git clone https://github.com/bio-ontology-research-group/physiomap.git
cd physiomap
uv sync --extra dev --extra analysis
```

Python 3.11 or later is required.

## Quick start

Predict the directional consequences of reduced hepcidin:

```bash
uv run python -m physiomap_core.knockout hepcidin -
```

List the modulation relations available to the gain-sensitivity query:

```bash
uv run python -m physiomap_core.modulation --list
```

Run the test suite:

```bash
uv run pytest
```

Serve the interactive viewer locally:

```bash
uv run python web/export_data.py
uv run python -m http.server 8099 --directory web
```

Then open <http://localhost:8099>.

## Reproduce the release

The complete release gate rebuilds the ontology and causal model, checks the
projection, runs the test and evaluation contracts, verifies generated
artifacts, and verifies deterministic reconstruction:

```bash
uv run python scripts/owl_scm_release_gate.py
```

The pinned HPO release inputs used by the rare-disease evaluation are stored
under [`benchmarks/data/hpo-2026-02-16/`](benchmarks/data/hpo-2026-02-16/).
The gate verifies their compressed and expanded checksums before use.

When the separate manuscript repository is linked at `paper/`, the same
command also compiles the paper and supplementary material. Submission
maintainers can make those two additional checks mandatory:

```bash
uv run python scripts/owl_scm_release_gate.py --require-paper
```

The main evaluation outputs are generated by:

| result | command |
|---|---|
| directional rare-disease prediction | `uv run python scripts/e1b_eval.py --leakage-sensitivity` |
| shortest-path comparison | `uv run python scripts/e2_baseline.py` |
| precision-coverage comparison | `uv run --extra analysis python scripts/e2c_risk_coverage.py` |
| inverse lesion ranking | `uv run python scripts/e4_diagnose.py` |
| inverse-ranking comparisons | `uv run --extra analysis python scripts/e4b_diagnosis_baselines.py` |
| manuscript figure and result macros | `uv run --extra analysis python scripts/generate_psb_rare_disease_figure.py` |

Generated outputs live under [`benchmarks/results/`](benchmarks/results/).
The current acceptance criteria and interpretation of each evaluation are in
[`docs/VALIDATION.md`](docs/VALIDATION.md).
Formal proofs and additional methods are in
[`supplement/`](supplement/), including the
[Lean 4 formalization](supplement/lean/).

## Repository layout

```text
physiomap_core/   data model, projection consumers, and inference
ontology/         OWL construction and ontology grounding
projection/       versioned OWL-to-SCM projection patterns
release/owl-scm/  canonical v1.1.1 release artifacts and checksums
benchmarks/       evaluation inputs and generated results
scripts/          release, evaluation, and curation commands
tests/            automated test suite
docs/             current semantics, validation, and review documentation
supplement/       supplementary methods, proofs, and Lean formalization
web/              interactive viewer and exported release data
```

## Scope and limitations

PhysioMap v1.1.1 supplies typed structural constraints and derivative signs,
not complete quantitative functions, parameters, exogenous distributions,
effect sizes, penetrance, thresholds, or dynamics. Numerical and population
inference requires those additional inputs.

The first-order solver assumes re-equilibration at a locally stable state.
Exact signed-determinant expansion is limited to feedback components of at
most 16 traits by default; larger components use a conservative approximation.
This cutoff is computational, configurable, and has no semantic significance.
Modulation supports a separate qualitative gain query but was not evaluated in
the rare-disease experiments.

## Citation

Please cite:

> Hoehndorf R, Schofield PN, Gkoutos GV. PhysioMap: an ontology-grounded
> causal knowledge graph of human physiology. Manuscript submitted to the
> Pacific Symposium on Biocomputing, 2026.

Machine-readable citation metadata is provided in
[`CITATION.cff`](CITATION.cff).

## License

- Software source code: [BSD 3-Clause](LICENSE).
- PhysioMap content, benchmark data, and documentation:
  [Creative Commons Attribution 4.0](LICENSE-DATA).
- Third-party inputs retain their original licenses. See
  [`LICENSING.md`](LICENSING.md) for the path-level licensing statement.
