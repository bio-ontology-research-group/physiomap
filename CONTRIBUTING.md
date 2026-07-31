# Contributing to PhysioMap

Contributions to the map, the solver, and the evaluations are welcome.

## Ground rules for the map

PhysioMap is a typed causal knowledge graph, not an association network. Two
rules preserve its semantics:

1. **Evidence controls admission, not application semantics.** A causal
   influence requires interventional evidence, a mechanistic-model derivative,
   or a curated mechanistic account, never binding, coexpression, or
   co-occurrence alone. Every assertion carries evidence and provenance, but
   solvers read the typed content rather than those annotations.
2. **Relation types are not interchangeable.** Causal influence, production,
   constitution, quantitative identity, and modulation have distinct structural
   causal model interpretations. Do not replace one with a causal edge for
   convenience. In particular, constitutive determination is directed from
   constituents to a whole and is not interlevel causation.

Add or edit map fragments under `benchmarks/human/systems/` (or `benchmarks/human/curated/`). Every
fragment is mechanically checked:

```bash
uv run python scripts/validate_fragment.py <fragment.yaml>   # schema + provenance + no dangling refs
uv run python scripts/verify_ontology_ids.py                 # OBO identifiers resolve
```

## Code

```bash
uv sync --extra dev
uv run pytest                 # the suite must stay green
```

- Python ≥ 3.11; the solver core (`physiomap_core/`) has no heavy dependencies (networkx, numpy,
  pydantic, pyyaml, clingo).
- Keep the soundness regression gate green: no forward prediction may contradict a curated phenotype
  direction (`scripts/hpo_regression_gate.py`).

## Pull requests

Open an issue first for substantial changes. By contributing you agree that your code is licensed
under BSD-3-Clause and your map/data contributions under CC BY 4.0 (see [LICENSING.md](LICENSING.md)).
