"use strict";

const SIGN_COLOR = { "+": "#3fb950", "-": "#f85149", "?": "#8b949e" };
const SCALE_COLOR = {
  molecular: "#b083f0", subcellular: "#8957e5", cellular: "#3fb6d6",
  tissue: "#2f9e6f", organ: "#3fb950", organ_system: "#4493f8", organism: "#db6d28",
};
const OBO = new Set(["UBERON", "GO", "CL", "PATO", "CHEBI", "PR", "MONDO", "HP", "UO"]);

function iriLink(curie) {
  if (!curie) return null;
  const [pfx, id] = curie.split(":");
  if (OBO.has(pfx)) return `http://purl.obolibrary.org/obo/${pfx}_${id}`;
  return `https://www.ebi.ac.uk/ols4/search?q=${encodeURIComponent(curie)}`;
}

function palette(items) {
  const m = {};
  items.forEach((s, i) => {
    const h = Math.round((360 * i) / items.length);
    m[s] = `hsl(${h}, 55%, 55%)`;
  });
  return m;
}

let cy, DATA, SYS_COLOR, SRC_COLOR, currentLayout = "preset";

// Knockout API base. In production the viewer is served under /physiomap/ and nginx proxies
// /physiomap/api/ to the solver service; in local dev the service is on :8081. Override with ?api=.
const API_BASE = (() => {
  const q = new URLSearchParams(location.search).get("api");
  if (q) return q.replace(/\/$/, "");
  if (location.pathname.includes("/physiomap")) return "/physiomap/api";
  return "http://127.0.0.1:8081";
})();

// Lazy-loading element store: the full map (~1361 nodes) is NEVER all added to Cytoscape at
// once (that is what made load slow). We keep every element *descriptor* in JS and add only the
// nodes/edges of the currently-enabled systems into `cy`; toggling a group adds/removes its
// subgraph on demand. node id -> descriptor / system; edges as a flat descriptor list.
let NODE_ELEM = {}, NODE_SYS = {}, NODE_SRC = {}, EDGE_ELEMS = [], HAS_POSITIONS = false;

// search index + synonym maps (built from DATA in init); neighbourhood-focus state
let SEARCH_IDX = [], SURFACE_TO_CANON = {}, CANON_TO_SURFACES = {};
let FOCUS = null;   // { center, radius, ids:Set } when neighbourhood-focus is active, else null
let ADJ = null;     // lazily-built undirected adjacency over the FULL edge list (all systems)

// Load the default current map, or an archived snapshot via ?data=physiomap-<ver>-<date>.json
// (older snapshots remain displayable; init() degrades gracefully if newer fields are absent).
const DATA_URL = (() => {
  const q = new URLSearchParams(location.search).get("data");
  return q && /^physiomap[\w.-]*\.json$/.test(q) ? q : "physiomap.json";  // same-dir json only
})();

const PAYLOAD_CACHE = { details: new Map(), interventions: new Map() };

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function payloadUrl(template, bucket) {
  const path = template.replace("{bucket}", bucket);
  const stamp = DATA?.data_revision || DATA?.git_commit || DATA?.generated || "current";
  return `${path}${path.includes("?") ? "&" : "?"}v=${encodeURIComponent(stamp)}`;
}

function loadPayloadBucket(kind, bucket) {
  const cache = PAYLOAD_CACHE[kind];
  if (cache.has(bucket)) return cache.get(bucket);
  const template = DATA?.payloads?.[kind];
  if (!template) return Promise.resolve(null);  // legacy monolithic snapshots need no bucket
  const pending = fetchJson(payloadUrl(template, bucket)).catch(error => {
    cache.delete(bucket);  // a transient failure remains retryable
    throw error;
  });
  cache.set(bucket, pending);
  return pending;
}

// Populate the version picker from versions.json; switching reloads with ?data=<file>.
async function initVersionPicker() {
  const sel = document.getElementById("version-picker");
  if (!sel) return;
  let manifest;
  try { manifest = await fetchJson("versions.json"); }
  catch { sel.parentElement.style.display = "none"; return; }
  const current = new URLSearchParams(location.search).get("data") || "physiomap.json";
  const currentFile = manifest.versions.find(v => v.data_version === manifest.current)?.file;
  for (const v of manifest.versions) {
    const opt = document.createElement("option");
    const isLatest = v.data_version === manifest.current;
    opt.value = isLatest ? "physiomap.json" : v.file;
    opt.textContent = `${v.data_version}${v.status && v.status !== "latest" ? ` (${v.status})` : v.status === "latest" ? " (latest)" : ""}`;
    if (v.note) opt.title = v.note;
    if (opt.value === current || (current === "physiomap.json" && opt.value === "physiomap.json")) opt.selected = true;
    sel.appendChild(opt);
  }
  sel.addEventListener("change", () => {
    const file = sel.value;
    location.search = file === "physiomap.json" ? "" : `?data=${encodeURIComponent(file)}`;
  });
}

async function loadModel() {
  const status = document.getElementById("stats");
  status.textContent = "loading model…";
  initVersionPicker();
  try {
    init(await fetchJson(DATA_URL));
  } catch (error) {
    status.textContent = "model failed to load";
    const detail = document.getElementById("detail");
    detail.innerHTML = "";
    const message = document.createElement("div");
    message.className = "placeholder";
    message.textContent = `Could not load the PhysioMap data (${error.message}). Reload to retry.`;
    detail.appendChild(message);
  }
}

loadModel();

