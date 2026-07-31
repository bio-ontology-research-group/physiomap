# GO-CAM: Gene Ontology Causal Activity Modeling — STUB

**[NO PDF — stub]** (Nature Genetics is paywalled; PMC author manuscript PMC7012280
and escholarship/OSTI copies all returned HTML/403, not a verifiable PDF. Abstract
and metadata verified via WebFetch of PubMed 31548717 and nature.com record.)

## Citation
Thomas PD, Hill DP, Mi H, Osumi-Sutherland D, Van Auken K, Carbon S, Balhoff JP,
Albou L-P, Good B, Gaudet P, Lewis SE, Mungall CJ. "Gene Ontology Causal Activity
Modeling (GO-CAM) moves beyond GO annotations to structured descriptions of
biological functions and systems." *Nature Genetics* 2019; 51(10):1429-1433.
PMID: 31548717. DOI: 10.1038/s41588-019-0500-1.

## Abstract (verbatim, via PubMed)
"To increase the utility of Gene Ontology annotations for interpretation of
genome-wide experimental data, we have developed GO-CAM, a structured framework for
linking multiple GO annotations into an integrated model of a biological system. We
expect that GO-CAM will enable new applications in pathway and network analysis as
well as improving standard GO annotations for traditional GO-based applications."

## Key concepts (from abstract + GO-CAM documentation / RO causal-relations page)
- A GO-CAM model is a graph of **molecular activities** (typed by GO Molecular
  Function) connected by **RO causal relations** (causally upstream of, regulates,
  positively/negatively regulates, provides input for, etc.). Each activity is the
  *realization* of a function by a gene product (`enabled_by`).
- Activities are given biological **context**: `part_of` a GO Biological Process,
  `occurs_in` a GO Cellular Component / CL cell type / Uberon anatomical structure,
  `has_input`/`has_output` ChEBI molecules.
- This is the OBO/BFO-grounded standard for representing **causal mechanism as a
  graph of typed activities with context** — the closest existing artifact to a
  PhysioMap within-scale causal edge expanded into its mechanism.

## RELEVANCE to PhysioMap
GO-CAM is the model PhysioMap's within-scale causal edges should *abbreviate*: a
PhysioMap edge (quality A -> quality B) compresses a GO-CAM-style
activity/process chain. When the OWL phase adds GO, the mechanism ref behind a
causal edge can point at (or be expanded into) a GO-CAM model. Reuse its activity
typing (GO-MF enabled_by gene product, occurs_in CL/Uberon, has_input/output ChEBI)
and its RO causal relation vocabulary as the controlled relation set for edges.
