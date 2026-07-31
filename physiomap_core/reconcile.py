"""Semantic node de-duplication gate for PhysioMap extraction/curation.

The cardinal import risk in parallel source curation is **silent
duplication**: a contributor invents a *new* node id for a variable that already exists under a
slightly different name (``MAP`` vs ``mean_arterial_pressure``) or a different — possibly
ambiguous — anatomical entity choice (``arterial pressure`` of the *circulatory system* vs of
the *systemic arterial system*). The plain id-collision check in
:func:`physiomap_core.curation.compose_candidate` does NOT catch this, because the ids differ.

This module is the missing gate. Given the canonical catalog (``scripts/export_node_catalog.py``)
and a set of proposed new nodes, it classifies each proposal:

* ``existing``  — the proposed id is already in the catalog (reuse it, or check whether the
  proposal is an unintended redefinition).
* ``duplicate`` — matches an existing node on the **(entity, quality, scale)** key (the E+Q
  identity) OR on a normalized-label exact match. Auto-remappable to the existing id.
* ``review``    — a strong fuzzy/partial match (same quality + similar entity label, or high
  label similarity) that a curator must adjudicate. This is the ambiguous-entity bucket:
  it is flagged and never merged automatically.
* ``novel``     — no plausible match; admit as a genuinely new node.

Matching is layered (strongest signal first); the strongest layer that fires sets the verdict.
The (entity, quality) identity is the principled signal, but because entity choice can be
ambiguous we *also* match on normalized label + a physiology synonym lexicon, and surface a
review band rather than over-trusting any single layer.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# --- normalization ---------------------------------------------------------------

_STOPWORDS = {"the", "a", "an", "of", "in", "level", "levels", "concentration", "amount"}
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")


def _load_synonyms(path: Path | None = None) -> dict[str, str]:
    """Build a variant->canonical map from the lexicon (normalized keys)."""
    p = path or (ROOT / "ontology" / "node_synonyms.yaml")
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    out: dict[str, str] = {}
    for canon, variants in (data.get("synonyms") or {}).items():
        ck = _basic_norm(canon)
        out[ck] = ck
        for v in variants or []:
            out[_basic_norm(v)] = ck
    return out


def _basic_norm(s: str) -> str:
    s = (s or "").strip().lower().replace("_", " ")
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def normalize_label(label: str, synonyms: dict[str, str] | None = None) -> str:
    """Canonical comparison form of a label: lowercase, depunctuated, synonym-folded,
    stopword-stripped, token-sorted (so word order does not matter)."""
    syn = synonyms if synonyms is not None else _SYNONYMS
    base = _basic_norm(label)
    if base in syn:  # whole-phrase synonym (e.g. "map" -> "mean arterial pressure")
        base = syn[base]
    toks = [t for t in base.split(" ") if t and t not in _STOPWORDS]
    toks = sorted(toks)
    return " ".join(toks)


_SYNONYMS = _load_synonyms()


# --- catalog ---------------------------------------------------------------------


@dataclass(frozen=True)
class CatalogNode:
    id: str
    label: str
    scale: str | None
    entity_iri: str | None
    quality_iri: str | None
    bearer_entity_iri: str | None = None


def load_catalog(path: Path | None = None) -> list[CatalogNode]:
    import json

    p = path or (ROOT / "benchmarks/results/node_catalog.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    return [
        CatalogNode(
            id=r["id"],
            label=r["label"],
            scale=r.get("scale"),
            entity_iri=r.get("entity_iri"),
            quality_iri=r.get("quality_iri"),
            bearer_entity_iri=r.get("bearer_entity_iri"),
        )
        for r in data
    ]


# --- matching --------------------------------------------------------------------


@dataclass
class Match:
    existing_id: str
    reason: str
    score: float


@dataclass
class Verdict:
    proposed_id: str
    proposed_label: str
    status: str  # existing | duplicate | review | novel
    matches: list[Match] = field(default_factory=list)

    @property
    def best(self) -> Match | None:
        return self.matches[0] if self.matches else None


class Reconciler:
    """Indexes a catalog and classifies proposed nodes against it."""

    FUZZY_REVIEW = 0.86  # SequenceMatcher ratio on normalized labels -> review band

    def __init__(self, catalog: list[CatalogNode], synonyms: dict[str, str] | None = None):
        self.catalog = catalog
        self.syn = synonyms if synonyms is not None else _SYNONYMS
        self._by_id = {c.id for c in catalog}
        self._by_eq: dict[tuple[str, str, str], list[CatalogNode]] = {}
        self._by_norm: dict[str, list[CatalogNode]] = {}
        for c in catalog:
            if c.entity_iri and c.quality_iri:
                self._by_eq.setdefault(
                    (c.entity_iri, c.quality_iri, c.scale or ""), []
                ).append(c)
            self._by_norm.setdefault(normalize_label(c.label, self.syn), []).append(c)

    def classify(
        self,
        proposed_id: str,
        label: str,
        *,
        scale: str | None = None,
        entity_iri: str | None = None,
        quality_iri: str | None = None,
    ) -> Verdict:
        # Layer 0: id already exists -> caller must reuse/check (not a new node).
        if proposed_id in self._by_id:
            return Verdict(proposed_id, label, "existing",
                           [Match(proposed_id, "id-already-in-catalog", 1.0)])

        norm = normalize_label(label, self.syn)

        # Layer 1: normalized-label (synonym-folded) exact match — the most RELIABLE signal,
        # because labels carry the variable's specific meaning (E+Q IRIs are often coarse).
        label_matches: list[Match] = []
        for c in self._by_norm.get(norm, []):
            if quality_iri and c.quality_iri and quality_iri != c.quality_iri:
                # homonymous label, conflicting quality -> not a safe merge.
                label_matches.append(Match(c.id, "normalized-label match but quality differs", 0.84))
            else:
                label_matches.append(Match(c.id, "normalized-label (synonym-folded) match", 0.95))
        if label_matches:
            best = max(m.score for m in label_matches)
            status = "duplicate" if best >= 0.9 else "review"
            return Verdict(proposed_id, label, status, _dedup(label_matches))

        # Layer 2: (entity, quality) identity but the normalized label DIFFERS (an exact-label
        # match would already have returned at Layer 1). E+Q identity is NECESSARY but NOT
        # sufficient: coarse IRIs (lung+volume, lung+flow-rate) collapse genuinely distinct
        # variables (tidal volume vs dead space vs blood volume; blood flow vs lymph flow). We
        # therefore NEVER auto-merge here — we flag for review. This is the ambiguous-entity
        # safety valve the whole gate exists for.
        eq_matches: list[Match] = []
        for key, nodes in self._by_eq.items():
            if key[0] != entity_iri or key[1] != quality_iri:
                continue
            for c in nodes:
                eq_matches.append(Match(
                    c.id,
                    "entity+quality identity but labels DIFFER (coarse IRI — verify same variable, "
                    "do not blind-merge)", 0.6))
        if eq_matches:
            return Verdict(proposed_id, label, "review", _dedup(eq_matches))

        # Layer 3: fuzzy label similarity -> review band (never auto-merge).
        fuzzy: list[Match] = []
        for c in self.catalog:
            r = difflib.SequenceMatcher(None, norm, normalize_label(c.label, self.syn)).ratio()
            if r >= self.FUZZY_REVIEW:
                reason = "fuzzy-label similarity"
                if quality_iri and c.quality_iri and quality_iri == c.quality_iri:
                    reason = "fuzzy-label + same quality"
                    r = min(1.0, r + 0.03)
                fuzzy.append(Match(c.id, reason, round(r, 3)))
        if fuzzy:
            return Verdict(proposed_id, label, "review", _dedup(fuzzy)[:5])

        return Verdict(proposed_id, label, "novel", [])


def _dedup(matches: list[Match]) -> list[Match]:
    best: dict[str, Match] = {}
    for m in matches:
        if m.existing_id not in best or m.score > best[m.existing_id].score:
            best[m.existing_id] = m
    return sorted(best.values(), key=lambda m: -m.score)
