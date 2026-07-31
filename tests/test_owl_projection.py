from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
import yaml

from physiomap_core.model import (CausalEdge, InfluenceContext, ModulationEdge, Node, PhysioMap,
                                  ProductionEdge, ProductionEvidenceClass,
                                  QuantitativeArgumentDefinition,
                                  QuantitativeDefinition, RatioDefinition, Scale, Sign)
from physiomap_core.owl_projection import (
    MigrationBuilder,
    RegistryTerm,
    source_registry,
    verify_elk_projection,
    write_artifacts,
    write_source_registry_cache,
)
from physiomap_core.scm import ScmManifest

ROOT = Path(__file__).resolve().parent.parent


def sample() -> PhysioMap:
    nodes = [Node(id=x, label=x.upper(), scale=Scale.CELLULAR) for x in "abcd"]
    return PhysioMap(nodes=nodes,
        causal_edges=[CausalEdge(source="a", target="b", sign=Sign.PLUS)],
        modulation_edges=[ModulationEdge(modulator="c", edge_source="a", edge_target="b",
                                         sign=Sign.MINUS)],
        ratio_definitions=[RatioDefinition(ratio="d", numerator="a", denominator="b")])


def test_projection_round_trip_and_named_modulation():
    owl, scm, report = MigrationBuilder(ROOT / "projection/patterns.yaml").build(sample())
    assert "ObjectSomeValuesFrom(pm:causedBy <https://w3id.org/physiomap/trait/a>)" in owl
    assert scm.modulation[0].influence_id == scm.influences[0].id
    assert scm.to_physiomap() == sample()
    assert report["summary"]["incomplete_traits"] == 4
    assert scm.influences[0].evidence_status == "legacy-evidence-unclassified"
    assert report["causal_policy"]["approval_status"] == "approved"


def test_source_registry_uses_frozen_cache_without_raw_obo_files(tmp_path):
    cache = tmp_path / "ontology/.obo_cache"
    registry_path = cache.parent / "registry/used-terms.json"
    registry_path.parent.mkdir(parents=True)
    identifier = "PATO:0000001"
    term = RegistryTerm(
        identifier=identifier,
        label="quality",
        synonyms=(),
        parents=(),
        obsolete=False,
        replaced_by=None,
        source="PATO.obo",
    )
    write_source_registry_cache(
        registry_path,
        {identifier},
        {identifier: term},
        {"PATO.obo": "frozen-source-checksum"},
    )

    loaded, checksums, mode = source_registry(cache, {identifier}, registry_path)

    assert set(loaded) == {identifier}
    assert loaded[identifier].label == term.label
    assert loaded[identifier].source == term.source
    assert checksums == {"PATO.obo": "frozen-source-checksum"}
    assert mode == "checksum-bound-cache"


def test_typed_product_is_not_projected_as_a_causal_influence():
    nodes = [Node(id=x, label=x, scale=Scale.ORGAN_SYSTEM) for x in ("hr", "sv", "co")]
    definition = QuantitativeDefinition(
        kind="product",
        result="co",
        arguments=[
            QuantitativeArgumentDefinition(node="hr", role="factor", derivative_sign=Sign.PLUS),
            QuantitativeArgumentDefinition(node="sv", role="factor", derivative_sign=Sign.PLUS),
        ],
        mechanism="CO = HR × SV",
        evidence="fixture",
    )
    pmap = PhysioMap(nodes=nodes, quantitative_definitions=[definition])
    owl, scm, _ = MigrationBuilder(ROOT / "projection/patterns.yaml").build(pmap)

    assert not scm.influences
    assert [(q.kind, q.origin, q.result) for q in scm.quantitative_expressions] == [
        ("product", "authored", "co")
    ]
    assert "trait/co> ObjectSomeValuesFrom(pm:hasFactor" in owl
    assert scm.to_physiomap() == pmap