function init(data) {
  DATA = data;
  SYS_COLOR = palette(data.systems);
  SRC_COLOR = palette(data.sources || []);
  document.getElementById("stats").textContent =
    `${data.stats.n_nodes} nodes · ${data.stats.n_causal} causal edges · ` +
    `${data.stats.n_production || 0} production · ` +
    `${data.stats.n_constitutive} constitutive · ` +
    `${data.stats.n_quantitative || 0} quantitative · ` +
    `${data.stats.n_modulation || 0} modulation · ` +
    `whole-body SCC = ${data.stats.big_scc_size}`;
  const sccSummary = document.getElementById("about-scc-summary");
  if (sccSummary && Number.isInteger(data.stats.big_scc_size)) {
    sccSummary.textContent = `the largest ${data.stats.big_scc_size}-node homeostatic feedback core`;
  }

  // software (viewer/engine) and data (model release) versions are shown SEPARATELY;
  // older snapshots predate these fields, so fall back gracefully.
  const verEl = document.getElementById("version");
  if (verEl) {
    const sw = data.software_version ? `v${data.software_version}` : "";
    const dv = (data.data_version || data.version) ? `v${data.data_version || data.version}` : "";
    const date = data.generated || data.release_date || "";
    const parts = [];
    if (sw) parts.push(`viewer ${sw}`);
    if (dv) parts.push(`data ${dv}`);
    if (date) parts.push(date);
    if (DATA_URL !== "physiomap.json") parts.push("(archived snapshot)");
    verEl.textContent = parts.join(" · ");
    verEl.title = `PhysioMap viewer/software ${sw || "?"}, data/model ${dv || "?"}` +
      `${date ? `, generated ${date}` : ""}` +
      `${data.data_revision ? `, artifact ${data.data_revision}` : ""}` +
      `${data.git_commit ? `, commit ${data.git_commit}` : ""}`;
  }

  for (const n of data.nodes) {
    const sysColor = SYS_COLOR[n.system] || "#888";
    const elem = { data: { ...n, sysColor,
      scaleColor: SCALE_COLOR[n.scale] || "#888", base: sysColor } };
    if (typeof n.x === "number" && typeof n.y === "number") elem.position = { x: n.x, y: n.y };
    NODE_ELEM[n.id] = elem;
    NODE_SYS[n.id] = n.system;
    NODE_SRC[n.id] = n.source;
  }
  HAS_POSITIONS = data.nodes.some(n => typeof n.x === "number");
  if (!HAS_POSITIONS && currentLayout === "preset") currentLayout = "fcose";
  for (const e of data.causal_edges) {
    if (e.source === e.target) continue;  // self-loops are not drawn (Cytoscape can't render them)
    EDGE_ELEMS.push({ data: {
      id: e.id || `c:${e.source}->${e.target}:${e.sign}`, source: e.source, target: e.target,
      sign: e.sign, mechanism: e.mechanism, evidence: e.evidence,
      evidence_status: e.evidence_status, context: e.context, kind: "causal",
      definitional: e.definitional ? 1 : 0, modulated: e.modulated ? 1 : 0,
      prov_source: e.prov_source, influence_id: e.id,
      detail_kind: "causal", detail_id: e.id, detail_bucket: e._detail_bucket,
      projection_pattern: e.projection_pattern, projection_entailment: e.projection_entailment,
      structural_interpretation: e.structural_interpretation, color: SIGN_COLOR[e.sign] } });
  }
  for (const e of (data.production_edges || [])) {
    EDGE_ELEMS.push({ data: {
      id: e.id || `p:${e.source}->${e.target}:${e.sign}`,
      source: e.source, target: e.target, sign: e.sign,
      mechanism: e.mechanism, evidence: e.evidence,
      production_evidence: e.production_evidence,
      evidence_status: e.evidence_status, kind: "production",
      detail_kind: "production", detail_id: e.id, detail_bucket: e._detail_bucket,
      prov_source: e.prov_source, projection_pattern: e.projection_pattern,
      projection_entailment: e.projection_entailment,
      structural_interpretation: e.structural_interpretation, color: "#39c5bb" } });
  }
  for (const e of data.constitutive_edges) {
    EDGE_ELEMS.push({ data: {
      id: `k:${e.micro}->${e.macro}`, source: e.micro, target: e.macro,
      sign: e.sign, relation: e.relation, kind: "constitutive", color: "#d29922" } });
  }
  // Typed quantitative identities are rendered as one explicitly tagged derivative edge
  // per argument. They are not authored causal influences.
  for (const q of (data.quantitative_definitions || [])) {
    (q.arguments || []).forEach((a, i) => EDGE_ELEMS.push({ data: {
      id: `q:${q.id}:${i}`, source: a.node, target: q.result,
      sign: a.derivative_sign, kind: "quantitative",
      quantitative_id: q.id, quantitative_kind: q.kind, origin: q.origin,
      role: a.role, mechanism: q.mechanism, evidence: q.evidence,
      detail_kind: "quantitative", detail_id: q.id, detail_bucket: q._detail_bucket,
      prov_source: q.prov_source, projection_pattern: q.projection_pattern,
      projection_entailment: q.projection_entailment,
      structural_interpretation: q.structural_interpretation, color: "#58a6ff" } }));
  }
  // modulation (multiplicative / gain) edges: modulator scales the strength of edge_source->edge_target.
  // Drawn modulator -> edge_target (alongside the edge's first-order shadow), purple + dashed.
  for (const e of (data.modulation_edges || [])) {
    EDGE_ELEMS.push({ data: {
      id: e.id || `m:${e.modulator}=>${e.edge_source}->${e.edge_target}:${e.sign}`,
      source: e.modulator, target: e.edge_target, sign: e.sign, kind: "modulation",
      edge_source: e.edge_source, edge_target: e.edge_target, modulator: e.modulator,
      can_flip_sign: e.can_flip_sign ? 1 : 0, mechanism: e.mechanism, evidence: e.evidence,
      interaction_sign: e.interaction_sign, regime: e.regime, prov_source: e.prov_source,
      detail_kind: "modulation", detail_id: e.id, detail_bucket: e._detail_bucket,
      influence_id: e.influence_id, projection_pattern: e.projection_pattern,
      color: "#d2a8ff" } });
  }

  cy = cytoscape({
    container: document.getElementById("cy"),
    elements: [],  // start empty; syncGraph() adds the enabled (core) systems below
    wheelSensitivity: 0.2,
    style: [
      { selector: "node", style: {
        "background-color": "data(base)", label: "data(label)",
        color: "#e6edf3", "font-size": 9, "text-wrap": "wrap", "text-max-width": 90,
        "text-valign": "center", "text-halign": "center", width: 26, height: 26,
        "border-width": 2, "border-color": "#0d1117", "text-outline-width": 2,
        "text-outline-color": "#0d1117" } },
      { selector: "node[scale = 'subcellular'], node[scale='molecular'], node[scale='cellular']",
        style: { shape: "diamond" } },
      { selector: "edge", style: {
        width: 2, "line-color": "data(color)", "target-arrow-color": "data(color)",
        "target-arrow-shape": "triangle", "curve-style": "bezier",
        "arrow-scale": 0.9, opacity: 0.85 } },
      { selector: "edge[kind = 'constitutive']", style: {
        "line-style": "dashed", width: 3, "target-arrow-shape": "diamond" } },
      { selector: "edge[kind = 'production']", style: {
        "line-style": "dotted", width: 2.5, "target-arrow-shape": "triangle" } },
      { selector: "edge[kind = 'quantitative']", style: {
        "line-style": "dotted", width: 2.5, "target-arrow-shape": "tee",
        label: "=", "font-size": 11, color: "#58a6ff", "text-outline-width": 2,
        "text-outline-color": "#0d1117" } },
      { selector: "edge[kind = 'modulation']", style: {       // multiplicative gain edge
        "line-style": "dashed", "line-color": "#d2a8ff", "target-arrow-color": "#d2a8ff",
        width: 2, "target-arrow-shape": "circle", "line-dash-pattern": [3, 3],
        label: "×", "font-size": 13, color: "#d2a8ff", "text-outline-width": 2,
        "text-outline-color": "#0d1117" } },
      { selector: "edge[definitional = 1]", style: {
        "line-style": "dotted", width: 3 } },  // algebraic identity (e.g. MAP = CO x TPR)
      // a causal edge that carries a multiplicative gain: purple ⊗ dot mid-edge so the figure
      // shows *which* edges are modulated at a glance (not only on click).
      { selector: "edge[modulated = 1]", style: {
        "mid-target-arrow-shape": "circle", "mid-target-arrow-color": "#d2a8ff",
        "mid-target-arrow-fill": "filled" } },
      { selector: ".hidden", style: { display: "none" } },
      { selector: ".faded", style: { opacity: 0.08 } },
      { selector: ".scc-hi", style: { "border-color": "#d29922", "border-width": 4 } },
      { selector: "node.sel", style: { "border-color": "#4493f8", "border-width": 5 } },
      { selector: ".pred-up", style: { "background-color": "#3fb950" } },
      { selector: ".pred-down", style: { "background-color": "#f85149" } },
      { selector: ".pred-amb", style: { "background-color": "#8b949e" } },
      { selector: ".pred-none", style: { "background-color": "#2d333b" } },
      { selector: ".pred-do", style: { "border-color": "#4493f8", "border-width": 6,
        "background-color": "#4493f8" } },
      // when a modulation (gain) edge is selected, light up the edge it modulates + its endpoints
      { selector: "edge.modul-hi", style: { "line-color": "#d2a8ff",
        "target-arrow-color": "#d2a8ff", width: 5, opacity: 1, "z-index": 9999 } },
      { selector: "node.modul-hi", style: { "border-color": "#d2a8ff", "border-width": 5 } },
    ],
    layout: { name: currentLayout, animate: false },
  });

  cy.on("tap", "node", e => showNode(e.target));
  cy.on("tap", "edge", e => showEdge(e.target));
  cy.on("tap", e => {
    if (e.target === cy) { DETAIL_REQUEST++; cy.elements().removeClass("sel modul-hi"); }
  });

  buildSynonyms();
  buildSearchIndex();
  buildFacets();
  buildInterventions();
  buildKnockoutList();
  wireControls();
  syncGraph();      // add only the enabled (core) systems — the big groups stay out until toggled
  runLayout();      // lay out the core (~276 nodes)
  runLazyPayloadSmokeScenario();
}

