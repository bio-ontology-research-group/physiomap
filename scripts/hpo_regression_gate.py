#!/usr/bin/env python3
"""Standing HPO soundness gate — run after every map change (and in CI).

PhysioMap's core guarantee is **soundness**: a determinate `+`/`-` prediction is never wrong.
As the map grows (new fragments, edges, gene mappings), the cheapest way to keep that guarantee
is to re-run every HPO prediction we have ground truth for and **fail loudly on any wrong
determinate call**. This script is that gate. It checks, over the *full mappable gene set*:

  1. **Curated pilot forward** — `do(primary)` vs the hand-curated secondary phenotypes in
     `benchmarks/hpo/disorders.yaml` (`hpo.forward_eval`): 0 wrong required.
  2. **REAL-HPO forward** — `do(primary)` vs the observed `genes_to_phenotype` directions
     (`hpo_validate.validate`): 0 wrong required.
  3. **Referential integrity** — every node referenced by `hpo_term_map.yaml` and
     `gene_lesions.yaml` exists in the composed map.

Exit code 0 iff all pass; non-zero (and a printed list of violations) otherwise. Abstentions
(`?`) are fine — only a determinate prediction that contradicts ground truth fails the gate.

Usage:  python scripts/hpo_regression_gate.py [-q]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from physiomap_core.hpo import build_map, forward_eval, load_disorders
from physiomap_core.hpo_validate import render as render_validate
from physiomap_core.hpo_validate import validate
from physiomap_core.model import PhysioMap  # noqa: F401  (type hint for check)

ROOT = Path(__file__).resolve().parent.parent
DISORDERS = ROOT / "benchmarks/hpo/disorders.yaml"
TERM_MAP = ROOT / "benchmarks/hpo/hpo_term_map.yaml"
GENE_LESIONS = ROOT / "benchmarks/hpo/gene_lesions.yaml"


def check(quiet: bool = False, pmap: "PhysioMap | None" = None) -> tuple[bool, list[str]]:
    """Return (ok, violations). ok iff no determinate prediction is wrong and refs resolve.

    ``pmap`` lets a caller (e.g. the curation editor's deep-validate) gate a *candidate* map —
    the composed map with a proposed contribution merged in — instead of the committed corpus.
    """
    if pmap is None:
        pmap = build_map()
    ids = set(pmap.node_ids)
    violations: list[str] = []
    log = (lambda *a: None) if quiet else print

    # 1) curated pilot forward soundness
    disorders = load_disorders(DISORDERS)
    fwd = forward_eval(pmap, disorders)
    pilot_wrong = sum(f.wrong for f in fwd)
    pilot_det = sum(f.scored for f in fwd)
    for f in fwd:
        for w in f.wrong_calls:
            violations.append(f"[curated:{f.disorder}] {w}")
    log(f"1. curated pilot forward : {len(disorders)} disorders, "
        f"{pilot_det} determinate, {pilot_wrong} WRONG")

    # 2) real-HPO forward soundness
    fwd_r, bwd_r = validate(pmap)
    for w in fwd_r.wrong_calls:
        violations.append(f"[real-HPO] {w}")
    log(f"2. REAL-HPO forward      : {fwd_r.genes_scored} genes, "
        f"{fwd_r.observations} determinate, {fwd_r.wrong} WRONG "
        f"(backward top-3 {bwd_r.top3}/{bwd_r.genes_scored})")

    # 3) referential integrity of the HPO mapping files
    tm = yaml.safe_load(TERM_MAP.read_text())["terms"]
    bad_tm = sorted({r["node"] for r in tm.values() if r["node"] not in ids})
    genes = yaml.safe_load(GENE_LESIONS.read_text())["genes"]
    bad_gl = sorted({n for g in genes.values() for n in g["primary"] if n not in ids})
    for n in bad_tm:
        violations.append(f"[hpo_term_map] node absent from map: {n}")
    for n in bad_gl:
        violations.append(f"[gene_lesions] primary node absent from map: {n}")
    log(f"3. referential integrity : {len(tm)} term-map + {len(genes)} gene nodes, "
        f"{len(bad_tm) + len(bad_gl)} dangling")

    return (not violations), violations


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-q", "--quiet", action="store_true", help="only print pass/fail + violations")
    ap.add_argument("--report", action="store_true", help="also print the full validation report")
    args = ap.parse_args(argv)

    ok, violations = check(quiet=args.quiet)
    if args.report:
        print(render_validate(*validate()))
    if ok:
        print("HPO soundness gate: PASS (0 wrong determinate predictions)")
        return 0
    print(f"HPO soundness gate: FAIL ({len(violations)} violation(s)):")
    for v in violations:
        print(f"  - {v}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
