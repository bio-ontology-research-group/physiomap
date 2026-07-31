# HPO node-gap fill — multi-agent fan-out  *** DRAFT FOR REVIEW ***

A multi-agent workflow (`scripts/hpo_align.py` → triage → author → adversarial verify) was run to
**fill the PhysioMap node gaps** identified from the 1360 directional HPO quantity terms
(`benchmarks/hpo/node_gaps_full.tsv`). This records what was added, what was deliberately left out,
and the guardrails that kept it sound. Everything here is a **draft for domain review**.

## Pipeline

1. **Triage** (4 agents): every gap term bucketed IN-SCOPE (a measurable physiological quantity —
   lab/vital/hormone/metabolite/enzyme-activity level) vs OUT-OF-SCOPE, and assigned to one of 22
   themes. **1192 in-scope / 166 out-of-scope.**
2. **Author** (one agent per theme): reviewed each analyte against databases + primary literature +
   textbooks, reused existing nodes where present, created new nodes only for genuine quantities
   with **OBO-verified** entity IRIs (null if unverifiable — no fabrication), added signed causal
   edges only with a real citation, and self-validated each fragment with `validate_fragment.py`.
3. **Verify** (one independent agent per theme): adversarially re-checked every HPO-mapping
   direction, every entity IRI against the OBO, and every edge sign — with explicit guards against
   the false-friend class (transferrin concentration vs *saturation*, free T3 vs T4, IGF-2 vs IGF-1,
   precursor-rises-because-product-falls, activity vs concentration).

## What was added

- **22 themed fragments** in `benchmarks/human/systems/hpo_*.yaml`: **902 new nodes** (after
  de-duplicating 19 analytes authored in two themes) + **149 signed causal edges** (all with
  literature/DB evidence). Themes: liver-function & muscle enzymes, plasma proteins,
  immunoglobulins/complement, lipids/lipoproteins, amino acids, organic acids, purine/pyrimidine,
  carbohydrate metabolites, fatty-acid oxidation, vitamins/cofactors, trace metals, mitochondrial &
  lysosomal enzymes, other endocrine hormones, hematology indices, coagulation factors,
  pulmonary/blood-gas, renal markers, CSF markers, neurotransmitter metabolites, other metabolites.
- **1179 HPO directional terms mapped** onto nodes in `hpo_term_map.yaml` (52 → **1301** total),
  each label re-verified verbatim against `hp.obo`. **10 mappings dropped** by the verifiers
  (1 wrong-term, 1 duplicate, 1 aldolase false-friend, 7 unverified).

## Correctness guardrails (all green)

- **Ontology IDs:** `verify_ontology_ids.py` — **739/739 OK**, 0 not-found, 0 obsolete, **0 label
  mismatch** across the whole corpus (manifest in `ontology/verified_ids.yaml`).
- **Soundness gate** (`hpo_regression_gate.py`): curated pilot **18/18**, REAL-HPO forward
  **22/22 determinate correct, 0 wrong** (mappable observed directions 50 → **93**), backward
  top-3 **20/20**. Adding the gap-fill *increased* determinate predictions while staying sound.
- **Tests:** full suite **138 green**.

## Honest accounting

- **Node-first, edge-conservative.** Most new nodes are **causally-island leaf analytes**: an
  OBO-grounded `(entity, PATO quality)` with no fabricated edges. They are valuable (browseable,
  HPO-mapped) and **safe** — with no parents a node simply *abstains* under intervention, so it can
  never produce a wrong sign. This is why the macro-grounding audit now reads
  **48 grounded / 1 exogenous / 203 derived / 615 ungrounded**: the 615 "ungrounded" are these
  ontologically-grounded but mechanistically-unconnected analytes (a coverage frontier, not a defect).
- **166 terms left OUT-OF-SCOPE by design** (the formalism cannot sign them): imaging/morphology
  findings (nuchal translucency, lipid droplets, organelle counts), in-vitro functional assays
  (T-cell proliferation, NADPH-oxidase burst, DNA-repair capacity), dynamic provocative-test
  responses (dexamethasone-suppression, Ellsworth-Howard), ratios with no single analyte
  (lactate:pyruvate), and composite clinical syndromes (high/low-output heart failure, hypovolemic
  shock). Forcing a sign onto these would fabricate predictions — so they are not added.
- **~149 in-scope terms remain unmapped** (`benchmarks/hpo/node_gaps.md`): residual analytes the
  authors could not confidently ground or that need their own node — the next review pass.
- The interactive viewer (`web/`) still ships the curated ~254-node map (its `SYSTEMS` list is
  explicit); the gap-fill fragments live in the composed human/HPO map used by the solver + gate.
