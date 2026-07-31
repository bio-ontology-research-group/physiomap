# PhysioMap web viewer

An interactive, browsable visualization of the canonical OWL-projected PhysioMap. Static
single-page app (Cytoscape.js) — no backend is required for browsing or benchmark overlays.

## Run

```bash
uv run python web/export_data.py     # regenerate the lossless sharded viewer payload
cd web && python -m http.server 8099  # then open http://localhost:8099/
```

`export_data.py` loads the canonical released SCM, tags each node with its source system, computes
the SCCs, and precomputes all benchmark interventions (including declared influence contexts).
The initial `physiomap.json` contains only the drawing/search bootstrap; complete ontology and
evidence records plus intervention results live in 16 deterministic lazy-loaded buckets apiece
under `data/`. Every JSON has a deterministic `.json.gz` sibling. The logical export is lossless;
`load_exported_web_payload()` reconstructs it exactly for the golden-baseline tests.

## What you can do

- **Browse the signed causal graph** — edges coloured by sign (green +, red −, grey ?),
  arrowheads show direction; cross-scale **constitutive** edges are dashed gold (toggle).
- **Colour nodes by physiological system** (default) or **by biological scale**.
- **Filter** the graph by system (checkboxes) and switch layouts (force-directed,
  concentric-by-degree, hierarchical, circle).
- **Search** a node and fly to it.
- **Click a node** → detail panel: label, system, scale, SCC membership, entity/quality
  ontology IRIs (linked to OLS/OBO), and every in/out edge with its sign, mechanism and
  evidence. **Click an edge** → its sign, mechanism, evidence.
- **Highlight the whole-body homeostatic SCC** (the exact size is computed from the release).
- **Intervention overlay** — pick any benchmark intervention/drug and the nodes recolour
  by the solver's predicted steady-state sign (↑ green / ↓ red / ? grey / intervened blue /
  unaffected dark), so you can *see* how a perturbation propagates through the map. The right
  panel also lists the **derived HPO phenotypes** with a signed mechanistic trace for each —
  the same payload the synthetic knockout produces, precomputed at export time.
- **Synthetic knockout (live)** — clamp *any* node `do(↑/↓)` and the knockout API derives the
  comparative-statics steady-state sign of every reachable node plus the determinate HPO
  phenotypes (with traces), live in ~0.1 s. Use **＋ add** (or Tab) to clamp **several nodes at
  once** — a joint multi-node `do()` solved in one pass, shown as removable ↑/↓ chips. Needs the
  `physiomap-api` service (see `deploy/`); without it the rest of the viewer still works.
- **"X affected" (direction undetermined)** — a reachable trait whose *net* sign the feedback core
  leaves `?` is reported in a separate **Affected** section (it *is* perturbed, just unsignable),
  linked to HPO's neutral *"Abnormality of X"* term. Shown for both the knockout and the
  intervention overlay.
- **Multiplicative (gain) edges** — a modulation scales the *strength* of a causal edge rather
  than adding to its target. Every modulated causal edge is drawn with a purple **⊗** dot at its
  midpoint (so you can see *which* edges carry a gain at a glance), and clicking the gain edge —
  or the modulated edge — names the modulator and lights up the `S→T` edge it acts on. Toggle the
  whole layer with "multiplicative (gain) edges". The data model guarantees every modulation
  modulates a real causal edge. The gain-edge popup also shows the **interaction sign** `ι = μ·σ`
  (amplify/dampen) and, for sign-flipping gains, the **regime case-analysis** (edge sign when the
  modulator is high vs low).
- **Gain changes & synergies (sign-only 2nd order)** — under a knockout/intervention the right panel
  adds a **Gain changes** section (couplings the `do()` determinately strengthens/weakens) and, for a
  joint multi-node `do()` that moves both a modulator and its edge's source, a **Synergies** section
  (super- vs sub-additive — synergistic/antagonistic). See `benchmarks/results/e9_modulation.md`.

## Live deployment

Deployed at **<https://bio2vec.net/physiomap/>** (served as static files by the
borg-server2 nginx that terminates `bio2vec.net`).

- Web root on borg-server2: `/var/www/physiomap/`.
- nginx: use [`deploy/nginx-physiomap-location.conf`](deploy/nginx-physiomap-location.conf).
  `gzip_static on` is required: without it the browser blocks on a multi-megabyte uncompressed
  model. `gzip on` also compresses the JavaScript/CSS, while `Cache-Control: no-cache` forces
  revalidation of stable artifact names after a deployment. Validate with `nginx -t` before
  reloading.
- **Redeploy** after a model change: regenerate and pass `web/export_data.py --check`, then rsync
  `index.html`, `editor.html`, the JS/CSS, `physiomap.json*`, `data/`, and `traces/` into the web
  root. Do not use `--delete`; archived `physiomap-*.json` snapshots are intentionally retained.
- Verify the public response has `Content-Encoding: gzip`, the compressed bootstrap is below
  200 kB, and the headless viewer smoke test reaches both a detail and intervention bucket.

## Notes

- Cytoscape.js is loaded from a CDN, so the first load needs internet; everything else is
  local (`physiomap.json`). To run fully offline, vendor `cytoscape.min.js` next to
  `index.html` and update the `<script src>` in `index.html`.
- YAML fixtures provide legacy provenance metadata during export, but the graph itself is loaded
  from `release/owl-scm/physiomap-scm.json`.
