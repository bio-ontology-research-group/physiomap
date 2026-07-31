#!/usr/bin/env python3
"""Move legacy ``relation: production`` records into the typed production layer.

The migration is deliberately textual so source comments and surrounding YAML formatting
remain intact. Exact duplicates of an already-authored causal influence are removed instead
of creating a second production shadow. All other legacy records receive an explicit
``legacy-evidence-unclassified`` status; controlled promotion requires a separate source audit.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_owl_scm import default_fragments  # noqa: E402

TOP_LEVEL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*:\s*(?:#.*)?$")
ITEM = re.compile(r"^(\s*)-\s+micro:\s*(\S+)\s*(?:#.*)?$")


def _section(lines: list[str], header: str) -> tuple[int, int] | None:
    key = header.removesuffix(":")
    start = next(
        (index for index, line in enumerate(lines)
         if re.match(rf"^{re.escape(key)}:\s*(?:#.*)?$", line)),
        None,
    )
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if TOP_LEVEL.match(lines[index]):
            end = index
            break
    return start, end


def migrate(path: Path, causal: set[tuple[str, str, str]]) -> tuple[str, int, int]:
    """Return migrated text plus ``(moved, duplicate_removed)`` counts."""
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    constitutive = data.get("constitutive_edges") or []
    legacy = [edge for edge in constitutive if edge.get("relation") == "production"]
    if not legacy:
        return text, 0, 0
    if len(legacy) != len(constitutive):
        raise ValueError(
            f"{path}: mixed constitutive/production section must be split explicitly first"
        )

    lines = text.splitlines()
    bounds = _section(lines, "constitutive_edges:")
    if bounds is None:
        raise ValueError(f"{path}: parsed constitutive_edges but could not locate its header")
    start, end = bounds
    item_starts = [index for index in range(start + 1, end) if ITEM.match(lines[index])]
    if len(item_starts) != len(legacy):
        raise ValueError(
            f"{path}: found {len(item_starts)} textual items for {len(legacy)} parsed records"
        )

    output = lines[:start] + ["production_edges:"]
    cursor = start + 1
    moved = removed = 0
    for number, item_start in enumerate(item_starts):
        item_end = item_starts[number + 1] if number + 1 < len(item_starts) else end
        output.extend(lines[cursor:item_start])
        block = lines[item_start:item_end]
        edge = legacy[number]
        key = (edge["micro"], edge["macro"], str(edge.get("sign", "+")))
        if key in causal:
            removed += 1
            cursor = item_end
            continue

        converted: list[str] = []
        sign_indent: str | None = None
        for line in block:
            if re.match(r"^\s*relation:\s*production", line):
                continue
            line = re.sub(r"^(\s*-\s*)micro:", r"\1source:", line)
            line = re.sub(r"^(\s*)macro:", r"\1target:", line)
            converted.append(line)
            match = re.match(r"^(\s*)sign:\s*", line)
            if match:
                sign_indent = match.group(1)
                converted.append(
                    f"{sign_indent}production_evidence: legacy-evidence-unclassified"
                )
        if sign_indent is None:
            raise ValueError(f"{path}: production record lacks sign: {edge}")
        output.extend(converted)
        moved += 1
        cursor = item_end
    output.extend(lines[cursor:end])
    output.extend(lines[end:])

    # If every record was an exact causal duplicate, remove the now-empty typed section.
    if moved == 0:
        output = lines[:start] + lines[end:]
    return "\n".join(output) + "\n", moved, removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="apply the migration in place")
    args = parser.parse_args()
    paths = default_fragments()
    causal: set[tuple[str, str, str]] = set()
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        causal.update(
            (edge["source"], edge["target"], str(edge["sign"]))
            for edge in data.get("causal_edges") or []
        )

    changed = moved = removed = 0
    for path in paths:
        migrated, file_moved, file_removed = migrate(path, causal)
        if migrated != path.read_text(encoding="utf-8"):
            changed += 1
            if args.write:
                path.write_text(migrated, encoding="utf-8")
        moved += file_moved
        removed += file_removed
    mode = "wrote" if args.write else "would change"
    print(
        f"{mode} {changed} files: {moved} typed production relations; "
        f"{removed} exact causal duplicates removed"
    )
    return 0 if args.write or changed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
