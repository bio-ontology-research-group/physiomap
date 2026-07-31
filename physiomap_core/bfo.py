"""BFO bearer categories and the constitution/causation ontology gate.

A PhysioMap node is a PATO quality inhering in a **bearer**, and the bearer is either a
**continuant** (an independent material entity — an anatomical structure, cell, or portion of a
substance; Uberon/CL/ChEBI/PR) or an **occurrent** (a process — a GO biological process; its
quality is a *rate*, *frequency*, or *flow rate*). The distinction is not cosmetic: it decides
which cross-scale relations are ontologically admissible.

**Constitution requires parthood, and parthood respects the BFO divide — but exists on both
sides of it.** A constitutive edge asserts that a micro configuration is *part of* a macro entity
and thereby fixes a macro quality. Parthood never crosses the continuant/occurrent divide, but it
runs *within* each side, giving a **trichotomy** of cross-grain determination
(:func:`determination_regime`):

1. **material constitution** — continuant ``part_of`` continuant (*spatial* mereology): a micro
   material configuration is part of a macro material entity and fixes a macro material quality
   (VSMC tone ▷ TPR; red-cell + plasma volume ▷ blood volume). Enters the upward determination
   lift, excluded from the Jacobian.

2. **process constitution** — occurrent ``part_of`` occurrent (*temporal* mereology,
   ``occurrent_part_of`` / ``has_occurrent_part``; BFO SPAN, Grenon & Smith 2004): a fine,
   recurring **sub-process** is a temporal part of a coarse process, and a quality of the coarse
   process composes from the sub-processes. An **extensive** process quantity (count of
   occurrences, total throughput / flow volume, total energy) is *additive* over the occurrent
   parts (sign ``+``); a **rate/frequency** is the *ratio* of such an extensive quantity over the
   process's **temporal extent** (duration) — the same ratio calculus as a concentration, with
   duration playing the role of the diluting volume. E.g. the *rate of single heart beats*
   (frequency of the fine occurrent parts) determines the *flow volume* / *cardiac output* of the
   extended "heart beating" process. So a **process quality CAN be constituted** — by a temporal
   mereology of sub-processes — contrary to the naive "processes never constitute". (The detailed
   classification of process phenes was flagged as future work by Hoehndorf, Oellrich &
   Rebholz-Schuhmann 2010; this is that classification for the quantitative case.)

3. **cross-BFO** — occurrent quality ↔ continuant quality: *no parthood bridges the BFO divide* (a
   process is not ``part_of`` a material entity — it relates by ``has_participant`` / ``occurs_in``
   / ``has_output``), so a cross-BFO determination is **causal**, never constitution. A beta-cell
   *insulin-secretion rate* (occurrent) does not *constitute* *plasma insulin concentration*
   (continuant). Process outputs belong in the typed ``production_edges`` layer; other drivers
   belong in ``causal_edges`` and must satisfy the appropriate evidence gate.

**Representation follows the ontological regime.** Material and genuine process constitution
remain in ``constitutive_edges`` and are handled only by the upward determination layer. A
cross-BFO record is invalid in that collection: it must be represented explicitly as production
or as an evidence-bearing causal influence. No constitutive record is silently converted into a
causal edge.

This module classifies bearers and the determination regime, and validates the divide
(:func:`bearer_kind`, :func:`determination_regime`, :func:`validate_bfo`).
"""
from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from physiomap_core.model import Node, PhysioMap

__all__ = ["BearerKind", "DeterminationRegime", "PROCESS_QUALITIES", "bearer_kind",
           "determination_regime", "is_production", "validate_bfo", "BFOReport",
           "entity_bearer_kind", "quality_required_bearer", "validate_bearer", "BearerAxiomReport"]


class BearerKind(str, Enum):
    CONTINUANT = "continuant"   # material entity (anatomy/cell/substance): Uberon/CL/ChEBI/PR
    OCCURRENT = "occurrent"     # process (GO biological process); quality is a rate/flux


