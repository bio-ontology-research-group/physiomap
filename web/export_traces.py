#!/usr/bin/env python3
"""Render static disease-trace pages for the web viewer.

For each Mendelian disorder in ``benchmarks/hpo/disorders.yaml`` this emits a self-contained
HTML page under ``web/traces/<slug>/index.html`` showing, for every endophenotype:
  * the **real HPO term** the endophenotype corresponds to (reverse-looked-up from
    ``hpo_term_map.yaml``, linked to hpo.jax.org),
  * the signed mechanistic **path(s)** from the variant's ``do()`` clamp to that phenotype
    (each step's edge sign + running ↑/↓, the cross-scale constitutive lift marked ▷), and
  * the **comparative-statics** net sign vs the naive **forward** path product — making
    "steady-state ≠ path propagation" visible (honest ? inside a homeostatic SCC).
Plus an index at ``web/traces/index.html``.

Usage:  uv run python web/export_traces.py [--check]
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import networkx as nx
import yaml

from physiomap_core.hpo import build_map, load_disorders
from physiomap_core.model import Sign
from physiomap_core.qualitative import Intervention
from physiomap_core.trace import trace

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
OUT = WEB / "traces"
DISORDERS = ROOT / "benchmarks/hpo/disorders.yaml"
TERM_MAP = ROOT / "benchmarks/hpo/hpo_term_map.yaml"

ARROW = {Sign.PLUS: "↑", Sign.MINUS: "↓", Sign.UNKNOWN: "?"}
SIGN_CLASS = {Sign.PLUS: "up", Sign.MINUS: "down", Sign.UNKNOWN: "amb"}

CSS = """
:root{--bg:#0f1419;--card:#1a2129;--ink:#e6edf3;--mut:#8b98a5;--up:#3fb950;--down:#f85149;
--amb:#d29922;--line:#30363d;--accent:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:940px;margin:0 auto;padding:28px 20px 64px}
h1{font-size:24px;margin:0 0 4px}.sub{color:var(--mut);margin:0 0 20px}
.badge{display:inline-block;background:#21262d;border:1px solid var(--line);border-radius:6px;
padding:2px 8px;margin-right:6px;font-size:12px;color:var(--mut)}
.mech{background:#161b22;border-left:3px solid var(--accent);padding:10px 14px;border-radius:0 6px 6px 0;
color:var(--mut);margin:0 0 22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:0 0 16px}
.phead{display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:6px}
.phead .node{font-weight:600;font-size:16px}
.hp{font-size:12px;color:var(--mut)}.hp .chip{background:#21262d;border:1px solid var(--line);
border-radius:5px;padding:1px 6px;margin-left:4px}
.net{font-size:13px;color:var(--mut);margin:2px 0 12px}
.up{color:var(--up)}.down{color:var(--down)}.amb{color:var(--amb)}
.path{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;background:#0d1117;
border:1px solid var(--line);border-radius:7px;padding:9px 11px;margin:6px 0;overflow-x:auto;white-space:nowrap}
.path .op{color:var(--mut)}.path .det{color:var(--amb)}
.nb{font-size:13px;color:var(--amb);background:#1f1a0e;border:1px solid #5c4813;border-radius:7px;
padding:8px 11px;margin-top:8px}
.legend{color:var(--mut);font-size:13px;border-top:1px solid var(--line);margin-top:26px;padding-top:14px}
table.idx{border-collapse:collapse;width:100%}table.idx td,table.idx th{border-bottom:1px solid var(--line);
padding:8px 10px;text-align:left;vertical-align:top}table.idx th{color:var(--mut);font-weight:600;font-size:13px}
.tag{font-size:11px;border-radius:5px;padding:1px 6px;border:1px solid var(--line)}
.tag.det{color:var(--up);border-color:#1f6f2b}.tag.scc{color:var(--amb);border-color:#5c4813}
.foot{color:var(--mut);font-size:12px;margin-top:30px}
.explain{background:#11161d;border:1px solid var(--line);border-radius:10px;padding:8px 18px 14px;margin:0 0 22px}
.explain h2{font-size:16px;margin:12px 0 6px}.explain p{margin:8px 0;font-size:14px}
.explain .mut{color:var(--mut);font-size:13px}.mut{color:var(--mut)}
"""


def explain_box(largest_scc: int) -> str:
    """Explain abstention using topology computed from the rendered canonical map."""
    return (
        '<div class="explain">'
        '<h2>How to read a prediction: <span class="up">determinate</span> vs '
        '<span class="amb">SCC&nbsp;?</span></h2>'
        '<p>PhysioMap predicts the <b>comparative-statics</b> sign — the direction a quantity moves at '
        'the new <b>steady state</b> after all feedback has settled, <code>sign(dx*/d&theta;)</code> — '
        '<i>not</i> the naive forward product of edge signs along a path.</p>'
        '<p><b><span class="up">Determinate (↑ / ↓).</span></b> The lesion drives the endophenotype one '
        'way regardless of the (unknown) reaction strengths — every numerical model consistent with the '
        'sign pattern agrees. PhysioMap commits to <b>↑</b> or <b>↓</b>. These predictions are '
        '<b>sound</b>: validated against the real HPO gene→phenotype data, a determinate sign is never '
        'wrong.</p>'
        '<p><b><span class="amb">SCC&nbsp;? (magnitude-dependent).</span></b> An <b>SCC</b> (strongly '
        'connected component) is a set of variables wired into a <b>feedback loop</b> — each reachable '
        f'from the others. The largest homeostatic SCC in this map has exactly {largest_scc} nodes. '
        'When an endophenotype sits inside such a loop, opposing feedback arms fight, and the net '
        'steady-state sign depends on <i>how strong</i> each arm is — information a qualitative model '
        'does not have. Rather than guess, PhysioMap returns <b>?</b> and abstains. The trace still '
        'shows the forward mechanism (e.g. “forward says ↑”), making explicit that <b>steady state ≠ '
        'path propagation</b> — getting pressure-natriuresis and the baroreflex right is exactly why '
        'we use comparative statics.</p>'
        '<p class="mut">Honest abstention is a feature: PhysioMap reports a sign only when it is forced, '
        'so the ↑/↓ calls you do see are trustworthy.</p>'
        '</div>'
    )


def largest_scc_size(pmap) -> int:
    """Return the exact largest causal strongly connected component size."""
    return max((len(component) for component in
                nx.strongly_connected_components(pmap.causal_subgraph())), default=0)


def slug(name: str) -> str:
    s = re.sub(r"\(.*?\)", "", name).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def reverse_term_map() -> dict[tuple[str, str], tuple[str, str]]:
    """(node, sign) -> (HP id, label) — the real HPO term for an endophenotype direction."""
    terms = yaml.safe_load(TERM_MAP.read_text())["terms"]
    rev: dict[tuple[str, str], tuple[str, str]] = {}
    for hp, r in terms.items():
        rev.setdefault((r["node"], r["sign"]), (hp, r["label"]))
    return rev


def fmt_path(pmap, intervention, p) -> str:
    def lab(n):
        try:
            return pmap.node(n).label
        except KeyError:
            return n
    s0 = intervention.targets[p.nodes[0]]
    parts = [f'<span class="{SIGN_CLASS[s0]}">{html.escape(lab(p.nodes[0]))} {ARROW[s0]}</span>']
    for st in p.steps:
        if st.kind == "constitutive":
            parts.append('<span class="det"> ▷(determination) </span>')
        elif st.kind == "production":
            parts.append(f'<span class="op"> ↠(production {st.edge_sign.value}) </span>')
        elif st.kind == "quantitative":
            parts.append(f'<span class="op"> =(identity {st.edge_sign.value}) </span>')
        else:
            parts.append(f'<span class="op"> →({st.edge_sign.value}) </span>')
        parts.append(f'<span class="{SIGN_CLASS[st.running]}">{html.escape(lab(st.dst))} {ARROW[st.running]}</span>')
    return "".join(parts)


def page(pmap, d, rev) -> tuple[str, bool]:
    iv = Intervention(targets=d.primary, label=d.name)
    src = ", ".join(f'{html.escape(n)} {ARROW[s]}' for n, s in d.primary.items())
    body = [f'<p><a href="../">&larr; all disease traces</a></p>',
            f'<h1>{html.escape(d.name)}</h1>',
            f'<p class="sub"><span class="badge">{html.escape(d.gene or "?")}</span>'
            f'<span class="badge">OMIM {html.escape(str(d.omim or "?"))}</span>'
            f'<span class="badge">do({src})</span></p>']
    if d.mechanism:
        body.append(f'<div class="mech">{html.escape(d.mechanism)}</div>')
    any_det = False
    for ph in d.phenotypes:
        r = trace(pmap, iv, ph.node)
        cs = r["net_comparative_statics"]
        fwd = r["net_forward"]
        try:
            nlab = pmap.node(ph.node).label
        except KeyError:
            nlab = ph.node
        hp = rev.get((ph.node, ph.sign.value))
        hp_html = ""
        if hp:
            hp_html = (f'<span class="hp">HPO: {html.escape(hp[1])}'
                       f'<a class="chip" href="https://hpo.jax.org/browse/term/{hp[0]}" '
                       f'target="_blank" rel="noopener">{hp[0]}</a></span>')
        body.append('<div class="card">')
        body.append(f'<div class="phead"><span class="node {SIGN_CLASS[ph.sign]}">{html.escape(nlab)} '
                    f'{ARROW[ph.sign]}</span>{hp_html}</div>')
        body.append(f'<div class="net">comparative-statics (steady-state) net: '
                    f'<b class="{SIGN_CLASS.get(cs, "amb")}">{ARROW.get(cs, "·")}</b></div>')
        if r["paths"]:
            for p in r["paths"][:5]:
                body.append(f'<div class="path">{fmt_path(pmap, iv, p)}</div>')
        else:
            body.append('<div class="net">(no explicit path enumerated — direct clamp or '
                        'cross-fragment)</div>')
        if cs is Sign.UNKNOWN and fwd in (Sign.PLUS, Sign.MINUS):
            body.append(f'<div class="nb">Forward mechanism says {ARROW[fwd]}, but the steady-state '
                        f'net is <b>?</b> — this endophenotype sits in a homeostatic feedback loop '
                        f'(the whole-body SCC); the compensated sign is magnitude-dependent. '
                        f'PhysioMap abstains rather than guess.</div>')
        if cs in (Sign.PLUS, Sign.MINUS):
            any_det = True
        body.append('</div>')
    body.append('<div class="legend">↑ increased &nbsp; ↓ decreased &nbsp; ? magnitude-dependent '
                '(SCC). <span class="up">→(+)</span> positive edge, <span class="down">→(−)</span> '
                'negative, <span class="det">▷</span> cross-scale constitutive lift. Endophenotypes '
                'are real HPO directional terms. <b>Draft for domain review.</b></div>')
    return wrap(f"{d.name} — PhysioMap trace", "\n".join(body)), any_det


def wrap(title: str, inner: str) -> str:
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{CSS}</style></head>'
            f'<body><div class="wrap">{inner}'
            f'<div class="foot">Generated by <code>web/export_traces.py</code> from the PhysioMap '
            f'maps. <a href="https://bio2vec.net/physiomap/">&larr; interactive map</a></div>'
            f'</div></body></html>')


def index_page(rows: list[tuple], largest_scc: int) -> str:
    body = ['<p><a href="../">&larr; interactive PhysioMap</a></p>',
            '<h1>Mendelian disease traces</h1>',
            '<p class="sub">Each variant is a <code>do()</code> clamp; PhysioMap traces the signed '
            'mechanistic path to its endophenotypes (real HPO directional terms) and reports the '
            'steady-state comparative-statics net sign.</p>',
            explain_box(largest_scc),
            '<table class="idx"><tr><th>Disorder</th><th>Gene</th><th>OMIM</th>'
            '<th>Endophenotypes (HPO)</th><th></th></tr>']
    for name, sl, gene, omim, phen, det in rows:
        tag = '<span class="tag det">determinate</span>' if det else '<span class="tag scc">SCC&nbsp;?</span>'
        body.append(f'<tr><td><a href="{sl}/">{html.escape(name)}</a></td><td>{html.escape(gene)}</td>'
                    f'<td>{html.escape(str(omim))}</td><td>{phen}</td><td>{tag}</td></tr>')
    body.append('</table>')
    return wrap("Mendelian disease traces — PhysioMap", "\n".join(body))


def render_site(pmap, disorders, rev) -> dict[Path, str]:
    """Render all trace pages in memory, keyed by paths relative to the output root."""
    rendered: dict[Path, str] = {}
    rows = []
    for d in disorders:
        sl = slug(d.name)
        htmlpage, any_det = page(pmap, d, rev)
        rendered[Path(sl) / "index.html"] = htmlpage
        phen = ", ".join(
            f'<a href="https://hpo.jax.org/browse/term/{rev[(p.node, p.sign.value)][0]}" '
            f'target="_blank" rel="noopener">{html.escape(rev[(p.node, p.sign.value)][1])}</a>'
            if (p.node, p.sign.value) in rev else html.escape(p.node)
            for p in d.phenotypes)
        rows.append((d.name, sl, d.gene or "?", d.omim or "?", phen, any_det))
    rendered[Path("index.html")] = index_page(rows, largest_scc_size(pmap))
    return rendered


def check_site(rendered: dict[Path, str], output_dir: Path) -> list[Path]:
    """Return changed, missing, or obsolete files in a generated trace tree."""
    expected = set(rendered)
    actual = {path.relative_to(output_dir) for path in output_dir.rglob("*") if path.is_file()}
    stale = expected ^ actual
    for relative in expected & actual:
        if (output_dir / relative).read_text(encoding="utf-8") != rendered[relative]:
            stale.add(relative)
    return sorted(stale)


def write_site(rendered: dict[Path, str], output_dir: Path) -> None:
    """Write the generated tree and remove obsolete generated files/directories."""
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = set(rendered)
    for path in output_dir.rglob("*"):
        if path.is_file() and path.relative_to(output_dir) not in expected:
            path.unlink()
    for relative, content in rendered.items():
        target = output_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    for path in sorted(output_dir.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if committed trace pages differ from a fresh render")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    pmap = build_map()
    disorders = load_disorders(DISORDERS)
    rendered = render_site(pmap, disorders, reverse_term_map())
    if args.check:
        stale = check_site(rendered, args.output_dir)
        if stale:
            print("stale generated disease traces: " + ", ".join(map(str, stale)))
            print("run: uv run python web/export_traces.py")
            return 1
        print(f"verified {len(disorders)} disease-trace pages + index")
        return 0
    write_site(rendered, args.output_dir)
    try:
        display = args.output_dir.relative_to(ROOT)
    except ValueError:
        display = args.output_dir
    print(f"wrote {len(disorders)} disease-trace pages + index under {display}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