// Release-gate hook: exercise one detail bucket and one intervention bucket in a real browser.
// It runs only for the explicit smoke-test query and has no effect on the public viewer.
async function runLazyPayloadSmokeScenario() {
  if (new URLSearchParams(location.search).get("smoke") !== "lazy-payloads") return;
  const marker = document.getElementById("stats");
  try {
    const search = document.getElementById("search");
    search.value = "PATO:0000033";
    runSearch();
    if (!document.querySelector("#search-results .r")) {
      throw new Error("ontology-aware bootstrap search returned no result");
    }
    marker.dataset.ontologySearchSmoke = "ready";
    const node = cy.getElementById("mean_arterial_pressure");
    if (node.empty()) throw new Error("smoke-test node is not visible");
    await hydrateElementDetails(node, "node");
    showNode(node);
    if (!document.getElementById("detail").textContent.includes("OWL trait:")) {
      throw new Error("hydrated node detail is missing its OWL trait");
    }
    marker.dataset.lazyDetailSmoke = "ready";
    const select = document.getElementById("intervention");
    select.value = "hyperinsulinemia";
    await applyOverlay(select.value);
    marker.dataset.lazyPayloadSmoke = "ready";
  } catch (error) {
    marker.dataset.lazyPayloadSmoke = `failed: ${error.message}`;
  }
}

// Lay out whatever is currently in the graph. 'preset' uses the precomputed coordinates shipped
// in the JSON (instant — no force-directed pass, the fix for slow big-group toggles); 'fcose' is
// the fast in-browser force layout for ad-hoc re-layout; the rest are Cytoscape built-ins.
function runLayout() {
  if (cy.elements().empty()) return;
  let opts;
  if (currentLayout === "preset") {
    // nodes already carry positions from cy.add(); just fit the viewport (instant)
    opts = { name: "preset", animate: false, fit: true, padding: 30 };
  } else if (currentLayout === "fcose") {
    opts = { name: "fcose", animate: false, quality: "default", randomize: false,
      nodeRepulsion: 9000, idealEdgeLength: 80, nodeSeparation: 80, padding: 30 };
  } else {
    opts = { name: currentLayout, animate: false, nodeRepulsion: 9000,
      idealEdgeLength: 80, padding: 30, concentric: n => n.degree(), levelWidth: () => 2 };
  }
  cy.layout(opts).run();
}

// Sync the graph to contain EXACTLY the nodes whose system is enabled (+ edges with both
// endpoints present). Adds/removes on demand so the heavy gap-fill / textbook groups are never
// built until the user ticks them. This is what keeps initial load fast.
function syncGraph() {
  // In neighbourhood-focus mode the displayed set is FOCUS.ids (across all facets); otherwise a
  // node shows iff BOTH its system AND its source facet are enabled. `want(id)` is that predicate.
  const sysOn = FOCUS ? null : systemEnabled();
  const srcOn = FOCUS ? null : sourceEnabled();
  const showConst = document.getElementById("show-constitutive").checked;
  const showQuant = document.getElementById("show-quantitative").checked;
  const showModul = document.getElementById("show-modulation").checked;
  // Provenance pull: an edge whose PROVENANCE source is enabled reveals its endpoint nodes, so a
  // curator's contribution (e.g. Gkoutos edges into pre-existing Guyton nodes) shows under their
  // source facet — not only their net-new nodes. Gated to NON-draft endpoints (a node whose own
  // source is default-hidden is never pulled in) so enabling a core source can't drag the large
  // draft groups (HPO gap-fill, textbook imports) into view.
  const hiddenSrc = new Set(DATA.default_hidden_sources || []);
  const pulled = new Set();
  if (!FOCUS) {
    for (const e of EDGE_ELEMS) {
      if (e.data.kind === "constitutive" && !showConst) continue;
      if (e.data.kind === "quantitative" && !showQuant) continue;
      if (e.data.kind === "modulation" && !showModul) continue;
      if (!e.data.prov_source || !srcOn[e.data.prov_source]) continue;
      for (const ep of [e.data.source, e.data.target]) {
        if (!!sysOn[NODE_SYS[ep]] && !hiddenSrc.has(NODE_SRC[ep])) pulled.add(ep);
      }
    }
  }
  const want = id => FOCUS ? FOCUS.ids.has(id)
    : (!!sysOn[NODE_SYS[id]] && (!!srcOn[NODE_SRC[id]] || pulled.has(id)));
  cy.batch(() => {
    // nodes: remove unwanted, add missing
    const remove = cy.nodes().filter(n => !want(n.id()));
    if (remove.nonempty()) cy.remove(remove);  // also removes their connected edges
    const addN = [];
    for (const id in NODE_ELEM) {
      if (want(id) && cy.getElementById(id).empty()) addN.push(NODE_ELEM[id]);
    }
    if (addN.length) cy.add(addN);
    // edges: present iff both endpoints loaded (+ per-kind toggle)
    const addE = [];
    for (const e of EDGE_ELEMS) {
      const ok = want(e.data.source) && want(e.data.target)
        && !(e.data.kind === "constitutive" && !showConst)
        && !(e.data.kind === "quantitative" && !showQuant)
        && !(e.data.kind === "modulation" && !showModul);
      const exists = !cy.getElementById(e.data.id).empty();
      if (ok && !exists) addE.push(e);
      else if (!ok && exists) cy.remove(cy.getElementById(e.data.id));
    }
    if (addE.length) cy.add(addE);
  });
  colorMode();  // newly-added nodes get the current colouring
}

// Sync + re-layout. Used by every control that changes what is shown.
function refresh() {
  syncGraph();
  runLayout();
  const iv = document.getElementById("intervention").value;
  if (iv) applyOverlay(iv);  // re-apply an active intervention overlay to any newly-added nodes
}

function colorMode() {
  const byScale = document.getElementById("color-by-scale").checked;
  cy.nodes().forEach(n => n.data("base", byScale ? n.data("scaleColor") : n.data("sysColor")));
}

function sysId(i) { return "sys_" + i; }  // index-based id (system names contain non-Latin1 chars)

function srcId(i) { return "src_" + i; }  // index-based id (source names contain non-Latin1 chars)