def test_typed_production_is_not_projected_as_a_causal_influence():
    nodes = [Node(id=x, label=x, scale=Scale.CELLULAR) for x in ("secretion", "pool")]
    edge = ProductionEdge(
        source="secretion",
        target="pool",
        sign=Sign.PLUS,
        production_evidence=ProductionEvidenceClass.LEGACY_UNCLASSIFIED,
    )
    pmap = PhysioMap(nodes=nodes, production_edges=[edge])
    owl, scm, _ = MigrationBuilder(ROOT / "projection/patterns.yaml").build(pmap)

    assert not scm.influences
    assert [(item.source, item.target) for item in scm.production_relations] == [
        ("secretion", "pool")
    ]
    assert "ObjectSomeValuesFrom(pm:hasMember ObjectSomeValuesFrom(pm:producedBy" in owl
    assert scm.to_physiomap() == pmap


def test_projection_rejects_legacy_definitional_causal_edge():
    nodes = [Node(id=x, label=x, scale=Scale.CELLULAR) for x in ("a", "b")]
    pmap = PhysioMap(
        nodes=nodes,
        causal_edges=[CausalEdge(source="a", target="b", sign=Sign.PLUS, definitional=True)],
    )
    with pytest.raises(ValueError, match="use quantitative_definitions"):
        MigrationBuilder(ROOT / "projection/patterns.yaml").build(pmap)


def test_approved_opposing_sign_contexts_are_preserved():
    nodes = [Node(id="plasma_insulin", label="insulin", scale=Scale.ORGAN_SYSTEM),
             Node(id="vldl_secretion", label="VLDL secretion", scale=Scale.ORGAN_SYSTEM)]
    pmap = PhysioMap(nodes=nodes, causal_edges=[
        CausalEdge(source="plasma_insulin", target="vldl_secretion", sign=Sign.PLUS,
                   context=InfluenceContext(
                       id="fed-state-hepatic-lipogenesis",
                       label="fed-state hepatic lipogenesis and substrate supply",
                   ), mechanism="lipogenesis", evidence="fixture"),
        CausalEdge(source="plasma_insulin", target="vldl_secretion", sign=Sign.MINUS,
                   context=InfluenceContext(
                       id="direct-hepatic-insulin-signaling",
                       label=("direct hepatic insulin signaling and suppression of "
                              "fatty-acid flux"),
                   ), mechanism="direct signaling", evidence="fixture"),
    ])
    owl, scm, _ = MigrationBuilder(ROOT / "projection/patterns.yaml").build(pmap)
    contexts = {edge.sign: edge.context.label for edge in scm.influences if edge.context}
    assert contexts == {
        "+": "fed-state hepatic lipogenesis and substrate supply",
        "-": "direct hepatic insulin signaling and suppression of fatty-acid flux",
    }
    assert len({edge.id for edge in scm.influences}) == 2
    assert owl.count("pm:influenceContext") == 3  # declaration plus two axiom annotations
    assert owl.count("pm:contextId") == 3
    assert scm.to_physiomap().causal_subgraph().edges[
        "plasma_insulin", "vldl_secretion"
    ]["sign"] == "?"


def test_generation_is_byte_deterministic(tmp_path):
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    outputs = []
    for directory in (tmp_path / "one", tmp_path / "two"):
        write_artifacts(directory, *builder.build(sample()))
        outputs.append({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in directory.iterdir()})
    assert outputs[0] == outputs[1]
    assert ScmManifest.from_json(tmp_path / "one/physiomap-scm.json").to_physiomap() == sample()


def test_complete_scm_is_reconstructed_from_owl_and_registry_only(tmp_path):
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    owl, expected, _ = builder.build(sample())
    owl_path = tmp_path / "standalone.owl"
    owl_path.write_text(owl, encoding="utf-8")

    # A fresh projector receives no PhysioMap/YAML input and recovers every typed record and trace.
    recovered = MigrationBuilder(ROOT / "projection/patterns.yaml").project_owl(owl_path)
    assert recovered == expected
    assert len(recovered.nodes) == 4
    assert len(recovered.influences) == 1
    assert len(recovered.quantitative_expressions) == 1
    assert len(recovered.modulation) == 1
    assert recovered.projection_traces == expected.projection_traces


