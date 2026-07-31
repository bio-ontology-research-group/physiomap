"""Offline tests for the citation-verification stage (PMID extraction + edge scan)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("verify_citations", ROOT / "scripts" / "verify_citations.py")
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)


def test_extract_pmids_handles_formats():
    txt = ("Meynard 2009 PMID 19252498; (PMID:18451267); PubMed 14647275; "
           "no-cite here; OMIM 248600 should NOT match; pmid 26001")
    assert vc.extract_pmids(txt) == [19252498, 18451267, 14647275, 26001]


def test_extract_pmids_empty():
    assert vc.extract_pmids("") == []
    assert vc.extract_pmids("OMIM 235200 only, no pubmed id") == []


def test_scan_finds_cited_edges(tmp_path):
    frag = tmp_path / "f.yaml"
    frag.write_text(
        "name: t\nnodes:\n- {id: a, label: A, scale: molecular}\n"
        "- {id: b, label: B, scale: molecular}\n"
        "causal_edges:\n"
        "- {source: a, target: b, sign: '+', evidence: 'mechanism X, PMID 12345 and PMID 67890'}\n"
        "- {source: b, target: a, sign: '-', evidence: 'textbook only, no pmid'}\n"
    )
    edges = vc.scan([str(frag)])
    assert len(edges) == 1                      # only the edge that cites a PMID
    assert edges[0]["pmids"] == [12345, 67890]
    assert edges[0]["source"] == "a"
