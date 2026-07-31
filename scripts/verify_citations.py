#!/usr/bin/env python3
"""Citation-verification stage: check every PMID cited in PhysioMap evidence against PubMed.

The fan-out authoring models sometimes fabricate plausible-looking PMIDs (real-format numbers
that index an unrelated paper). This stage fetches the REAL PubMed record for each cited PMID via
NCBI E-utilities (cached locally) so we never keep an identifier we have not checked:

  * EXISTENCE (deterministic gate) — a cited PMID that PubMed does not return is fabricated/wrong.
    ``--audit`` reports every PMID + its real title and exits nonzero if any does not resolve.
  * CONCORDANCE (model step, run as a workflow) — ``--bundle`` emits, per causal edge, the edge's
    claim plus the fetched title+abstract of each of its PMIDs, so an agent can judge whether the
    paper actually supports THIS edge's sign/claim. Only agent-confirmed PMIDs are then kept.

Network access is the same outbound-HTTP path ``verify_ontology_ids.py`` already uses. Results are
cached under ``benchmarks/.citation_cache/`` (gitignored) so re-runs are offline.

Usage:
  uv run python scripts/verify_citations.py --audit  benchmarks/human/systems/isolated_connections.yaml ...
  uv run python scripts/verify_citations.py --bundle out.json  <fragment.yaml> ...
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "benchmarks" / ".citation_cache"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# PMID appears as "PMID 12345", "PMID:12345", "PubMed 12345", "(PMID 12345)" etc.
PMID_RE = re.compile(r"(?:PMID|PubMed)\s*:?\s*(\d{4,9})", re.IGNORECASE)


def extract_pmids(text: str) -> list[int]:
    return [int(m) for m in PMID_RE.findall(text or "")]


def _get(url: str, retries: int = 3) -> str:
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    return ""


def fetch_summaries(pmids: list[int]) -> dict[int, dict]:
    """{pmid: {found: bool, title: str}} via batched esummary (cached per pmid)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out: dict[int, dict] = {}
    todo: list[int] = []
    for p in pmids:
        f = CACHE / f"sum_{p}.json"
        if f.exists():
            out[p] = json.loads(f.read_text())
        else:
            todo.append(p)
    for i in range(0, len(todo), 180):
        batch = todo[i : i + 180]
        ids = ",".join(str(p) for p in batch)
        url = f"{EUTILS}/esummary.fcgi?db=pubmed&retmode=json&id={ids}"
        try:
            data = json.loads(_get(url)).get("result", {})
        except Exception:  # noqa: BLE001
            data = {}
        for p in batch:
            rec = data.get(str(p))
            entry = {"found": bool(rec and "title" in rec and not rec.get("error")),
                     "title": (rec or {}).get("title", "")}
            (CACHE / f"sum_{p}.json").write_text(json.dumps(entry))
            out[p] = entry
        time.sleep(0.34)  # NCBI: <=3 req/s without an API key
    return out


def fetch_abstracts(pmids: list[int]) -> dict[int, str]:
    """{pmid: abstract_text} via batched efetch XML, parsed PER-PMID (cached per pmid).

    Uses retmode=xml and maps each <PubmedArticle>'s <PMID> to its concatenated <AbstractText>
    so the abstract returned for a PMID is genuinely that article's (the earlier text-mode batch
    blob conflated records and caused false concordance rejections).
    """
    import xml.etree.ElementTree as ET

    CACHE.mkdir(parents=True, exist_ok=True)
    out: dict[int, str] = {}
    todo: list[int] = []
    for p in pmids:
        f = CACHE / f"abs_{p}.txt"
        if f.exists():
            out[p] = f.read_text()
        else:
            todo.append(p)
    for i in range(0, len(todo), 50):
        batch = todo[i : i + 50]
        ids = ",".join(str(p) for p in batch)
        url = f"{EUTILS}/efetch.fcgi?db=pubmed&retmode=xml&id={ids}"
        parsed: dict[int, str] = {}
        try:
            root = ET.fromstring(_get(url))
            for art in root.iter("PubmedArticle"):
                pid_el = art.find(".//MedlineCitation/PMID")
                if pid_el is None or not (pid_el.text or "").isdigit():
                    continue
                pid = int(pid_el.text)
                parts = []
                for ab in art.iter("AbstractText"):
                    label = ab.get("Label")
                    txt = "".join(ab.itertext()).strip()
                    parts.append(f"{label}: {txt}" if label else txt)
                parsed[pid] = " ".join(parts).strip()
        except Exception:  # noqa: BLE001
            parsed = {}
        for p in batch:
            txt = parsed.get(p, "")
            (CACHE / f"abs_{p}.txt").write_text(txt)
            out[p] = txt
        time.sleep(0.34)
    return out


