# Heart-rate control — curated by George Gkoutos (with T3 worked example)

*Added 2026-06-06. Source: G. Gkoutos, `heart_rate_physio_with_T3_example` (2026), an expert
hand-derived decomposition of heart rate into signed causal "pressures" with per-step mechanisms,
worked through for T3. Encoded as `benchmarks/human/systems/george_heart_rate.yaml`; evidence
class `curated_mechanistic`, evidence code **ECO:0000305** (curator inference used in manual
assertion). DRAFT for George's own review.*

## What the curation contributed

George independently re-derived PhysioMap's formalism by hand: his `Heart Rate = SA intrinsic +
sympathetic − vagal + hormonal + temperature + …` is a signed causal decomposition; his per-step
↑/↓ arrows are edge signs; his mechanism chains are the `quality→disposition→process→quality`
abbreviation; and his baroreflex *counter-pathways* are a negative-feedback SCC. Most of his T3→HR
graph was already in the map (`free_t3→heart_rate/metabolic_rate/TPR/cardiac_output`,
`sympathetic/parasympathetic/core_temperature→heart_rate`). Two elements his synthesis adds —
now encoded:

1. **SA-node automaticity as an explicit pacemaker mediator** (`sa_node_automaticity`,
   UBERON:0002351 / PATO:0000161). The intrinsic-chronotropic drivers now route through it:
   the existing `free_t3→heart_rate` and `core_temperature→heart_rate` edges were **re-routed** to
   `…→sa_node_automaticity→heart_rate` (sign-preserving; the funny current / L-type Ca / SERCA /
   phase-4 mechanism that both edges already named, GO:0086015 / GO:0086046).
2. **Cardiac β1-adrenergic chronotropic responsiveness** (`beta1_adrenergic_chronotropic_responsiveness`,
   UBERON:0002351 / PATO:0000085 "sensitivity toward"): `free_t3 →(+) responsiveness →(+) heart_rate`
   (GO:0003064 regulation of heart rate by hormone) — his point 4.

## The multiplicative edge — now a first-class construct

β-adrenergic responsiveness is genuinely a **multiplicative gain** on `sympathetic_tone→heart_rate`.
This is now modelled directly with a **`ModulationEdge`** (`physiomap_core/modulation.py`):

```
modulation_edges:
  - modulator: beta1_adrenergic_chronotropic_responsiveness
    edge_source: sympathetic_tone
    edge_target: heart_rate
    sign: "+"          # raises the gain
```

Why this is sound *and* adds new power:

- **First order** — around a positive operating point a modulation degenerates to an ordinary
  additive edge `modulator → edge_target` (here `responsiveness → heart_rate`, +), because
  `∂HR/∂responsiveness = sympathetic_tone · k′ > 0`. That additive **shadow edge is kept** in the
  fragment, so the sign solver is untouched and **no node-level prediction changes** (`shadow_is_present`
  verifies the two are consistent). This is exactly why the earlier hand-added additive edge was
  sign-correct.
- **Second order** — the genuinely new content is the cross-partial
  `∂²HR/∂(sympathetic_tone)∂θ`, whose sign `gain_sensitivity()` computes. For `do(free_t3↑)` it
  returns **`+`**: T3 *amplifies the sympathetic chronotropic effect* — George's point 4, now a formal,
  queryable prediction the additive graph could not state. (Control: `do(parasympathetic↑)` returns
  *no gain change* — nothing on that path moves the modulator.)

CLI: `python -m physiomap_core.modulation free_t3 + sympathetic_tone heart_rate` →
`net heart_rate = ? ; gain sensitivity of sympathetic_tone → heart_rate = +`. `--list` shows all
modulation edges. `can_flip_sign` (default False) marks a gain that can cross zero (then the modulated
edge's own sign degrades to `?` when the modulator is unpinned).

## What the model computes for `do(free_t3 ↑)`

The trace now contains George's structure — `free_t3 → β1_chronotropic_responsiveness → heart_rate`
and `core_temperature → sa_node_automaticity → heart_rate`. The **net** sign of `heart_rate` is
**`?`**, *agreeing with George's own caveat*: the direct/sympathetic/temperature up-pressures compete
with the baroreflex counter-path he drew —
`free_t3↑ → … → TPR↑ → mean_arterial_pressure↑ → baroreceptor_firing↑ → parasympathetic↑ → heart_rate↓`.
HR, like the rest of the cardiovascular/autonomic cluster, sits in the ~87-node homeostatic SCC, so
the steady-state net is magnitude-dependent (the documented precision frontier). Every individual
edge sign George drew that the map stores is **determinate and matches**; only the loop-net is `?`.

## Verification

- All ontology IRIs OBO-verified (980/980 OK, 0 mismatch); new term PATO:0000085 added to the manifest.
- `validate_fragment` OK (3/3 provenance, refs resolve), `validate_causal_evidence` OK
  (all `curated_mechanistic`, interventional).
- Composed map **1527 nodes**; both new nodes join the giant component (no new islands).
- **HPO soundness gate PASS (0 wrong); 159 tests pass.** Re-routing is sign-preserving, so no
  prediction changed.