// Two orthogonal facet filters. SYSTEM = the physiological system a node belongs to (what it is);
// SOURCE = the fragment/evidence it was introduced by (where it came from). A node is shown iff
// BOTH facets are enabled (see syncGraph). Draft textbook/HPO imports are off by default via the
// SOURCE facet — not by misfiling them under a fake "system".
function buildFacets() {
  const sbox = document.getElementById("systems");
  sbox.innerHTML = "";
  DATA.systems.forEach((s, i) => {
    const row = document.createElement("label");
    row.innerHTML = `<input type="checkbox" id="${sysId(i)}" checked />
      <span class="swatch" style="background:${SYS_COLOR[s]}"></span>${s}`;
    sbox.appendChild(row);
    row.querySelector("input").addEventListener("change", refresh);
  });
  const cbox = document.getElementById("sources");
  cbox.innerHTML = "";
  const hidden = new Set(DATA.default_hidden_sources || []);  // draft/coverage imports off by default
  // per-source footprint: nodes + causal edges + gain edges introduced by each source. This is what
  // makes a curator's full contribution legible (e.g. Gkoutos = 2 nodes but also 3 edges + 1 gain),
  // not just their net-new node count.
  const cnt = {};
  const bump = (src, key) => { if (!src || !key) return; (cnt[src] = cnt[src] || { n: 0, e: 0, q: 0, g: 0 })[key]++; };
  for (const id in NODE_SRC) bump(NODE_SRC[id], "n");
  for (const e of EDGE_ELEMS) bump(e.data.prov_source,
    e.data.kind === "modulation" ? "g" :
      (e.data.kind === "quantitative" ? "q" : (e.data.kind === "causal" ? "e" : null)));
  (DATA.sources || []).forEach((s, i) => {
    const off = hidden.has(s);
    const c = cnt[s] || { n: 0, e: 0, q: 0, g: 0 };
    const parts = [c.n ? `${c.n}n` : "", c.e ? `${c.e}e` : "",
      c.q ? `${c.q}q` : "", c.g ? `${c.g}g` : ""].filter(Boolean);
    const tag = parts.length ? ` <span class="muted" style="font-size:10px">(${parts.join(" · ")})</span>` : "";
    const row = document.createElement("label");
    row.innerHTML = `<input type="checkbox" id="${srcId(i)}" ${off ? "" : "checked"} />
      <span class="swatch" style="background:${SRC_COLOR[s]}"></span>${s}${tag}` +
      (off ? ` <em style="opacity:.55;font-size:11px">(off)</em>` : "");
    cbox.appendChild(row);
    row.querySelector("input").addEventListener("change", refresh);
  });
}

function sourceEnabled() {
  const on = {};
  (DATA.sources || []).forEach((s, i) => {
    const b = document.getElementById(srcId(i));
    on[s] = b ? b.checked : true;
  });
  return on;
}

function toggleSrc(on) {
  (DATA.sources || []).forEach((s, i) => {
    const b = document.getElementById(srcId(i));
    if (b) b.checked = on;
  });
  refresh();
}

function systemEnabled() {
  const on = {};
  DATA.systems.forEach((s, i) => { on[s] = document.getElementById(sysId(i)).checked; });
  return on;
}


// ---- Search: ranked, over ALL nodes (incl. hidden groups), synonym- and ontology-aware ----

