"""The causal-evidence gate: admit an edge only if its evidence is *interventional*.

A PhysioMap causal edge means ``do(source) -> Δtarget`` (set the source, hold everything
else fixed, the target shifts). That is a strictly stronger claim than "source and target
co-vary". When edges are imported from external resources — gene-regulatory networks
(TRRUST / DoRothEA / CollecTRI / SIGNOR), whole-cell / ODE models (Physiome / BioModels),
pathway databases — most candidate relations are **associations** (co-expression,
TF-binding) that have *never* been shown to be causal under intervention. Importing those
would silently turn PhysioMap into a correlation network and break soundness.

This module defines which :class:`~physiomap_core.model.CausalEvidenceClass` values count
as interventional (do-supported) vs associational, and a gate that admits an edge only on
the former. ``scripts/validate_causal_evidence.py`` runs it over a fragment.

Hierarchy of interventional strength (all admissible; strongest first):

  1. ``perturbation``             — direct molecular do(): KO / KD / CRISPR / RNAi /
                                    overexpression of the source, target measured.
  2. ``pharmacological``          — agonist / antagonist / inhibitor of the source, target
                                    measured (e.g. a HIF prolyl-hydroxylase inhibitor).
  3. ``genetic_lof_gof``          — a human Mendelian loss/gain-of-function in the source is
                                    a *natural* do(); the downstream change is the effect.
  4. ``mendelian_randomization``  — a germline variant used as an instrument (IV ~ do()).
  5. ``mechanistic_model``        — sign read from the Jacobian of a curated mechanistic
                                    (mass-action / rate-law) ODE; causal by construction.
  6. ``curated_mechanistic``      — a pathway-DB *causal* statement (SIGNOR / INDRA / GO-CAM)
                                    whose underlying evidence is mechanistic or perturbational.

Associational (INADMISSIBLE — must not be imported as a causal edge):

  * ``binding_only``              — ChIP-seq / motif occupancy: physical binding is not a
                                    demonstrated functional effect.
  * ``coexpression``             — correlation / co-expression inference (ARACNe, GENIE3,
                                    WGCNA, GTEx-derived networks).
  * ``observational_association`` — epidemiological / GWAS association without an instrument.
  * ``unknown``                   — class not established.
"""

from __future__ import annotations

from physiomap_core.model import (
    CausalEdge,
    CausalEvidenceClass,
    ModulationEdge,
    PhysioMap,
)

# ---------------------------------------------------------------------------
# the partition: interventional (do-supported) vs associational
# ---------------------------------------------------------------------------

INTERVENTIONAL: frozenset[CausalEvidenceClass] = frozenset(
    {
        CausalEvidenceClass.PERTURBATION,
        CausalEvidenceClass.PHARMACOLOGICAL,
        CausalEvidenceClass.GENETIC_LOF_GOF,
        CausalEvidenceClass.MENDELIAN_RANDOMIZATION,
        CausalEvidenceClass.MECHANISTIC_MODEL,
        CausalEvidenceClass.CURATED_MECHANISTIC,
    }
)

ASSOCIATIONAL: frozenset[CausalEvidenceClass] = frozenset(
    {
        CausalEvidenceClass.BINDING_ONLY,
        CausalEvidenceClass.COEXPRESSION,
        CausalEvidenceClass.OBSERVATIONAL_ASSOCIATION,
        CausalEvidenceClass.UNKNOWN,
    }
)

assert INTERVENTIONAL | ASSOCIATIONAL == set(CausalEvidenceClass), (
    "every CausalEvidenceClass must be partitioned as interventional or associational"
)
assert not (INTERVENTIONAL & ASSOCIATIONAL), "the partition must be disjoint"

# Default evidence class implied by a source resource. This is *guidance* for an importing
# agent — the per-edge tag should reflect the SPECIFIC evidence behind that edge, but this
# captures what a database can deliver at best, so a co-expression GRN cannot masquerade as
# causal merely by being in a "regulatory network" file. Keys are lowercase substrings
# matched against the resource name.
SOURCE_DEFAULT: dict[str, CausalEvidenceClass] = {
    # signed, mechanism/perturbation-curated regulatory resources
    "signor": CausalEvidenceClass.CURATED_MECHANISTIC,
    "indra": CausalEvidenceClass.CURATED_MECHANISTIC,
    "trrust": CausalEvidenceClass.CURATED_MECHANISTIC,
    "collectri": CausalEvidenceClass.CURATED_MECHANISTIC,
    "omnipath": CausalEvidenceClass.CURATED_MECHANISTIC,
    "go-cam": CausalEvidenceClass.CURATED_MECHANISTIC,
    # quantitative mechanistic models
    "biomodels": CausalEvidenceClass.MECHANISTIC_MODEL,
    "cellml": CausalEvidenceClass.MECHANISTIC_MODEL,
    "physiome": CausalEvidenceClass.MECHANISTIC_MODEL,
    # logical models project to a signed interaction graph (modeller's causal claim)
    "ginsim": CausalEvidenceClass.CURATED_MECHANISTIC,
    "cell collective": CausalEvidenceClass.CURATED_MECHANISTIC,
    # association-only resources — NOT admissible
    "aracne": CausalEvidenceClass.COEXPRESSION,
    "genie3": CausalEvidenceClass.COEXPRESSION,
    "wgcna": CausalEvidenceClass.COEXPRESSION,
    "coexpression": CausalEvidenceClass.COEXPRESSION,
    "co-expression": CausalEvidenceClass.COEXPRESSION,
    "chip-seq": CausalEvidenceClass.BINDING_ONLY,
    "chip-atlas": CausalEvidenceClass.BINDING_ONLY,
    "encode tfbs": CausalEvidenceClass.BINDING_ONLY,
    "gwas catalog": CausalEvidenceClass.OBSERVATIONAL_ASSOCIATION,
}


