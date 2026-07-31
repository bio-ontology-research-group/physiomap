#!/usr/bin/env python3
"""Auto-align HPO directional physiological-quantity terms to PhysioMap nodes.

WHY LEXICAL (not EQ): the cleanest alignment would use HPO's EQ logical definitions
(`Hyperkalemia ≡ has-part some (increased-concentration and inheres-in some potassium …)`).
We probed the released artifacts directly: `hp.obo` and `hp.json` carry **0** logical
definitions, and `hp-full.json` carries only **20**, all onset or chorioretinal-morphology
terms, **none** of the directional lab/metabolite terms. The cross-species EQ exists only in
uPheno (a 416 MB OWL needing a reasoner). Therefore, this aligner is **lexical**: it detects the
directional morphology of the term name/synonyms, extracts the analyte, and matches it to a
PhysioMap node label or its ontology-entity label (from the verified OBO caches). Every
proposal is a **candidate for human review**, never auto-merged into `hpo_term_map.yaml`.

Outputs (drafts):
  benchmarks/hpo/hpo_alignment.yaml: proposed term→(node, sign) candidates and a reproduction
                                       check of the lexical matcher against the 49 curated terms.
  benchmarks/hpo/node_gaps.md: directional quantity terms with NO PhysioMap node, ranked
                                       by HPO gene-annotation frequency (highest-coverage first).

Inputs (cached, gitignored, under ontology/.obo_cache/; fetched by build_hpo_observations.py):
  hp.obo, genes_to_phenotype.txt, plus the entity-label OBO caches (CHEBI/PR/GO/UBERON/PATO/CL).

Usage:  python scripts/hpo_align.py            # write both artifacts
        python scripts/hpo_align.py --print    # also print a summary
"""

from __future__ import annotations

import argparse
import collections
import re
from pathlib import Path

import yaml

from physiomap_core.hpo import build_map
from physiomap_core.model import PhysioMap

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "ontology" / ".obo_cache"
HP_OBO = CACHE / "hp.obo"
G2P = CACHE / "genes_to_phenotype.txt"
TERM_MAP = ROOT / "benchmarks" / "hpo" / "hpo_term_map.yaml"
OUT_YAML = ROOT / "benchmarks" / "hpo" / "hpo_alignment.yaml"
OUT_GAPS = ROOT / "benchmarks" / "hpo" / "node_gaps.md"
OUT_GAPS_FULL = ROOT / "benchmarks" / "hpo" / "node_gaps_full.tsv"

# HPO subtree roots whose descendants are physiological *quantity* terms (signed comparative
# statics applies). Derived from the ancestors of the curated seed; the script self-reports how
# many curated terms fall outside them so the set can be widened with evidence.
QUANTITY_ROOTS = {
    "HP:0001939",  # Abnormality of metabolism/homeostasis (electrolytes, metabolites, glucose…)
    "HP:0003117",  # Abnormal circulating hormone concentration
    "HP:0011025",  # Abnormal cardiovascular system physiology (blood pressure, heart rate)
}

# direction word/affix -> sign
_PLUS = re.compile(r"\b(increased|elevated|high|excess|excessive|raised)\b|^hyper", re.I)
_MINUS = re.compile(r"\b(decreased|reduced|low|deficiency|deficient|depleted|loss|reduction)\b|^hypo", re.I)

# tokens to strip before matching the analyte core of a term name
_STOP = {
    "abnormal", "abnormality", "abnormally", "circulating", "serum", "plasma", "blood",
    "concentration", "level", "levels", "of", "the", "in", "increased", "decreased",
    "elevated", "reduced", "high", "low", "excess", "excessive", "raised", "deficiency",
    "deficient", "depleted", "content", "amount", "total", "a", "an",
}

# generic determinable tokens that, ALONE, do not pin down an analyte (a confident match needs
# at least one *specific* token besides these).
_GENERIC = {
    "pressure", "protein", "hormone", "acid", "cell", "volume", "rate", "output",
    "vitamin", "factor", "count", "index", "mass", "function", "activity", "response",
    "system", "ratio", "concentration", "enzyme", "globulin", "compound", "metabolite",
}

# standard clinical morphology: -emia/-uria roots -> the plain-English analyte (reviewable).
_CLINICAL_ROOT = {
    "kalemia": "potassium", "kalaemia": "potassium", "natremia": "sodium",
    "natraemia": "sodium", "calcemia": "calcium", "calcaemia": "calcium",
    "phosphatemia": "phosphate", "phosphataemia": "phosphate", "glycemia": "glucose",
    "glycaemia": "glucose", "uricemia": "urate", "uricaemia": "urate",
    "magnesemia": "magnesium", "magnesaemia": "magnesium", "cholesterolemia": "cholesterol",
    "triglyceridemia": "triglyceride", "ammonemia": "ammonia", "ammonaemia": "ammonia",
    "lipidemia": "lipid", "proteinemia": "protein", "insulinemia": "insulin",
    "phenylalaninemia": "phenylalanine", "methioninemia": "methionine",
    "bilirubinemia": "bilirubin", "magnesiumemia": "magnesium",
}