function normQ(s) { return (s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(); }

function buildSynonyms() {
  // DATA.synonyms: canonical phrase -> [surface variants]. Build the bidirectional normalized
  // maps so the query "MAP" expands to "mean arterial pressure" (and vice versa) for matching.
  SURFACE_TO_CANON = {}; CANON_TO_SURFACES = {};
  const syn = DATA.synonyms || {};
  for (const canon in syn) {
    const cn = normQ(canon);
    const surfaces = [cn, ...(syn[canon] || []).map(normQ)].filter(Boolean);
    CANON_TO_SURFACES[cn] = surfaces;
    for (const s of surfaces) SURFACE_TO_CANON[s] = cn;
  }
}

function buildSearchIndex() {
  SEARCH_IDX = DATA.nodes.map(n => ({
    id: n.id, label: n.label, system: n.system, source: n.source, scale: n.scale,
    nid: normQ(n.id), nlab: normQ(n.label),
    ent: (n.entity_iri || "").toLowerCase(), qual: (n.quality_iri || "").toLowerCase(),
  }));
  const tot = document.getElementById("search-total");
  if (tot) tot.textContent = SEARCH_IDX.length;
}

function expandSynonyms(qn) {
  // all surface forms that share qn's canonical (empty if qn is not a known synonym/abbreviation)
  const canon = SURFACE_TO_CANON[qn];
  return canon ? CANON_TO_SURFACES[canon] : [];
}

function scoreNode(n, qn, exps) {
  if (n.nlab === qn || n.nid === qn) return 100;
  if (n.nlab.startsWith(qn) || n.nid.startsWith(qn)) return 80;
  for (const e of exps) if (n.nlab === e) return 78;
  if (qn.length >= 2 && (n.nlab.includes(qn) || n.nid.includes(qn))) return 60;
  for (const e of exps) if (e.length >= 3 && n.nlab.includes(e)) return 55;
  return 0;
}

function runSearch() {
  const raw = document.getElementById("search").value.trim();
  const box = document.getElementById("search-results");
  if (!raw) { box.className = "results"; box.innerHTML = ""; return; }
  let scored;
  if (/^[A-Za-z]+:\S*$/.test(raw)) {
    // ontology IRI facet, e.g. "PATO:0000033" or just "CHEBI:" — prefix match on entity/quality
    const q = raw.toLowerCase();
    scored = SEARCH_IDX
      .filter(n => n.ent.startsWith(q) || n.qual.startsWith(q))
      .map(n => ({ n, s: 50 }));
  } else {
    const qn = normQ(raw);
    const exps = expandSynonyms(qn);
    scored = [];
    for (const n of SEARCH_IDX) { const s = scoreNode(n, qn, exps); if (s > 0) scored.push({ n, s }); }
    scored.sort((a, b) => b.s - a.s || a.n.label.length - b.n.label.length);
  }
  renderSearchResults(scored, raw);
}

function renderSearchResults(scored, raw) {
  const box = document.getElementById("search-results");
  box.className = "results open";
  if (!scored.length) { box.innerHTML = `<div class="none">no node matches “${raw}”.</div>`; return; }
  const top = scored.slice(0, 12);
  box.innerHTML = top.map(({ n }) =>
    `<button class="r" data-id="${n.id}">` +
    `<div class="rl"><span class="sw" style="background:${SYS_COLOR[n.system] || "#888"}"></span>${n.label}</div>` +
    `<div class="rm">${n.system} · ${n.scale} · <i>${n.source || "?"}</i></div></button>`
  ).join("") + (scored.length > top.length ? `<div class="more">+${scored.length - top.length} more — refine the query</div>` : "");
  box.querySelectorAll(".r").forEach(b =>
    b.addEventListener("click", () => { gotoNode(b.dataset.id); box.className = "results"; }));
}

// Reveal a node (exiting focus or enabling its hidden system as needed), centre + select + detail.
function gotoNode(id) {
  focusNode(id);
  const n = cy.getElementById(id);
  if (n.nonempty()) showNode(n);
}

// ---- Neighbourhood (ego-graph) focus: isolate a node's N-hop causal neighbourhood ----

function buildAdjacency() {
  if (ADJ) return ADJ;
  ADJ = {};
  const link = (a, b) => {
    (ADJ[a] = ADJ[a] || new Set()).add(b);
    (ADJ[b] = ADJ[b] || new Set()).add(a);
  };
  for (const e of EDGE_ELEMS) link(e.data.source, e.data.target);  // full graph, all systems
  return ADJ;
}

function neighbourhood(center, radius) {
  const adj = buildAdjacency();
  const seen = new Set([center]);
  let frontier = [center];
  for (let r = 0; r < radius; r++) {
    const next = [];
    for (const u of frontier) for (const v of (adj[u] || [])) {
      if (!seen.has(v)) { seen.add(v); next.push(v); }
    }
    frontier = next;
  }
  return seen;
}

function focusNeighbourhood(center, radius) {
  if (!NODE_ELEM[center]) return;
  FOCUS = { center, radius, ids: neighbourhood(center, radius) };
  syncGraph();
  // local force layout (the global preset coords would scatter the neighbourhood across the canvas)
  cy.layout({ name: "fcose", animate: false, randomize: true, quality: "default",
    nodeRepulsion: 9000, idealEdgeLength: 80, nodeSeparation: 80, padding: 30 }).run();
  const n = cy.getElementById(center);
  if (n.nonempty()) { cy.elements().removeClass("sel"); n.addClass("sel"); }
  const iv = document.getElementById("intervention").value;
  if (iv) applyOverlay(iv);
  updateFocusStatus();
}

function exitFocus() {
  if (!FOCUS) return;
  FOCUS = null;
  refresh();
  updateFocusStatus();
}

function updateFocusStatus() {
  const s = document.getElementById("focus-status");
  const ex = document.getElementById("focus-exit");
  if (FOCUS) {
    s.textContent = `Focused on ${labelOf(FOCUS.center)} · ${FOCUS.ids.size} nodes ≤ ${FOCUS.radius} hop(s) (system filters paused)`;
    ex.style.display = "inline-block";
  } else { s.textContent = ""; ex.style.display = "none"; }
}

function buildInterventions() {
  const sel = document.getElementById("intervention");
  (DATA.interventions || []).forEach(iv => {
    const o = document.createElement("option");
    o.value = iv.id; o.textContent = `${iv.label}`;
    sel.appendChild(o);
  });
}

async function loadIntervention(indexRecord) {
  if (indexRecord.predicted) return indexRecord;  // backward-compatible archived snapshot
  const bucket = indexRecord._intervention_bucket;
  if (!bucket) throw new Error("intervention payload location is missing");
  const payload = await loadPayloadBucket("interventions", bucket);
  const record = payload?.interventions?.[indexRecord.id];
  if (!record) throw new Error(`intervention ${indexRecord.id} is missing from bucket ${bucket}`);
  return { ...indexRecord, ...record };
}

let OVERLAY_REQUEST = 0;

async function applyOverlay(ivId) {
  const request = ++OVERLAY_REQUEST;
  const legend = document.getElementById("overlay-legend");
  const info = document.getElementById("intervention-info");
  cy.nodes().removeClass("pred-up pred-down pred-amb pred-none pred-do");
  if (!ivId) { legend.style.display = "none"; info.textContent = ""; colorMode(); return; }
  const indexRecord = DATA.interventions.find(i => i.id === ivId);
  if (!indexRecord) { info.textContent = "intervention not found"; return; }
  info.textContent = "loading intervention…";
  let iv;
  try {
    iv = await loadIntervention(indexRecord);
  } catch (error) {
    if (request === OVERLAY_REQUEST) info.textContent = `intervention failed to load: ${error.message}`;
    return;
  }
  if (request !== OVERLAY_REQUEST || document.getElementById("intervention").value !== ivId) return;
  const doTxt = Object.entries(iv.do).map(([k, v]) => `do(${(iv.do_labels || {})[k] || k} = ${v})`).join(", ");
  const contextTxt = iv.contexts?.length ? ` · context: ${iv.contexts.join(", ")}` : "";
  info.innerHTML = `<b>${doTxt}</b> · benchmark: ${iv.benchmark}${contextTxt}`;
  applyPredictionOverlay(iv.predicted, iv.do);
  // same derived-phenotype panel the dynamic knockout shows, on the right
  renderPhenotypePanel({
    title: "Intervention overlay", doMap: iv.do, doLabels: iv.do_labels,
    phenotypes: iv.phenotypes, affected: iv.affected,
    gainChanges: iv.gain_changes, synergies: iv.synergies, traces: iv.traces,
    meta: `<span class="badge">benchmark: ${iv.benchmark}</span>`,
    note: "Comparative-statics steady-state signs predicted for this benchmark intervention. " +
          "Determinate (↑/↓) predictions are sound; reachable traits with an ambiguous net direction are “affected”.",
  });
}

function signSpan(s) {
  const cls = s === "+" ? "plus" : s === "-" ? "minus" : "unknown";
  const t = s === "+" ? "+" : s === "-" ? "−" : "?";
  return `<span class="sign ${cls}">${t}</span>`;
}

let DETAIL_REQUEST = 0;

async function hydrateElementDetails(element, defaultKind) {
  const data = element.data();
  const bucket = data.detail_bucket || data._detail_bucket;
  if (!bucket || data._details_loaded) return false;
  const kind = data.detail_kind || defaultKind;
  const identifier = data.detail_id || data.id;
  const payload = await loadPayloadBucket("details", bucket);
  const details = payload?.records?.[`${kind}:${identifier}`];
  if (!details) throw new Error(`${kind} ${identifier} is missing from detail bucket ${bucket}`);
  for (const [key, value] of Object.entries(details)) element.data(key, value);
  element.data("_details_loaded", 1);
  return true;
}

function detailLoadingHtml(data) {
  return (data.detail_bucket || data._detail_bucket) && !data._details_loaded
    ? `<p class="small muted">Loading ontology, evidence, and projection details…</p>` : "";
}

function reportDetailLoadError(request, error) {
  if (request !== DETAIL_REQUEST) return;
  const message = document.createElement("p");
  message.className = "small";
  message.textContent = `Details failed to load (${error.message}). Click again to retry.`;
  document.getElementById("detail").appendChild(message);
}

function showNode(n) {
  const request = ++DETAIL_REQUEST;
  cy.elements().removeClass("sel modul-hi"); n.addClass("sel");
  const d = n.data();
  const ent = iriLink(d.entity_iri), q = iriLink(d.quality_iri);
  let html = `<h2>${d.label}</h2>`;
  html += `<div><span class="badge" title="physiological system">${d.system}</span>` +
    `<span class="badge" title="source / evidence">src: ${d.source || "?"}</span>` +
    `<span class="badge">scale: ${d.scale}</span>`;
  html += d.in_big_scc ? `<span class="badge">whole-body SCC</span>` : `<span class="badge">SCC #${d.scc}</span>`;
  html += `</div><div class="small">id: <code>${d.id}</code></div>`;
  html += `<button class="btn-inline focus-btn" data-node="${d.id}" style="margin:6px 0">⊙ focus neighbourhood</button>`;
  if (d.entity_iri) html += `<div class="small">entity: <a href="${ent}" target="_blank">${d.entity_iri}</a></div>`;
  if (d.quality_iri) html += `<div class="small">quality: <a href="${q}" target="_blank">${d.quality_iri}</a></div>`;
  if (d.trait_iri) html += `<div class="small">OWL trait: <code>${d.trait_iri}</code></div>`;
  if (d.migration_status) html += `<div class="small">migration: <b>${d.migration_status}</b> · satisfiable: ${d.satisfiable}</div>`;
  if (d.verified_terms?.length) html += `<div class="small">verified terms: ${d.verified_terms.join(", ")}</div>`;
  if (d.asserted_axioms?.length) html += `<details><summary class="small">asserted OWL axioms</summary><code class="small">${d.asserted_axioms.join("<br>")}</code></details>`;

  const outs = n.outgoers("edge"), ins = n.incomers("edge");
  html += `<h3 style="margin:12px 0 2px;font-size:13px">outgoing relations →</h3>`;
  outs.forEach(e => html += edgeRow(e, e.target().data("label"), true));
  html += `<h3 style="margin:12px 0 2px;font-size:13px">← incoming relations</h3>`;
  ins.forEach(e => html += edgeRow(e, e.source().data("label"), false));
  html += detailLoadingHtml(d);
  document.getElementById("detail").innerHTML = html;
  hydrateElementDetails(n, "node").then(changed => {
    if (changed && request === DETAIL_REQUEST && n.hasClass("sel")) showNode(n);
  }).catch(error => reportDetailLoadError(request, error));
}

function edgeRow(e, other, out) {
  const d = e.data();
  const kind = d.kind === "constitutive" ? " <i>(constitutive)</i>"
    : (d.kind === "production" ? " <i>(production)</i>"
      : (d.kind === "quantitative" ? ` <i>(${d.quantitative_kind} identity)</i>` : ""));
  let r = `<div class="edge">${signSpan(d.sign)} ${out ? "" : ""}<b>${other}</b>${kind}`;
  if (d.mechanism) r += `<div class="small">${d.mechanism}</div>`;
  if (d.evidence) r += `<div class="small">▪ ${d.evidence}</div>`;
  return r + `</div>`;
}

function showEdge(e) {
  const request = ++DETAIL_REQUEST;
  const d = e.data();
  if (d.kind === "modulation") return showModulation(e, request);
  cy.elements().removeClass("modul-hi");
  const s = cy.getElementById(d.source).data("label");
  const t = cy.getElementById(d.target).data("label");
  let html = `<h2>${s} ${signSpan(d.sign)}→ ${t}</h2>`;
  html += `<div><span class="badge">${d.kind}</span>`;
  if (d.definitional) html += `<span class="badge">definitional (algebraic identity)</span>`;
  if (d.prov_source) html += `<span class="badge" title="curator / fragment that introduced this edge">added by: ${d.prov_source}</span>`;
  html += `</div>`;
  if (d.mechanism) html += `<p>${d.mechanism}</p>`;
  if (d.context) html += `<p class="small"><b>Context:</b> ${d.context}</p>`;
  if (d.evidence_status) html += `<p class="small"><b>Evidence status:</b> ${d.evidence_status}</p>`;
  if (d.production_evidence) html += `<p class="small"><b>Production evidence:</b> ${d.production_evidence}</p>`;
  if (d.quantitative_id) html += `<p class="small"><b>Quantitative definition:</b> <code>${d.quantitative_id}</code> · ${d.quantitative_kind} · ${d.origin}; argument role: ${d.role}</p>`;
  if (d.evidence) html += `<p class="small">Evidence: ${d.evidence}</p>`;
  if (d.relation) html += `<p class="small">relation: ${d.relation}</p>`;
  if (d.influence_id) html += `<p class="small">influence: <code>${d.influence_id}</code></p>`;
  if (d.projection_pattern) html += `<p class="small">projection: <b>${d.projection_pattern}</b> · ${d.structural_interpretation || ""}</p>`;
  if (d.projection_entailment) html += `<details><summary class="small">OWL entailment witness</summary><code class="small">${d.projection_entailment}</code></details>`;
  // gains acting on this causal edge (the ⊗ mid-edge dot) — name the modulators
  if (d.modulated) {
    const mods = EDGE_ELEMS.filter(x => x.data.kind === "modulation"
      && x.data.edge_source === d.source && x.data.edge_target === d.target);
    if (mods.length) {
      html += `<h3 style="margin:12px 0 2px;font-size:13px">Modulated by (gain)</h3>`;
      for (const m of mods) {
        const verb = m.data.sign === "+" ? "amplifies" : m.data.sign === "-" ? "dampens" : "modulates";
        html += `<div class="edge">${signSpan(m.data.sign)}⊗ <b>${labelOf(m.data.modulator)}</b> ` +
          `<i>${verb} this edge</i>${m.data.can_flip_sign ? ` <span class="badge">can flip sign</span>` : ""}</div>`;
      }
    }
  }
  html += detailLoadingHtml(d);
  document.getElementById("detail").innerHTML = html;
  hydrateElementDetails(e, d.detail_kind || d.kind).then(changed => {
    if (changed && request === DETAIL_REQUEST) showEdge(e);
  }).catch(error => reportDetailLoadError(request, error));
}

function showModulation(e, request) {
  const d = e.data();
  const lab = id => { const n = cy.getElementById(id); return n.empty() ? id : n.data("label"); };
  const verb = d.sign === "+" ? "amplifies" : d.sign === "-" ? "dampens" : "modulates";
  // a modulation acts on the S->T *edge*, not just on T — light that edge (+ its endpoints) up.
  cy.elements().removeClass("modul-hi");
  const modEdge = cy.edges().filter(x =>
    x.data("kind") === "causal" && x.data("source") === d.edge_source
    && x.data("target") === d.edge_target);
  modEdge.addClass("modul-hi");
  cy.getElementById(d.edge_source).addClass("modul-hi");
  cy.getElementById(d.edge_target).addClass("modul-hi");
  const onGraph = modEdge.nonempty() && !modEdge.hasClass("hidden");
  let html = `<h2>${lab(d.modulator)} ${signSpan(d.sign)}⊗ gain of (${lab(d.edge_source)} → ${lab(d.edge_target)})</h2>`;
  html += `<div><span class="badge">modulation (multiplicative / gain)</span>`;
  if (d.can_flip_sign) html += `<span class="badge">can flip sign</span>`;
  if (d.prov_source) html += `<span class="badge" title="curator / fragment that introduced this gain">added by: ${d.prov_source}</span>`;
  html += `</div>`;
  if (d.influence_id) html += `<p class="small">targets SCM influence <code>${d.influence_id}</code> via ${d.projection_pattern || "projection"}</p>`;
  html += `<p>A <b>gain</b> edge: raising <b>${lab(d.modulator)}</b> ${verb} the strength of the ` +
    `<b>${lab(d.edge_source)}&nbsp;→&nbsp;${lab(d.edge_target)}</b> edge — it scales how strongly ` +
    `${lab(d.edge_source)} drives ${lab(d.edge_target)}, rather than adding to ${lab(d.edge_target)} on its own. ` +
    `Formally the sign of the interaction ∂²(${lab(d.edge_target)})/∂(${lab(d.edge_source)})∂(${lab(d.modulator)}).</p>`;
  // intrinsic interaction sign iota = mu . sigma (sign-only 2nd-order content) + sign-flip regimes
  if (d.interaction_sign) {
    const it = d.interaction_sign === "+" ? "amplifies (steeper response)"
      : d.interaction_sign === "-" ? "dampens (shallower response, toward reversal)"
      : "interaction direction undetermined";
    html += `<p class="small"><b>Interaction sign</b> ${signSpan(d.interaction_sign)} (ι = modulation × base-edge): ` +
      `raising ${lab(d.modulator)} <b>${it}</b> — a qualitative (sign-only) second-derivative fact.</p>`;
  }
  if (d.regime) {
    html += `<p class="small"><b>Sign-flipping gain</b> — the edge sign is context-dependent, so ` +
      `unconditionally it is <b>?</b>. Conditional on the modulator's regime:<br>` +
      `&nbsp;• ${lab(d.modulator)} high ⇒ ${lab(d.edge_source)}→${lab(d.edge_target)} is ${signSpan(d.regime.modulator_high)}<br>` +
      `&nbsp;• ${lab(d.modulator)} low ⇒ ${lab(d.edge_source)}→${lab(d.edge_target)} is ${signSpan(d.regime.modulator_low)}<br>` +
      `<i class="muted">(the threshold itself is quantitative and deliberately unlocated)</i></p>`;
  }
  html += onGraph
    ? `<p class="small">The modulated <b>${lab(d.edge_source)} → ${lab(d.edge_target)}</b> edge is highlighted in the graph.</p>`
    : `<p class="small">The modulated <b>${lab(d.edge_source)} → ${lab(d.edge_target)}</b> edge is on a layer that is currently hidden.</p>`;
  if (d.mechanism) html += `<p>${d.mechanism}</p>`;
  if (d.evidence) html += `<p class="small">Evidence: ${d.evidence}</p>`;
  html += detailLoadingHtml(d);
  document.getElementById("detail").innerHTML = html;
  hydrateElementDetails(e, "modulation").then(changed => {
    if (changed && request === DETAIL_REQUEST) showEdge(e);
  }).catch(error => reportDetailLoadError(request, error));
}

// ---- Synthetic knockout (dynamic): clamp any node via the solver service, derive phenotypes ----

let LABEL_TO_ID = {};
let KO_TARGETS = {};   // multi-node clamp set: node id -> "+"/"-" (added via the ＋ add button)

function buildKnockoutList() {
  const dl = document.getElementById("ko-nodelist");
  if (!dl) return;
  DATA.nodes.forEach(n => {
    LABEL_TO_ID[n.label.toLowerCase()] = n.id;
    LABEL_TO_ID[n.id.toLowerCase()] = n.id;
    const o = document.createElement("option");
    o.value = n.id; o.label = n.label;
    dl.appendChild(o);
  });
}

function resolveNodeId(text) {
  const t = (text || "").trim().toLowerCase();
  if (!t) return null;
  if (LABEL_TO_ID[t]) return LABEL_TO_ID[t];
  // fall back to a unique substring match on id or label
  const hits = DATA.nodes.filter(n =>
    n.id.toLowerCase().includes(t) || n.label.toLowerCase().includes(t));
  return hits.length ? hits[0].id : null;
}

// --- multi-node clamp set -------------------------------------------------
function renderKoTargets() {
  const box = document.getElementById("ko-targets");
  if (!box) return;
  box.innerHTML = Object.entries(KO_TARGETS).map(([id, s]) =>
    `<span class="ko-chip ${s === "+" ? "up" : "down"}">${arrow(s)} ${labelOf(id)}` +
    `<span class="x" data-id="${id}" title="remove">×</span></span>`).join("");
  box.querySelectorAll(".x").forEach(x =>
    x.addEventListener("click", () => { delete KO_TARGETS[x.dataset.id]; renderKoTargets(); }));
}

function addKnockoutTarget() {
  const status = document.getElementById("ko-status");
  const node = resolveNodeId(document.getElementById("ko-node").value);
  const dir = document.querySelector('input[name="ko-dir"]:checked').value;
  if (!node) { status.textContent = "node not found — type a node id or label"; return; }
  KO_TARGETS[node] = dir;
  document.getElementById("ko-node").value = "";
  status.textContent = `${Object.keys(KO_TARGETS).length} node(s) clamped — add more or derive phenotypes`;
  renderKoTargets();
  document.getElementById("ko-node").focus();
}

// Collect the clamp set to solve: the added chips, plus the current input box if it names a node
// (so a single-node knockout still works without pressing ＋ add first).
function collectKnockoutDo() {
  const do_ = { ...KO_TARGETS };
  const node = resolveNodeId(document.getElementById("ko-node").value);
  if (node) do_[node] = document.querySelector('input[name="ko-dir"]:checked').value;
  return do_;
}

async function runKnockout() {
  const status = document.getElementById("ko-status");
  const doMap = collectKnockoutDo();
  if (!Object.keys(doMap).length) {
    status.textContent = "no node clamped — type a node id or label (or ＋ add several)"; return;
  }
  // a live knockout overrides any precomputed-intervention overlay
  document.getElementById("intervention").value = "";
  status.textContent = "solving…";
  try {
    const r = await fetch(`${API_BASE}/knockout`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ do: doMap }),
    });
    const data = await r.json();
    if (data.error) { status.textContent = `error: ${data.error}`; return; }
    KO_TARGETS = { ...data.do };  // sync chips to what was actually solved
    renderKoTargets();
    const doTxt = Object.entries(data.do).map(([k, v]) => `do(${data.do_labels[k] || k}=${v})`).join(", ");
    const nAff = (data.affected || []).length;
    status.textContent = `${doTxt} · ${data.n_determinate} determinate of ` +
      `${data.n_predicted} reachable · ${data.phenotypes.length} phenotype(s) + ${nAff} affected · ${data.solve_ms} ms`;
    applyPredictionOverlay(data.predicted, data.do);
    renderPhenotypePanel({
      title: "Synthetic knockout", doMap: data.do, doLabels: data.do_labels,
      phenotypes: data.phenotypes, affected: data.affected,
      gainChanges: data.gain_changes, synergies: data.synergies, traces: data.traces,
      meta: `<span class="badge">${data.solve_ms} ms</span>`,
      note: "Comparative-statics steady-state signs. Determinate (↑/↓) predictions are sound; " +
            "reachable traits whose direction the feedback core leaves ambiguous are reported as “affected”.",
    });
  } catch (e) {
    status.textContent = `service unreachable (${API_BASE}). Is the knockout API running?`;
  }
}

