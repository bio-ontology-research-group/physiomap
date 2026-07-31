"use strict";

// PhysioMap curation editor. Builds a typed contribution, validates it
// against the live deployment gates via the API, and submits it (token-gated) for maintainer review.

const API_BASE = (() => {
  const q = new URLSearchParams(location.search).get("api");
  if (q) return q.replace(/\/$/, "");
  if (location.pathname.includes("/physiomap")) return "/physiomap/api";
  return "http://127.0.0.1:8081";
})();

// the contribution under construction
const C = { nodes: [], causal_edges: [], production_edges: [], constitutive_edges: [], modulation_edges: [], quantitative_definitions: [] };
let lastReport = null, reviewEnabled = false;

const $ = id => document.getElementById(id);
const val = id => ($(id).value || "").trim();
const setErr = m => { $("form-err").textContent = m || ""; };

// ---- token persistence (browser-local only) ----
$("token").value = localStorage.getItem("pm_edit_token") || "";
$("curator").value = localStorage.getItem("pm_curator") || "";
$("token").addEventListener("change", () => localStorage.setItem("pm_edit_token", $("token").value));
$("curator").addEventListener("change", () => localStorage.setItem("pm_curator", $("curator").value));

// ---- tabs ----
document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
  document.querySelectorAll(".panel").forEach(x => x.classList.remove("active"));
  t.classList.add("active");
  $("panel-" + t.dataset.tab).classList.add("active");
}));

// ---- startup: health + node list ----
async function init() {
  try {
    const h = await (await fetch(`${API_BASE}/health`)).json();
    reviewEnabled = !!(h.curation && h.curation.review_enabled);
    $("apistat").textContent = `${h.nodes} nodes · submit ${h.curation && h.curation.submit_enabled ? "on" : "off"}`;
    $("admin-hint").textContent = reviewEnabled
      ? "Deep-validate / approve require the admin token in the Edit-token box."
      : "Review actions are disabled on this server.";
  } catch (e) { $("apistat").textContent = "API unreachable"; }
  try {
    const d = await (await fetch(`${API_BASE}/nodes`)).json();
    const dl = $("nodelist");
    d.nodes.forEach(n => { const o = document.createElement("option"); o.value = n.id; o.label = n.label; dl.appendChild(o); });
  } catch (e) { /* offline: autocomplete simply absent */ }
  try {
    const d = await (await fetch(`${API_BASE}/influences`)).json();
    const dl = $("influencelist");
    d.influences.forEach(edge => {
      const option = document.createElement("option");
      option.value = edge.id;
      option.label = `${edge.source} ${edge.sign}→ ${edge.target}${edge.context ? ` [${edge.context}]` : ""}`;
      dl.appendChild(option);
    });
  } catch (e) { /* offline: autocomplete simply absent */ }
  loadQueue();
}

// ---- add handlers ----
function need(obj, fields) {
  for (const f of fields) if (!obj[f]) { setErr(`missing required field: ${f}`); return false; }
  setErr(""); return true;
}

$("add-node").addEventListener("click", () => {
  const n = { id: val("n-id"), label: val("n-label"), scale: $("n-scale").value };
  if (!need(n, ["id", "label", "scale"])) return;
  if (val("n-entity")) n.entity_iri = val("n-entity");
  if (val("n-quality")) n.quality_iri = val("n-quality");
  if (val("n-bearer")) n.bearer_entity_iri = val("n-bearer");
  if ($("n-exo").checked) n.exogenous = true;
  C.nodes.push(n);
  ["n-id", "n-label", "n-entity", "n-quality", "n-bearer"].forEach(i => $(i).value = "");
  $("n-exo").checked = false;
  render();
});

$("add-causal").addEventListener("click", () => {
  const e = { source: val("c-src"), target: val("c-tgt"), sign: $("c-sign").value,
    causal_evidence: $("c-ce").value, evidence: val("c-ev") };
  if (!need(e, ["source", "target", "sign", "causal_evidence", "evidence"])) return;
  const contextId = val("c-context-id"), contextLabel = val("c-context-label");
  if (!!contextId !== !!contextLabel) { setErr("context id and label must be supplied together"); return; }
  if (contextId) e.context = { id: contextId, label: contextLabel, kind: $("c-context-kind").value };
  if (val("c-mech")) e.mechanism = val("c-mech");
  C.causal_edges.push(e);
  ["c-src", "c-tgt", "c-context-id", "c-context-label", "c-mech", "c-ev"].forEach(i => $(i).value = "");
  render();
});

