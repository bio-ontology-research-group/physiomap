#!/usr/bin/env python3
"""Maintainer merge: run the FULL pre-deployment gate suite on a curation fragment, then place it.

A curator's submission, once approved in the editor, is exported as a fragment YAML (the editor's
"fragment ↓" button, or ``GET /curate/fragment``). Before it can become part of the live map a
maintainer must run the *complete* pre-deploy discipline on it — the same gates CI/release run —
not just the live editor gates. This script orchestrates them on a candidate fragment:

  1. schema + provenance            — scripts/validate_fragment.py
  2. causal-evidence interventional — scripts/validate_causal_evidence.py
  3. ontology IDs vs OBO            — scripts/verify_ontology_ids.py  (authoritative; downloads OBO)
  4. HPO soundness regression       — scripts/hpo_regression_gate.py  (with the fragment composed in)

On success it copies the fragment into ``benchmarks/human/curated/`` as a canonical-build input.
The runtime does not read that YAML: a maintainer must rebuild, validate, and package OWL/SCM
before the contribution is live. The script does NOT commit or
deploy for you — that stays a deliberate human step.

Usage:  python scripts/curation_merge.py <fragment.yaml> [--place]
        python scripts/curation_merge.py <fragment.yaml> --place   # also copy into the repo
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CURATED = ROOT / "benchmarks" / "human" / "curated"


def _run(label: str, args: list[str]) -> bool:
    print(f"\n=== {label}: {' '.join(args)} ===", flush=True)
    rc = subprocess.run([sys.executable, *args], cwd=ROOT).returncode
    print(f"--- {label}: {'PASS' if rc == 0 else 'FAIL'} (rc={rc})")
    return rc == 0


def _soundness_with_fragment(fragment: Path) -> bool:
    """Compose the corpus + this fragment and run the soundness gate on the candidate map."""
    print("\n=== 4. HPO soundness regression (fragment composed in) ===", flush=True)
    import yaml

    from physiomap_core.curation import validate_contribution
    from physiomap_core.hpo import build_map

    contribution = yaml.safe_load(fragment.read_text()) or {}
    report = validate_contribution(build_map(), contribution, deep=True)
    for g in report.gates:
        mark = "PASS" if g.ok else "FAIL"
        print(f"  [{mark}] {g.gate}" + ("" if g.ok else f": {g.errors}"))
    print(f"--- soundness: {'PASS' if report.ok else 'FAIL'}")
    return report.ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fragment", help="path to the exported contribution fragment YAML")
    ap.add_argument("--place", action="store_true",
                    help="on success, copy the fragment into benchmarks/human/curated/")
    ap.add_argument("--skip-obo", action="store_true",
                    help="skip the OBO id download/verification (do it separately)")
    args = ap.parse_args(argv)
    frag = Path(args.fragment).resolve()
    if not frag.exists():
        print(f"no such fragment: {frag}")
        return 2

    ok = True
    ok &= _run("1. schema + provenance", ["scripts/validate_fragment.py", str(frag)])
    ok &= _run("2. causal-evidence gate", ["scripts/validate_causal_evidence.py", str(frag)])
    if not args.skip_obo:
        ok &= _run("3. ontology IDs vs OBO (manifest)", ["scripts/verify_ontology_ids.py", "--write-manifest"])
    else:
        print("\n=== 3. ontology IDs vs OBO: SKIPPED (run scripts/verify_ontology_ids.py --write-manifest) ===")
    ok &= _soundness_with_fragment(frag)

    print("\n" + "=" * 60)
    if not ok:
        print("MERGE GATE: FAIL — do NOT commit this fragment until every gate passes.")
        return 1
    print("MERGE GATE: PASS — every pre-deploy gate is green.")
    if args.place:
        CURATED.mkdir(parents=True, exist_ok=True)
        dest = CURATED / frag.name
        shutil.copy2(frag, dest)
        print(f"placed: {dest.relative_to(ROOT)}")
    print("Next: rebuild/package canonical OWL+SCM, refresh web/paper artifacts, run")
    print("scripts/owl_scm_release_gate.py, commit, then redeploy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
