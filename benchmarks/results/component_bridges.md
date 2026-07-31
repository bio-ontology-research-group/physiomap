# Bridging isolated components to the physiological core

*Run 2026-06-05. Multi-agent author→adversarial-verify workflow (64 agents, ~3.7M tokens, live
WebSearch), then deterministic main-loop integration.*

## Problem

Connecting isolated *nodes* (previous pass) produced many small *islands* — biochemically-coherent
inborn-error-of-metabolism clusters (an enzyme + the metabolites it controls) that were still
disconnected from the giant physiological component. Before this run: **giant = 495 nodes**, with
**234 islands of size ≥ 2** (urea cycle, BCAA/MSUD, phenylalanine, copper/Wilson, acylcarnitines,
porphyrins, glycolytic enzymes, oxalate, creatine, …) plus 148 lone nodes.

Goal: bridge each island to the giant via the **disease mechanism** — the accumulating/deficient
metabolite's downstream physiological effect — as an interventional causal edge, or leave it
unbridged rather than fabricate.

## Pipeline

1. **Bridge** (32 themed batches, Sonnet + live WebSearch): for each island find ONE causal edge from
   a member node to a giant-component node, grounded in a real `do()` (usually the IEM enzyme defect).
2. **Verify** (adversarial, Opus): is each bridge interventional, correctly signed, identifier-clean,
   and does it actually reach the giant? Default reject.
3. **Integrate** (deterministic, main loop): admitted edges only; dedup; strip workflow-only fields
   (fold `intervention` into `evidence`); split by endpoint ownership — pure human-scale bridges into
   `benchmarks/human/systems/component_bridges.yaml` (163), bridges touching a multiscale-owned node
   into `benchmarks/multiscale/component_bridges.yaml` (19) — so both `test_human` (human-scale only)
   and the full `build_map` compose without dangling refs. Run all gates + meta-acyclicity + soundness.

## Result

- Agents proposed **225 bridges**; verifier **admitted 182** (81%), rejected 43; **9** components left
  unbridged (no sound mechanism). 0 new nodes (all bridges reuse existing nodes).
- Integrated **182 causal bridge edges** (163 human-scale + 19 multiscale-touching).
- **Giant component 495 → 1191 nodes**; **size-≥2 islands 234 → 52**; total components 383 → 201
  (the remaining 148 size-1 nodes are the deliberately-isolated lone analytes). Composed map
  **1525 nodes / 1498 causal edges / 91 constitutive lifts**.
- All gates green; **HPO soundness gate PASS** (0 wrong determinate predictions); no cross-scale cycle;
  156 tests pass.

Representative bridges (all interventional `do()` handles):
- `carbamoylphosphate_synthetase_1_activity —(+)→ blood_urea_nitrogen` (CPS1 deficiency → urea-cycle
  block → low BUN; OTC/NAGS analogous) — merges the urea-cycle island.
- `plasma_ceruloplasmin —(+)→ plasma_iron` (ceruloplasmin ferroxidase; aceruloplasminaemia) — copper
  island into iron metabolism.
- `plasma_creatine —(+)→ plasma_creatinine` (AGAT/GAMT deficiency) — creatine island.
- BCAA/serine clusters → `muscle_protein_synthesis_rate` / `hepatic_gluconeogenesis`; FAO clusters →
  `hepatic_ketogenesis` / `plasma_glucose`; mitochondrial/ETF clusters → `cellular_atp_level`.

## Honest residual

**52 islands (size ≥ 2) and 148 lone nodes remain off the giant** — left so deliberately where no
sound interventional bridge exists (nonspecific markers, immunoglobulin/complement sets, some
composite analytes). Forcing edges there would import associations, which the gate exists to prevent.
A future pass with a PubMed citation-verification stage could connect a further fraction.
