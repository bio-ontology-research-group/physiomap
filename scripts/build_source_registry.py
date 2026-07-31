#!/usr/bin/env python3
"""Refresh checksum-bound source-term registries from local OBO releases."""

from __future__ import annotations

import argparse
import gzip
import json
from dataclasses import asdict
from pathlib import Path

from physiomap_core.model import PhysioMap
from physiomap_core.owl_projection import (RegistryTerm, parse_obo, source_registry,
                                            write_source_registry_cache)
from scripts.build_owl_scm import default_fragments

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "ontology/.obo_cache"


def add_ancestor_closure(
    registry: dict[str, RegistryTerm],
    identifiers: set[str],
    *,
    prefixes: tuple[str, ...] = ("GO", "PATO"),
    cache_dir: Path = CACHE,
) -> dict[str, RegistryTerm]:
    """Add the source ``is_a`` ancestors needed by bearer classification.

    ``requested_identifiers`` remains the set used directly by PhysioMap.  The
    additional terms make the transitive classifications reproducible without
    shipping complete source ontologies or relying on an untracked OBO cache.
    """
    expanded = dict(registry)
    for prefix in prefixes:
        wanted = {identifier for identifier in identifiers
                  if identifier.startswith(f"{prefix}:")}
        if not wanted:
            continue
        source = cache_dir / f"{prefix}.obo"
        if not source.exists():
            raise FileNotFoundError(
                f"cannot refresh {prefix} ancestry without source ontology {source}"
            )
        source_terms = parse_obo(source)
        stack = list(wanted)
        seen: set[str] = set()
        while stack:
            identifier = stack.pop()
            if identifier in seen:
                continue
            seen.add(identifier)
            term = source_terms.get(identifier)
            if term is None:
                continue
            expanded[identifier] = term
            stack.extend(term.parents)
    return expanded


def used_identifiers() -> set[str]:
    pmap = PhysioMap.load_composed(default_fragments(), name="physiomap")
    return {value for node in pmap.nodes
            for value in (node.entity_iri, node.quality_iri, node.bearer_entity_iri) if value}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true",
                        help="also write complete per-source gzip registries for ontology refresh")
    args = parser.parse_args()
    identifiers = used_identifiers()
    registry, checksums, _ = source_registry(CACHE, identifiers)
    registry = add_ancestor_closure(registry, identifiers)
    output = ROOT / "ontology/registry/used-terms.json"
    write_source_registry_cache(output, identifiers, registry, checksums)
    print(
        f"wrote {output.relative_to(ROOT)} "
        f"({len(identifiers)} directly used identifiers; {len(registry)} terms with ancestors)"
    )
    if args.full:
        full_dir = ROOT / "ontology/registry/full"
        full_dir.mkdir(parents=True, exist_ok=True)
        for source in sorted(CACHE.glob("*.obo")):
            terms = parse_obo(source)
            payload = json.dumps({"schema_version": "1.0.0", "source": source.name,
                                  "checksum": checksums.get(source.name),
                                  "terms": {key: asdict(value) for key, value in sorted(terms.items())}},
                                 sort_keys=True).encode()
            target = full_dir / f"{source.stem}.json.gz"
            with target.open("wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                    zipped.write(payload)
            print(f"wrote {target.relative_to(ROOT)} ({len(terms)} terms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
