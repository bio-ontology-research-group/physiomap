# Conolly et al. 2017 — Quantitative Adverse Outcome Pathways and Their Application to Predictive Toxicology

**[NO PDF — stub]** (ACS Environ. Sci. Technol., paywalled; PMC author manuscript PMC6134852 gated behind an NCBI JavaScript proof-of-work challenge not solvable via curl)

- **Authors:** Rory B. Conolly, Gerald T. Ankley, WanYun Cheng, Michael L. Mayo, David H. Miller, Edward J. Perkins, Daniel L. Villeneuve, Karen H. Watanabe
- **Journal:** Environmental Science & Technology 51(8): 4661–4672, 2017
- **DOI:** 10.1021/acs.est.6b06230
- **PMID:** 28355063 | **PMCID:** PMC6134852

## Abstract (paraphrased from verified PubMed record)
Defines a **quantitative AOP (qAOP)** as a biologically based, computational model describing the **key event relationships** linking an MIE to an AO, such that the magnitude and probability of the downstream adverse outcome can be predicted from the degree of MIE perturbation. Demonstrated with the aromatase (CYP19) inhibition AOP in fathead minnow (AOP:25): aromatase converts testosterone to 17β-estradiol (E2); egg production is E2-dependent, so inhibition causes reproductive failure and population decline. The qAOP chains four linked sub-models — a mechanistic hypothalamus–pituitary–gonad (HPG) feedback model, a vitellogenin (VTG) liver compartment model, a statistical VTG→fecundity model, and a density-dependent population matrix model — spanning molecular to population scales, for use in regulatory risk assessment.

## Relevance to PhysioMap
The clearest demonstration that a qualitative cross-scale causal pathway can be promoted to a dynamical model. The HPG sub-model is an explicit **feedback (cyclic) endocrine control system** — directly analogous to PhysioMap's cyclic signed causal maps (e.g., the Guyton cardiovascular feedback fragment). Shows the qualitative-to-quantitative continuum: PhysioMap's signed edges (sign(dx*/dθ)) are the qualitative limit of Conolly's response-response functions; the steady-state of the implied cyclic SCM corresponds to the equilibrium of the HPG/VTG/population coupled models. Cross-scale composition (molecular→cellular→organ→organism→population) via linked compartment models is exactly PhysioMap's scale stacking with constitutive cross-scale links.
