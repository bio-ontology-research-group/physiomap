"""Multiplicative (gain) edges — the second-order layer George Gkoutos's curation surfaced.

A :class:`~physiomap_core.model.ModulationEdge` says a node scales the *strength* of a causal
edge. This module answers the new question that structure enables — **gain sensitivity**: does a
do()-intervention change the sensitivity of one variable to another?

It also exposes the **first-order shadow**: the ordinary additive edge a modulation implies around
a positive operating point (``modulator -> edge_target`` with the modulation's sign), which is how
the existing sign solver already picks up the modulation's main effect — so adding modulations
changes no node-level prediction (soundness preserved); they only *add* the gain query.

See ``benchmarks/results/george_heart_rate.md`` and the representation section
of ``README.md``.
"""

from __future__ import annotations

from pydantic import BaseModel

from physiomap_core.model import ModulationEdge, PhysioMap, Sign
from physiomap_core.qualitative import Intervention, solve_signs


def _mul(a: Sign | None, b: Sign | None) -> Sign | None:
    """Sign product (``?`` absorbs, ``None`` = no effect propagates)."""
    if a is None or b is None:
        return None
    if a == Sign.UNKNOWN or b == Sign.UNKNOWN:
        return Sign.UNKNOWN
    return Sign.PLUS if a == b else Sign.MINUS


def _add(a: Sign | None, b: Sign | None) -> Sign | None:
    """Sign sum: ``+ + + = +``, ``- + - = -``, opposing signs or any ``?`` -> ``?``."""
    if a is None:
        return b
    if b is None:
        return a
    if a == b:
        return a
    return Sign.UNKNOWN


def modulations_of(
    pmap: PhysioMap, edge: str | tuple[str, str]
) -> list[ModulationEdge]:
    """All modulations of one influence ID, or a compatibility source/target pair."""
    if isinstance(edge, str):
        return [m for m in pmap.modulation_edges if m.influence_id == edge]
    source, target = edge
    return [
        m
        for m in pmap.modulation_edges
        if (m.edge_source, m.edge_target) == (source, target)
    ]


def gain_sensitivity(
    pmap: PhysioMap, intervention: Intervention, edge: tuple[str, str]
) -> Sign | None:
    """Sign of ``d(gain of edge)/dθ`` under ``intervention`` — the cross-partial
    ``d² edge_target / d(edge_source) d(θ)``.

    For each modulator of ``edge``: propagate the intervention to the modulator with the
    ordinary comparative-statics solver, multiply by the modulation's sign, and sum the
    contributions over all modulators. Returns ``None`` if no modulator responds to θ,
    ``Sign.UNKNOWN`` on an ambiguous/conflicting result.
    """
    mods = modulations_of(pmap, edge)
    if not mods:
        return None
    predicted = solve_signs(pmap, intervention).predicted
    total: Sign | None = None
    for m in mods:
        dmod = predicted.get(m.modulator)  # sign of d(modulator)/dθ (None = unchanged)
        total = _add(total, _mul(dmod, m.sign))
    return total


# ---------------------------------------------------------------------------
# Second-order *qualitative* layer: the sign-only content of a multiplicative edge.
#
# A modulation ``m scales (s -> t)`` means J_ts = k(x_m) g'(x_s); its distinctive content is the
# mixed second partial d2 t / ds dm = k'(x_m) g'(x_s). Three sign-only objects fall out, none of
# which need magnitudes (only the *sign* of a second derivative — which is itself qualitative):
#   * interaction sign  iota = mu . sigma           (intrinsic: amplify / dampen / reverse)
#   * gain change (sensitization) under do(theta):  mu . sign(d x_m / d theta)
#   * joint synergy of do(s) & do(m) at t:          iota . sign(Δs) . sign(Δm)   (super/sub-additive)
# Determinacy follows the usual discipline: any '?' input -> abstain (report nothing, count it).
# ---------------------------------------------------------------------------


