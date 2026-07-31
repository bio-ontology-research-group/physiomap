# PhysioMap cellular scale — cell–cell communication provenance manifest (2026-06-03)

Six within-`cellular`-scale modules authored from **signed ligand–receptor resources**
(OmniPath consensus stimulation/inhibition, CellPhoneDB/CellChat), Cell Ontology, BioModels,
and primary literature + textbooks, then **adversarially audited** (every cell–cell sign +
citation checked; BioModels/CL ids spot-checked) and **revised**. Each passes
`scripts/validate_fragment.py`. Cell–cell edges are lateral causation; modules integrate
upward by constitutive lift (or a within-cellular edge into an existing cellular node) and add
**no downward macro→micro edges** (meta-graph stays acyclic). Cellular scale: 6 → 30 nodes.

| module | file | cells | cell–cell edges | integrates via | audit | sign fix | ev flag |
|---|---|--:|--:|---|---|--:|--:|
| islet_paracrine | `multiscale/islet_paracrine.yaml` | 3 | 6 | plasma_insulin, plasma_glucagon | pass | 0 | 1 |
| jga_cellcomm | `multiscale/jga_cellcomm.yaml` | 4 | 4 | renin, gfr | pass | 0 | 0 |
| bone_remodeling | `multiscale/bone_remodeling.yaml` | 5 | 6 | plasma_calcium, plasma_phosphate | revise | 0 | 0 |
| endothelium_smc | `multiscale/endothelium_smc.yaml` | 4 | 6 | (lateral edge into existing cellular node) | pass | 0 | 0 |
| immune_paracrine | `multiscale/immune_paracrine.yaml` | 5 | 5 | tnf_alpha, il6 | pass | 0 | 0 |
| erythroblastic_island | `multiscale/erythroblastic_island.yaml` | 3 | 6 | red_cell_mass | pass | 0 | 1 |

## Notes

- **Signs from biology, not just presence:** OmniPath/CellPhoneDB give the ligand–receptor
  *pair*; the +/- sign was set from receptor coupling / function (e.g. somatostatin SSTR is
  Gi-coupled → inhibitory `-`; osteoblast **OPG is a decoy** → `-` on osteoclast; endothelial
  NO relaxes smooth muscle → `-` on tone) and cited to literature/textbook.
- **Audit caught real fixes**, e.g. a macula-densa CL IRI correction (CL:1000839 was the wrong
  cell type → CL:1000850 macula densa epithelial cell) and retargeting an over-reaching
  systemic edge to a local afferent-arteriolar tone node (see `jga_cellcomm.yaml` header).
- **Honest `?`:** cell-level interventions whose lift lands in the 72-node whole-body SCC
  (e.g. β-cell secretion ▷ plasma_insulin) are returned `?` by the conservative loop engine —
  the documented precision frontier, not a wrong sign.
- One **contested** edge (β-cell insulin → δ-cell somatostatin) kept at consensus `+` with LOW
  confidence + the conflicting citation (Hauge-Evans 2012, PMID 22526610) flagged in-edge.
- All modules remain **DRAFTS for domain review**.
