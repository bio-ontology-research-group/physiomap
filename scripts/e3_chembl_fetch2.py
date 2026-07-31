#!/usr/bin/env python3
"""E3 ChEMBL fetch (optimised): TARGETS first, then only the molecules whose mechanism
hits a PhysioMap-resolvable target. Cuts molecule fetches from ~6000 to a few hundred.
"""
from __future__ import annotations

import json
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMP = ROOT / "benchmarks/.imports/sidekick"
U2P = ROOT / "benchmarks/.imports/uniprot_to_pr.json"
BASE = "https://www.ebi.ac.uk/chembl/api/data"
UA = {"User-Agent": "Mozilla/5.0 (PhysioMap/1.0; research)"}


def fetch(url: str) -> dict:
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            print(f"  retry {attempt}: {e}", flush=True)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(url)


def uniprot_node_accessions() -> set[str]:
    """UniProt accessions that resolve to a PR-grounded PhysioMap node."""
    from physiomap_core.hpo import build_map

    pmap = build_map()
    pr_nodes = {n.entity_iri for n in pmap.nodes
                if getattr(n, "entity_iri", None) and n.entity_iri.startswith("PR:")}
    u2p = json.loads(U2P.read_text())["uniprot_to_pr"]
    return {uni.split("-")[0] for uni, pr in u2p.items() if pr in pr_nodes}


def main() -> None:
    mechs = json.loads((IMP / "chembl_mechanisms.json").read_text())
    tgt_ids = sorted({m["target_chembl_id"] for m in mechs if m.get("target_chembl_id")})
    print(f"targets to fetch: {len(tgt_ids)}", flush=True)

    tgts = {}
    for i in range(0, len(tgt_ids), 40):
        chunk = ",".join(tgt_ids[i : i + 40])
        d = fetch(f"{BASE}/target.json?target_chembl_id__in={chunk}&limit=40")
        for t in d["targets"]:
            accs = [c["accession"] for c in (t.get("target_components") or []) if c.get("accession")]
            tgts[t["target_chembl_id"]] = {
                "pref_name": t.get("pref_name"), "target_type": t.get("target_type"),
                "organism": t.get("organism"), "accessions": accs,
            }
        print(f"  targets {len(tgts)}/{len(tgt_ids)}", flush=True)
    (IMP / "chembl_targets.json").write_text(json.dumps(tgts, indent=1))
    print(f"targets done: {len(tgts)}", flush=True)

    node_accs = uniprot_node_accessions()
    print(f"node-resolvable UniProt accessions: {len(node_accs)}", flush=True)

    # mechanisms whose target resolves to a PhysioMap node -> their molecules
    keep_mol = set()
    for m in mechs:
        t = tgts.get(m.get("target_chembl_id"))
        if t and t.get("organism") == "Homo sapiens" and any(a in node_accs for a in t["accessions"]):
            if m.get("molecule_chembl_id"):
                keep_mol.add(m["molecule_chembl_id"])
    mol_ids = sorted(keep_mol)
    print(f"molecules to fetch (target-resolvable drugs only): {len(mol_ids)}", flush=True)

    mols = {}
    for i in range(0, len(mol_ids), 40):
        chunk = ",".join(mol_ids[i : i + 40])
        d = fetch(f"{BASE}/molecule.json?molecule_chembl_id__in={chunk}&limit=40")
        for m in d["molecules"]:
            syns = [s["molecule_synonym"] for s in (m.get("molecule_synonyms") or [])]
            mols[m["molecule_chembl_id"]] = {"pref_name": m.get("pref_name"), "synonyms": syns}
        print(f"  molecules {len(mols)}/{len(mol_ids)}", flush=True)
    (IMP / "chembl_molecules.json").write_text(json.dumps(mols, indent=1))
    print(f"molecules done: {len(mols)}", flush=True)


if __name__ == "__main__":
    main()
