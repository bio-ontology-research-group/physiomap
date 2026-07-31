#!/usr/bin/env python3
"""Build the neutral **"Abnormality of X"** HPO link for every mapped PhysioMap trait.

PhysioMap reports a phenotype as **directional** ("X increased / decreased") only when the
comparative-statics sign is determinate. When a node is *reachable* from an intervention but its
net sign is ``?`` (typically a feedback-core node), the trait is still **affected** — we just
cannot sign it. That neutral "X affected" prediction corresponds to HPO's direction-neutral
*"Abnormal X"* / *"Abnormality of X"* term (the parent of the increased/decreased pair), e.g.

    Hypertension (HP:0000822) ─is_a→ Increased blood pressure ─is_a→ **Abnormal systemic blood
    pressure (HP:0030972)**   ← the neutral term we link "blood pressure affected" to.

This script reads the curated, hp.obo-verified ``hpo_term_map.yaml`` (HP → node + direction) and,
for each node, walks **up** the HP ``is_a`` hierarchy from its directional term(s) to the nearest
*non-directional* ``Abnormal…`` ancestor common to all of them, taking the label straight from
hp.obo. The result is written to ``benchmarks/hpo/hpo_abnormality_terms.yaml`` (committed, so the
runtime never needs hp.obo, which is gitignored).

Run:  uv run python scripts/build_abnormality_terms.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
HP_OBO = ROOT / "ontology" / ".obo_cache" / "hp.obo"
TERM_MAP = ROOT / "benchmarks" / "hpo" / "hpo_term_map.yaml"
OUT = ROOT / "benchmarks" / "hpo" / "hpo_abnormality_terms.yaml"

# names that still encode a *direction* — not the neutral "Abnormal X" we want to link to
_DIRECTIONAL = re.compile(
    r"increas|decreas|elevat|reduc|\bhigh\b|\blow\b|hyper|hypo|excess|deficien|"
    r"\braised\b|\bloss\b|\bgain\b",
    re.I,
)


def parse_obo(path: Path) -> dict[str, dict]:
    terms: dict[str, dict] = {}
    cur: str | None = None
    for ln in path.read_text().splitlines():
        if ln == "[Term]":
            cur = None
        elif ln.startswith("id: HP:"):
            cur = ln[4:].strip()
            terms[cur] = {"name": "", "is_a": []}
        elif cur and ln.startswith("name: "):
            terms[cur]["name"] = ln[6:].strip()
        elif cur and ln.startswith("is_a: HP:"):
            terms[cur]["is_a"].append(ln[6:].split("!")[0].strip())
    return terms


def ancestors(hp: str, terms: dict[str, dict]) -> set[str]:
    seen: set[str] = set()
    stack = list(terms.get(hp, {}).get("is_a", []))
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(terms.get(c, {}).get("is_a", []))
    return seen


_DEPTH: dict[str, int] = {}


def depth(hp: str, terms: dict[str, dict]) -> int:
    """Longest is_a distance to a root (more specific terms are deeper)."""
    if hp in _DEPTH:
        return _DEPTH[hp]
    parents = terms.get(hp, {}).get("is_a", [])
    _DEPTH[hp] = 0 if not parents else 1 + max(depth(p, terms) for p in parents)
    return _DEPTH[hp]


# compartment qualifiers that mark a *non-systemic* abnormal term (PhysioMap models the systemic
# blood/plasma/serum compartment, so prefer those over salivary/urinary/CSF variants on a tie)
_NON_SYSTEMIC = re.compile(r"saliva|urin|urine|csf|cerebrospinal|sweat|fecal|stool|sputum", re.I)
_SYSTEMIC = re.compile(r"circulat|blood|plasma|serum|systemic", re.I)


def nearest_abnormal(hp: str, terms: dict[str, dict]) -> str | None:
    """Nearest (BFS up is_a) non-directional ``Abnormal…`` ancestor of a single directional term."""
    seen: set[str] = set()
    queue = list(terms.get(hp, {}).get("is_a", []))
    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        nm = terms.get(cur, {}).get("name", "")
        if nm.lower().startswith("abnormal") and not _DIRECTIONAL.search(nm):
            return cur
        queue.extend(terms.get(cur, {}).get("is_a", []))
    return None


def neutral_abnormal(dir_terms: list[str], terms: dict[str, dict]) -> str | None:
    """The neutral ``Abnormal X`` term for a node: a vote over each directional term's nearest
    abnormal ancestor, scored by (frequency, systemic-compartment, specificity). This is robust to
    compound/qualified HP terms (``Hypokalemic alkalosis``, ``Decreased salivary cortisol``) that
    a strict common-ancestor would let drag the result up to a generic parent."""
    votes: dict[str, int] = {}
    for d in dir_terms:
        a = nearest_abnormal(d, terms)
        if a is not None:
            votes[a] = votes.get(a, 0) + 1
    if not votes:
        return None

    def score(a: str) -> tuple[int, int, int]:
        nm = terms.get(a, {}).get("name", "")
        systemic = 1 if (_SYSTEMIC.search(nm) and not _NON_SYSTEMIC.search(nm)) else 0
        return (votes[a], systemic, depth(a, terms))

    return max(votes, key=score)


def main() -> int:
    if not HP_OBO.exists():
        print(f"hp.obo not found at {HP_OBO} (download via scripts/build_hpo_observations.py)")
        return 1
    terms = parse_obo(HP_OBO)
    tm = yaml.safe_load(TERM_MAP.read_text()) or {}
    block = set(tm.get("block_propagation", []))

    # group the directional HP terms by node
    by_node: dict[str, list[str]] = {}
    for hp, spec in (tm.get("terms") or {}).items():
        if hp in block:
            continue
        node = spec.get("node")
        if node and spec.get("sign") in ("+", "-"):
            by_node.setdefault(node, []).append(hp)

    out: dict[str, dict[str, str]] = {}
    missing: list[str] = []
    for node, dir_terms in sorted(by_node.items()):
        neutral = neutral_abnormal(dir_terms, terms)
        if neutral is None:
            missing.append(node)
            continue
        out[node] = {"hpo": neutral, "label": terms[neutral]["name"]}

    header = (
        "# =============================================================================\n"
        "# PhysioMap node -> neutral HPO \"Abnormality of X\" term  *** GENERATED ***\n"
        "# =============================================================================\n"
        "# Built by scripts/build_abnormality_terms.py from hpo_term_map.yaml + hp.obo: for each\n"
        "# node, the nearest non-directional `Abnormal X` ancestor common to its increased/decreased\n"
        "# HP terms. Used to report a reachable-but-direction-undetermined ('?') trait as\n"
        "# \"X affected\" with a link to HPO's direction-neutral term. Labels verbatim from hp.obo.\n"
        "# Do not hand-edit; re-run the script (hp.obo is gitignored, so this file is committed).\n"
        "# =============================================================================\n"
    )
    OUT.write_text(header + yaml.safe_dump({"abnormality_terms": out}, sort_keys=True))
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} nodes linked to a neutral 'Abnormal X' term")
    if missing:
        print(f"  {len(missing)} node(s) had no non-directional Abnormal ancestor (no link): "
              + ", ".join(missing[:12]) + (" …" if len(missing) > 12 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
