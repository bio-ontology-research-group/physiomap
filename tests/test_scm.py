"""Canonical SCM boundary: strict schema, lossless loader, explicit compatibility adapter."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from physiomap_core.model import ConstitutiveEdge, Node, PhysioMap, Scale, Sign
from physiomap_core.owl_projection import MigrationBuilder
from physiomap_core.scm import (
    ScmManifest,
    load_canonical_physiomap,
    load_canonical_scm,
)

ROOT = Path(__file__).resolve().parent.parent


def _manifest_with_derived_expression() -> ScmManifest:
    pmap = PhysioMap(
        nodes=[
            Node(id="part", label="Part", scale=Scale.CELLULAR),
            Node(id="whole", label="Whole", scale=Scale.ORGAN),
        ],
        constitutive_edges=[
            ConstitutiveEdge(
                micro="part", macro="whole", relation="aggregation", sign=Sign.PLUS
            )
        ],
    )
    _, manifest, _ = MigrationBuilder(ROOT / "projection/patterns.yaml").build(pmap)
    return manifest


def test_scm_nodes_are_strict_typed_nodes():
    manifest = _manifest_with_derived_expression()
    assert all(isinstance(node, Node) for node in manifest.nodes)
    malformed = manifest.model_dump(mode="json")
    malformed["nodes"][0] = {"id": "part", "nonsense": 42}
    with pytest.raises(ValidationError):
        ScmManifest.model_validate(malformed)


def test_generated_schema_forbids_unknown_node_fields():
    schema = ScmManifest.model_json_schema(mode="validation")
    node_schema = schema["$defs"]["Node"]
    assert node_schema["additionalProperties"] is False
    assert set(node_schema["required"]) >= {"id", "label", "scale"}


def test_canonical_loader_is_lossless_and_compatibility_loader_is_explicit(
    tmp_path, monkeypatch
):
    expected = _manifest_with_derived_expression()
    path = tmp_path / "scm.json"
    expected.write_json(path)
    monkeypatch.setenv("PHYSIOMAP_SCM_PATH", str(path))

    canonical = load_canonical_scm()
    assert isinstance(canonical, ScmManifest)
    assert canonical == expected
    assert [(q.kind, q.origin) for q in canonical.quantitative_expressions] == [
        ("aggregation", "derived")
    ]
    assert canonical.projection_traces

    compatibility = load_canonical_physiomap()
    assert isinstance(compatibility, PhysioMap)
    assert compatibility.quantitative_definitions == []


def test_released_canonical_loader_exposes_all_projection_layers(monkeypatch):
    monkeypatch.delenv("PHYSIOMAP_SCM_PATH", raising=False)
    manifest = load_canonical_scm()
    assert len(manifest.quantitative_expressions) == 9
    assert {expression.origin for expression in manifest.quantitative_expressions} == {
        "authored", "derived"
    }
    assert len(manifest.projection_traces) == 2387
    assert len([edge for edge in manifest.influences if edge.context]) == 2
