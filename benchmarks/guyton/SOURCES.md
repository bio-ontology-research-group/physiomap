# Guyton benchmark — source models (provenance)

The PhysioMap Guyton cardiovascular fragment is **derived from published computational
models, not invented**. The machine-readable model files needed to trace the benchmark
are retained here. Source publications and ancillary documentation are cited but are not
redistributed.

## Primary model — Guyton 1972 "Circulation: overall regulation"

> Guyton AC, Coleman TG, Granger HJ. *Circulation: overall regulation.*
> Annu Rev Physiol. 1972;34:13-46.

The model is distributed as a **modular** system. Two complementary sources are used
because BioModels hosts the *control/neuro-endocrine* subsystems while the
*hemodynamic + renal integrator* subsystems (which close the feedback loops) are only in
the CellML Physiome Model Repository.

### `biomodels/` — control subsystems (SBML, from EBI BioModels)

Downloaded via the BioModels REST API (`/model/download/{accession}`). These supply the
RAAS, baroreflex, hormonal and electrolyte edge signs.

| file | accession | subsystem |
|------|-----------|-----------|
| Guyton1972_Angiotensin | MODEL0911342562 | renin / angiotensin (RAAS) |
| Guyton1972_Aldosterone | MODEL0911376350 | aldosterone |
| Guyton1972_AntidiureticHormone | MODEL0911309080 | ADH / vasopressin |
| Guyton1972_AtrialNatriureticPeptide | MODEL0911272039 | ANP |
| Guyton1972_Autonomics | MODEL0911270005 | baroreflex / sympathetic tone |
| Guyton1972_volumeReceptors | MODEL0909931851 | atrial volume receptors |
| Guyton1972_HeartRateStrokeVolume | MODEL0911270006 | heart rate & stroke volume |
| Guyton1972_Electrolytes | MODEL0912160001 | Na/K/water electrolytes |
| Guyton1972_CapillaryDynamics | MODEL0912160000 | capillary fluid shift |
| Guyton1972_NonMuscleBloodFlowControl | MODEL0911169699 | non-muscle autoregulation |
| Guyton1972_MuscleBloodFlowControl | MODEL0911202318 | muscle autoregulation |
| Guyton1972_StressRelaxation | MODEL0910896131 | venous stress relaxation |
| Guyton1972_RedCells_Viscosity | MODEL0910928451 | red cells / viscosity |
| Guyton1972_HeartHypertrophy | MODEL0911231713 | cardiac hypertrophy |
| Guyton1972_ThirstDrinking_SaltAppetite | MODEL0910846879 | thirst / salt appetite |
| Guyton1972_PulmonaryFluidDynamics | MODEL0911091440 | pulmonary fluid |
| Guyton1972_PulmonaryOxygenIntake | MODEL0911047946 | pulmonary O2 |

These are CellML→SBML auto-conversions and use Guyton's original FORTRAN variable codes
(e.g. `MDFLW` = macula densa flow, `ANC` = angiotensin concentration, `ANM` = AngII
multiplier, `PA` = arterial pressure, `AMC` = aldosterone concentration, `AU` =
autonomic multiplier). Inter-module coupling is by shared variable name.

### `cellml_integrator/` — hemodynamic + renal integrator (CellML, from Physiome MR)

Downloaded as workspace archives from <https://models.cellml.org>. These close the loops
(they compute `PA`, cardiac output, resistances, venous return, and `MDFLW`/renal Na &
water excretion that the BioModels control modules consume but do not themselves
compute).

| path | workspace / exposure | subsystem |
|------|----------------------|-----------|
| `circ/circulation.cellml` (+ parent, parameters, units) | `guyton_circulatory_dynamics_2008` | **circulatory dynamics** — arterial pressure `PA`, cardiac output `QAO/QLO`, total peripheral resistance `RTP/total_peripheral_resistance`, venous return `QVO`, systemic venous volume `VVS`, right atrial pressure `PRA` |
| `kidney/kidney.cellml` (+ parent, parameters, units) | `guyton_kidney_2008` | **kidney** — `perfusion_pressure → glomerular_pressure → glomerular_filtration_rate`; afferent/efferent arteriolar resistance with angiotensin/autonomic/ANP effects; `angiotensin_induced_Na_reabsorption`; urinary Na & water excretion (**pressure natriuresis**) |
| `master/Guyton_Model_1-0.cellml` | `guyton_2008` | master import map for the full integrated model |

These CellML components are translations of the Guyton 1972 model; the component names in
`kidney.cellml`/`circulation.cellml` are literally the causal structure used to source the
hemodynamic and pressure-natriuresis edge signs.

The public Physiome Model Repository exposure identifies its public content as
[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) and asks users to cite the
model name, exposure URL, access date, and CellML authors. The files above were accessed
on 2 June 2026. The repository's
[license and citation page](https://models.physiomeproject.org/exposure/f97a5eb092b12f4f0f32ac51ee20d20e/guyton_angiotensin_2008.cellml/license_citation)
provides the applicable terms and citation instructions. PhysioMap does not redistribute
the ancillary Guyton model PDF.

## Cross-check model — modern closed-loop CV+renal model

| file | accession | note |
|------|-----------|------|
| `biomodels/CVS_model__MODEL2202160001.xml` | MODEL2202160001 | A multiscale, **closed-loop** cardiovascular + renal model with explicit baroreflex (Nervous system), RAAS (Renin/Angiotensin/Aldosterone), and pressure natriuresis (Glomerular filtration / Diuresis / Sodium). SBML-comp hierarchical model (only the coupling/ports file is on BioModels; the 20 submodule equation files are external). Used as an independent structural cross-check of the loop topology, **not** as the primary sign source. |

Ref: a multiscale model of the cardiovascular system regulating arterial pressure via
closed-loop baroreflex control (BioModels MODEL2202160001).

## How signs are derived

For each `CausalEdge` in `guyton_cv_core.yaml`, the `evidence` field cites the specific
source file + variable/component (e.g. `Guyton1972_Angiotensin MODEL0911342562: MDFLW→ANC`
or `kidney.cellml: perfusion_pressure→glomerular_filtration_rate`). The sign is the sign
of the partial derivative of the target's defining equation w.r.t. the source variable in
that model. **This fragment is a DRAFT for domain review.**