class DeterminationRegime(str, Enum):
    """Ontological regime of a cross-grain determination, fixed by the bearer BFO categories.

    Parthood respects the continuant/occurrent divide but exists on both sides, so a determination
    is **material constitution** (continuant↔continuant, spatial parthood), **process constitution**
    (occurrent↔occurrent, temporal parthood), or **causal** (cross-BFO — no parthood bridges the
    divide). See the module docstring for solver realization.
    """

    MATERIAL = "material_constitution"   # continuant part_of continuant (spatial)
    PROCESS = "process_constitution"     # occurrent part_of occurrent (temporal)
    CAUSAL = "causal"                    # occurrent <-> continuant: no bridging parthood


# PATO qualities that inhere in a *process* (occurrent). PATO:0000161 "rate" is defined as
# "a quality of a single process"; flow/growth rate, frequency, and velocity are likewise
# process qualities. (Verified vs ontology/.obo_cache/PATO.obo.)
PROCESS_QUALITIES = {
    "PATO:0000161",  # rate
    "PATO:0001574",  # flow rate
    "PATO:0002243",  # fluid flow rate
    "PATO:0001492",  # growth rate
    "PATO:0000044",  # frequency
    "PATO:0002242",  # velocity
}


def bearer_kind(node: Node) -> BearerKind:
    """BFO category of the node's quality bearer (``continuant`` | ``occurrent``).

    An explicit ``Node.bearer_kind`` wins; otherwise a *process* quality (a rate/flux, see
    :data:`PROCESS_QUALITIES`) or a GO-process entity marks an **occurrent**, and everything else
    (a material entity bearing amount/concentration/pressure/…) is a **continuant** (the default).
    """
    if node.bearer_kind:
        return BearerKind(node.bearer_kind)
    if node.quality_iri in PROCESS_QUALITIES:
        return BearerKind.OCCURRENT
    return BearerKind.CONTINUANT


def determination_regime(micro: Node, macro: Node) -> DeterminationRegime:
    """Ontological regime of a cross-grain determination ``micro ▷ macro`` from BFO bearer types.

    Continuant↔continuant is **material constitution** (spatial parthood); occurrent↔occurrent is
    **process constitution** (temporal parthood over sub-processes); a determination that crosses
    the continuant/occurrent divide is **causal** (no parthood bridges it). See the module
    docstring for how each regime is *realized* by the solver.
    """
    bi, ba = bearer_kind(micro), bearer_kind(macro)
    if bi == BearerKind.CONTINUANT and ba == BearerKind.CONTINUANT:
        return DeterminationRegime.MATERIAL
    if bi == BearerKind.OCCURRENT and ba == BearerKind.OCCURRENT:
        return DeterminationRegime.PROCESS
    return DeterminationRegime.CAUSAL


def is_production(relation: str) -> bool:
    """Return whether a legacy relation label denotes production.

    New records use the top-level ``production_edges`` collection; this helper remains for
    migration diagnostics only.
    """
    return relation == "production"


class BFOReport(BaseModel):
    errors: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_bfo(pmap: PhysioMap) -> BFOReport:
    """Audit the constitution/causation trichotomy across BFO bearer categories.

    Material and process constitution are admissible within their respective BFO categories.
    Any constitutive edge crossing the continuant/occurrent divide is a hard error: the record
    must be moved to ``production_edges`` or to an evidence-bearing ``causal_edges`` record.
    Production records are inspected separately and never used to excuse a malformed
    constitutive assertion.
    """
    nodes = {n.id: n for n in pmap.nodes}
    rep = BFOReport()
    for e in pmap.constitutive_edges:
        mi, ma = nodes.get(e.micro), nodes.get(e.macro)
        if mi is None or ma is None:
            continue
        regime = determination_regime(mi, ma)
        if regime is DeterminationRegime.PROCESS:
            rep.notes.append(
                f"{e.micro} ▷ {e.macro} ({e.relation}): process (occurrent, temporal-mereological) "
                "constitution; retained in the determination layer and excluded from causal reasoning"
            )
        elif regime is DeterminationRegime.CAUSAL:
            rep.errors.append(
                f"{e.micro} → {e.macro} ({e.relation}): crosses the occurrent/continuant divide; "
                "move it to production_edges or to an evidence-bearing causal edge"
            )
    for edge in pmap.production_edges:
        source, target = nodes.get(edge.source), nodes.get(edge.target)
        if source is None or target is None:
            continue
        if determination_regime(source, target) is not DeterminationRegime.CAUSAL:
            rep.notes.append(
                f"{edge.source} → {edge.target}: production relation does not cross the BFO "
                "continuant/occurrent divide; verify the node bearer annotations"
            )
    return rep


