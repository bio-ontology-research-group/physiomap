# Tracing a Mendelian disease from variant to endophenotype  *** DRAFT ***

`physiomap_core/trace.py` renders the **signed mechanistic path** from a gene lesion (a `do()`
that clamps a node ↑/↓) to a target endophenotype: every step shows its edge sign and the running
↑/↓ state, the cross-scale **constitutive lift** is marked `▷(determination)`, and the forward
path-product is reconciled against the **comparative-statics** net sign (`solve_multiscale`).
Endophenotypes are increased/decreased qualities (PATO directions), rendered ↑/↓/?.

```
# disorder mode (reads benchmarks/hpo/disorders.yaml):
python -m physiomap_core.trace hemochromatosis
# ad-hoc mode:  <node> <+|-> <target>
python -m physiomap_core.trace insulin_receptor_activity - peripheral_glucose_uptake
```

## 1. Hereditary hemochromatosis (HFE) — a fully determinate variant → endophenotype trace

The HFE variant disables iron sensing by the BMP/SMAD co-receptor complex, so hepcidin is
synthesised at an **inappropriately low** level (the homeostatic iron→hepcidin loop is broken by
the mutation). Modelling the variant as `do(hepcidin ↓)` therefore breaks the loop and the
downstream chain is determinate:

```
variant ⇒ do(hepcidin ↓)  ──▶  transferrin_saturation ↑   [increased transferrin saturation]
  hepcidin↓ →(-) ferroportin_activity↑ →(+) plasma_iron↑ →(+) transferrin_saturation↑
variant ⇒ do(hepcidin ↓)  ──▶  plasma_iron ↑              [elevated serum iron]
  hepcidin↓ →(-) ferroportin_activity↑ →(+) plasma_iron↑
```

↑ transferrin saturation is exactly the first diagnostic lab to rise in HFE hemochromatosis. The
tool also honestly reports **ferritin = ?**: two opposing mechanisms converge on it
(`hepcidin↓ →(+) ferritin↓` vs `hepcidin↓ → iron↑ →(+) ferritin↑`), so the qualitative net is
undetermined rather than guessed.

**Why hepcidin is low** (the molecular upstream of the clamp), traced separately:

```
do(bmp_smad_signaling ↓)  →(+) hepcidin_transcription↓  ▷(determination)  hepcidin
```

`hepcidin_transcription ↓` is determinate; the lift `hepcidin_transcription ▷ hepcidin` is the
cross-scale (molecular → organ-system) constitutive determination. With the iron-sensing loop
*intact* the net at hepcidin is `?` — which is precisely why the disease is defined by hepcidin
being clamped inappropriately low (the variant overrides the feedback).

## 2. Severe insulin resistance (INSR) — a molecular cascade crossing the constitutive lift

A variant in the insulin receptor clamps `do(insulin_receptor_activity ↓)`. The trace crosses
four within-scale signalling steps and the constitutive lift to the organ-system node:

```
variant ⇒ do(insulin_receptor_activity ↓)  ──▶  peripheral_glucose_uptake ?
  insulin_receptor_activity↓ →(+) irs1_signaling↓ →(+) pi3k_akt_activity↓
      →(+) glut4_membrane_translocation↓  ▷(determination)  peripheral_glucose_uptake↓
  NB forward mechanism says ↓, but the steady-state (comparative-statics) net is ? —
     peripheral_glucose_uptake sits in a homeostatic feedback loop (SCC).
```

This is the PhysioMap thesis made visible: the **forward mechanism** unambiguously says glucose
uptake falls, but glucose disposal is homeostatically regulated, so the **compensated steady-state
sign is magnitude-dependent (`?`)** — comparative statics ≠ naive path propagation. Every molecular
vertical lifts into such a loop (peripheral glucose uptake, cardiac output, TPR, hepcidin/iron); a
determinate *systemic* readout requires the lesion to clamp a node that breaks the loop (as in
hemochromatosis), which is itself a faithful statement about which monogenic defects produce a
fixed, non-compensable shift.
```
