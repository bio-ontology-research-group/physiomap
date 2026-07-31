#!/usr/bin/env python3
"""Validate a single PhysioMap fragment for schema correctness + provenance.

Used by the fan-out authoring agents (and CI-style checks) to guarantee that every
new system fragment (a) parses against the real pydantic model, (b) carries provenance
on *every* causal edge, and (c) has its inter-fragment references accounted for
(resolved against the rest of the corpus, or flagged as dangling/typo).

A fragment may legitimately reference *boundary* nodes owned by sibling fragments
(e.g. ``mean_arterial_pressure``). To validate it standalone regardless of sibling
authoring order, we stub any external reference, then load the stubbed composition.

Usage:  uv run python scripts/validate_fragment.py benchmarks/human/systems/foo.yaml
Exit 0 = OK (well-formed + full provenance). Exit 1 = hard error (must fix).
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from physiomap_core.model import PhysioMap  # noqa: E402

CORPUS_GLOBS = [
    "benchmarks/guyton/guyton_cv_core.yaml",
    "benchmarks/human/systems/*.yaml",
    "benchmarks/human/curated/*.yaml",
    "benchmarks/multiscale/*.yaml",
]


def corpus_node_ids(exclude: Path) -> set[str]:
    ids: set[str] = set()
    for g in CORPUS_GLOBS:
        for f in glob.glob(str(ROOT / g)):
            if Path(f).resolve() == exclude.resolve():
                continue
            data = yaml.safe_load(Path(f).read_text()) or {}
            for nd in data.get("nodes", []) or []:
                ids.add(nd["id"])
    return ids


def main(path_str: str) -> int:
    path = Path(path_str)
    data = yaml.safe_load(path.read_text()) or {}
    errors: list[str] = []
    warnings: list[str] = []

    own_ids = {nd["id"] for nd in data.get("nodes", []) or []}
    other_ids = corpus_node_ids(path)

    causal = data.get("causal_edges", []) or []
    production = data.get("production_edges", []) or []
    const = data.get("constitutive_edges", []) or []
    modulation = data.get("modulation_edges", []) or []
    quantitative = data.get("quantitative_definitions", []) or []

    # provenance: every causal edge needs evidence; mechanism strongly recommended
    for i, e in enumerate(causal):
        if not (e.get("evidence") or "").strip():
            errors.append(f"causal_edge[{i}] {e.get('source')}->{e.get('target')}: MISSING evidence")
        if not (e.get("mechanism") or "").strip():
            warnings.append(f"causal_edge[{i}] {e.get('source')}->{e.get('target')}: no mechanism")
        if e.get("sign") not in ("+", "-", "?"):
            errors.append(f"causal_edge[{i}]: bad sign {e.get('sign')!r}")
    for i, edge in enumerate(production):
        tag = f"{edge.get('source')}->{edge.get('target')}"
        if edge.get("production_evidence") != "legacy-evidence-unclassified":
            if not (edge.get("evidence") or "").strip():
                errors.append(f"production_edge[{i}] {tag}: MISSING evidence")
            if not (edge.get("mechanism") or "").strip():
                errors.append(f"production_edge[{i}] {tag}: MISSING mechanism")

    # references: resolved within fragment / against corpus / dangling
    refs: set[str] = set()
    for e in causal:
        refs.update([e.get("source"), e.get("target")])
    for e in production:
        refs.update([e.get("source"), e.get("target")])
    for e in const:
        refs.update([e.get("micro"), e.get("macro")])
    for edge in modulation:
        refs.update([edge.get("modulator"), edge.get("edge_source"), edge.get("edge_target")])
    for definition in quantitative:
        refs.add(definition.get("result"))
        refs.update(argument.get("node") for argument in definition.get("arguments") or [])
    refs.discard(None)
    boundary = sorted(r for r in refs if r not in own_ids and r in other_ids)
    dangling = sorted(r for r in refs if r not in own_ids and r not in other_ids)
    for d in dangling:
        errors.append(f"dangling reference (typo or undefined node): {d!r}")

    # load a stubbed composition so we exercise the real validator
    stub_nodes = [
        {"id": r, "label": f"[boundary] {r}", "scale": "organ_system"}
        for r in sorted((refs - own_ids))
    ]
    try:
        PhysioMap.model_validate(
            {
                "name": data.get("name", "frag"),
                "nodes": (data.get("nodes", []) or []) + stub_nodes,
                "causal_edges": causal,
                "production_edges": production,
                "constitutive_edges": const,
                "modulation_edges": modulation,
                "quantitative_definitions": quantitative,
            }
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"pydantic validation failed: {exc}")

    integrates = bool(boundary) or not other_ids  # connects to existing map?

    print(f"fragment: {path}")
    print(
        f"  nodes: {len(own_ids)}  causal_edges: {len(causal)}  "
        f"production_edges: {len(production)}  constitutive_edges: {len(const)}"
    )
    print(f"  provenance: {sum(1 for e in causal if (e.get('evidence') or '').strip())}/{len(causal)} causal edges cite evidence")
    print(f"  boundary refs (resolve to existing map): {boundary or '—'}")
    if not integrates:
        warnings.append("fragment does not reference any existing-map node (island; will not integrate)")
    for w in warnings:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        print("RESULT: FAIL")
        return 1
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
