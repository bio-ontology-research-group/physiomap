#!/usr/bin/env python3
"""Refresh cached OWLAPI bottom-locality TBox modules for used source terms."""

from __future__ import annotations

import hashlib
import json
import subprocess
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "ontology/registry/used-terms.json"
SOURCE_DIR = ROOT / "ontology/.obo_cache"
MODULE_DIR = ROOT / "ontology/modules"


def obo_iri(identifier: str) -> str:
    prefix, local = identifier.split(":", 1)
    return f"http://purl.obolibrary.org/obo/{prefix}_{local}"


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    by_source: dict[str, list[str]] = {}
    for identifier, term in registry["terms"].items():
        by_source.setdefault(term["source"], []).append(obo_iri(identifier))
    MODULE_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for source_name, iris in sorted(by_source.items()):
        source = (SOURCE_DIR / source_name).resolve()
        signature = MODULE_DIR / f"{source.stem}.signature.txt"
        module = (MODULE_DIR / f"{source.stem}.owl").resolve()
        signature.write_text("\n".join(sorted(iris)) + "\n", encoding="utf-8")
        started = time.perf_counter()
        completed = subprocess.run([
            "gradle", "--quiet", "-p", str(ROOT / "ontology"), "run",
            f"--args=--module {source} {signature.resolve()} {module} 100000",
        ], cwd=ROOT, check=True, text=True, capture_output=True)
        elapsed = time.perf_counter() - started
        match = re.search(r"Extracted locality TBox module: (\d+) axioms", completed.stdout)
        if not match:
            raise RuntimeError(f"could not read module size from extractor output: {completed.stdout}")
        records.append({
            "source": source_name,
            "source_sha256": registry["checksums"][source_name],
            "signature": signature.name,
            "signature_sha256": hashlib.sha256(signature.read_bytes()).hexdigest(),
            "module": module.name,
            "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
            "axiom_count": int(match.group(1)),
            "extraction_seconds": round(elapsed, 3),
        })
    manifest = {"schema_version": "1.0.0", "module_type": "BOT",
                "abox_policy": "excluded", "modules": records}
    (MODULE_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"source locality modules: OK ({len(records)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
