# Connecting isolated nodes — causal-evidence-gated fan-out

*Run 2026-06-04. Multi-agent author→adversarial-verify workflow (78 agents, ~5.6M tokens) over
all 771 isolated nodes, then deterministic main-loop integration.*

## Problem

The node-first / edge-conservative HPO gap-fill and textbook extraction left **771 fully-isolated
nodes** (no causal *or* constitutive edge — the dots floating in the viewer): mostly plasma / CSF /
urinary metabolite analytes. They abstain soundly (a parentless node can never give a wrong sign),
but they carry no mechanism. Goal: for each, find an **interventional (causal)** connection — never
an association — with real provenance, or leave it isolated rather than fabricate.

## Pipeline

1. **Connect** (40 themed batches, Sonnet + live WebSearch): for each isolated node find the
   interventional `do()` handle. For a metabolite the canonical one is its **inborn error of
   metabolism**: the enzyme/transporter whose loss-of-function sets the level (substrate
   *accumulates* when the enzyme is low → `enzyme —(−)→ substrate`; product *falls* → `+`),
   following the existing `pah_enzyme_activity → plasma_phenylalanine` pattern. IRIs grounded by
   grepping the OBO cache; provenance = textbook chapter + IEM disease name + search-verified PMIDs.
2. **Verify** (adversarial, Opus): per edge — interventional (not a metabolic-adjacency guess)?
   sign direction correct? identifiers real and on-topic (not fabricated)? Default reject.
3. **Integrate** (deterministic, main loop): admitted edges only; re-verify *every* IRI against the
   OBO files (0 nulled — agents grepped correctly); dedup enzyme/bridge nodes across batches; strip
   workflow-only fields (fold `intervention` into `evidence`); drop edges referencing
   multiscale-only nodes so the fragment composes within guyton+human/systems; run
   `validate_fragment` + `validate_causal_evidence` + `verify_ontology_ids` + `validate_constitution`
   + meta-acyclicity + the HPO soundness gate.

## Result

- Agents proposed **736 edges**; verifier **admitted 658** (89%), **rejected 78**; **81** nodes
  honestly left isolated (no clean causal handle — many plasma proteins / immunoglobulins).
- After dedup + resolution + the multiscale-ref drop: **635 causal edges + 11 constitutive lifts +
  164 new enzyme/transporter/bridge nodes** integrated into
  `benchmarks/human/systems/isolated_connections.yaml`.
- **Isolated nodes: 771 → 148** (623 connected). Composed map **1525 nodes / 1316 causal edges /
  91 constitutive lifts**.
- All gates green; **HPO soundness gate PASS** (REAL-HPO forward 23 determinate, 0 wrong — one
  *more* determinate prediction than before, still zero wrong); 156 tests pass.

Most new edges are `genetic_lof_gof` (the IEM enzyme is a clean human `do()`): e.g.
`succinate_dehydrogenase_activity —(−)→ plasma_succinate` (SDH deficiency → succinic aciduria),
`gcdh_activity —(−)→ … ` (glutaric aciduria), the aconitase/2-oxoglutarate-dehydrogenase TCA
biomarkers, etc.

## Honest residual

**148 nodes remain isolated** — left so deliberately. They are analytes with no specific
interventional handle in scope (nonspecific plasma proteins, immunoglobulin/complement components,
some composite markers). Forcing edges there would mean importing associations, which the gate
exists to prevent. They continue to abstain soundly. A future pass with the planned
**citation-verification stage** (PubMed-confirming agents) could connect a further fraction.
