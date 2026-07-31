# Validation against the REAL HPO gene→phenotype annotations  *** DRAFT ***

Quantitative test of PhysioMap against the **actual Human Phenotype Ontology** gene→phenotype
data (`genes_to_phenotype.txt`, HPO release **2026-02-16**), not hand-curated phenotype lists.

Pipeline (reproducible): `scripts/build_hpo_observations.py` reads HPO `genes_to_phenotype.txt` +
`hp.obo`, propagates each annotated term up the HP `is_a` hierarchy (true-path rule), and matches
against the curated, hp.obo-verified `benchmarks/hpo/hpo_term_map.yaml` (122 directional
lab/vital/hormone terms — grown from 49 via the reviewed `scripts/hpo_align.py` candidates) to
emit, per gene in `gene_lesions.yaml`, the observed increased/decreased directions →
`benchmarks/hpo/hpo_gene_observations.yaml` (committed). `physiomap_core/hpo_validate.py` then
scores forward prediction and backward abduction.

## Coverage
- 21 genes placed onto a PhysioMap primary node; **19** have ≥1 HPO phenotype that maps to a
  PhysioMap node (HPO `is_a`-propagated). **50** mappable observed directions.
- HPO gene-level annotations aggregate across diseases/alleles: a gene with both LoF and GoF
  diseases (e.g. `SCNN1B` = Liddle GoF **and** pseudohypoaldosteronism LoF) carries *both*
  directions for some nodes — those conflicts are dropped at build time and reported, not scored.

## Forward — do(gene primary) vs observed HPO direction

| | value |
|---|---|
| genes scored | 19 |
| determinate predictions | 16 |
| correct | **16** |
| **wrong (soundness)** | **0** |
| abstain (`?`) | 34 |
| directional accuracy (determinate) | **100%** |

The 34 abstentions are the documented precision frontier: RAAS/volume/glucose endophenotypes sit
in the giant homeostatic SCC, where the compensated steady-state sign is magnitude-dependent.

## Backward — abduce the gene's primary lesion from its HPO directions

| | value |
|---|---|
| genes scored | 19 |
| unique top-1 | **10/19** |
| top-3 | **19/19** |

Cleanly recovered (unique top-1, 10/19): the metabolic/iron/lipid/endocrine lesions with
determinate, specific downstream signatures (LDLR, HFE, HAMP, TPO, PAH, CBS, XDH, UGT1A1, PHEX,
TRPM6). The richer term map (the reviewed `hpo_align.py` additions) lifted unique top-1 from 9 to
10. The RAAS/volume genes tie at the top (their downstream nodes abstain in the SCC) but stay
within top-3.

## A real-data subtlety the run surfaced (and how it was handled)

The first run reported **1 wrong** (`CYP21A2: cortisol HPO=+ predicted=−`). Tracing it: HPO files
`HP:6000516 "Elevated 21-deoxycortisol"` (and `HP:0025436 "Elevated 11-deoxycortisol"`, CYP11B2)
as `is_a` children of `HP:0003118 "Increased circulating cortisol level"`. These deoxycortisols are
steroid **precursors that accumulate precisely because cortisol synthesis is blocked** — i.e. they
rise *because cortisol falls*. PhysioMap correctly predicts cortisol↓ for 21-hydroxylase
deficiency; the true-path propagation had wrongly counted the precursor as "cortisol↑". Fixed by a
documented `block_propagation` list in `hpo_term_map.yaml` (these two precursor terms do not
propagate to the cortisol node). This is a genuine HPO-class-hierarchy / analyte-identity issue,
not a model error — and exactly the kind of thing a direct, quantitative validation exposes.