// colour every node by its predicted sign; the clamped do() nodes get the do-ring.
function applyPredictionOverlay(predicted, doMap) {
  document.getElementById("overlay-legend").style.display = "block";
  cy.nodes().removeClass("pred-up pred-down pred-amb pred-none pred-do");
  cy.nodes().forEach(n => {
    const id = n.id();
    if (id in doMap) { n.addClass("pred-do"); return; }
    const p = predicted[id];
    if (p === "+") n.addClass("pred-up");
    else if (p === "-") n.addClass("pred-down");
    else if (p === "?") n.addClass("pred-amb");
    else n.addClass("pred-none");
  });
}

function arrow(s) { return s === "+" ? "↑" : s === "-" ? "↓" : "?"; }

// Shared derived-phenotype detail panel (used by both the dynamic knockout and the precomputed
// intervention overlay) — `doMap` is node->"+"/"-", `phenotypes`/`traces` as the API returns them.
function renderPhenotypePanel({ title, doMap, doLabels, phenotypes, affected, gainChanges, synergies, traces, meta, note }) {
  doLabels = doLabels || {};
  phenotypes = phenotypes || [];
  affected = affected || [];
  gainChanges = gainChanges || [];
  synergies = synergies || [];
  traces = traces || {};
  const doTxt = Object.entries(doMap || {})
    .map(([k, v]) => `do(${doLabels[k] || labelOf(k)} = ${v})`).join(", ");

  // one trait row (with its illustrative signed trace), shared by both sections
  const row = (h, neutral) => {
    const tr = traces[h.node];
    const scc = h.in_big_scc ? ` <i class="muted">(SCC)</i>` : "";
    const head = neutral
      ? `${signSpan("?")} <b>${h.label}</b> <i class="muted">affected</i>${scc}`
      : `${signSpan(h.sign)} <b>${h.hpo_label || h.label}</b>${scc}`;
    const sub = neutral
      ? (h.hpo ? `<div class="small">≈ <a href="${iriLink(h.hpo)}" target="_blank">${h.hpo_label || h.hpo}</a> (direction undetermined)</div>` : `<div class="small">direction undetermined</div>`)
      : `<div class="small">${h.label}` + (h.hpo ? ` · <a href="${iriLink(h.hpo)}" target="_blank">${h.hpo}</a>` : "") + `</div>`;
    let r = `<div class="edge ko-pheno" data-node="${h.node}">${head}${sub}`;
    if (tr && tr.length) {
      // the path starts at whichever clamped node is nearest; seed the chain with its direction
      r += `<div class="small" style="opacity:.8">${labelOf(tr[0].src)}${arrow(doMap[tr[0].src] || "?")} ` +
        tr.map(s => `${({ constitutive: "▷", production: "↠", quantitative: "=" }[s.kind] || "→")}(${s.sign}) ${labelOf(s.dst)}${arrow(s.running)}`).join(" ") +
        `</div>`;
    }
    return r + `</div>`;
  };

  let html = `<h2>${title}</h2>`;
  html += `<div><span class="badge">${doTxt}</span>${meta || ""}</div>`;
  if (note) html += `<p class="small">${note}</p>`;
  if (!phenotypes.length && !affected.length) {
    html += `<p class="small">No HPO trait was reached — the clamp drives only feedback-core nodes ` +
      `(which abstain) or leaf analytes with no mapped phenotype.</p>`;
  }
  if (phenotypes.length) {
    html += `<h3 style="margin:12px 0 2px;font-size:13px">Derived phenotypes — direction determined (${phenotypes.length})</h3>`;
    for (const h of phenotypes) html += row(h, false);
  }
  if (affected.length) {
    html += `<h3 style="margin:12px 0 2px;font-size:13px">Affected — direction undetermined (${affected.length})</h3>`;
    html += `<p class="small" style="margin:2px 0 4px">Reachable HPO traits the intervention <i>affects</i>, ` +
      `but whose net direction the feedback core leaves ambiguous (≈ HPO “Abnormality of X”).</p>`;
    for (const h of affected) html += row(h, true);
  }
  // second-order modulation layer: gain changes (sensitization) + synergies (super/sub-additive)
  if (gainChanges.length) {
    html += `<h3 style="margin:12px 0 2px;font-size:13px">Gain changes — sensitization (${gainChanges.length})</h3>`;
    html += `<p class="small" style="margin:2px 0 4px">Couplings this intervention determinately ` +
      `strengthens/weakens (a 2nd-order, sign-only prediction the additive graph cannot make).</p>`;
    for (const g of gainChanges) {
      const word = g.direction === "+" ? "strengthened ↑" : "weakened ↓";
      html += `<div class="edge">${signSpan(g.direction)} <b>${labelOf(g.edge_source)} → ${labelOf(g.edge_target)}</b> ` +
        `<i class="muted">coupling ${word}</i><div class="small">via ${labelOf(g.modulator)} (gain)</div></div>`;
    }
  }
  if (synergies.length) {
    html += `<h3 style="margin:12px 0 2px;font-size:13px">Synergies — combined effect (${synergies.length})</h3>`;
    html += `<p class="small" style="margin:2px 0 4px">Where the intervention moves both a modulator ` +
      `and its edge's source: is the joint effect more- or less-than-additive?</p>`;
    for (const s of synergies) {
      const v = s.verdict === "synergistic" ? `<b style="color:#3fb950">synergistic</b> (super-additive)`
        : s.verdict === "antagonistic" ? `<b style="color:#f85149">antagonistic</b> (sub-additive)`
        : `reinforces toward ${signSpan(s.cross_sign)} <i class="muted">(net direction ambiguous)</i>`;
      html += `<div class="edge ko-pheno" data-node="${s.edge_target}">${v} on <b>${labelOf(s.edge_target)}</b>` +
        `<div class="small">${labelOf(s.edge_source)} × ${labelOf(s.modulator)} (gain) → ${labelOf(s.edge_target)}</div></div>`;
    }
  }
  document.getElementById("detail").innerHTML = html;
  // click a trait row to reveal & centre that node
  document.querySelectorAll(".ko-pheno").forEach(el =>
    el.addEventListener("click", () => focusNode(el.getAttribute("data-node"))));
}

