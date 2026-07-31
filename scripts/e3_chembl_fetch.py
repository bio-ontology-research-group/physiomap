#!/usr/bin/env python3
"""E3 step 2 — fetch ChEMBL mechanism-of-action (MoA) data via the public API.

Pulls every drug-mechanism row (molecule -> target, action_type, MoA text), then
resolves the referenced molecules to a preferred name + synonyms (to crosswalk to
SIDEKICK ingredient names) and the targets to UniProt accessions (to crosswalk to
PhysioMap enzyme/receptor nodes via the gene->node resolver). Open data, CC-BY-SA.

Robust to the default-User-Agent block (EBI 403s urllib's default UA).
"""
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
            print(f"  retry {attempt} {url[:80]}: {e}")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def page_all(endpoint: str, fields_key: str) -> list[dict]:
    out: list[dict] = []
    url = f"{BASE}/{endpoint}.json?limit=1000"
    while url:
        d = fetch(url)
        out.extend(d[fields_key])
        nxt = d["page_meta"].get("next")
        url = f"https://www.ebi.ac.uk{nxt}" if nxt else None
        print(f"  {endpoint}: {len(out)}")
    return out


def main() -> None:
    # 1. all mechanisms
    mechs = page_all("mechanism", "mechanisms")
    (OUT / "chembl_mechanisms.json").write_text(json.dumps(mechs, indent=1))
    print(f"mechanisms: {len(mechs)}")

    mol_ids = sorted({m["molecule_chembl_id"] for m in mechs if m.get("molecule_chembl_id")})
    tgt_ids = sorted({m["target_chembl_id"] for m in mechs if m.get("target_chembl_id")})
    print(f"unique molecules: {len(mol_ids)}, targets: {len(tgt_ids)}")

    # 2. molecules -> pref_name + synonyms (batch via id__in)
    mols = {}
    for i in range(0, len(mol_ids), 50):
        chunk = ";".join(mol_ids[i : i + 50])
        d = fetch(f"{BASE}/molecule.json?molecule_chembl_id__in={chunk}&limit=50")
        for m in d["molecules"]:
            syns = [s["molecule_synonym"] for s in (m.get("molecule_synonyms") or [])]
            mols[m["molecule_chembl_id"]] = {
                "pref_name": m.get("pref_name"),
                "synonyms": syns,
            }
        print(f"  molecules {len(mols)}/{len(mol_ids)}")
    (OUT / "chembl_molecules.json").write_text(json.dumps(mols, indent=1))

    # 3. targets -> UniProt accessions
    tgts = {}
    for i in range(0, len(tgt_ids), 50):
        chunk = ";".join(tgt_ids[i : i + 50])
        d = fetch(f"{BASE}/target.json?target_chembl_id__in={chunk}&limit=50")
        for t in d["targets"]:
            accs = [c["accession"] for c in (t.get("target_components") or []) if c.get("accession")]
            tgts[t["target_chembl_id"]] = {
                "pref_name": t.get("pref_name"),
                "target_type": t.get("target_type"),
                "organism": t.get("organism"),
                "accessions": accs,
            }
        print(f"  targets {len(tgts)}/{len(tgt_ids)}")
    (OUT / "chembl_targets.json").write_text(json.dumps(tgts, indent=1))
    print("done")


if __name__ == "__main__":
    main()