def test_owl_projection_fails_if_a_record_is_detached_from_its_axiom():
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    owl, _, _ = builder.build(sample())
    tampered = "\n".join(
        line for line in owl.splitlines() if "Annotation(pm:influenceId" not in line
    ) + "\n"
    with pytest.raises(ValueError, match="lacks its OWL witness"):
        builder.project_owl(tampered)


def test_owl_projection_fails_on_missing_embedded_record():
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    owl, _, _ = builder.build(sample())
    lines = owl.splitlines()
    record_index = next(i for i, line in enumerate(lines)
                        if "pm:scmProjectionRecord" in line and "AnnotationAssertion" in line)
    del lines[record_index]
    with pytest.raises(ValueError, match="record sequence is incomplete"):
        builder.project_owl("\n".join(lines) + "\n")


def test_owl_projection_registry_version_must_match(tmp_path):
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    owl, _, _ = builder.build(sample())
    registry = yaml.safe_load((ROOT / "projection/patterns.yaml").read_text())
    registry["version"] = "99.0.0"
    path = tmp_path / "patterns.yaml"
    path.write_text(yaml.safe_dump(registry))
    with pytest.raises(ValueError, match="does not match projection registry"):
        MigrationBuilder(path).project_owl(owl)


def test_projection_registry_rejects_unknown_reasoning_mode(tmp_path):
    registry = yaml.safe_load((ROOT / "projection/patterns.yaml").read_text())
    registry["patterns"][0]["reasoning_mode"] = "silently-ignore"
    path = tmp_path / "patterns.yaml"
    path.write_text(yaml.safe_dump(registry))
    with pytest.raises(ValueError, match="unsupported reasoning mode"):
        MigrationBuilder(path)


def test_elk_projection_equivalence_detects_missing_and_extra(tmp_path):
    _, scm, _ = MigrationBuilder(ROOT / "projection/patterns.yaml").build(sample())
    path = tmp_path / "entailed.tsv"
    path.write_text("pattern_id\targ1\targ2\targ3\n"
                    "causal-collection-v2\ta\tb\t\n"
                    "ratio-v1\td\ta\tb\n"
                    "multiplicative-modulation-v2\tc\ta\tb\n")
    assert verify_elk_projection(path, scm)["causal-collection-v2"] == 1
    path.write_text(path.read_text().replace("ratio-v1\td\ta\tb\n", ""))
    with pytest.raises(ValueError, match="ELK/SCM projection mismatch"):
        verify_elk_projection(path, scm)


def _phene_map() -> PhysioMap:
    """Two blood-volume parts plus a process trait and an intensive trait."""
    nodes = [
        Node(id="blood_volume", label="blood volume", scale=Scale.ORGAN_SYSTEM,
             entity_iri="UBERON:0000178", quality_iri="PATO:0000918"),
        Node(id="plasma_volume", label="plasma volume", scale=Scale.ORGAN_SYSTEM,
             entity_iri="UBERON:0001969", quality_iri="PATO:0000918"),
        Node(id="hepatic_gluconeogenesis", label="hepatic gluconeogenesis rate",
             scale=Scale.ORGAN, entity_iri="GO:0006094", quality_iri="PATO:0000161",
             bearer_entity_iri="UBERON:0002107"),
        Node(id="arterial_pressure", label="mean arterial pressure", scale=Scale.ORGAN_SYSTEM,
             entity_iri="UBERON:0001637", quality_iri="PATO:0001595"),
    ]
    return PhysioMap(nodes=nodes,
                     causal_edges=[CausalEdge(source="blood_volume", target="arterial_pressure",
                                              sign=Sign.PLUS)])