# --------------------------------------------------------------------------- entity/quality axiom
# A PhysioMap node is a TRAIT (E, Q). The quality Q demands a bearer BFO category (process quality
# -> occurrent; physical-object quality -> continuant), and the entity E has its own category (from
# its ontology). They must agree: this is the "clear OWL axiom" the trait model requires. Enforced
# here by a curated map + PATO/GO is_a fallback; the matching universal restriction ships in the
# DL artifact (`ProcessQuality SubClassOf qualityOf only Process`), outside the EL profile.

_ONTO = Path(__file__).resolve().parent.parent / "ontology"
_OBO = _ONTO / ".obo_cache"
_SOURCE_REGISTRY = _ONTO / "registry/used-terms.json"
_QBEARER_PATH = _ONTO / "quality_bearer.yaml"
_PATO_PROCESS_Q = "PATO:0001236"      # process quality
_PATO_PHYSOBJ_Q = "PATO:0001241"      # physical object quality
_GO_BIOLOGICAL_PROCESS = "GO:0008150"
_GO_CELLULAR_COMPONENT = "GO:0005575"

# entity-IRI prefixes whose members are continuants (material entities) by construction.
_CONTINUANT_PREFIXES = {"UBERON", "CL", "CHEBI", "PR", "FMA", "CLO", "GO"}  # GO refined via is_a

_qbearer_cache: dict | None = None
_isa_cache: dict[str, dict[str, set[str]]] = {}


def _load_qbearer() -> dict:
    global _qbearer_cache
    if _qbearer_cache is None:
        data = yaml.safe_load(_QBEARER_PATH.read_text()) if _QBEARER_PATH.exists() else {}
        _qbearer_cache = {
            "occurrent": set(data.get("occurrent") or []),
            "continuant": set(data.get("continuant") or []),
        }
    return _qbearer_cache


def _isa_ancestors(prefix: str, term: str) -> set[str]:
    """Return transitive ``is_a`` ancestors from the pinned source registry.

    A raw OBO source is a development fallback only.  When the committed
    registry exists, using it exclusively keeps local and clean-clone builds
    independent of untracked ontology caches.
    """
    if prefix not in _isa_cache:
        parents: dict[str, list[str]] = {}
        if _SOURCE_REGISTRY.is_file():
            payload = json.loads(_SOURCE_REGISTRY.read_text(encoding="utf-8"))
            for identifier, value in payload.get("terms", {}).items():
                if identifier.startswith(f"{prefix}:"):
                    parents[identifier] = list(value.get("parents", []))
        else:
            path = _OBO / f"{prefix}.obo"
            if not path.exists():
                _isa_cache[prefix] = parents
                return set()
            for block in path.read_text().split("[Term]"):
                idm = re.search(r"^id: (%s:\d+)" % prefix, block, re.M)
                if idm:
                    parents[idm.group(1)] = re.findall(r"^is_a: (%s:\d+)" % prefix, block, re.M)
        _isa_cache[prefix] = parents
    parents = _isa_cache[prefix]
    seen: set[str] = set()
    stack = [term]
    while stack:
        for p in parents.get(stack.pop(), []):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    return seen


