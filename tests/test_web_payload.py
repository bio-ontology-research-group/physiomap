import gzip
import json
from pathlib import Path

from web.export_data import (
    BOOTSTRAP_GZIP_LIMIT,
    WEB,
    _build_date,
    load_exported_web_payload,
    split_web_payload,
    sync_web_payload,
)


def _toy_payload() -> dict:
    return {
        "version": "test",
        "generated": "2026-07-14",
        "git_commit": "deadbee",
        "ontology": {"iri": "https://example.org/ontology"},
        "projection_version": "test",
        "nodes": [{
            "id": "n", "label": "Node", "scale": "organism", "system": "Test",
            "source": "fixture", "entity_iri": "CHEBI:1", "quality_iri": "PATO:1",
            "scc": 0, "in_big_scc": True, "x": 1.0, "y": 2.0,
        }],
        "causal_edges": [{
            "id": "i", "source": "n", "target": "n", "sign": "+", "kind": "causal",
            "context": None, "context_id": None, "definitional": False, "modulated": False,
            "prov_source": "fixture", "evidence": "evidence retained in a detail bucket",
        }],
        "production_edges": [],
        "constitutive_edges": [],
        "quantitative_definitions": [],
        "modulation_edges": [],
        "interventions": [{
            "id": "raise_n", "label": "Raise N", "benchmark": "toy", "contexts": ["fed"],
            "do": {"n": "+"}, "predicted": {"n": "+"}, "phenotypes": [], "affected": [],
        }],
        "systems": ["Test"], "sources": ["fixture"], "default_hidden_sources": [],
        "synonyms": {}, "scales": ["organism"],
        "stats": {"n_nodes": 1, "n_causal": 1, "big_scc_size": 1},
    }


def test_build_date_is_the_versioned_release_date():
    assert _build_date() == "2026-07-31"


def test_sharded_payload_is_deterministic_lossless_and_stale_checked(tmp_path: Path):
    logical = _toy_payload()
    first = split_web_payload(logical)
    second = split_web_payload(logical)

    assert first == second
    assert gzip.decompress(first[Path("physiomap.json.gz")]) == first[Path("physiomap.json")]
    assert first[Path("physiomap.json.gz")][4:8] == b"\0\0\0\0"  # deterministic mtime

    sync_web_payload(first, tmp_path)
    sync_web_payload(first, tmp_path, check=True)
    assert load_exported_web_payload(tmp_path) == logical

    (tmp_path / "data/details/0.json").write_text("stale", encoding="utf-8")
    try:
        sync_web_payload(first, tmp_path, check=True)
    except RuntimeError as error:
        assert "data/details/0.json" in str(error)
    else:  # pragma: no cover - protects the test itself
        raise AssertionError("stale generated shard was not detected")


def test_committed_bootstrap_is_small_compressed_and_full_export_is_recoverable():
    bootstrap_bytes = (WEB / "physiomap.json").read_bytes()
    compressed = (WEB / "physiomap.json.gz").read_bytes()
    bootstrap = json.loads(bootstrap_bytes)

    assert gzip.decompress(compressed) == bootstrap_bytes
    assert len(compressed) <= BOOTSTRAP_GZIP_LIMIT
    assert bootstrap["web_payload_format"] == "2.0.0"
    assert all("asserted_axioms" not in node and "_detail_bucket" in node
               for node in bootstrap["nodes"])
    assert all("entity_iri" in node and "quality_iri" in node for node in bootstrap["nodes"])
    assert all("predicted" not in case and "_intervention_bucket" in case
               for case in bootstrap["interventions"])

    logical = load_exported_web_payload()
    assert logical["stats"] == {
        "n_nodes": 1699,
        "n_causal": 2268,
        "n_production": 85,
        "n_constitutive": 4,
        "n_quantitative": 9,
        "n_modulation": 19,
        "n_sccs": 1448,
        "big_scc_size": 213,
    }
    assert len(logical["interventions"]) == 92
    hyperinsulinemia = next(case for case in logical["interventions"]
                            if case["id"] == "hyperinsulinemia")
    assert hyperinsulinemia["contexts"] == ["fed-state-hepatic-lipogenesis"]
    # The full canonical map has additional opposing paths and may therefore abstain even after
    # the direct fed-state influence is selected; the important transport contract is that the
    # declared slice reaches the web solve and remains visible to the user.
    assert hyperinsulinemia["predicted"]["vldl_secretion"] in {"+", "?"}
    assert logical["nodes"][0]["asserted_axioms"]


def test_deployment_location_serves_precompressed_json():
    config = (WEB / "deploy/nginx-physiomap-location.conf").read_text(encoding="utf-8")
    assert "location /physiomap/" in config
    assert "gzip_static on;" in config
    assert "application/json" in config
    assert 'Cache-Control "no-cache"' in config
