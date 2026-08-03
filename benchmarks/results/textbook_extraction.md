# Textbook-derived curation

PhysioMap used physiology and biochemistry textbooks to identify candidate
relations and to corroborate existing mechanisms. Copyrighted editions were
consulted through lawful institutional access and are not redistributed.
Openly licensed sources retain their original attribution.

Textbook statements were not treated as PhysioMap content automatically.
Candidates were reviewed under the evidence model and represented as causal
influences, production relations, constitutive constraints, quantitative
identities, or modulations according to their semantics. Descriptive,
associational, duplicated, and insufficiently directional claims were held or
rejected.

The released textbook-derived content is consolidated in
[`benchmarks/human/systems/textbook_extracted.yaml`](../human/systems/textbook_extracted.yaml)
and the source-specific curated fragments. Evidence and provenance are stored
with each retained axiom. Raw text, extraction batches, and internal review
transcripts are excluded from the public repository.

## Historical proposal batch

The proposal batch divided three open-licensed textbooks into 258 sections. It
made 362 model calls and processed approximately 10.8 million tokens, using
Claude Sonnet for extraction and Claude Opus for a separate adversarial review.
The batch proposed 111 unique new nodes and 228 distinct signed relations.
Semantic and scale filtering retained all 111 nodes and 87 causal influences
for integration.

These counts come from the contemporaneous run report. The original
orchestration implementation, immutable model snapshot identifiers, sampling
parameters, complete invocation metadata, section-level structured outputs,
and internal reconciliation transcripts are not part of the public release.
The integrated fragment and retained relation-level evidence can be audited,
but the calls and processing totals cannot be reconstructed or replayed exactly
from the public archive.