def base_edge_sign(pmap: PhysioMap, edge: tuple[str, str]) -> Sign | None:
    """Sign sigma of the modulated causal edge ``edge``; ``UNKNOWN`` if parallel edges disagree,
    ``None`` if the edge is absent (the model validator guarantees it is not, for a modulation)."""
    s, t = edge
    signs = {e.sign for e in pmap.causal_edges if e.source == s and e.target == t}
    if not signs:
        return None
    if len(signs) > 1:
        return Sign.UNKNOWN
    return signs.pop()


def interaction_sign(pmap: PhysioMap, m: ModulationEdge) -> Sign | None:
    """Intrinsic interaction sign ``iota = mu . sigma`` (no intervention needed): does raising the
    modulator make the ``edge_source -> edge_target`` effect **more positive** (``+``, amplify) or
    **more negative** (``-``, dampen / toward reversal)?"""
    sigma = pmap.influence(m.influence_id).sign if m.influence_id else base_edge_sign(
        pmap, (m.edge_source, m.edge_target)
    )
    return _mul(m.sign, sigma)


def interaction_phrase(iota: Sign | None, can_flip: bool) -> str:
    if iota == Sign.PLUS:
        return "amplifies (steeper response)"
    if iota == Sign.MINUS:
        return "dampens (shallower response)" + (" — can reverse the edge" if can_flip else "")
    return "modulates (interaction direction undetermined)"


class GainChange(BaseModel):
    """A modulation whose **gain** an intervention determinately strengthens/weakens (sensitization)."""

    modulator: str
    edge_source: str
    edge_target: str
    modulation_sign: str          # mu
    modulator_change: str         # sign(d modulator / d theta) under the intervention
    direction: str                # "+" gain strengthened / "-" gain weakened  (= mu . modulator_change)


class Synergy(BaseModel):
    """A joint do() that moves **both** a modulator and its edge's source: the qualitative
    departure-from-additivity at the modulated target."""

    modulator: str
    edge_source: str
    edge_target: str
    interaction_sign: str         # iota = mu . sigma
    source_change: str            # sign(Δ edge_source) under the intervention
    modulator_change: str         # sign(Δ modulator) under the intervention
    cross_sign: str               # iota . source_change . modulator_change  (sign of the cross term)
    target_direction: str         # additive predicted sign of the target ("+"/"-"/"?")
    verdict: str                  # "synergistic" | "antagonistic" | "reinforces" (target dir '?')


def _change(node: str, do: dict[str, Sign], predicted: dict[str, Sign]) -> Sign | None:
    """Signed change of ``node`` under an intervention: the clamp if clamped, else the solver's
    comparative-static prediction, else ``None`` (no change / unreached)."""
    if node in do:
        return do[node]
    return predicted.get(node)


def gain_changes(
    pmap: PhysioMap, do: dict[str, Sign], predicted: dict[str, Sign]
) -> list[GainChange]:
    """Every modulation whose gain the intervention **determinately** strengthens or weakens.

    ``predicted`` is the comparative-statics field already solved for this intervention (so this is
    a pure post-processing pass — no extra solve)."""
    out: list[GainChange] = []
    for m in pmap.modulation_edges:
        dmod = _change(m.modulator, do, predicted)
        d = _mul(m.sign, dmod)
        if d in (Sign.PLUS, Sign.MINUS):
            out.append(GainChange(
                modulator=m.modulator, edge_source=m.edge_source, edge_target=m.edge_target,
                modulation_sign=m.sign.value, modulator_change=dmod.value, direction=d.value))
    return out


def synergies(
    pmap: PhysioMap, do: dict[str, Sign], predicted: dict[str, Sign]
) -> list[Synergy]:
    """Qualitative synergy/antagonism at each modulated target whose **source and modulator are both
    moved** by the intervention. The second-order cross term contributes ``iota . Δs . Δm`` to the
    target; comparing its sign to the additive direction gives super- vs sub-additivity."""
    out: list[Synergy] = []
    for m in pmap.modulation_edges:
        ds = _change(m.edge_source, do, predicted)
        dm = _change(m.modulator, do, predicted)
        if ds not in (Sign.PLUS, Sign.MINUS) or dm not in (Sign.PLUS, Sign.MINUS):
            continue  # need both endpoints actually moved (no cross term otherwise)
        iota = interaction_sign(pmap, m)
        cross = _mul(iota, _mul(ds, dm))
        if cross not in (Sign.PLUS, Sign.MINUS):
            continue
        tdir = predicted.get(m.edge_target)
        if tdir == Sign.PLUS or tdir == Sign.MINUS:
            verdict = "synergistic" if cross == tdir else "antagonistic"
        else:
            verdict = "reinforces"  # additive direction itself ambiguous; only the curvature is signed
        out.append(Synergy(
            modulator=m.modulator, edge_source=m.edge_source, edge_target=m.edge_target,
            interaction_sign=iota.value, source_change=ds.value, modulator_change=dm.value,
            cross_sign=cross.value, target_direction=(tdir.value if tdir else "?"), verdict=verdict))
    return out


