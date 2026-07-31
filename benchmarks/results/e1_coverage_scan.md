# E1 coverage scan — IEM gene-knockout reachability  *** sizing, 2026-06-13 ***

Sizes the Mendelian/IEM forward experiment (E1) before building the reaction-edge layer.
Method: HPOA `genes_to_phenotype` (release 2026-02-16) × the 1301 directional `hpo_term_map`
terms (phenotype side) × gene→product→PhysioMap-node resolution (lesion side) via
HGNC (entrez/symbol→UniProt) + PRO `promapping.txt` (PR↔UniProt). Reproducible from
`benchmarks/.imports/{hgnc_complete_set,promapping}.txt` + `e1_coverage_scan.json`.

## Node inventory (node_catalog.json, 1664 nodes)
- **399 distinct ChEBI metabolites** (614 metabolite nodes) — the substrate pool.
- **377 enzyme/activity nodes** (`PATO:0001414`); 276 resolve to a UniProt via PRO. Includes
  transporters (ABCA1/ABCD1/ABCG5-8/SLC*), so transporter-deficiency IEMs are in scope.
- **1301 directional HP→node terms** mapping to 980 distinct nodes.

## Wiring state (already better than assumed)
The HPO gap-fill nodes are **mostly already connected**, not islands:
- enzyme nodes that are causal **islands** (in no edge): **13 / 377**.
- enzyme nodes with an out-edge **to a ChEBI metabolite** (a reaction edge): **254 / 377**.
- ChEBI metabolite islands: **20 / 614**.
⇒ The bottleneck is **not** the reaction edges — it's the **gene→clampable-node lesion map**
(`gene_lesions.yaml` currently has ~21 genes).

## Phenotype side (rich)
- HPOA genes total: **5251**; with ≥1 directional (scoreable) phenotype: **2423**
  (≥3 phenotypes: 1181; ≥5: 616). Distinct PhysioMap nodes hit: 626.

## Lesion side — the decisive numbers (among the 2423 scoreable genes)
| bucket | genes | meaning |
|---|---|---|
| **evaluable now** | **142** | gene→enzyme node **already wired** to a metabolite → run knockouts today |
| enzyme needs wiring | 61 | enzyme node exists but lacks reaction edges → **E1a target** |
| non-enzyme node | 65 | product is a receptor/hormone/transporter node (clampable, different lift) |
| no node | 2155 | product not in PhysioMap → expansion frontier (node+edge add) |
| **lesion-mappable total** | **268** | |

**E1 jumps from 21 → 142 genes immediately (≈7×); ≈203 after wiring the 61.**
The 2155 no-node genes are the honest coverage ceiling/frontier (mostly non-metabolic or
not-yet-modeled products), not a defect — they abstain soundly.

## Validation spot-check
`do(asl_activity = −)` → **↑ CSF argininosuccinate (HP:0034734)** — correct for argininosuccinic
aciduria. Derived 1 determinate phenotype of ASL's 11 scoreable; the rest abstain (`?`).
⇒ confirms "wired" ⇒ determinate prediction, and the **precision-first / abstention-heavy**
profile: per-gene determinate yield is modest, so the paper metric is **soundness (0-wrong) +
recall**, never raw coverage.

## Highest-yield E1a wiring targets (enzyme node present, edges missing; by #scoreable pheno)
CPT2 (15), HMGCL (15), LIPA (10), HADHA (9), PMM2 (9), MLYCD (7), PFKM (6), PYGM (6), MOGS (6),
CPT1A (6) — classic fatty-acid-oxidation / glycogen-storage / CDG IEMs.

## Top evaluable-now genes (by #scoreable pheno)
SLC37A4 (14, GSD-Ib), CTNS (13, cystinosis), DPYS (13), CYP17A1 (13), GALT (12, galactosemia),
SLC12A1 (12, Bartter), UPB1 (12), ASL (11), PCK1 (11), HSD3B2 (11), ALDOB (10, HFI), SDHA (10).

## Implication for the plan
- E1b can start **now** on the 142 evaluable-now genes (no new modeling) — that alone is a
  publishable forward benchmark vs HPOA.
- E1a is a **bounded** wiring job (+61 enzyme genes) — Rhea/EC reaction edges among existing
  ChEBI nodes, gated, highest-yield list above.
- Defer the 2155 no-node genes (frontier) and the 65 non-enzyme lifts to post-paper / stretch.
