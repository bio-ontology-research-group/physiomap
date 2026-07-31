# Changelog

This public repository begins with the frozen PhysioMap v1.1.1 research
artifact. Development history and internal curation materials are retained
separately from the outward-facing release.

## [Unreleased]

No unreleased changes.

## [1.1.1] - 2026-07-31

### Resource

- Released 1,699 physiological traits and 2,387 typed relation instances:
  2,270 causal influences, 85 production relations, 4 constitutive
  constraints, 9 quantitative identities, and 19 modulations.
- Added the curated angiotensin-II/AT1 and bradykinin/NO vascular-resistance
  mechanisms and corrected the causal interpretation of the
  myosin-light-chain phosphorylation, vascular tone, and resistance chain.
- Froze the OWL knowledge base, projection registry, typed structural causal
  model, provenance, and checksums as one versioned artifact.

### Semantics and reasoning

- Defined quantitative structural causal model semantics for all five content
  relation types.
- Kept derivative signs as a separate qualitative abstraction used by the
  first-order intervention solver.
- Added exact signed-determinant reasoning for bounded feedback components,
  conservative handling of larger components, and a separate modulation
  gain-sensitivity query.
- Added the OWL collection pattern for causal influence, production, and
  modulation while retaining OWL 2 EL classification for the operational
  artifact.

### Evaluation and review

- Added a fixed 866-pair rare-disease directional evaluation, including a
  complete row-level gene, intervention, phenotype, and HPO provenance table.
- Added shortest-path, signed-diffusion, and inverse-ranking comparisons.
- Archived a fixed-seed, cross-relation expert review of 83 projected
  relations: 69 accepted, 12 flagged for investigation, and 2 rejected.
- Added reproducible manuscript figures, result macros, release checks, and
  Lean formalization of the qualitative sign core.

### Distribution

- Added separate BSD 3-Clause software and CC BY 4.0 data/documentation
  licenses, machine-readable citation metadata, and third-party attribution.
- Removed internal curation transcripts, licensed source-text extracts, and
  ancillary source documents from the public release.