def regime_conditional_signs(pmap: PhysioMap, m: ModulationEdge) -> dict[str, str] | None:
    """For a sign-flipping gain (``can_flip_sign``), the **context-conditional** edge sign by
    modulator regime — the case analysis that is sound with up/down alone (the threshold itself is
    quantitative and deliberately left unlocated). ``None`` if the gain cannot cross zero."""
    if not m.can_flip_sign:
        return None
    sigma = pmap.influence(m.influence_id).sign if m.influence_id else base_edge_sign(
        pmap, (m.edge_source, m.edge_target)
    )
    sg = sigma.value if sigma in (Sign.PLUS, Sign.MINUS) else "?"
    flip = "-" if sg == "+" else ("+" if sg == "-" else "?")
    # mu = direction the gain k moves with the modulator; above threshold k has sign sigma's sign
    if m.sign == Sign.PLUS:        # gain rises with modulator
        return {"modulator_high": sg, "modulator_low": flip, "unconditional": "?"}
    if m.sign == Sign.MINUS:       # gain falls with modulator
        return {"modulator_high": flip, "modulator_low": sg, "unconditional": "?"}
    return {"modulator_high": "?", "modulator_low": "?", "unconditional": "?"}


def first_order_shadow(m: ModulationEdge) -> tuple[str, str, Sign]:
    """The additive edge a modulation implies at a positive operating point:
    ``(modulator -> edge_target, sign = m.sign)``. The existing solver should already carry
    this as a normal causal edge (the modulation's main effect)."""
    return (m.modulator, m.edge_target, m.sign)


def shadow_is_present(pmap: PhysioMap, m: ModulationEdge) -> bool:
    """True if the modulation's first-order shadow exists as a causal edge with matching sign."""
    src, tgt, sgn = first_order_shadow(m)
    return any(
        e.source == src and e.target == tgt and e.sign == sgn for e in pmap.causal_edges
    )


def _main(argv: list[str]) -> int:
    """CLI: do(<node> <+|->) and report the gain sensitivity of edge <src> -> <tgt>.

    Usage:  python -m physiomap_core.modulation <do_node> <+|-> <edge_source> <edge_target>
            python -m physiomap_core.modulation --list        # list all modulation edges
    """
    from physiomap_core.hpo import build_map

    pmap = build_map()
    if argv[:1] == ["--list"]:
        for m in pmap.modulation_edges:
            iota = interaction_sign(pmap, m)
            iv = iota.value if iota in (Sign.PLUS, Sign.MINUS) else "?"
            print(
                f"{m.modulator}  scales[{m.sign.value}]  "
                f"{m.edge_source} -> {m.edge_target}"
                f"   [iota={iv}: {interaction_phrase(iota, m.can_flip_sign)}]"
                + ("  (sign-flipping)" if m.can_flip_sign else "")
            )
        return 0
    if len(argv) != 4 or argv[1] not in ("+", "-"):
        print(_main.__doc__)
        return 2
    do_node, do_sign, es, et = argv
    interv = Intervention(targets={do_node: Sign(do_sign)})
    gs = gain_sensitivity(pmap, interv, (es, et))
    net = solve_signs(pmap, interv).predicted.get(et)
    print(f"do({do_node} {do_sign})")
    print(f"  net effect on {et:<24} : {getattr(net, 'value', net) or '0 (unchanged)'}")
    gv = "(no modulator responds)" if gs is None else gs.value
    print(f"  gain sensitivity of {es} -> {et} : {gv}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(_main(sys.argv[1:]))
