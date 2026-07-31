"""Constitution layer: part_of backbone + constitutive-edge validation + conservation.

Cross-scale location does not by itself determine relation type. PhysioMap keeps genuine
constitution, process-output production, quantitative identity, and interventional influence
separate. This module makes only the constitution layer *checkable* against a curated
``part_of`` mereology (``ontology/partof.yaml``, grounded in Uberon/CL).

Constitutive-edge **kinds** (the ``relation`` field):

* ``part_of+determination`` — *structural* constitution: the micro node's bearer entity is a
  ``part_of`` the macro node's entity, and the micro configuration determines a quality of the
  whole (VSMC tone ▷ total peripheral resistance).
* ``aggregation`` — the macro quantity is a **mereological sum** of its parts (red-cell volume
  ▷ blood volume; adipose + lean mass ▷ body weight). Sign is necessarily ``+``; this is the
  basis of conservation/mass-balance invariants (evaluation family 9).
* ``participation`` — reserved (a molecule participates in a process); not yet used.

Production/process-output relations are represented separately by ``ProductionEdge`` and are
never accepted in this collection.

The canonical OWL/ELK release checks registered TBox entailments; this Python scaffold
complements it by validating that the
constitution we assert is consistent with real part-whole structure and to expose gaps.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import yaml
from pydantic import BaseModel, Field

from physiomap_core.model import PhysioMap, Sign

__all__ = [
    "CONSTITUTIVE_KINDS",
    "load_partof",
    "partof_graph",
    "is_part_of",
    "validate_constitution",
    "free_floating_macro",
    "classify_macro_grounding",
    "check_conservation",
    "ConstitutionReport",
]

CONSTITUTIVE_KINDS = {"part_of+determination", "aggregation", "participation"}

_SCALES = ["molecular", "subcellular", "cellular", "tissue", "organ", "organ_system", "organism"]
_SCALE_IX = {s: i for i, s in enumerate(_SCALES)}

_DEFAULT_PARTOF = Path(__file__).resolve().parent.parent / "ontology" / "partof.yaml"


def _prefix(iri: str | None) -> str | None:
    return iri.split(":")[0] if iri else None


def _kind(iri: str | None) -> str:
    """Coarse entity kind from the IRI prefix."""
    p = _prefix(iri)
    if p in ("UBERON", "CL"):
        return "anatomical"
    if p in ("CHEBI", "PR"):
        return "substance"
    if p == "GO":
        return "process"
    return "unknown"


def load_partof(path: str | Path | None = None) -> dict:
    """Load the curated part_of backbone (``IRI -> {label, scale, part_of:[...]}``)."""
    data = yaml.safe_load(Path(path or _DEFAULT_PARTOF).read_text()) or {}
    return data.get("entities", {})


def partof_graph(partof: dict | None = None) -> nx.DiGraph:
    """Directed graph of the mereology: an edge ``part -> whole`` for each ``part_of``."""
    partof = partof if partof is not None else load_partof()
    g: nx.DiGraph = nx.DiGraph()
    for iri, rec in partof.items():
        g.add_node(iri, **{k: rec.get(k) for k in ("label", "scale")})
        for whole in rec.get("part_of", []) or []:
            g.add_edge(iri, whole)
    if not nx.is_directed_acyclic_graph(g):
        raise ValueError("part_of backbone must be acyclic")
    return g


def is_part_of(g: nx.DiGraph, part: str, whole: str) -> bool:
    """Is ``part`` a (transitive) part_of ``whole`` (or equal)?"""
    if part == whole:
        return True
    return g.has_node(part) and g.has_node(whole) and nx.has_path(g, part, whole)


class ConstitutionReport(BaseModel):
    """Result of validating the constitutive layer against the part_of backbone."""

    n_constitutive: int = 0
    by_kind: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)        # things that are likely wrong
    notes: list[str] = Field(default_factory=list)         # advisory (e.g. unverifiable)
    free_floating_macro: list[str] = Field(default_factory=list)
    conservation: list[str] = Field(default_factory=list)  # aggregation / mass-balance wholes

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_constitution(pmap: PhysioMap, partof: dict | None = None) -> ConstitutionReport:
    """Type-check every constitutive edge and validate it against the part_of mereology.

    Hard *errors*: unknown relation kind; scale inversion (micro coarser than macro);
    ``part_of+determination`` between two anatomical entities with no part_of path;
    ``aggregation`` with a non-``+`` sign or no part_of path (anatomical case). Advisory *notes*:
    structural/aggregation edges
    whose micro bearer is molecular/process (part_of unverifiable — recommend recording a
    bearer entity), and macro nodes with no micro grounding.
    """
    g = partof_graph(partof)
    nodes = {n.id: n for n in pmap.nodes}
    rep = ConstitutionReport(n_constitutive=len(pmap.constitutive_edges))

    for e in pmap.constitutive_edges:
        tag = f"{e.micro} ▷ {e.macro}"
        rel = e.relation
        rep.by_kind[rel] = rep.by_kind.get(rel, 0) + 1
        if rel not in CONSTITUTIVE_KINDS:
            rep.errors.append(f"{tag}: unknown relation kind {rel!r}")
            continue
        mi, ma = nodes[e.micro], nodes[e.macro]
        # scale ordering: micro must be finer-or-equal than macro
        si, sa = _SCALE_IX.get(mi.scale.value, -1), _SCALE_IX.get(ma.scale.value, -1)
        if si > sa:
            rep.errors.append(
                f"{tag}: scale inversion ({mi.scale.value} ▷ {ma.scale.value}) — micro coarser than macro"
            )
        mk, ak = _kind(mi.entity_iri), _kind(ma.entity_iri)

        if rel == "part_of+determination":
            # the micro part_of anchor: an anatomical entity_iri, else the recorded bearer
            micro_anchor = mi.entity_iri if mk == "anatomical" else mi.bearer_entity_iri
            # the macro whole anchor: an anatomical entity_iri, else its recorded bearer
            macro_anchor = ma.entity_iri if ak == "anatomical" else ma.bearer_entity_iri
            if ak == "substance":
                rep.errors.append(
                    f"{tag}: part_of+determination into a SUBSTANCE ({ma.entity_iri}); "
                    "a cell/process producing a substance belongs in production_edges"
                )
            elif micro_anchor and macro_anchor:
                if g.has_node(micro_anchor) and g.has_node(macro_anchor):
                    if not is_part_of(g, micro_anchor, macro_anchor):
                        rep.errors.append(
                            f"{tag}: no part_of path {micro_anchor} → {macro_anchor} in the backbone"
                        )
                else:
                    rep.notes.append(
                        f"{tag}: part_of anchors not in backbone "
                        f"({micro_anchor}, {macro_anchor}) — add them to validate"
                    )
            else:
                missing = "micro bearer" if not micro_anchor else "macro bearer"
                rep.notes.append(
                    f"{tag}: structural edge with non-anatomical entity and no {missing}; "
                    "part_of unverifiable — record bearer_entity_iri on the molecular node"
                )
        elif rel == "aggregation":
            if e.sign is not Sign.PLUS:
                rep.errors.append(f"{tag}: aggregation must have sign '+', got {e.sign.value}")
            if mk == "anatomical" and ak == "anatomical":
                if g.has_node(mi.entity_iri) and g.has_node(ma.entity_iri):
                    if not is_part_of(g, mi.entity_iri, ma.entity_iri):
                        rep.errors.append(
                            f"{tag}: aggregation but {mi.entity_iri} is not part_of {ma.entity_iri}"
                        )
                else:
                    rep.notes.append(
                        f"{tag}: aggregation entities not in part_of backbone — add them to validate"
                    )

    rep.free_floating_macro = free_floating_macro(pmap)
    rep.conservation = sorted(
        {e.macro for e in pmap.constitutive_edges if e.relation == "aggregation"}
    )
    return rep


def free_floating_macro(pmap: PhysioMap) -> list[str]:
    """Macro (organ / organ_system / organism) nodes with no micro grounding.

    A macro node is *free-floating* if it has no incoming constitutive edge **and** is not
    flagged ``exogenous`` (a forcing/boundary input is legitimately not constituted, so it
    is not a grounding gap). For a finer accounting of *why* each remaining node is
    ungrounded, see :func:`classify_macro_grounding`.
    """
    constituted = {e.macro for e in pmap.constitutive_edges}
    macro_scales = {"organ", "organ_system", "organism"}
    return sorted(
        n.id
        for n in pmap.nodes
        if n.scale.value in macro_scales
        and n.id not in constituted
        and not n.exogenous
    )


def classify_macro_grounding(pmap: PhysioMap) -> dict[str, list[str]]:
    """Bucket every macro node by *how* it is (or is not) grounded — an honest audit.

    Constitution is cross-scale; many macro variables are legitimately explained
    *within* their own scale (an algebraic identity or a node with same-scale causal
    parents) and should **not** be given a fabricated constitutive edge. This classifier
    avoids the false impression that every ungrounded macro is a defect:

    * ``grounded``      — has an incoming **material** constitutive edge (aggregation/structural).
    * ``exogenous``     — flagged ``exogenous`` (forcing/boundary input; constitution N/A).
    * ``derived``       — ungrounded but has ≥1 causal parent (explained causally / definitionally,
      including a typed production-derived compatibility edge).
    * ``ungrounded``    — ungrounded **and** a causal root (no causal parents): the genuine
      residual grounding gap (a pool/output that should be constituted but is not yet).

    Returns ``{bucket: sorted[node id]}``.
    """
    graph = pmap.causal_subgraph()  # includes tagged production shadows for compatibility
    constituted = {e.macro for e in pmap.constitutive_edges}
    macro_scales = {"organ", "organ_system", "organism"}
    out: dict[str, list[str]] = {"grounded": [], "exogenous": [], "derived": [], "ungrounded": []}
    for n in pmap.nodes:
        if n.scale.value not in macro_scales:
            continue
        if n.id in constituted:
            out["grounded"].append(n.id)
        elif n.exogenous:
            out["exogenous"].append(n.id)
        elif any(s != n.id for s in graph.predecessors(n.id)):  # has a non-self causal parent
            out["derived"].append(n.id)
        else:
            out["ungrounded"].append(n.id)
    return {k: sorted(v) for k, v in out.items()}


def check_conservation(pmap: PhysioMap) -> dict[str, list[str]]:
    """Group aggregation edges into conservation relations ``whole <- [parts]``.

    A whole quantity is the mereological sum of its parts; every part contributes ``+``. This
    is the structural basis for mass-balance / conservation invariants (evaluation family 9):
    at steady state ``Δwhole = Σ Δparts``. Returns ``{whole: [part ids]}``.
    """
    out: dict[str, list[str]] = {}
    for e in pmap.constitutive_edges:
        if e.relation == "aggregation":
            out.setdefault(e.macro, []).append(e.micro)
    return out