def test_trait_uses_the_phene_pattern_with_the_right_context_relation():
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    owl, _, _ = builder.build(_phene_map())
    assert "pm:hasEntity" not in owl and "pm:hasAttribute" not in owl
    # a continuant trait: has a continuant part that bears the entity-specific quality
    assert ("SubClassOf(<https://w3id.org/physiomap/trait/plasma_volume> "
            "ObjectSomeValuesFrom(pm:hasContinuantPart ObjectIntersectionOf("
            "<http://purl.obolibrary.org/obo/UBERON_0001969> "
            "ObjectSomeValuesFrom(pm:hasQuality") in owl
    # a process trait localizes with occursIn, never with parthood
    assert ("ObjectSomeValuesFrom(pm:hasOccurrentPart ObjectIntersectionOf("
            "<http://purl.obolibrary.org/obo/GO_0006094> "
            "ObjectSomeValuesFrom(pm:occursIn "
            "<http://purl.obolibrary.org/obo/UBERON_0002107>)") in owl
    assert ("SubObjectPropertyOf(ObjectPropertyChain(pm:occursIn pm:partOf) pm:occursIn)") in owl
    assert "SubClassOf(<https://w3id.org/physiomap/trait/plasma_volume> pm:MapVariable)" in owl


def test_mechanism_relations_are_asserted_of_the_trait_collection():
    """A causal edge claims a witness in the target's collection, not a property of every bearer."""
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    owl, manifest, _ = builder.build(_phene_map())
    target = "<https://w3id.org/physiomap/trait/arterial_pressure>"
    source = "<https://w3id.org/physiomap/trait/blood_volume>"
    # the plain subclass form -- false of any bearer whose source arm is blocked -- is gone
    assert f"SubClassOf({target} ObjectSomeValuesFrom(pm:causedBy {source}))" not in owl
    collection = re.search(
        r"AnnotationAssertion\(pm:collectionFor (<[^>]+>) \"arterial_pressure\"\)", owl
    )[1]
    assert f"SubClassOf({target} ObjectSomeValuesFrom(pm:memberOf {collection}))" in owl
    assert f"SubClassOf({collection} ObjectSomeValuesFrom(pm:hasMember {target}))" in owl
    assert (f"{collection} ObjectSomeValuesFrom(pm:hasMember "
            f"ObjectSomeValuesFrom(pm:causedBy {source}))") in owl
    trace = {t.trace_id: t for t in manifest.projection_traces}
    influence = manifest.influences[0]
    assert trace[influence.trace_ids[0]].pattern_id == "causal-collection-v2"


def test_collection_singleton_and_homogeneity_stay_out_of_el(tmp_path):
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    owl, manifest, report = builder.build(_phene_map())
    write_artifacts(tmp_path, owl, manifest, report, dl_owl=builder.dl_owl)
    el = (tmp_path / "physiomap-el.owl").read_text()
    dl = (tmp_path / "physiomap-dl.owl").read_text()
    assert "ObjectAllValuesFrom(pm:hasMember" in dl and "ObjectAllValuesFrom(pm:hasMember" not in el
    assert "ObjectOneOf(" in dl and "ObjectOneOf(" not in el
    assert "InverseObjectProperties(pm:hasMember pm:memberOf)" in dl


def test_part_inclusive_grouping_is_minted_only_for_composable_qualities():
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    _, _, report = builder.build(_phene_map())
    groupings = {g["quality_iri"]: g for g in report["groupings"]}
    assert "PATO:0000918" in groupings                      # volume is extensive: composes
    assert "PATO:0001595" not in groupings                  # pressure is intensive: must not
    assert set(groupings["PATO:0000918"]["expected_members"]) == {"blood_volume", "plasma_volume"}
    assert groupings["PATO:0000918"]["entity_iri"] == "UBERON:0000178"


def test_dl_artifact_carries_the_axioms_outside_el(tmp_path):
    builder = MigrationBuilder(ROOT / "projection/patterns.yaml")
    owl, manifest, report = builder.build(_phene_map())
    write_artifacts(tmp_path, owl, manifest, report, dl_owl=builder.dl_owl)
    el = (tmp_path / "physiomap-el.owl").read_text()
    dl = (tmp_path / "physiomap-dl.owl").read_text()
    universal = ("SubClassOf(pm:ProcessQuality "
                 "ObjectAllValuesFrom(pm:qualityOf pm:Process))")
    assert universal in dl and universal not in el
    assert "InverseObjectProperties(pm:hasPart pm:partOf)" in dl
    assert "InverseObjectProperties" not in el
    assert "SubClassOf(<http://purl.obolibrary.org/obo/GO_0006094> pm:Process)" in dl
    assert el.splitlines()[:5] == dl.splitlines()[:5]
