# Licensing

PhysioMap is released under a **dual license** that follows the usual split for a
research artifact: the **software** is BSD-licensed, and the **map, data, and
documentation** are Creative-Commons-licensed. Some inputs are **third-party** and
keep their own licenses; those are listed at the bottom and are *not* relicensed here.

| Component | License | Files |
|---|---|---|
| **Software** | [BSD 3-Clause](LICENSE) | `physiomap_core/`, `scripts/`, `web/*.py`, `web/*.js`, `web/*.css`, `web/*.html`, `tests/`, `supplement/lean/`, `ontology/src/`, `pyproject.toml`, `uv.lock`, and all `*.py` / `*.js` / `*.lean` / `*.groovy` / `*.gradle` files |
| **Map, data & docs** | [CC BY 4.0](LICENSE-DATA) | The curated PhysioMap map and its groundings: `benchmarks/human/**`, `benchmarks/hpo/**` (PhysioMap-authored mappings), `benchmarks/multiscale/**`, `benchmarks/drug_panel/**`, PhysioMap-generated results in `benchmarks/results/**`, the exported `web/physiomap.json`, PhysioMap-authored `ontology/` outputs, `docs/**`, `supplement/README.md`, `README.md`, and `CHANGELOG.md` |

**SPDX.** Software: `BSD-3-Clause`. Data/docs: `CC-BY-4.0`.

## How to attribute (CC BY 4.0)

If you use the map or evaluation data, please cite the paper and this repository:

> Hoehndorf R., Schofield P.N., Gkoutos G.V. *PhysioMap: an
> ontology-grounded causal knowledge graph of human physiology.*
> Manuscript under review, 2026.
> Code & data: https://github.com/bio-ontology-research-group/physiomap

See [`CITATION.cff`](CITATION.cff) for machine-readable metadata.

## Third-party components (not relicensed)

These inputs are used under their own terms; PhysioMap re-expresses facts with citations
and does **not** redistribute the copyrighted source documents. Consult each source for reuse.

| Source | What we use | Its license / terms |
|---|---|---|
| **Guyton/CellML circulation models** (`benchmarks/guyton/cellml_integrator/`) | Machine-readable reference model structure for the cardiovascular benchmark | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) under the [Physiome Model Repository citation terms](https://models.physiomeproject.org/exposure/f97a5eb092b12f4f0f32ac51ee20d20e/guyton_angiotensin_2008.cellml/license_citation); cite the original model and CellML authors |
| **Human Phenotype Ontology (HPO)** | Phenotype identifiers and directional term mappings | CC BY 4.0 (hpo.jax.org) |
| **ChEMBL** | Drug mechanism-of-action records (derived annotations only) | CC BY-SA 3.0; derived annotations here are provided for reproducibility; consult ChEMBL for reuse |
| **SIDEKICK** | Side-effect / indication mappings for the abstention evaluation | See the SIDEKICK release (Zenodo DOI in the paper) |
| **NHANES 2017–2018** | Analyte values for the conditional-independence check | U.S. public domain (CDC/NCHS) |
| **OBO Foundry ontologies** (ChEBI, PR, GO, CL, Uberon, PATO) | Stable identifiers for entities and qualities | Each ontology's own open license (mostly CC BY / CC0) |
| **Textbooks** (Hall, West, Williams; OpenStax A&P 2e) | Draft fact extraction for curation | Copyrighted textbook PDFs are **not** distributed and are `.gitignore`d; extracted facts are re-expressed and cited. OpenStax content is CC BY. |

If you believe any file is mislabeled or should carry different attribution, please open an
issue. We will correct it promptly.