$("add-production").addEventListener("click", () => {
  const e = { source: val("p-src"), target: val("p-tgt"), sign: $("p-sign").value,
    production_evidence: $("p-pe").value, mechanism: val("p-mech"), evidence: val("p-ev") };
  if (!need(e, ["source", "target", "sign", "production_evidence", "mechanism", "evidence"])) return;
  C.production_edges.push(e);
  ["p-src", "p-tgt", "p-mech", "p-ev"].forEach(i => $(i).value = "");
  render();
});

$("add-const").addEventListener("click", () => {
  const e = { micro: val("k-micro"), macro: val("k-macro"), relation: $("k-rel").value, sign: $("k-sign").value };
  if (!need(e, ["micro", "macro", "relation", "sign"])) return;
  C.constitutive_edges.push(e);
  ["k-micro", "k-macro"].forEach(i => $(i).value = "");
  render();
});

$("add-modul").addEventListener("click", () => {
  const e = { modulator: val("m-mod"), influence_id: val("m-influence"),
    sign: $("m-sign").value, causal_evidence: $("m-ce").value, evidence: val("m-ev") };
  if (!need(e, ["modulator", "influence_id", "sign", "causal_evidence", "evidence"])) return;
  if (val("m-mech")) e.mechanism = val("m-mech");
  if ($("m-flip").checked) e.can_flip_sign = true;
  C.modulation_edges.push(e);
  ["m-mod", "m-influence", "m-mech", "m-ev"].forEach(i => $(i).value = ""); $("m-flip").checked = false;
  render();
});

$("add-ratio").addEventListener("click", () => {
  const result = val("r-result"), numerator = val("r-num"), denominator = val("r-den");
  if (!result || !numerator || !denominator) { setErr("fill result, numerator, and denominator"); return; }
  const r = { kind: "ratio", result, arguments: [
    { node: numerator, role: "numerator", derivative_sign: "+" },
    { node: denominator, role: "denominator", derivative_sign: "-" },
  ] };
  if (val("r-mech")) r.mechanism = val("r-mech");
  if (val("r-ev")) r.evidence = val("r-ev");
  C.quantitative_definitions.push(r);
  ["r-result", "r-num", "r-den", "r-mech", "r-ev"].forEach(i => $(i).value = "");
  render();
});

$("term-search").addEventListener("click", async () => {
  const q = val("term-query");
  if (!q) return;
  try {
    const data = await (await fetch(`${API_BASE}/ontology/lookup?q=${encodeURIComponent(q)}`)).json();
    $("term-results").innerHTML = (data.terms || []).map((term, index) =>
      `<div class="item"><b>${esc(term.id)}</b> ${esc(term.label)}<br>` +
      `<button class="mini use-term" data-i="${index}" data-field="n-entity">use as entity</button> ` +
      `<button class="mini use-term" data-i="${index}" data-field="n-quality">use as quality</button></div>`).join("") || "no local matches";
    document.querySelectorAll(".use-term").forEach(button => button.addEventListener("click", () => {
      $(button.dataset.field).value = data.terms[+button.dataset.i].id;
    }));
  } catch (e) { $("term-results").textContent = "lookup unavailable"; }
});

