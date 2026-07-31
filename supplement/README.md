# PhysioMap supplementary material

This directory accompanies:

> Hoehndorf R, Schofield PN, Gkoutos GV. *PhysioMap: an
> ontology-grounded causal knowledge graph of human physiology.*

The complete supplementary PDF for PhysioMap v1.1.1 is archived with the
[GitHub release](https://github.com/bio-ontology-research-group/physiomap/releases/tag/v1.1.1).
It specifies:

- the OWL trait and collection patterns;
- the entailment-to-model projection;
- the quantitative structural causal model semantics;
- proofs of the direct-effect identity and feedback solver;
- the evidence and provenance model used during construction;
- the two expert-review protocols and complete archived results;
- the gene-to-intervention and HPO direction-mapping procedures;
- reproduction commands and generated content characterization.

The [`lean/`](lean/) directory contains a machine-checked Lean 4
formalization of the combinatorial core of the derivative-sign solver's
selective-soundness argument. Its README records the exact toolchain and build
command.

The repository release gate regenerates and checks the source artifacts used
by the manuscript:

```bash
uv run python scripts/owl_scm_release_gate.py
```

Evaluation outputs are under
[`benchmarks/results/`](../benchmarks/results/). The complete 866-row
adjudicated forward-evaluation reference is
[`e1b_forward_pairs.tsv`](../benchmarks/results/e1b_forward_pairs.tsv).
