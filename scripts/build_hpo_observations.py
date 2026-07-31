#!/usr/bin/env python3
"""Build benchmarks/hpo/hpo_gene_observations.yaml from the REAL HPO gene->phenotype data.

For every gene in benchmarks/hpo/gene_lesions.yaml, read its actual HPO annotations from
``genes_to_phenotype.txt``, propagate each annotated term up the HP ``is_a`` hierarchy
(true-path rule), match against the curated ``hpo_term_map.yaml`` (each HP id's label re-verified
against hp.obo), and record the observed (node -> increased/decreased) directions, with the
contributing HP terms as provenance and any direction conflicts flagged.

Inputs (downloaded to ontology/.obo_cache/, gitignored):
  hp.obo                          http://purl.obolibrary.org/obo/hp.obo
  genes_to_phenotype.txt          https://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt

Usage:  python scripts/build_hpo_observations.py   (commits the small derived YAML)
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "ontology" / ".obo_cache"
HP_OBO = CACHE / "hp.obo"
G2P = CACHE / "genes_to_phenotype.txt"
TERM_MAP = ROOT / "benchmarks/hpo/hpo_term_map.yaml"
GENE_LESIONS = ROOT / "benchmarks/hpo/gene_lesions.yaml"
OUT = ROOT / "benchmarks/hpo/hpo_gene_observations.yaml"
SOURCES = {
    HP_OBO: "http://purl.obolibrary.org/obo/hp.obo",
    G2P: "https://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt",
}


def fetch() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    for dest, url in SOURCES.items():
        if not dest.exists():
            print(f"  downloading {dest.name}", file=sys.stderr)
            urllib.request.urlretrieve(url, dest)


def parse_hp() -> tuple[dict[str, str], dict[str, set[str]], str]:
    names: dict[str, str] = {}
    parents: dict[str, set[str]] = {}
    version = "?"
    cur = None
    for ln in HP_OBO.read_text(encoding="utf-8").splitlines():
        if ln.startswith("data-version:"):
            version = ln.split(":", 1)[1].strip()
        elif ln == "[Term]":
            cur = None
        elif ln.startswith("id: HP:"):
            cur = ln[4:].strip(); names[cur] = ""; parents[cur] = set()
        elif cur and ln.startswith("name: "):
            names[cur] = ln[6:].strip()
        elif cur and ln.startswith("is_a: "):
            parents[cur].add(ln[6:].split("!")[0].strip())
    return names, parents, version


def ancestors(term: str, parents: dict[str, set[str]]) -> set[str]:
    seen, stack = set(), [term]
    while stack:
        t = stack.pop()
        for p in parents.get(t, ()):
            if p not in seen:
                seen.add(p); stack.append(p)
    return seen | {term}


def main() -> int:
    fetch()
    names, parents, version = parse_hp()
    tm_doc = yaml.safe_load(TERM_MAP.read_text())
    term_map = tm_doc["terms"]
    block = set(tm_doc.get("block_propagation", []))  # annotations that must not is_a-propagate
    genes = yaml.safe_load(GENE_LESIONS.read_text())["genes"]

    # verify every term-map HP label against hp.obo
    bad = [(hp, rec["label"], names.get(hp)) for hp, rec in term_map.items()
           if names.get(hp, "").lower() != rec["label"].lower()]
    if bad:
        print("HP label mismatches vs hp.obo (fix hpo_term_map.yaml):")
        for hp, asserted, actual in bad:
            print(f"  {hp}: asserted {asserted!r} != hp.obo {actual!r}")
        return 1

    # gene_symbol -> set of annotated HP ids
    gene_hpo: dict[str, set[str]] = {}
    with G2P.open() as fh:
        header = fh.readline().rstrip("\n").split("\t")
        gi, hi = header.index("gene_symbol"), header.index("hpo_id")
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) > max(gi, hi):
                gene_hpo.setdefault(f[gi], set()).add(f[hi])

    out: dict[str, dict] = {}
    for gene, rec in genes.items():
        ann = gene_hpo.get(gene)
        if not ann:
            out[gene] = {"primary": rec["primary"], "observed": {}, "sources": {},
                         "note": "gene not present in genes_to_phenotype"}
            continue
        # node -> {sign -> [contributing HP terms]}
        node_signs: dict[str, dict[str, list[str]]] = {}
        for hp in ann:
            anc_set = {hp} if hp in block else ancestors(hp, parents)  # blocked: exact-only
            for anc in anc_set:
                m = term_map.get(anc)
                if m:
                    src = f"{hp} {names.get(hp,'')}" + ("" if hp == anc else f" (via {anc} {names.get(anc,'')})")
                    node_signs.setdefault(m["node"], {}).setdefault(m["sign"], []).append(src)
        observed, sources, conflicts = {}, {}, []
        for node, signs in node_signs.items():
            if len(signs) == 1:
                sgn = next(iter(signs))
                observed[node] = sgn
                sources[f"{node}{sgn}"] = sorted(set(signs[sgn]))
            else:
                conflicts.append(node)  # both directions annotated across diseases -> drop
        out[gene] = {"primary": rec["primary"], "observed": observed, "sources": sources}
        if conflicts:
            out[gene]["conflicts"] = sorted(conflicts)

    body = {"hpo_release": version, "source": "genes_to_phenotype.txt + hp.obo (is_a propagated)",
            "observations": out}
    OUT.write_text(
        "# Auto-generated by scripts/build_hpo_observations.py from the REAL HPO\n"
        "# genes_to_phenotype annotations (is_a-propagated, matched to hpo_term_map.yaml).\n"
        "# Do not edit by hand; regenerate after an HPO release.\n"
        + yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=100)
    )
    n_obs = sum(len(g["observed"]) for g in out.values())
    print(f"wrote {OUT}  (HPO {version}; {len(out)} genes, {n_obs} mappable observed directions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