def parse_hp(path: Path = HP_OBO) -> tuple[dict[str, str], dict[str, set[str]], dict[str, list[str]]]:
    """Return (names, is_a-parents, synonyms) keyed by HP id."""
    names: dict[str, str] = {}
    parents: dict[str, set[str]] = collections.defaultdict(set)
    syns: dict[str, list[str]] = collections.defaultdict(list)
    cur = None
    obsolete = set()
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln == "[Term]":
            cur = None
        elif ln.startswith("id: HP:"):
            cur = ln[4:].strip()
        elif cur and ln.startswith("name: "):
            names[cur] = ln[6:].strip()
        elif cur and ln.startswith("is_a: "):
            parents[cur].add(ln[6:].split("!")[0].strip())
        elif cur and ln.startswith("synonym: "):
            m = re.search(r'"([^"]*)"', ln)
            if m:
                syns[cur].append(m.group(1))
        elif cur and ln.startswith("is_obsolete: true"):
            obsolete.add(cur)
    for o in obsolete:
        names.pop(o, None)
    return names, parents, syns


def ancestors(term: str, parents: dict[str, set[str]]) -> set[str]:
    seen, stack = set(), [term]
    while stack:
        t = stack.pop()
        for p in parents.get(t, ()):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    return seen | {term}


def descendants(term: str, children: dict[str, set[str]]) -> set[str]:
    seen, stack = set(), [term]
    while stack:
        t = stack.pop()
        for c in children.get(t, ()):
            if c not in seen:
                seen.add(c)
                stack.append(c)
    return seen | {term}


def direction(name: str) -> str | None:
    """`+`/`-` from a term name, or None if not clearly directional / both."""
    plus, minus = bool(_PLUS.search(name)), bool(_MINUS.search(name))
    if plus and not minus:
        return "+"
    if minus and not plus:
        return "-"
    return None


def _tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", s.lower()) if t}


def analyte_tokens(name: str) -> set[str]:
    """Content tokens of a term name after stripping direction/quality words; expands -emia roots."""
    toks = _tokens(name)
    out: set[str] = set()
    for t in toks:
        if t in _STOP or len(t) <= 2:  # drop direction/quality words + single/double-char tokens
            continue
        # strip hyper/hypo prefix and map a clinical root (kalemia->potassium)
        root = re.sub(r"^(hyper|hypo)", "", t)
        if root in _CLINICAL_ROOT:
            out |= _tokens(_CLINICAL_ROOT[root])
        else:
            out.add(t)
    return out


def has_specific(an_toks: set[str]) -> bool:
    """True if the analyte has at least one non-generic token (so a match is meaningful)."""
    return any(t not in _GENERIC for t in an_toks)


# ---- entity labels from the verified OBO caches -----------------------------------------------

_OBO_FILE = {"CHEBI": "CHEBI.obo", "CL": "CL.obo", "GO": "GO.obo",
             "PATO": "PATO.obo", "PR": "PR.obo", "UBERON": "UBERON.obo"}


def entity_labels(iris: set[str]) -> dict[str, str]:
    """Map each needed `PREFIX:1234` id to its OBO `name:` (scans only needed files/ids)."""
    by_prefix: dict[str, set[str]] = collections.defaultdict(set)
    for iri in iris:
        if iri and ":" in iri:
            by_prefix[iri.split(":")[0]].add(iri)
    labels: dict[str, str] = {}
    for prefix, ids in by_prefix.items():
        fn = _OBO_FILE.get(prefix)
        if not fn or not (CACHE / fn).exists():
            continue
        want, cur = set(ids), None
        for ln in (CACHE / fn).read_text(encoding="utf-8", errors="replace").splitlines():
            if ln.startswith("id: "):
                cur = ln[4:].strip()
            elif cur in want and ln.startswith("name: "):
                labels[cur] = ln[6:].strip()
                want.discard(cur)
                if not want:
                    break
    return labels


def build_node_index(pmap: PhysioMap) -> dict[str, set[str]]:
    """node_id -> searchable token set (label + entity label + id words)."""
    iris = {n.entity_iri for n in pmap.nodes if n.entity_iri}
    elabels = entity_labels(iris)
    index: dict[str, set[str]] = {}
    for n in pmap.nodes:
        toks = _tokens(n.label) | _tokens(n.id.replace("_", " "))
        if n.entity_iri and n.entity_iri in elabels:
            toks |= _tokens(elabels[n.entity_iri])
        index[n.id] = toks - _STOP
    return index


