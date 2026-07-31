# PhysioMap expansion — provenance manifest (2026-06-03)

Fan-out of 17 new fragments (12 organ/organ-system + 5 molecular verticals) authored from
**BioModels** (live API, model IDs + publications verified), primary literature, and
physiology textbooks, then **adversarially audited** (every edge sign + citation checked,
BioModels IDs spot-checked via the API) and **revised**. Each fragment passes
`scripts/validate_fragment.py` (schema + 100% provenance coverage + no dangling refs).

Composed human map: **146 nodes, ~285 signed causal edges, 8 constitutive lifts**, one
~72-node whole-body SCC. Benchmark (65 interventions): **0 wrong / 91 determinate, 100%**.

| system | file | nodes | causal | audit | sign fixes | evidence fixes | BioModels models cited |
|---|---|--:|--:|---|--:|--:|---|
| reproductive_hpg | `human/systems/reproductive_hpg.yaml` | 7 | 18 | revise | 1 | 8 | BIOMD0000000494 |
| growth_hormone_igf1 | `human/systems/growth_hormone_igf1.yaml` | 5 | 16 | revise | 0 | 7 | MODEL0912096133, MODEL9811206584 |
| energy_balance_appetite | `human/systems/energy_balance_appetite.yaml` | 6 | 14 | pass | 0 | 0 | BIOMD0000000901 |
| iron_hepcidin | `human/systems/iron_hepcidin.yaml` | 6 | 10 | revise | 0 | 1 | MODEL1805140003, MODEL2211030002 |
| coagulation_hemostasis | `human/systems/coagulation_hemostasis.yaml` | 8 | 12 | revise | 1 | 0 | BIOMD0000000338, BIOMD0000000339, BIOMD0000000340, BIOMD0000000740, BIOMD0000000611, BIOMD0000000747, MODEL1808210002, MODEL1806130001 |
| potassium_homeostasis | `human/systems/potassium_homeostasis.yaml` | 2 | 7 | pass | 0 | 1 | MODEL0911376350 |
| gi_incretin | `human/systems/gi_incretin.yaml` | 5 | 10 | revise | 0 | 3 | MODEL2403070001 |
| oxygen_transport | `human/systems/oxygen_transport.yaml` | 4 | 9 | pass | 0 | 0 | BIOMD0000000248, MODEL2305140001 |
| cardiac_function | `human/systems/cardiac_function.yaml` | 5 | 12 | revise | 0 | 3 | MODEL2202160001 |
| autonomic_baroreflex | `human/systems/autonomic_baroreflex.yaml` | 4 | 10 | pass | 0 | 0 | MODEL2101280001 |
| inflammation_cytokine | `human/systems/inflammation_cytokine.yaml` | 5 | 16 | pass | 0 | 2 | BIOMD0000000714, BIOMD0000000151 |
| lipid_metabolism | `human/systems/lipid_metabolism.yaml` | 7 | 10 | pass | 0 | 0 | BIOMD0000000434 |
| insulin_signaling | `multiscale/insulin_signaling.yaml` | 4 | 5 | pass | 0 | 1 | BIOMD0000000137 |
| beta_adrenergic | `multiscale/beta_adrenergic.yaml` | 5 | 6 | pass | 0 | 0 | MODEL1006230118, BIOMD0000000165 |
| epo_jak_stat | `multiscale/epo_jak_stat.yaml` | 6 | 8 | pass | 0 | 2 | BIOMD0000000271, BIOMD0000001077 |
| cardiomyocyte_calcium | `multiscale/cardiomyocyte_calcium.yaml` | 6 | 10 | revise | 0 | 1 | MODEL7914464799, MODEL0393108880 |
| hepcidin_signaling | `multiscale/hepcidin_signaling.yaml` | 5 | 6 | pass | 0 | 1 | BIOMD0000000734, MODEL2307050001 |

## Notes

- **Provenance discipline:** every causal edge carries a `mechanism` (quality→disposition→
  process→quality chain) and an `evidence` citation. The audit stage re-sourced vague or
  over-attributed citations to verifiable primary papers / textbook chapters and verified
  BioModels IDs against the API (catching and removing any that did not resolve).
- **Molecular verticals** connect to the macro map only by an *upward constitutive lift*;
  the downward macro→micro causal driver edges initially authored were removed (PhysioMap
  does not model downward causation — see CLAUDE.md / MULTISCALE.md), keeping the combined
  causal+constitutive meta-graph acyclic.
- **One model fix surfaced by the benchmark:** the lipid fragment's hepatocyte cholesterol
  uptake was re-routed through the *regulated LDL-receptor activity* (receptor-gated) rather
  than directly from plasma LDL, so familial hypercholesterolemia (LDLR loss) correctly
  depletes the hepatocyte pool and de-represses synthesis (Brown & Goldstein).
- All fragments remain **DRAFTS for domain review**.
