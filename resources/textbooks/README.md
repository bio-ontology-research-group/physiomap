# Reference textbooks by scale of granularity

One reference textbook per PhysioMap **scale** (`Scale` in `physiomap_core/model.py`:
organism → organ_system → organ → tissue → cellular → subcellular → molecular). The aim is a
canonical, browsable text grounding the biology at each level.

**Licensing / honesty note.** The canonical references for several levels — *Molecular Biology of
the Cell* (Alberts), *Guyton & Hall Textbook of Medical Physiology*, *Medical Physiology* (Boron &
Boulpaep), *Lehninger Principles of Biochemistry* — are **copyrighted**. Where they are "available
online" (e.g. NCBI Bookshelf) they are **free to read, not free to download**; downloadable PDFs of
them are pirated. We therefore do **not** vendor those. Instead, for each scale we download a
genuinely **open-licensed (CC-BY/-NC-SA) or author-free** textbook (the PDFs below), and list the
copyrighted canonical text with its legitimate read-only link for reference.

PDFs are stored locally in this directory and are **git-ignored** (binary bloat + redistribution),
exactly like `resources/<theme>/*.pdf`. This README (the mapping + sources) is versioned.

**Guyton & Hall (institutional copy).** `Guyton_and_Hall_Textbook_of_Medical_Physiology.pdf`
(11th ed., the canonical organism-/system-scale reference and the conceptual source of PhysioMap's
Guyton CV/renal core) is present locally as a **read-only institutional copy obtained through the
KAUST library** — it is **not** vendored/redistributed (git-ignored like every other PDF here, and
**not** linked or uploaded anywhere). It is used only as a local extraction/corroboration source
for the curator. Provenance mined from it carries the citation tag `Guyton & Hall, Medical
Physiology, 11th ed.` with chapter/section anchors; see
[`benchmarks/results/guyton_extraction.md`](../../benchmarks/results/guyton_extraction.md).

## Mapping

| Scale | Open textbook (downloaded PDF) | License | Canonical (copyrighted, read-only) |
|---|---|---|---|
| organism | OpenStax **Anatomy & Physiology 2e** | CC BY-NC-SA 4.0 | Guyton & Hall, *Medical Physiology* |
| organ_system | OpenStax **Anatomy & Physiology 2e** | CC BY-NC-SA 4.0 | Boron & Boulpaep, *Medical Physiology* |
| organ | OpenStax **Anatomy & Physiology 2e** | CC BY-NC-SA 4.0 | Boron & Boulpaep, *Medical Physiology* |
| tissue | OpenStax **Anatomy & Physiology 2e** (Tissue Level ch.) | CC BY-NC-SA 4.0 | Ross & Pawlina, *Histology: A Text and Atlas* |
| cellular | Wong, **Cells: Molecules and Mechanisms** (+ OpenStax **Biology 2e**) | CC BY-NC-SA 3.0 / 4.0 | Alberts et al., *Molecular Biology of the Cell* |
| subcellular | Wong, **Cells: Molecules and Mechanisms** | CC BY-NC-SA 3.0 | Alberts et al., *Molecular Biology of the Cell* |
| molecular | Jakubowski & Flatt, **Fundamentals of Biochemistry** (Vol I) | CC BY-NC-SA 4.0 | Lehninger / Berg–Stryer, *Biochemistry* |

OpenStax **Biology 2e** is included as a general cross-scale supplement (cell → molecular genetics).

## Downloaded files & sources

- `OpenStax_Anatomy_and_Physiology_2e.pdf` — OpenStax A&P 2e (CC BY-NC-SA 4.0).
  Source: <https://openstax.org/details/books/anatomy-and-physiology-2e/>
  (full-book PDF via LibreTexts batch print: `https://batch.libretexts.org/print/Letter/Finished/med-68748/Full.pdf`).
- `Wong_Cells_Molecules_and_Mechanisms.pdf` — E. V. Wong, *Cells: Molecules and Mechanisms*
  (Axolotl Academica; CC BY-NC-SA 3.0). Source: <https://www.axopub.com/> ·
  <https://bio.libretexts.org/Bookshelves/Cell_and_Molecular_Biology/Cells_-_Molecules_and_Mechanisms_(Wong)>
  (`https://batch.libretexts.org/print/Letter/Finished/bio-16085/Full.pdf`).
- `Jakubowski_Fundamentals_of_Biochemistry_Vol1.pdf` — Jakubowski & Flatt, *Fundamentals of
  Biochemistry*, Vol. I (Structure and Catalysis) (CC BY-NC-SA 4.0).
  Source: <https://bio.libretexts.org/Bookshelves/Biochemistry/Fundamentals_of_Biochemistry_(Jakubowski_and_Flatt)>
  (`https://batch.libretexts.org/print/Letter/Finished/bio-38638/Full.pdf`).
- `OpenStax_Biology_2e.pdf` — OpenStax *Biology 2e* (CC BY-NC-SA 4.0).
  Source: <https://openstax.org/details/books/biology-2e>
  (`https://assets.openstax.org/oscms-prodcms/media/documents/Biology2e-WEB.pdf`).

## Legitimate read-only access to the canonical (copyrighted) texts

- *Molecular Biology of the Cell* (Alberts), 4th ed — NCBI Bookshelf (read online):
  <https://www.ncbi.nlm.nih.gov/books/NBK21054/>
- *Molecular Cell Biology* (Lodish), 4th ed — NCBI Bookshelf: <https://www.ncbi.nlm.nih.gov/books/NBK21475/>
- *The Cell: A Molecular Approach* (Cooper), 2nd ed — NCBI Bookshelf: <https://www.ncbi.nlm.nih.gov/books/NBK9839/>
- *Biochemistry* (Berg, Tymoczko, Stryer), 5th ed — NCBI Bookshelf: <https://www.ncbi.nlm.nih.gov/books/NBK21154/>
- Guyton & Hall, Boron & Boulpaep, Ross & Pawlina — purchase / institutional library only.