function labelOf(id) { return NODE_ELEM[id] ? NODE_ELEM[id].data.label : id; }

function focusNode(id) {
  // if neighbourhood-focus is on but this node is outside it, drop focus so the node is reachable
  if (FOCUS && !FOCUS.ids.has(id)) exitFocus();
  // enable the node's system AND source facet if either is hidden, then centre on it
  const sys = NODE_SYS[id], src = NODE_SRC[id];
  let changed = false;
  DATA.systems.forEach((s, i) => {
    if (s === sys) { const b = document.getElementById(sysId(i)); if (b && !b.checked) { b.checked = true; changed = true; } }
  });
  (DATA.sources || []).forEach((s, i) => {
    if (s === src) { const b = document.getElementById(srcId(i)); if (b && !b.checked) { b.checked = true; changed = true; } }
  });
  if (changed) refresh();
  const n = cy.getElementById(id);
  if (n.nonempty()) {
    cy.elements().removeClass("sel"); n.addClass("sel");
    cy.animate({ center: { eles: n }, zoom: 1.4 }, { duration: 350 });
  }
}

function clearKnockout() {
  DETAIL_REQUEST++;
  KO_TARGETS = {};
  renderKoTargets();
  document.getElementById("ko-node").value = "";
  document.getElementById("ko-status").textContent = "";
  document.getElementById("intervention").value = "";
  document.getElementById("intervention-info").textContent = "";
  document.getElementById("overlay-legend").style.display = "none";
  cy.nodes().removeClass("pred-up pred-down pred-amb pred-none pred-do");
  colorMode();
  document.getElementById("detail").innerHTML =
    `<div class="placeholder">Click a node or edge for details.</div>`;
}

