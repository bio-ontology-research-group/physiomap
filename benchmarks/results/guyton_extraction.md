# Guyton source curation

The Guyton cardiovascular fragment was curated from two source families:

- the machine-readable Guyton 1972 modules distributed by BioModels and the
  Physiome Model Repository; and
- the corresponding physiological mechanisms described in *Guyton and Hall
  Textbook of Medical Physiology*.

The redistributable model files and exact source identifiers are documented in
[`benchmarks/guyton/SOURCES.md`](../guyton/SOURCES.md). The textbook was
consulted through an institutional library and is not redistributed.

Candidate relations were admitted only when the source supported the semantics
of the asserted relation type. For a causal influence, this required an
intervention, a signed derivative in a mechanistic model, or a sufficiently
specific mechanistic account. Production, constitution, quantitative identity,
and modulation were curated under their own criteria. Evidence and provenance
remain attached to the resulting axioms.

The current curated content is in
[`benchmarks/guyton/guyton_cv_core.yaml`](../guyton/guyton_cv_core.yaml) and
[`benchmarks/human/systems/guyton_extracted.yaml`](../human/systems/guyton_extracted.yaml).
Raw extraction transcripts and copyrighted source text are not part of the
public release.