def match_node(an_toks: set[str], index: dict[str, set[str]]) -> list[str]:
    """Nodes whose token set contains all analyte content tokens; most specific first."""
    if not an_toks:
        return []
    hits = [nid for nid, toks in index.items() if an_toks <= toks]
    return sorted(hits, key=lambda nid: (len(index[nid]), nid))


# ---- the alignment run ------------------------------------------------------------------------

def gene_annotation_counts(terms_of_interest: set[str], children: dict[str, set[str]]) -> dict[str, int]:
    """For each term, # distinct genes annotated to it or any is_a-descendant (coverage weight)."""
    if not G2P.exists():
        return {}
    term_genes: dict[str, set[str]] = collections.defaultdict(set)
    with G2P.open() as fh:
        header = fh.readline().rstrip("\n").split("\t")
        gi, hi = header.index("gene_symbol"), header.index("hpo_id")
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) > max(gi, hi):
                term_genes[f[hi]].add(f[gi])
    out: dict[str, int] = {}
    for t in terms_of_interest:
        genes: set[str] = set()
        for d in descendants(t, children):
            genes |= term_genes.get(d, set())
        out[t] = len(genes)
    return out


def run() -> dict:
    pmap = build_map()
    names, parents, syns = parse_hp()
    children: dict[str, set[str]] = collections.defaultdict(set)
    for c, ps in parents.items():
        for p in ps:
            children[p].add(c)
    index = build_node_index(pmap)
    curated = yaml.safe_load(TERM_MAP.read_text())["terms"]
    curated_ids = set(curated)

    # universe = directional quantity terms (under a QUANTITY_ROOT)
    quantity = {hp for hp in names if QUANTITY_ROOTS & ancestors(hp, parents)}
    directional = {hp: d for hp in quantity if (d := direction(names[hp]))}

    # a term is already representable if it (or an is_a ancestor) is a curated mapped term
    def covered_by_map(hp: str) -> str | None:
        for a in ancestors(hp, parents):
            if a in curated_ids:
                return a
        return None

    candidates, ambiguous, gaps = [], [], []
    for hp, sgn in directional.items():
        an = analyte_tokens(names[hp])
        nodes = match_node(an, index)
        mapped_anc = covered_by_map(hp)
        if mapped_anc:
            continue  # already representable via an is-a ancestor in the curated map
        if not nodes:
            gaps.append(hp)
            continue
        rec = {"hp": hp, "name": names[hp], "sign": sgn, "node": nodes[0],
               "alt_nodes": nodes[1:4], "matched_on": sorted(an)}
        # confident = a specific (non-generic) analyte AND a unique most-specific node
        unique_top = len(nodes) == 1 or len(index[nodes[0]]) < len(index[nodes[1]])
        if has_specific(an) and unique_top:
            candidates.append(rec)
        else:
            ambiguous.append(rec)

    # rank gaps by gene-annotation coverage
    counts = gene_annotation_counts(set(gaps), children)
    gaps_ranked = sorted(gaps, key=lambda hp: (-counts.get(hp, 0), names.get(hp, hp)))

    # reproduction check: does the lexical matcher recover the 49 curated mappings?
    repro = {"matched": 0, "missed": [], "sign_conflict": [], "node_conflict": []}
    for hp, rec in curated.items():
        nm = names.get(hp)
        if not nm:
            repro["missed"].append(f"{hp} (not in hp.obo)")
            continue
        d = direction(nm)
        nodes = match_node(analyte_tokens(nm), index)
        if d == rec["sign"] and rec["node"] in nodes:
            repro["matched"] += 1
        elif d and d != rec["sign"]:
            repro["sign_conflict"].append(f"{hp} {nm}: lexical {d} vs curated {rec['sign']}")
        else:
            repro["node_conflict"].append(f"{hp} {nm} -> curated {rec['node']}; lexical {nodes[:3] or 'no-match'}")

    # how many curated terms fall outside QUANTITY_ROOTS (root-set adequacy)?
    outside = [hp for hp in curated_ids if hp in names and not (QUANTITY_ROOTS & ancestors(hp, parents))]

    return {
        "names": names, "candidates": candidates, "ambiguous": ambiguous,
        "gaps_ranked": gaps_ranked, "counts": counts, "repro": repro,
        "outside_roots": outside, "n_quantity": len(quantity),
        "n_directional": len(directional),
    }


