# GRN and signalling import provenance

*Run 2026-06-04. Ten anchored regulatory modules underwent independent
authoring and review followed by deterministic identifier and regression
checks.*

## What this is

The construction-evidence policy summarized in
[`docs/MULTISCALE.md`](../../docs/MULTISCALE.md#content-versus-construction-evidence)
admits an edge only if its evidence is **interventional** (`do(source)→Δtarget`), never
associational. This is the first fan-out that uses it to scale edge import from gene-regulatory
and signalling knowledge, each module anchored to an existing PhysioMap node.

## Pipeline

1. **Author** (Sonnet, 1 agent/module): build a molecular/subcellular regulatory module beneath a
   named anchor; ground every IRI by grepping the local OBO cache; cite real drugs / Mendelian
   LoF-GoF / KO; tag each edge with a `causal_evidence` class.
2. **Verify** (adversarial, inherit/Opus): per edge — is it genuinely interventional? does the
   cited intervention imply *this* sign? are the identifiers real and on-topic? Default to reject.
3. **Integrate** (deterministic, main loop — *not* delegated): keep admitted edges; re-resolve
   every IRI authoritatively against the OBO files; enforce the architecture (molecular roots +
   upward constitutive lifts, **no** downward macro→micro causal edges); correct signs; run
   `validate_fragment` + `validate_causal_evidence` + `verify_ontology_ids` + `validate_constitution`
   + meta-acyclicity + the HPO soundness gate. Integrate only what survives all gates.

## Headline finding: the cheap author model fabricates citations

The adversarial verifier's most important catch was **systematic PMID fabrication** by the
Sonnet authoring agents: plausible-looking citations whose PMIDs actually index unrelated papers
(Drosophila cytokinesis, ovarian torsion, equine hypertrophic osteopathy, IL-17 angiogenesis…).
The *biology and signs were mostly correct*, but the specific identifiers were invented. Examples
the verifier flagged: `PMID 15240570` (claimed liver GR-KO; actually Drosophila cytokinesis),
`PMID 27066282` (claimed mifepristone/Cushing; actually ovarian torsion), `PMID 23913124` (claimed
Nesbit GNA11; actually IL-17 tumour angiogenesis — correct is PMID 23802516).

**Policy consequence (honouring the no-fabrication rule):** no PMID/OMIM was carried into the repo
unless the verifier independently confirmed it on-topic. Integrated edges are grounded on
**real drug names + Mendelian disease names + verifier-confirmed PMIDs only**; unconfirmed numeric
identifiers were dropped, with `evidence` stating the interventional fact and "primary citations
pending verification" where needed. The `causal_evidence` class + the specific intervention
(drug / variant) carry the do()-grounding.

The verifier also enforced the **within-scale + constitutive-lift architecture** (rejecting
downward macro→micro causal edges and cross-scale causal arrows), and **caught a pre-existing
bug**: `hepcidin_signaling.yaml`'s `bmp6_ligand` used `PR:000004801` (B-Raf) instead of
`PR:000000167` (BMP6) — now fixed.

## Integrated (6 modules · +18 nodes / +14 causal edges / +8 constitutive lifts)

| module | anchor | edges | interventional grounding |
|---|---|---|---|
| `hepcidin_bmp_smad_axis` | `bmp_smad_signaling` → hepcidin | 3 | HJV/TMPRSS6/HFE-TFR2 Mendelian (juvenile HH, IRIDA, HH); Bmp6 KO. PMIDs verifier-confirmed |
| `srebp_ldlr_pcsk9_axis` | `hepatic_ldl_receptor_activity`, `hmg_coa_reductase_activity` | 2 | statins, PCSK9 inhibitors; LDLR/PCSK9 Mendelian |
| `casr_pth_secretion` | `parathyroid_chief_pth_secretion` | 0 (lift) | cinacalcet; CaSR FHH/ADH Mendelian |
| `tshr_thyroid_synthesis` | `thyroid_follicular_t4_secretion` | 3 | TSHR GoF/LoF Mendelian; thionamides |
| `leptin_melanocortin_appetite` | `hypothalamic_appetite_drive` | 4 | leptin/MC4R Mendelian; metreleptin, setmelanotide |
| `gr_gluconeogenesis` | `hepatic_glucose_production` | 2 | dexamethasone, mifepristone; liver GR-KO (all PMIDs were fabricated → drug/KO facts only) |

Interventional smoke tests (molecular `do()` lifting upward) behave soundly, e.g.:
- TSHR gain-of-function → organification↑, T4 secretion↑, **free T4↑** (fully determinate, correct).
- CaSR↑ (cinacalcet) → parathyroid PTH secretion↓ (correct); plasma PTH/Ca `?` in the feedback SCC.
- SREBP-2↑ → PCSK9↑ (determinate); LDLR/LDL `?` (SCC). GR↑ → PEPCK↑; systemic glucose `?` (SCC).

Composed map: **1361 nodes / 681 causal edges / 80 constitutive lifts**; soundness gate green
(REAL-HPO forward 22/22, 0 wrong); 156 tests pass.

## Deferred (4 modules) — pending a citation-verification stage

Biologically endorsed by the verifier but held back:

- `nfkb_cytokine` (NF-κB→TNF/IL-6): conflated/fabricated citations; also **duplicates** existing
  `macrophage_activation ▷ tnf_alpha / il6` production lifts in `immune_paracrine.yaml`.
- `beta_cell_katp` (K_ATP→insulin): two **sign-convention errors** on the membrane-potential
  intermediate (verifier-corrected) + a fabricated Cav1.3-KO citation. Salvageable after rework.
- `ppar_lipid` (PPARα/γ): multi-step cross-scale chain needs an architecture pass (roots + lifts).
- `glp1_incretin` (GLP-1R→insulin): mostly downward/cross-scale edges rejected; small clean remainder.

## Next step

Add a **citation-verification stage** (agents with PubMed/web access that confirm each PMID/OMIM
against its actual title/abstract before integration). With that gate in place the deferred
modules — and a much larger fan-out — can be imported without manual citation triage.