function wireControls() {
  document.getElementById("layout").addEventListener("change", ev => {
    currentLayout = ev.target.value; runLayout();
  });
  document.getElementById("show-constitutive").addEventListener("change", refresh);
  document.getElementById("show-quantitative").addEventListener("change", refresh);
  document.getElementById("show-modulation").addEventListener("change", refresh);
  document.getElementById("color-by-scale").addEventListener("change", () => {
    if (!document.getElementById("intervention").value) colorMode();
  });
  document.getElementById("highlight-scc").addEventListener("change", ev => {
    cy.nodes().removeClass("scc-hi");
    if (ev.target.checked) cy.nodes("[?in_big_scc]").addClass("scc-hi");
  });
  document.getElementById("intervention").addEventListener("change", ev => applyOverlay(ev.target.value));
  document.getElementById("relayout").addEventListener("click", runLayout);
  document.getElementById("ko-run").addEventListener("click", runKnockout);
  document.getElementById("ko-clear").addEventListener("click", clearKnockout);
  document.getElementById("ko-add").addEventListener("click", addKnockoutTarget);
  document.getElementById("ko-node").addEventListener("keydown", ev => {
    if (ev.key === "Enter") runKnockout();
    else if (ev.key === "Tab" && document.getElementById("ko-node").value.trim()) {
      ev.preventDefault(); addKnockoutTarget();  // Tab = add to the clamp set, keep typing
    }
  });
  document.getElementById("sys-all").addEventListener("click", () => toggleSys(true));
  document.getElementById("sys-none").addEventListener("click", () => toggleSys(false));
  document.getElementById("src-all").addEventListener("click", () => toggleSrc(true));
  document.getElementById("src-none").addEventListener("click", () => toggleSrc(false));
  const searchEl = document.getElementById("search");
  searchEl.addEventListener("input", runSearch);
  searchEl.addEventListener("keydown", ev => {
    const box = document.getElementById("search-results");
    if (ev.key === "Enter") {
      const first = box.querySelector(".r");
      if (first) { gotoNode(first.dataset.id); box.className = "results"; }
    } else if (ev.key === "Escape") { box.className = "results"; }
  });
  // neighbourhood-focus controls
  document.getElementById("focus-exit").addEventListener("click", exitFocus);
  document.getElementById("focus-radius").addEventListener("change", () => {
    const r = parseInt(document.getElementById("focus-radius").value, 10) || 2;
    if (FOCUS) focusNeighbourhood(FOCUS.center, r);
  });
  // delegated: the "⊙ focus neighbourhood" button rendered inside a node's detail panel
  document.getElementById("detail").addEventListener("click", ev => {
    const b = ev.target.closest(".focus-btn");
    if (b) focusNeighbourhood(b.dataset.node, parseInt(document.getElementById("focus-radius").value, 10) || 2);
  });
  colorMode();
}

function toggleSys(on) {
  DATA.systems.forEach((s, i) => { document.getElementById(sysId(i)).checked = on; });
  refresh();
}