CORPUS = ["benchmarks/guyton/*.yaml", "benchmarks/human/systems/*.yaml", "benchmarks/multiscale/*.yaml"]


def scan(paths: list[str]) -> list[dict]:
    """Return [{file, source, target, evidence, pmids:[...]}] for every edge with >=1 PMID."""
    edges = []
    for ps in paths:
        for f in sorted(Path(ROOT).glob(ps)) if "*" in ps else [Path(ps)]:
            data = yaml.safe_load(Path(f).read_text()) or {}
            for e in (data.get("causal_edges") or []):
                ev = e.get("evidence") or ""
                pm = sorted(set(extract_pmids(ev)))
                if pm:
                    edges.append({"file": str(f), "source": e.get("source"),
                                  "target": e.get("target"), "sign": e.get("sign"),
                                  "mechanism": e.get("mechanism"), "evidence": ev, "pmids": pm})
    return edges


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("--audit", "--bundle"):
        print(__doc__)
        return 2
    mode = argv[0]
    if mode == "--bundle":
        out_path = argv[1]
        paths = argv[2:] or CORPUS
    else:
        out_path = None
        paths = argv[1:] or CORPUS

    edges = scan(paths)
    all_pmids = sorted({p for e in edges for p in e["pmids"]})
    print(f"scanned: {len(edges)} edges citing PMIDs; {len(all_pmids)} distinct PMIDs", file=sys.stderr)
    summ = fetch_summaries(all_pmids)
    missing = [p for p in all_pmids if not summ.get(p, {}).get("found")]

    if mode == "--audit":
        print(f"PMIDs resolved: {len(all_pmids) - len(missing)}/{len(all_pmids)}")
        for p in missing:
            citing = [f"{e['source']}->{e['target']}" for e in edges if p in e["pmids"]]
            print(f"  NOT FOUND  PMID {p}   (cited by: {', '.join(citing[:3])})")
        Path(ROOT / "benchmarks/results/citation_audit.json").write_text(
            json.dumps({str(p): summ[p] for p in all_pmids}, indent=1))
        print(f"wrote benchmarks/results/citation_audit.json", file=sys.stderr)
        if missing:
            print(f"RESULT: FAIL ({len(missing)} cited PMIDs do not exist in PubMed)")
            return 1
        print("RESULT: OK (every cited PMID exists; run --bundle for concordance)")
        return 0

    # --bundle: emit per-edge bundles with real titles+abstracts for the concordance fan-out
    abstracts = fetch_abstracts(all_pmids)
    bundles = []
    for e in edges:
        recs = [{"pmid": p, "found": summ.get(p, {}).get("found", False),
                 "real_title": summ.get(p, {}).get("title", ""),
                 "abstract": abstracts.get(p, "")[:4000]} for p in e["pmids"]]
        bundles.append({**{k: e[k] for k in ("file", "source", "target", "sign", "mechanism")},
                        "claim_evidence": e["evidence"], "records": recs})
    Path(out_path).write_text(json.dumps(bundles, indent=1))
    print(f"wrote {out_path}: {len(bundles)} edge bundles", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
