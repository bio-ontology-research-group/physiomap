# Frozen HPO evaluation inputs

These files pin the Human Phenotype Ontology inputs used by the PhysioMap
v1.1.1 rare-disease evaluation.

| File | Source | Uncompressed SHA256 | Compressed SHA256 |
|---|---|---|---|
| `hp.obo.gz` | `http://purl.obolibrary.org/obo/hp.obo` | `8d6c23798667d4506767ce643fc3c028f0d1c85e7e1d8810e491181a345d53cd` | `a5b6a4a6988d1cf38202a830e667f215a7bdbd723e6232d7a40e6124ae0169b4` |
| `genes_to_phenotype.txt.gz` | `https://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt` | `25d3e5a40203cbb4cc027747c70fcb5431bcfb26283479608a97f3d810285c7d` | `843a4c74ad782433f1089d42d6b5f92ed901b5875b3eab4e8ed0d7bfe20a3d24` |

The ontology declares `hp/releases/2026-02-16`. The archives were compressed
deterministically with gzip and without a timestamp. The release gate verifies
both compressed and uncompressed checksums before evaluation.

HPO is distributed under the
[CC BY 4.0 license](https://hpo.jax.org/license).