def quality_required_bearer(quality_iri: str | None) -> BearerKind | None:
    """BFO bearer category a PATO quality ``Q`` demands (``None`` if unknown/unresolvable).

    Curated ``ontology/quality_bearer.yaml`` is authoritative; otherwise PATO ``is_a`` decides
    (under ``process quality`` -> occurrent, ``physical object quality`` -> continuant); PATO's
    NEITHER-branch qualities that are not curated stay ``None``.
    """
    if not quality_iri:
        return None
    qb = _load_qbearer()
    if quality_iri in qb["occurrent"]:
        return BearerKind.OCCURRENT
    if quality_iri in qb["continuant"]:
        return BearerKind.CONTINUANT
    anc = _isa_ancestors("PATO", quality_iri)
    if _PATO_PROCESS_Q in anc:
        return BearerKind.OCCURRENT
    if _PATO_PHYSOBJ_Q in anc:
        return BearerKind.CONTINUANT
    return None


def entity_bearer_kind(node: Node) -> BearerKind | None:
    """BFO category of a node's **entity** ``E`` (``None`` if it cannot be resolved).

    Determined from the entity ontology: a GO *biological process* is an occurrent; GO *cellular
    component* and every Uberon/CL/ChEBI/PR/FMA member is a continuant. Under the phene pattern
    the quality inheres in ``entity_iri``; ``bearer_entity_iri`` is the trait's *context* (the site
    a process occurs in, or the compartment a substance is part of) and is consulted only when no
    entity is recorded.
    """
    iri = node.entity_iri or node.bearer_entity_iri
    if not iri or ":" not in iri:
        return None
    prefix = iri.split(":")[0]
    if prefix == "GO":
        anc = _isa_ancestors("GO", iri) | {iri}
        if _GO_BIOLOGICAL_PROCESS in anc:
            return BearerKind.OCCURRENT
        if _GO_CELLULAR_COMPONENT in anc:
            return BearerKind.CONTINUANT
        return None  # molecular function: a disposition, left unresolved
    if prefix in _CONTINUANT_PREFIXES:
        return BearerKind.CONTINUANT
    return None


class BearerAxiomReport(BaseModel):
    """Result of the entity/quality BFO-consistency axiom check."""

    errors: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    checked: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_bearer(pmap: PhysioMap, *, strict: bool = False) -> BearerAxiomReport:
    """Check the entity/quality BFO axiom on every node ``(E, Q)``.

    For a node whose entity category and quality-required bearer are both resolvable, they must
    agree: a *process quality* (rate/flux) must inhere in a **process** entity, a *physical-object
    quality* (concentration/amount/volume/pressure/…) in a **continuant**. A disagreement (e.g. a
    secretion *rate* whose modelled entity is the secreting *cell* rather than the secretion
    *process*, or an enzyme-*activity* rate borne by the *protein*) is reported as an advisory
    **note** by default: the quality/entity pairing is ontologically loose and the entity should
    be the process. With ``strict=True`` the same mismatch is a hard error; this mode is used for
    new contributions so historical, explicitly baselined debt cannot grow. A real OWL
    ``inheres_in`` domain/range axiom is deferred to the ontology-build phase.
    """
    rep = BearerAxiomReport()
    for n in pmap.nodes:
        eb = entity_bearer_kind(n)
        qb = quality_required_bearer(n.quality_iri)
        if eb is None or qb is None:
            continue
        rep.checked += 1
        if eb is not qb:
            message = (
                f"{n.id}: quality {n.quality_iri} demands a {qb.value} bearer but entity "
                f"{n.bearer_entity_iri or n.entity_iri} is a {eb.value} — the trait pairs a "
                f"{qb.value} quality with a {eb.value} entity (record the process as entity, or a "
                "bearer_entity_iri)"
            )
            (rep.errors if strict else rep.notes).append(message)
    return rep