def is_interventional(cls: CausalEvidenceClass | None) -> bool:
    """True iff ``cls`` establishes a do()-supported (causal) relation."""
    return cls in INTERVENTIONAL


def classify_source(resource: str) -> CausalEvidenceClass:
    """Best-case evidence class a *named resource* can deliver (guidance for importers).

    Returns :attr:`CausalEvidenceClass.UNKNOWN` for an unrecognised resource — i.e. an
    importing agent must supply explicit per-edge evidence rather than rely on the source.
    """
    name = (resource or "").lower()
    for key, cls in SOURCE_DEFAULT.items():
        if key in name:
            return cls
    return CausalEvidenceClass.UNKNOWN


def admit(edge: CausalEdge) -> tuple[bool, str]:
    """Decide whether ``edge`` may be imported as a causal edge.

    Returns ``(ok, reason)``. ``ok`` is True only when the edge carries an *interventional*
    :class:`CausalEvidenceClass`. A missing class, or any associational class, is rejected
    with an explanatory reason.
    """
    cls = edge.causal_evidence
    if cls is None:
        return False, "no causal_evidence class (cannot confirm the edge is interventional)"
    if cls in ASSOCIATIONAL:
        return (
            False,
            f"evidence class {cls.value!r} is ASSOCIATIONAL (binding/co-expression/"
            "observational) — an association is not a cause; not admissible",
        )
    return True, f"interventional evidence ({cls.value})"


def audit_map(pmap: PhysioMap, require_all: bool = False) -> list[str]:
    """Return a list of admissibility violations for the causal edges of ``pmap``.

    With ``require_all=False`` (default) only edges that *carry* a class are checked, and a
    violation is an associational class (a hand-curated edge with no class is left alone).
    With ``require_all=True`` every edge must carry an interventional class — the mode used
    to gate a freshly *imported* fragment, where provenance is mandatory.
    """
    violations: list[str] = []
    for e in pmap.causal_edges:
        if e.causal_evidence is None and not require_all:
            continue
        ok, reason = admit(e)
        if not ok:
            violations.append(f"{e.source} -> {e.target} ({e.sign.value}): {reason}")
    return violations


# ---------------------------------------------------------------------------
# modulation (multiplicative / gain) edges
# ---------------------------------------------------------------------------
#
# A ModulationEdge is the SIGN OF AN INTERACTION (a mixed second derivative): increasing the
# modulator changes the strength of an edge. It is a strictly stronger and more easily
# over-claimed assertion than a first-order edge — you cannot read it off single-factor
# interventions (see README.md, Representation). So it is gated *harder*: a modulation
# is admissible only with INTERVENTIONAL evidence of the interaction itself — a two-factor /
# 2x2 do() showing the effect of ``edge_source`` on ``edge_target`` genuinely changes with the
# modulator's level, or a mechanistic-model Jacobian carrying the cross term. The admissible
# vocabulary is the same INTERVENTIONAL set; the difference is that a class is ALWAYS required
# (a modulation never gets the hand-curated "no class" pass an ordinary edge may take).


def admit_modulation(mod: ModulationEdge) -> tuple[bool, str]:
    """Decide whether ``mod`` may stand as a modulation (gain) edge.

    Returns ``(ok, reason)``. Admissible only with an *interventional* class — and, because a
    gain claim is unfalsifiable without it, the evidence must in spirit be **interaction**
    evidence (the slope ``∂edge_target/∂edge_source`` changes with the modulator). A missing
    class or any associational class is rejected.
    """
    cls = mod.causal_evidence
    if cls is None:
        return (
            False,
            "no causal_evidence class — a gain edge needs INTERACTION evidence (a two-factor "
            "do() showing the effect of edge_source on edge_target changes with the modulator, "
            "or a mechanistic-model cross term)",
        )
    if cls in ASSOCIATIONAL:
        return (
            False,
            f"evidence class {cls.value!r} is ASSOCIATIONAL — a correlation of slopes is not a "
            "demonstrated interaction; not admissible for a gain edge",
        )
    return True, f"interventional interaction evidence ({cls.value})"


def audit_modulations(pmap: PhysioMap) -> list[str]:
    """Return admissibility violations for the modulation edges of ``pmap``.

    Unlike :func:`audit_map`, every modulation edge is checked (a class is *always* required):
    a multiplicative claim is too easily over-asserted to leave ungated.
    """
    violations: list[str] = []
    for m in pmap.modulation_edges:
        ok, reason = admit_modulation(m)
        if not ok:
            violations.append(
                f"{m.modulator} scales ({m.edge_source} -> {m.edge_target}) "
                f"[{m.sign.value}]: {reason}"
            )
    return violations