def write_outputs(res: dict) -> None:
    names = res["names"]
    repro = res["repro"]
    n_cur = repro["matched"] + len(repro["missed"]) + len(repro["sign_conflict"]) + len(repro["node_conflict"])
    doc = {
        "_about": "DRAFT lexical HPO->PhysioMap alignment (scripts/hpo_align.py). Review before "
                  "merging any candidate into hpo_term_map.yaml. HPO has no public EQ for these "
                  "terms; matches are name/entity-label based.",
        "summary": {
            "directional_quantity_terms": res["n_directional"],
            "expansion_candidates": len(res["candidates"]),
            "ambiguous_candidates": len(res["ambiguous"]),
            "uncovered_gaps": len(res["gaps_ranked"]),
            "curated_reproduction": f"{repro['matched']}/{n_cur}",
            "curated_outside_quantity_roots": res["outside_roots"],
        },
        "candidates": res["candidates"],
        "ambiguous_candidates": res["ambiguous"],
        "curated_reproduction_detail": {
            "matched": repro["matched"],
            "sign_conflict": repro["sign_conflict"],
            "node_conflict": repro["node_conflict"],
            "missed": repro["missed"],
        },
    }
    OUT_YAML.write_text(
        "# Auto-generated by scripts/hpo_align.py. Candidates require review and are not auto-merged.\n"
        + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)
    )

    lines = [
        "# PhysioMap node gaps from HPO directional quantity terms",
        "",
        "Directional physiological-quantity HPO terms (under "
        f"`{'`, `'.join(sorted(QUANTITY_ROOTS))}`) with no PhysioMap node and no mapped "
        "is-a ancestor are coverage gaps. They are ranked by the number of distinct genes "
        "annotated to the term or any descendant. This file is generated by "
        "`scripts/hpo_align.py`. An unconnected node yields no prediction; relations require "
        "independent evidence and provenance.",
        "",
        f"- directional quantity terms scanned: **{res['n_directional']}**",
        f"- expansion candidates (map to an existing node): **{len(res['candidates'])}** "
        "(see `hpo_alignment.yaml`)",
        f"- uncovered gaps: **{len(res['gaps_ranked'])}**",
        "",
        "| rank | genes | HP id | term | dir |",
        "|---|---|---|---|---|",
    ]
    for i, hp in enumerate(res["gaps_ranked"][:120], 1):
        d = direction(names.get(hp, "")) or "?"
        lines.append(f"| {i} | {res['counts'].get(hp, 0)} | {hp} | {names.get(hp, '?')} | {d} |")
    if len(res["gaps_ranked"]) > 120:
        lines.append(f"\n_({len(res['gaps_ranked']) - 120} further lower-coverage gaps omitted.)_")
    lines.append("")
    OUT_GAPS.write_text("\n".join(lines))

    # complete machine-readable gap list (ALL gaps, not just the top 120)
    full = ["rank\tgenes\thp_id\tdir\tname"]
    for i, hp in enumerate(res["gaps_ranked"], 1):
        d = direction(names.get(hp, "")) or "?"
        full.append(f"{i}\t{res['counts'].get(hp, 0)}\t{hp}\t{d}\t{names.get(hp, '?')}")
    OUT_GAPS_FULL.write_text("\n".join(full) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--print", dest="show", action="store_true", help="print a summary")
    args = ap.parse_args(argv)
    if not HP_OBO.exists() or not G2P.exists():
        raise SystemExit(f"missing cache; run scripts/build_hpo_observations.py first ({CACHE})")
    res = run()
    write_outputs(res)
    r = res["repro"]
    n_cur = r["matched"] + len(r["missed"]) + len(r["sign_conflict"]) + len(r["node_conflict"])
    print(f"wrote {OUT_YAML.relative_to(ROOT)} and {OUT_GAPS.relative_to(ROOT)}")
    print(f"  directional quantity terms: {res['n_directional']}   "
          f"candidates: {len(res['candidates'])} (+{len(res['ambiguous'])} ambiguous)   "
          f"gaps: {len(res['gaps_ranked'])}")
    print(f"  lexical matcher reproduces curated mappings: {r['matched']}/{n_cur}")
    if res["outside_roots"]:
        print(f"  NOTE: {len(res['outside_roots'])} curated terms fall outside QUANTITY_ROOTS: "
              f"{res['outside_roots']}")
    if args.show:
        for c in res["candidates"][:30]:
            print(f"    + {c['hp']} {c['name'][:48]:48s} -> {c['node']} ({c['sign']})")
        print("  top gaps:")
        for hp in res["gaps_ranked"][:15]:
            print(f"    ! {res['counts'].get(hp,0):3d} genes  {hp} {res['names'].get(hp,'')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
