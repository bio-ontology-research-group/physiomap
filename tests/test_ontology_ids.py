"""Every ontology IRI in the corpus must exist and match its intended label.

Two tiers:
  * **offline (always runs):** every IRI used in the fixtures + ``partof.yaml`` must be in the
    checked-in manifest ``ontology/verified_ids.yaml`` (canonical OBO label per IRI), the labels
    asserted in ``partof.yaml`` must match that canonical label, and no manifest label may be
    empty or obsolete. A new/typo'd IRI fails until it is OBO-verified and added to the manifest.
  * **network-gated:** if the OBO cache is present (``scripts/verify_ontology_ids.py --refresh``
    primes it), re-check the manifest against the live OBO files — existence, non-obsolescence,
    exact label match — so the manifest can never silently drift. Skipped when the cache is absent.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "verify_ontology_ids", ROOT / "scripts" / "verify_ontology_ids.py"
)
vo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vo)

PREFIX_RE = re.compile(
    r"^(CHEBI|CL|GO|PATO|PR|UBERON):[A-Za-z0-9][A-Za-z0-9._-]*$"
)


def _manifest() -> dict[str, str]:
    data = yaml.safe_load((ROOT / "ontology" / "verified_ids.yaml").read_text())
    return data["ids"]


def test_every_corpus_id_is_in_verified_manifest():
    used, _ = vo.collect_ids()
    manifest = _manifest()
    missing = sorted(i for i in used if i not in manifest)
    assert not missing, (
        "ontology IRIs used but not OBO-verified — run "
        "`python scripts/verify_ontology_ids.py --write-manifest`: " + str(missing)
    )


def test_alphanumeric_protein_ontology_ids_are_collected_and_verified():
    used, _ = vo.collect_ids()
    expected = {"PR:Q9GZV9", "PR:Q9UEF7"}
    assert expected <= used
    assert expected <= set(_manifest())


def test_partof_labels_match_canonical():
    manifest = _manifest()
    pf = yaml.safe_load((ROOT / "ontology" / "partof.yaml").read_text())["entities"]
    bad = []
    for iri, rec in pf.items():
        lab, canon = rec.get("label"), manifest.get(iri)
        if lab and canon and vo.norm(lab) != vo.norm(canon):
            bad.append((iri, lab, canon))
    assert not bad, "partof.yaml labels differ from canonical OBO name: " + str(bad)


def test_manifest_labels_are_well_formed():
    for iri, label in _manifest().items():
        assert PREFIX_RE.match(iri), f"unexpected IRI shape: {iri}"
        assert label and label.strip(), f"empty label for {iri}"
        assert not label.lower().startswith("obsolete"), f"obsolete term in manifest: {iri} ({label})"


@pytest.mark.skipif(not vo.cache_present(),
                    reason="OBO cache absent; run scripts/verify_ontology_ids.py --refresh")
def test_manifest_matches_live_obo():
    terms = vo.parse_terms()
    not_found, obsolete, mismatch = [], [], []
    for iri, label in _manifest().items():
        t = terms.get(iri)
        if t is None:
            not_found.append(iri)
        elif t["obs"]:
            obsolete.append(iri)
        elif vo.norm(label) != vo.norm(t["name"]) and vo.norm(label) not in t["syn"]:
            mismatch.append((iri, label, t["name"]))
    assert not not_found, f"manifest IDs absent from OBO: {not_found}"
    assert not obsolete, f"manifest IDs now obsolete: {obsolete}"
    assert not mismatch, f"manifest labels drifted from OBO: {mismatch}"
