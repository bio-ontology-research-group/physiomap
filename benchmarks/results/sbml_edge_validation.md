# Edge-sign validation against the Guyton ODE models (family 2 extension)

Each row perturbs a constant input of a vendored Guyton SBML module by +5%, integrates the ODE to steady state, and compares the sign of the output's steady-state change to the sign PhysioMap encodes.

- **non-adaptive edges confirmed: 5/5** (direct sign agreement with the published ODE)
- adaptive (reflex) edges: 2 — chronic steady-state ~0 in 2/2 (see note)

| module | input | output | ODE sign | PhysioMap | verdict | edge |
|---|---|---|:--:|:--:|:--:|---|
| Angiotensin | MDFLW | ANC | - | - | OK | renal_perfusion_pressure -> renin (-)  [higher macula densa flow suppresses renin] |
| Angiotensin | MDFLW | ANM | - | - | OK | renal_perfusion_pressure -> (renin->) angiotensin effect (-) |
| Aldosterone | ANM | AMC | + | + | OK | angiotensin_II -> aldosterone (+) |
| AntidiureticHormone | CNA | ADHC | + | + | OK | plasma_osmolality/sodium -> adh (+) |
| AtrialNatriureticPeptide | PRA | ANPC | + | + | OK | blood_volume/atrial pressure -> anp (+) |
| Autonomics | PA | AU | 0 | - | adaptive | mean_arterial_pressure -> sympathetic_tone (-)  [ARTERIAL BAROREFLEX — adapts, BAROTC] |
| AntidiureticHormone | PA1 | ADHC | 0 | - | adaptive | mean_arterial_pressure -> adh (-)  [pressure arm — adaptive] |

## Note on the adaptive edges

The arterial baroreflex (`Autonomics`, time constant `BAROTC`) and the ADH pressure arm **adapt**: their *chronic* steady-state response to a sustained pressure change is ~0. This is Guyton's own classic result — the arterial baroreflex does not set long-term arterial pressure (renal pressure-natriuresis does). PhysioMap's edge encodes the **acute** reflex sign, so a chronic `0` here is an expected, informative timescale distinction, not a contradiction. It flags that these edges should carry an acute/chronic annotation for steady-state use.