// ---- render the current contribution ----
function row(kind, text, idx) {
  return `<div class="item"><span class="x" data-kind="${kind}" data-i="${idx}" title="remove">✕</span>${text}</div>`;
}
function esc(s) { return (s || "").replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

function render() {
  let h = "";
  C.nodes.forEach((n, i) => h += row("nodes", `<b>node</b> <code class="k">${esc(n.id)}</code> — ${esc(n.label)} <span class="muted2">[${n.scale}]${n.entity_iri ? " " + n.entity_iri : ""}${n.quality_iri ? " / " + n.quality_iri : ""}</span>`, i));
  C.causal_edges.forEach((e, i) => h += row("causal_edges", `<b>causal</b> ${esc(e.source)} <b>${e.sign}</b>→ ${esc(e.target)} <span class="muted2">[${e.causal_evidence}${e.context ? `; ${esc(e.context.id)}` : ""}]</span>`, i));
  C.production_edges.forEach((e, i) => h += row("production_edges", `<b>production</b> ${esc(e.source)} <b>${e.sign}</b>→ ${esc(e.target)} <span class="muted2">[${e.production_evidence}]</span>`, i));
  C.constitutive_edges.forEach((e, i) => h += row("constitutive_edges", `<b>constitutive</b> ${esc(e.micro)} ▷ ${esc(e.macro)} <span class="muted2">[${e.relation}, ${e.sign}]</span>`, i));
  C.modulation_edges.forEach((e, i) => h += row("modulation_edges", `<b>modulation</b> ${esc(e.modulator)} ⊗ <code>${esc(e.influence_id || `${e.edge_source}→${e.edge_target}`)}</code> <b>${e.sign}</b>`, i));
  C.quantitative_definitions.forEach((e, i) => h += row("quantitative_definitions", `<b>${esc(e.kind)}</b> ${esc(e.result)}(${e.arguments.map(a => `${esc(a.role)}=${esc(a.node)} [${esc(a.derivative_sign)}]`).join(", ")})`, i));
  const total = C.nodes.length + C.causal_edges.length + C.production_edges.length + C.constitutive_edges.length + C.modulation_edges.length + C.quantitative_definitions.length;
  $("contribution").innerHTML = total ? h : `<div class="muted2">empty — add nodes/edges from the left.</div>`;
  document.querySelectorAll("#contribution .x").forEach(x => x.addEventListener("click", () => {
    C[x.dataset.kind].splice(+x.dataset.i, 1); lastReport = null; $("btn-submit").disabled = true; render();
  }));
  $("btn-submit").disabled = !(lastReport && lastReport.ok);
}

// ---- validate / submit ----
$("btn-validate").addEventListener("click", validate);
$("btn-clear").addEventListener("click", () => {
  ["nodes", "causal_edges", "production_edges", "constitutive_edges", "modulation_edges", "quantitative_definitions"].forEach(k => C[k] = []);
  lastReport = null; render(); $("validation").innerHTML = "";
});

async function validate() {
  $("validation").innerHTML = `<div class="muted2">running gates…</div>`;
  try {
    const r = await (await fetch(`${API_BASE}/curate/validate`, {
      method: "POST", headers: { "Content-Type": "application/json", "X-Edit-Token": $("token").value },
      body: JSON.stringify({ contribution: C }),
    })).json();
    lastReport = r.report;
    renderReport(r.report);
    $("btn-submit").disabled = !r.report.ok;
  } catch (e) { $("validation").innerHTML = `<div class="g-err" style="color:#f85149">API unreachable</div>`; }
}

$("btn-preview").addEventListener("click", async () => {
  $("axiom-preview").textContent = "building preview…";
  $("preview-box").open = true;
  try {
    const data = await (await fetch(`${API_BASE}/curate/preview`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contribution: C }),
    })).json();
    $("axiom-preview").innerHTML = (data.axioms || []).map(esc).join("<br>") || "no axioms";
  } catch (e) { $("axiom-preview").textContent = "preview unavailable"; }
});

function renderReport(rep) {
  let h = `<div style="margin-bottom:6px"><b>${rep.ok ? "✓ ADMISSIBLE" : "✗ REJECTED"}</b> — ${esc(rep.summary)}</div>`;
  for (const g of rep.gates) {
    h += `<div class="gate ${g.ok ? "ok" : "bad"}"><b>${g.ok ? "✓" : "✗"} ${g.gate}</b>${g.detail ? ` <span class="muted2">${esc(g.detail)}</span>` : ""}`;
    g.errors.forEach(e => h += `<div class="g-err">• ${esc(e)}</div>`);
    g.warnings.forEach(w => h += `<div class="g-warn">• ${esc(w)}</div>`);
    h += `</div>`;
  }
  $("validation").innerHTML = h;
}

$("btn-submit").addEventListener("click", async () => {
  const curator = val("curator"), token = $("token").value;
  if (!curator) { setErr("enter your name (Curator) before submitting"); return; }
  if (!token) { setErr("enter the edit token before submitting"); return; }
  const title = prompt("Short title for this contribution:", "") || "";
  try {
    const res = await fetch(`${API_BASE}/curate/submit`, {
      method: "POST", headers: { "Content-Type": "application/json", "X-Edit-Token": token },
      body: JSON.stringify({ curator, title, contribution: C }),
    });
    const r = await res.json();
    if (!res.ok) { renderReport(r.report || { ok: false, gates: [], summary: r.error }); setErr(r.error || "submit failed"); return; }
    setErr("");
    $("validation").innerHTML = `<div class="gate ok"><b>✓ submitted</b> as <code class="k">${r.id}</code> — pending review.</div>`;
    ["nodes", "causal_edges", "production_edges", "constitutive_edges", "modulation_edges", "quantitative_definitions"].forEach(k => C[k] = []);
    lastReport = null; render(); loadQueue();
  } catch (e) { setErr("submit failed: API unreachable"); }
});

// ---- review queue ----
$("btn-refresh").addEventListener("click", loadQueue);

