#!/usr/bin/env python3
"""Generate the auditable review queue for the 621 legacy causal influences.

The frozen baseline prevents an influence from disappearing merely because a source
YAML edge was deleted or its mechanism changed. Resolution requires an approved entry
in ``ontology/legacy-evidence-decisions.yaml`` whose outcome agrees with the canonical
SCM. The generated worklist contains every item not yet approved and resolved.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from physiomap_core.model import PhysioMap
from physiomap_core.scm import ScmManifest, canonical_scm_path
from scripts.build_owl_scm import ROOT, default_fragments

BASELINE = ROOT / "ontology/registry/legacy-evidence-baseline.json"
LEDGER = ROOT / "ontology/legacy-evidence-decisions.yaml"
JSON_OUT = ROOT / "docs/generated/legacy-evidence-worklist.json"
TSV_OUT = ROOT / "docs/generated/legacy-evidence-worklist.tsv"
ACCEPT = {"perturbation", "pharmacological", "genetic_lof_gof",
          "mendelian_randomization", "mechanistic_model", "curated_mechanistic"}
REMOVE = {"rejected_not_causal", "reclassified_constitutive",
          "reclassified_quantitative", "reclassified_production", "duplicate_removed"}
SUPERSEDE = {"superseded_by_scientific_correction"}


def work_item_id(source: str, target: str, sign: str) -> str:
    digest = hashlib.sha256(f"{source}\0{target}\0{sign}".encode()).hexdigest()[:20]
    return f"legacy-evidence-{digest}"


def source_owners() -> dict[tuple[str, str, str], dict[str, Any]]:
    """Return the effective (last-merged) source location for every causal triple."""
    owners: dict[tuple[str, str, str], dict[str, Any]] = {}
    for path in default_fragments():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for index, edge in enumerate(data.get("causal_edges") or []):
            key = (edge["source"], edge["target"], str(edge["sign"]))
            owners[key] = {"source_file": path.relative_to(ROOT).as_posix(),
                           "yaml_edge_index": index}
    return owners


def source_influences() -> dict[tuple[str, str, str], Any]:
    """Return the effective authored causal edge for every signed triple."""
    pmap = PhysioMap.load_composed(default_fragments(), name="physiomap")
    return {(edge.source, edge.target, edge.sign.value): edge for edge in pmap.causal_edges}


def _causal_class(edge: Any | None) -> str | None:
    value = getattr(edge, "causal_evidence", None)
    return getattr(value, "value", value)


def validate_decision_application(
    work_item_id: str,
    decision: dict[str, Any],
    source_edge: Any | None,
    released_edge: Any | None,
    replacement_source_edge: Any | None = None,
    replacement_released_edge: Any | None = None,
) -> None:
    """Enforce the human-approval boundary in both source and released state.

    A proposal records a prospective decision only.  Until it is approved, the
    original legacy influence must remain present and evidence-unclassified in the
    authoring YAML and canonical SCM.  Approved decisions must be reflected in both.
    """
    outcome = decision["decision"]
    replacement = None
    if outcome in SUPERSEDE:
        replacement = decision.get("replacement")
        required = {"source", "target", "sign", "causal_evidence", "source_file"}
        if not isinstance(replacement, dict) or required - set(replacement):
            raise ValueError(
                f"scientific supersession lacks a complete replacement: {work_item_id}"
            )
        if str(replacement["sign"]) not in {"+", "-", "?"}:
            raise ValueError(
                f"scientific supersession replacement has invalid sign: {work_item_id}"
            )
        if replacement["causal_evidence"] not in ACCEPT:
            raise ValueError(
                f"scientific supersession replacement has invalid evidence class: {work_item_id}"
            )

    if decision["status"] == "proposed":
        for layer, edge in (("source YAML", source_edge), ("canonical SCM", released_edge)):
            if edge is None:
                raise ValueError(
                    f"proposed decision prematurely removed/reclassified in {layer}: {work_item_id}"
                )
            if _causal_class(edge) is not None:
                raise ValueError(
                    f"proposed promotion prematurely reflected in {layer}: {work_item_id}"
                )
            if layer == "canonical SCM" and edge.evidence_status != "legacy-evidence-unclassified":
                raise ValueError(
                    f"proposed decision has inconsistent released evidence status: {work_item_id}"
                )
        return

    if outcome in ACCEPT:
        for layer, edge in (("source YAML", source_edge), ("canonical SCM", released_edge)):
            if edge is None or _causal_class(edge) != outcome:
                raise ValueError(
                    f"approved promotion not reflected in {layer}: {work_item_id}"
                )
        if released_edge.evidence_status != "controlled":
            raise ValueError(f"approved promotion has inconsistent SCM status: {work_item_id}")
    elif outcome in REMOVE:
        if source_edge is not None or released_edge is not None:
            raise ValueError(
                f"approved removal/reclassification still causal: {work_item_id}"
            )
    elif outcome in SUPERSEDE:
        if source_edge is not None or released_edge is not None:
            raise ValueError(
                f"superseded causal influence is still present: {work_item_id}"
            )
        for layer, edge in (
            ("source YAML", replacement_source_edge),
            ("canonical SCM", replacement_released_edge),
        ):
            if edge is None or _causal_class(edge) != replacement["causal_evidence"]:
                raise ValueError(
                    f"approved scientific supersession replacement not reflected in {layer}: "
                    f"{work_item_id}"
                )
        if replacement_released_edge.evidence_status != "controlled":
            raise ValueError(
                f"scientific supersession replacement has inconsistent SCM status: {work_item_id}"
            )
    else:
        raise ValueError(f"invalid decision outcome for {work_item_id}: {outcome}")


def initialize_baseline(path: Path) -> None:
    pmap = PhysioMap.load_composed(default_fragments(), name="physiomap")
    scm = ScmManifest.from_json(canonical_scm_path())
    influence = {(edge.source, edge.target, edge.sign): edge for edge in scm.influences}
    owners = source_owners()
    items = []
    for edge in pmap.causal_edges:
        if edge.causal_evidence is not None:
            continue
        key = (edge.source, edge.target, edge.sign.value)
        projected = influence[key]
        items.append({"work_item_id": work_item_id(*key),
                      "source": key[0], "target": key[1], "sign": key[2],
                      "original_influence_id": projected.id,
                      "original_source_file": owners[key]["source_file"],
                      "original_yaml_edge_index": owners[key]["yaml_edge_index"]})
    payload = {"schema_version": "1.0.0", "frozen_policy": "approved-2026-07-11",
               "description": "Immutable inventory of causal influences awaiting evidence review",
               "total": len(items), "items": sorted(items, key=lambda x: x["work_item_id"])}
    if len(items) != 621:
        raise SystemExit(f"refusing to initialize baseline: expected 621 items, found {len(items)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_outputs() -> tuple[str, str]:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    ledger_data = yaml.safe_load(LEDGER.read_text(encoding="utf-8")) or {}
    decisions = ledger_data.get("decisions") or []
    by_id = {item["work_item_id"]: item for item in decisions}
    if len(by_id) != len(decisions):
        raise ValueError("duplicate work_item_id in legacy evidence decision ledger")

    scm = ScmManifest.from_json(canonical_scm_path())
    current = {(edge.source, edge.target, edge.sign): edge for edge in scm.influences}
    authored = source_influences()
    owners = source_owners()
    open_items, resolved = [], Counter()
    for frozen in baseline["items"]:
        key = (frozen["source"], frozen["target"], frozen["sign"])
        edge = current.get(key)
        decision = by_id.get(frozen["work_item_id"])
        status = "unreviewed"
        if decision:
            required = {"work_item_id", "status", "decision", "reviewer", "reviewed_on",
                        "source_file", "rationale", "evidence_checked"}
            missing = required - set(decision)
            if missing:
                raise ValueError(f"decision {frozen['work_item_id']} lacks {sorted(missing)}")
            if decision["source_file"] != frozen["original_source_file"]:
                raise ValueError(f"decision source mismatch for {frozen['work_item_id']}")
            if not isinstance(decision["evidence_checked"], list) or not decision["evidence_checked"]:
                raise ValueError(f"decision evidence_checked must be a non-empty list: {frozen['work_item_id']}")
            if decision.get("status") not in {"proposed", "approved"}:
                raise ValueError(f"invalid decision status for {frozen['work_item_id']}")
            outcome = decision.get("decision")
            if outcome not in ACCEPT | REMOVE | SUPERSEDE:
                raise ValueError(f"invalid decision outcome for {frozen['work_item_id']}")
            status = "proposal-pending" if decision["status"] == "proposed" else "approved"
            if decision["status"] == "approved" and (
                not decision.get("approved_by") or not decision.get("approved_on")
            ):
                raise ValueError(f"approved decision lacks approval provenance: {frozen['work_item_id']}")

            replacement_source_edge = None
            replacement_released_edge = None
            if outcome in SUPERSEDE:
                replacement = decision.get("replacement")
                required_replacement = {
                    "source", "target", "sign", "causal_evidence", "source_file"
                }
                if not isinstance(replacement, dict) or required_replacement - set(replacement):
                    raise ValueError(
                        f"scientific supersession lacks a complete replacement: "
                        f"{frozen['work_item_id']}"
                    )
                if str(replacement["sign"]) not in {"+", "-", "?"}:
                    raise ValueError(
                        f"scientific supersession replacement has invalid sign for "
                        f"{frozen['work_item_id']}"
                    )
                if replacement["causal_evidence"] not in ACCEPT:
                    raise ValueError(
                        f"scientific supersession replacement has invalid evidence class for "
                        f"{frozen['work_item_id']}"
                    )
                replacement_key = (
                    replacement["source"],
                    replacement["target"],
                    str(replacement["sign"]),
                )
                if replacement_key == key:
                    raise ValueError(
                        f"scientific supersession repeats the original identity: "
                        f"{frozen['work_item_id']}"
                    )
                replacement_owner = owners.get(replacement_key)
                if replacement_owner is not None and (
                    replacement_owner["source_file"] != replacement["source_file"]
                ):
                    raise ValueError(
                        f"scientific supersession replacement source mismatch for "
                        f"{frozen['work_item_id']}"
                    )
                if decision["status"] == "approved" and replacement_owner is None:
                    raise ValueError(
                        f"approved scientific supersession replacement has no authored owner: "
                        f"{frozen['work_item_id']}"
                    )
                replacement_source_edge = authored.get(replacement_key)
                replacement_released_edge = current.get(replacement_key)

            validate_decision_application(
                frozen["work_item_id"],
                decision,
                authored.get(key),
                edge,
                replacement_source_edge,
                replacement_released_edge,
            )
            if decision["status"] == "approved":
                resolved[outcome] += 1
                continue
        location = owners.get(key, {"source_file": frozen["original_source_file"],
                                    "yaml_edge_index": frozen["original_yaml_edge_index"]})
        open_items.append({**frozen, **location, "review_status": status,
                           "current_influence_id": edge.id if edge else None,
                           "current_evidence_status": edge.evidence_status if edge else "missing-from-scm",
                           "current_causal_evidence": edge.causal_evidence if edge else None,
                           "context": edge.context.label if edge and edge.context else None,
                           "mechanism": edge.mechanism if edge else None,
                           "evidence": edge.evidence if edge else None,
                           "self_regulation": key[0] == key[1]})

    by_source = Counter(item["source_file"] for item in open_items)
    payload = {
        "schema_version": "1.0.0",
        "baseline": BASELINE.relative_to(ROOT).as_posix(),
        "decision_ledger": LEDGER.relative_to(ROOT).as_posix(),
        "canonical_scm": canonical_scm_path().relative_to(ROOT).as_posix(),
        "projection_version": scm.projection_version,
        "allowed_promotion_classes": sorted(ACCEPT),
        "allowed_noncausal_outcomes": sorted(REMOVE),
        "allowed_scientific_correction_outcomes": sorted(SUPERSEDE),
        "summary": {"baseline_total": baseline["total"], "open": len(open_items),
                    "approved_resolved": sum(resolved.values()),
                    "proposal_pending": sum(i["review_status"] == "proposal-pending"
                                            for i in open_items),
                    "by_source_file": dict(sorted(by_source.items())),
                    "approved_outcomes": dict(sorted(resolved.items()))},
        "items": sorted(open_items, key=lambda x: (x["source_file"], x["yaml_edge_index"],
                                                   x["work_item_id"])),
    }
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    stream = io.StringIO()
    fields = ["work_item_id", "source_file", "yaml_edge_index", "source", "target", "sign",
              "review_status", "current_evidence_status", "context", "self_regulation",
              "mechanism_excerpt", "evidence_excerpt"]
    writer = csv.DictWriter(stream, fieldnames=fields, dialect="excel-tab", lineterminator="\n")
    writer.writeheader()
    for item in payload["items"]:
        row = {key: item.get(key) for key in fields if not key.endswith("_excerpt")}
        row["mechanism_excerpt"] = " ".join((item.get("mechanism") or "").split())[:240]
        row["evidence_excerpt"] = " ".join((item.get("evidence") or "").split())[:240]
        writer.writerow(row)
    return json_text, stream.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initialize-baseline", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.initialize_baseline:
        if BASELINE.exists():
            raise SystemExit(f"baseline already exists: {BASELINE}")
        initialize_baseline(BASELINE)
    json_text, tsv_text = build_outputs()
    if args.check:
        stale = []
        for path, expected in ((JSON_OUT, json_text), (TSV_OUT, tsv_text)):
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                stale.append(path.relative_to(ROOT).as_posix())
        if stale:
            raise SystemExit("stale legacy evidence worklist: " + ", ".join(stale))
        print("legacy evidence worklist: current")
        return 0
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json_text, encoding="utf-8")
    TSV_OUT.write_text(tsv_text, encoding="utf-8")
    summary = json.loads(json_text)["summary"]
    print(f"wrote legacy evidence worklist: {summary['open']} open / "
          f"{summary['baseline_total']} baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
