#!/usr/bin/env python3
"""Re-fetch ChEMBL molecules + targets with the correct `__in` (comma) separator."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "benchmarks/.imports/sidekick"
BASE = "https://www.ebi.ac.uk/chembl/api/data"
UA = {"User-Agent": "Mozilla/5.0 (PhysioMap/1.0; research)"}


def fetch(url: str) -> dict:
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            print(f"  retry {attempt}: {e}")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def main() -> None:
    mechs = json.loads((OUT / "chembl_mechanisms.json").read_text())
    mol_ids = sorted({m["molecule_chembl_id"] for m in mechs if m.get("molecule_chembl_id")})
    tgt_ids = sorted({m["target_chembl_id"] for m in mechs if m.get("target_chembl_id")})
    print(f"molecules to fetch: {len(mol_ids)}, targets: {len(tgt_ids)}")

    mols = {}
    for i in range(0, len(mol_ids), 40):
        chunk = ",".join(mol_ids[i : i + 40])
        d = fetch(f"{BASE}/molecule.json?molecule_chembl_id__in={chunk}&limit=40")
        for m in d["molecules"]:
            syns = [s["molecule_synonym"] for s in (m.get("molecule_synonyms") or [])]
            mols[m["molecule_chembl_id"]] = {"pref_name": m.get("pref_name"), "synonyms": syns}
        if i % 400 == 0:
            print(f"  molecules {len(mols)}/{len(mol_ids)}")
    (OUT / "chembl_molecules.json").write_text(json.dumps(mols, indent=1))
    print(f"molecules done: {len(mols)}")

    tgts = {}
    for i in range(0, len(tgt_ids), 40):
        chunk = ",".join(tgt_ids[i : i + 40])
        d = fetch(f"{BASE}/target.json?target_chembl_id__in={chunk}&limit=40")
        for t in d["targets"]:
            accs = [c["accession"] for c in (t.get("target_components") or []) if c.get("accession")]
            tgts[t["target_chembl_id"]] = {
                "pref_name": t.get("pref_name"),
                "target_type": t.get("target_type"),
                "organism": t.get("organism"),
                "accessions": accs,
            }
        if i % 400 == 0:
            print(f"  targets {len(tgts)}/{len(tgt_ids)}")
    (OUT / "chembl_targets.json").write_text(json.dumps(tgts, indent=1))
    print(f"targets done: {len(tgts)}")


if __name__ == "__main__":
    main()