async function loadQueue() {
  try {
    const d = await (await fetch(`${API_BASE}/curate/submissions`)).json();
    if (!d.submissions.length) { $("queue").innerHTML = `<div class="muted2">no submissions yet.</div>`; return; }
    let h = "";
    for (const s of d.submissions) {
      const cnt = Object.entries(s.counts || {}).filter(([, v]) => v).map(([k, v]) => `${v} ${k.replace("_edges", "").replace("_", " ")}`).join(", ");
      h += `<div class="item"><div><span class="pill ${s.status}">${s.status}</span> <b>${esc(s.title || s.id)}</b></div>
        <div class="muted2">${esc(s.curator)} · ${esc(s.created.slice(0, 16).replace("T", " "))} · ${esc(cnt)}</div>
        <div style="margin-top:5px;display:flex;gap:5px;flex-wrap:wrap">
          <button class="mini" data-act="view" data-id="${s.id}">view</button>
          ${reviewEnabled ? `<button class="mini" data-act="deep" data-id="${s.id}">deep-validate</button>
          <button class="mini" data-act="approve" data-id="${s.id}">approve</button>
          <button class="mini" data-act="reject" data-id="${s.id}">reject</button>
          <button class="mini" data-act="fragment" data-id="${s.id}">fragment ↓</button>` : ""}
        </div></div>`;
    }
    $("queue").innerHTML = h;
    document.querySelectorAll("#queue button").forEach(b => b.addEventListener("click", () => queueAction(b.dataset.act, b.dataset.id)));
  } catch (e) { $("queue").innerHTML = `<div class="g-err" style="color:#f85149">queue unreachable</div>`; }
}

async function queueAction(act, id) {
  const token = $("token").value;
  const hdr = { "Content-Type": "application/json", "X-Edit-Token": token };
  if (act === "view") {
    const d = await (await fetch(`${API_BASE}/curate/submission?id=${encodeURIComponent(id)}`)).json();
    if (d.submission) { lastReport = d.submission.report; loadIntoView(d.submission); }
    return;
  }
  if (act === "deep") {
    $("validation").innerHTML = `<div class="muted2">deep validation (soundness regression, ~15s)…</div>`;
    const r = await (await fetch(`${API_BASE}/curate/deep-validate`, { method: "POST", headers: hdr, body: JSON.stringify({ id }) })).json();
    if (r.report) renderReport(r.report); else setErr(r.error || "deep failed");
    loadQueue(); return;
  }
  if (act === "approve" || act === "reject") {
    const note = prompt(`${act} note (optional):`, "") || "";
    const r = await (await fetch(`${API_BASE}/curate/review`, { method: "POST", headers: hdr, body: JSON.stringify({ id, status: act === "approve" ? "approved" : "rejected", review_note: note }) })).json();
    if (r.error) setErr(r.error); loadQueue(); return;
  }
  if (act === "fragment") {
    const r = await (await fetch(`${API_BASE}/curate/fragment?id=${encodeURIComponent(id)}`, { headers: hdr })).json();
    if (r.error) { setErr(r.error); return; }
    const blob = new Blob([r.fragment], { type: "text/yaml" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `${id}.yaml`; a.click();
  }
}

function loadIntoView(sub) {
  if (sub.report) renderReport(sub.report);
  let h = `<h3 style="margin:16px 0 4px;font-size:14px">${esc(sub.title || sub.id)} <span class="pill ${sub.status}">${sub.status}</span></h3>`;
  h += `<div class="muted2">by ${esc(sub.curator)} · ${esc(sub.created)}</div>`;
  const c = sub.contribution || {};
  (c.nodes || []).forEach(n => h += `<div class="item"><b>node</b> <code class="k">${esc(n.id)}</code> ${esc(n.label)}</div>`);
  (c.causal_edges || []).forEach(e => h += `<div class="item"><b>causal</b> ${esc(e.source)} ${e.sign}→ ${esc(e.target)} <div class="muted2">${esc(e.mechanism || "")}<br>▪ ${esc(e.evidence || "")}</div></div>`);
  (c.production_edges || []).forEach(e => h += `<div class="item"><b>production</b> ${esc(e.source)} ${e.sign}→ ${esc(e.target)} <span class="muted2">[${esc(e.production_evidence)}]</span></div>`);
  (c.constitutive_edges || []).forEach(e => h += `<div class="item"><b>constitutive</b> ${esc(e.micro)} ▷ ${esc(e.macro)} [${e.relation}]</div>`);
  (c.modulation_edges || []).forEach(e => h += `<div class="item"><b>modulation</b> ${esc(e.modulator)} ⊗ <code>${esc(e.influence_id || `${e.edge_source}→${e.edge_target}`)}</code></div>`);
  (c.quantitative_definitions || []).forEach(e => h += `<div class="item"><b>${esc(e.kind)}</b> ${esc(e.result)}(${(e.arguments || []).map(a => `${esc(a.role)}=${esc(a.node)}`).join(", ")})</div>`);
  (c.ratio_definitions || []).forEach(e => h += `<div class="item"><b>legacy ratio</b> ${esc(e.ratio)} = ${esc(e.numerator)} / ${esc(e.denominator)}</div>`);
  $("contribution").innerHTML = h;
}

render();
init();
