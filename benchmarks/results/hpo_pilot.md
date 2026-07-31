# Historical HPO monogenic pilot

Historical pilot retained as construction provenance. The released
rare-disease evaluation is documented in
[`e1b_forward.md`](e1b_forward.md). Run: `python -m physiomap_core.hpo`.
Pilot of **18** monogenic disorders whose primary lesion and secondary phenotypes both live in
the current human map. Forward = predict phenotypes from `do(primary)`; backward = abduce the
primary lesion from the observed phenotype signs. (9 RAAS/endocrine/iron + 9 added with the
metabolic-coverage expansion: amino-acid, purine/urate, trace-metal, intermediary-fuel,
bilirubin, phosphate/FGF23.)

## Forward (comparative-statics phenotype prediction)

| | value |
|---|---|
| determinate predictions | 18 |
| correct | **18** |
| **wrong (soundness)** | **0** |
| abstain (`?`) | 29 |
| directional accuracy (on determinate) | **100%** |

Determinate + correct on the **feedback axes and self-contained metabolic subsystems**: 21-OHD →
ACTH ↑; FH → LDL ↑; hemochromatosis → iron ↑, transferrin sat ↑; congenital hypothyroidism →
TSH ↑, free T3 ↓; PKU → Phe ↑, Tyr ↓; homocystinuria → Hcy ↑, Met ↑; MSUD → BCAA ↑; Lesch-Nyhan →
urate ↑; xanthinuria → urate ↓, xanthine ↑; GSD-Ia → lactate ↑; Gilbert → unconjugated bilirubin
↑; XLH → phosphate ↓. The RAAS/volume disorders (Liddle, Gitelman, Bartter, GRA, central DI) and a
few nodes that route into the giant SCC (von Gierke's glucose, Wilson's copper/ceruloplasmin loop,
XLH's calcitriol) **abstain (`?`)** — the documented precision frontier. Sound throughout (0 wrong).
Novel determinate predictions on un-annotated nodes (hypotheses) are emitted too (e.g. 21-OHD → 6).

## Backward (lesion abduction)

| | value |
|---|---|
| unique top-1 | **10/18** |
| top-3 | **18/18** |

Cleanly recovered (unique top-1): FH, hemochromatosis, congenital hypothyroidism, PKU,
homocystinuria, MSUD, xanthinuria, GSD-Ia, Gilbert, XLH — their determinate, specific downstream
signs point uniquely to the lesion. The SCC-entangled disorders land within top-3 but **tie at the
top** (forward abstains there, so candidate lesions score equally) — again the SCC frontier, not a
wrong call. The coverage expansion thus both *added* HPO-mappable disorders and *raised* clean
recovery (3/9 → 10/18).

## The honest headline

The discriminating case we want — **Liddle vs Gitelman** (same hypokalemia, *opposite*
aldosterone/renin direction) — is currently **latent**: both route through the monolithic
whole-body SCC, where the solver correctly abstains rather than guess. Resolving it needs SCC
refinement (acute/chronic or timescale separation, or breaking the SCC with more definitional
edges), not more data. This is the concrete next step the pilot surfaces.

## Caveats

- Annotations are chronic/compensated and incomplete → we score **direction + soundness**, never
  recall; absent phenotypes are never negatives.
- Backward candidates that coincide with an observed node get a self-agreement point (mild
  abduction artifact) — does not affect the cleanly-recovered cases.
- OMIM numbers curated; per-phenotype HPO-term IDs intentionally omitted pending EQ/uPheno
  binding (the documented next step). No identifier is fabricated.
