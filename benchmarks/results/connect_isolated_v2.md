# Connect-isolated round 2 — lone nodes + small islands, citation-verified

*Run 2026-06-05. Goal: connect the remaining disconnected nodes and small (≤5-node) islands to the
physiological core with **causal** edges whose **PMID/textbook citation was checked against its real
source** before admission — the discipline the user required.*

## Starting point (live composed map, 1525 nodes / 1498 causal edges)

- **148 lone nodes** (degree 0) + **45 small islands** (2–5 nodes, 113 nodes) = **193 components, 261 nodes**.
- Mostly HPO gap-fill leaf analytes (plasma/urine/CSF metabolites) and enzyme↔metabolite IEM islands.

## Pipeline (3 fan-outs + deterministic gate)

1. **Authoring** (17 agents, WebSearch). One interventional connecting edge proposed per component,
   anchored to an existing core node from a 1191-node catalog, each with a `do()` mechanism, an
   admissible `causal_evidence` class, and a citation the agent had to open and quote. **145 connected,
   48 abstained** (no fabrication when evidence was lacking). 0 new nodes (all reused existing ids).
2. **Existence audit** (deterministic, NCBI E-utilities): **117/117 distinct PMIDs resolve — 0 fabricated.**
3. **Concordance** (13 agents): 11 judged each PMID's **real abstract** (fetched, supplied) against the
   claim + checked the agent's quote was genuinely in it; 2 used WebSearch to confirm the textbook
   citations. **111 supported + quote-confirmed, 12 supported-but-quote-unconfirmed, 22 rejected (15%).**

## Admission rule & result

Admit iff `supports = true AND quote_in_source = true`. **111 edges admitted** (93 human-scale, 18 with a
molecular/cellular endpoint), split into `benchmarks/human/systems/connect_isolated_v2.yaml` and
`benchmarks/multiscale/connect_isolated_v2.yaml` (edge-only, `nodes: []`, reuse existing nodes). The 12
quote-unconfirmed and 22 rejected were **dropped, not fabricated around**.

- **Rejections were genuine misattributions/over-reach**, e.g. `p5c_dehydrogenase→urinary_pyrroline_hydroxycarboxylate`
  (cited paper was about HOGA1 / primary hyperoxaluria type 3), `bckdh→csf_alloisoleucine` (paper was
  leucine/KIC neurotoxicity, not BCKDH accumulation), `csf_mbp→macrophage_activation` (abstract states
  MBP does *not* activate NF-κB — contradicts the sign), two `transaldolase→csf_xylitol/erythritol`
  (the abstract named other polyols, not these).

## Connectivity impact

| metric | before | after |
|---|---|---|
| causal edges | 1498 | **1609** (+111) |
| connected components | 201 | **90** |
| giant component | 1191 | **1337** (+146 nodes) |
| lone nodes (deg 0) | 148 | **59** |
| small islands (2–5) | 45 | **23** |

Map still composes for solving (no cross-scale cycle introduced); **HPO soundness gate PASS (0 wrong),
159 tests pass**. Edges are interventional with verified citations but remain **DRAFT for domain review**.

## Caveat

Concordance verifies the **citation**, not the ground-truth biology. A small number of authoring agents
echoed the paper *title* in the verdict `source` field; these were recovered via the bundle index (target
intact) so no good edge was lost. The 12 quote-unconfirmed proposals (e.g. `transaldolase→urinary_sedoheptulose`
— abstract does report sedoheptulose, but the agent's composite quote was not verbatim) are held out for a
future pass that can re-source a confirmable citation, rather than admitted on an unverified quote.
