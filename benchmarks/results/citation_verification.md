# Citation verification — PubMed concordance over the whole corpus

*Run 2026-06-05. `scripts/verify_citations.py` (deterministic PubMed fetch + existence gate) +
a concordance fan-out (20 agents) that judged each cited PMID's real title/abstract against the
edge's claim.*

## Why

The fan-out authoring models (and earlier hand-curation) sometimes cite **real-format PMIDs that
index an unrelated paper** — fabrications the PubMed-blind adversarial verifier could not catch
(it only sees the citation string, not the actual article). This stage checks every cited PMID
against PubMed itself, so no identifier survives unless its real record supports the claim.

## The stage (`scripts/verify_citations.py`)

- **`--audit`** — deterministic existence gate: extract every `PMID` from edge evidence, fetch the
  real record via NCBI E-utilities (cached, gitignored), fail if any does not resolve.
- **`--bundle`** — emit per-edge the claim + each PMID's **real title + (per-PMID) abstract** for the
  concordance fan-out. (The abstract is parsed per-PMID from efetch XML — an earlier text-mode batch
  blob conflated records and caused false rejections; fixed.)
- Concordance fan-out: per PMID, `supports_claim` requires a **verbatim supporting quote** from the
  real record; an off-topic real title is rejected (the misattribution case). Each edge's evidence is
  rewritten to keep confirmed PMIDs + all non-PMID provenance (textbook / disease / OMIM) and drop the
  rest, tagged `[citations PubMed-verified]`.

## Result (whole corpus, 306 edges citing 272 distinct PMIDs)

- **Existence:** 271/272 resolved; **1 fabricated** (`PMID 20905869`).
- **Concordance:** **235 PMIDs confirmed, 157 rejected** (≈40% of citations were misattributed),
  **144 edges corrected**. After correction the corpus cites **175 distinct PMIDs across 197 edges**
  (≈97 bad PMIDs removed); the existence audit is now clean (175/175).
- Rejections concentrated in the cheap-author fan-out fragments (`isolated_connections` 65,
  `component_bridges` 49); curated fragments had few genuine misses once the abstract bug was fixed.
- Examples caught: `PMID 7240353` (N-nitroso carcinogenicity, cited for DMGDH), `13903543`
  (hemangiomatosis, cited for histidine decarboxylase), `31858131` (testicular organ culture, cited
  for SLC6A6/taurine), `5183342` (schistosomiasis, cited for GM1 gangliosidosis), `19252498`
  (a neuroscience time-coding paper, cited in `hepcidin_bmp_smad_axis` as "Meynard 2009 Bmp6 KO").
- All signs/structure unchanged → **HPO soundness gate unaffected; 159 tests pass.**

## Second pass — the curated-fragment concordance gap (run 2026-06-05)

The first pass tagged 144 edges but only ran concordance over the fan-out fragments. An audit of
the live map then found **162 edges that cite a real, existence-verified PMID but had never been
concordance-checked** — concentrated in the *older curated* molecular/system fragments that predate
the stage (`growth_hormone_igf1` 15, `cardiomyocyte_calcium` 9, `erythroblastic_island`/`iron_hepcidin`/
`bone_remodeling` 6 each, `insulin_signaling`/`energy_balance_appetite` 4 each, plus the
`isolated_connections`/`component_bridges` survivors that kept a PMID). A 14-agent concordance fan-out
judged all 162 (200 PMID records):

- **177 PMID verdicts confirmed, 23 rejected (~12%)** — far below the ~40% of the cheap-author run,
  confirming the older curated edges were better-sourced. **162 edges corrected** (every one now tagged).
- Rejections were genuine misattributions or over-generic reviews, e.g. `PMID 3395335` (peroxisomal
  PIPOX deficiency, cited for ALDH7A1/antiquitin), `11751331` (an integrin α4β1–VCAM homology-modeling
  paper, cited for macrophage→erythroblast support), `17185408` (the Farhy GH-model paper — correctly
  KEPT where it is the genuine BioModels source, stripped only on 3 GH edges where it was tacked on),
  `38270467` (a broad erythrocyte-metabolism review cited for the PaO₂→SaO₂ edge).
- All signs/structure unchanged; **159 tests pass, HPO soundness gate PASS (0 wrong)**.

**Live coverage after both passes:** the composed map (1498 causal edges) now has **0 edges that cite
a PMID without being PubMed-verified** — **306 edges tagged**, **179 still cite ≥1 confirmed PMID**,
existence audit clean (**159/159** distinct PMIDs resolve). The remaining 1192 edges cite no PMID
(they rest on textbook / BioModels / disease provenance, not machine-checkable against PubMed), and
664 curated edges still carry no machine `do()`-evidence class (legacy-exempt by design).

## Caveat & next use

This verifies the **citation**, not the biology — a stripped edge keeps its (sound) sign and its
textbook/disease grounding; only the unverifiable identifier is removed. The stage is now reusable:
future fan-outs (the remaining islands, the 4 deferred GRN modules) can run `--audit` + the
concordance pass so citations self-clean instead of needing manual triage. OMIM numbers are not yet
machine-verified (licensed); they are retained as best-effort and flagged DRAFT.
