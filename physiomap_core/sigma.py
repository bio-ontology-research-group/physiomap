"""SCC condensation + sigma-separation for cyclic causal graphs.

Design decision **D1** (see ``resources/ode-causality/NOTES.md``): two
independent implementations of sigma-separation, differentially tested against each other
and (on acyclic inputs) against ``networkx`` d-separation.

* :func:`sigma_separated_acyclify` — **primary**. Build the *acyclification* of the causal
  DiGraph (Forré & Mooij 2017; Bongers, Forré, Mooij & Mooij, *Ann. Statist.* 2021) and
  delegate to networkx d-separation. sigma-separation in the cyclic graph equals
  d-separation in the acyclified graph. On a DAG the acyclification is the identity, so
  this agrees with networkx on acyclic inputs by construction.
* :func:`sigma_separated_oracle` — **independent oracle**. Applies a hand-rolled
  ancestral-moral-graph d-separation (Lauritzen separation) to the *same* acyclification,
  on a code path independent of networkx's d-separation. (A direct walk criterion on the
  cyclic graph would require enumerating walks that revisit nodes inside an SCC, which is
  unbounded; the moral-graph engine on the acyclification is correct and finite.) The
  differential test pins the two separation engines against each other; the acyclic anchor
  pins the acyclification against networkx on the original graph.

Acyclification recipe (Forré & Mooij 2017, Def. 2.7.1), with ``Sc(v)`` = the strongly
connected component of ``v``:

* directed edges: ``v -> w`` iff ``v ∉ Sc(w)`` and some ``w' ∈ Sc(w)`` has ``v -> w'`` in
  ``G`` (condense SCCs, lift every inter-SCC edge to all targets in the target SCC, erase
  intra-SCC edges);
* bidirected (confounding) edges among all pairs within each SCC.

We realise the bidirected clique of each SCC by a single latent common cause ``L_S -> s``
for every ``s`` in the component, turning the acyclification into an ordinary DAG on which
networkx d-separation computes m-separation correctly (latents present but never
conditioned). This makes same-SCC nodes inseparable, as sigma-separation requires.
"""

from __future__ import annotations

import itertools
from collections import deque
from collections.abc import Iterable

import networkx as nx

from physiomap_core.model import PhysioMap

__all__ = [
    "acyclify",
    "deterministic_closure",
    "sigma_separated",
    "sigma_separated_acyclify",
    "sigma_separated_oracle",
]

NodeSet = set


# --------------------------------------------------------------------------- #
# Acyclification + networkx d-separation (primary)
# --------------------------------------------------------------------------- #


def _sccs(graph: nx.DiGraph) -> tuple[list[frozenset], dict]:
    comps = [frozenset(c) for c in nx.strongly_connected_components(graph)]
    node2comp = {n: i for i, c in enumerate(comps) for n in c}
    return comps, node2comp


def acyclify(graph: nx.DiGraph) -> tuple[nx.DiGraph, set]:
    """Return ``(G_acy, latents)``: the acyclification of ``graph`` as an ordinary DAG.

    Each SCC's bidirected clique is encoded by a fresh latent common cause (a node
    ``("_L", i)``). ``latents`` is the set of those latent node ids. d-separation on
    ``G_acy`` (latents present, never conditioned) equals sigma-separation on ``graph``.
    """
    comps, node2comp = _sccs(graph)
    h: nx.DiGraph = nx.DiGraph()
    h.add_nodes_from(graph.nodes)

    # directed inter-SCC edges, lifted to every node of the target SCC
    for u, v in graph.edges:
        cu, cv = node2comp[u], node2comp[v]
        if cu != cv:
            for w in comps[cv]:
                h.add_edge(u, w)

    # latent common cause per non-trivial SCC -> bidirected clique
    latents: set = set()
    for i, comp in enumerate(comps):
        if len(comp) >= 2:
            lat = ("_L", i)
            latents.add(lat)
            h.add_node(lat)
            for n in comp:
                h.add_edge(lat, n)
    return h, latents


def _nx_d_separated(dag: nx.DiGraph, x: set, y: set, z: set) -> bool:
    """Call whichever d-separation primitive this networkx version exposes."""
    if hasattr(nx, "is_d_separator"):
        return bool(nx.is_d_separator(dag, x, y, z))
    return bool(nx.d_separated(dag, x, y, z))  # networkx < 3.3


def sigma_separated_acyclify(
    graph: nx.DiGraph, x: Iterable, y: Iterable, z: Iterable = ()
) -> bool:
    """sigma-separation of ``x`` and ``y`` given ``z`` via acyclification + d-separation."""
    xs, ys, zs = set(x), set(y), set(z)
    dag, _latents = acyclify(graph)
    return _nx_d_separated(dag, xs, ys, zs)


# --------------------------------------------------------------------------- #
# Independent oracle: ancestral-moral-graph d-separation on the acyclification
# --------------------------------------------------------------------------- #


def _d_sep_moral(dag: nx.DiGraph, x: set, y: set, z: set) -> bool:
    """d-separation by the ancestral + moral graph criterion (Lauritzen separation).

    Independent of ``networkx`` d-separation: restrict to the ancestral set of X∪Y∪Z,
    moralise (marry co-parents, drop arrow directions), delete Z, then test undirected
    reachability between X and Y.
    """
    keep = set(x) | set(y) | set(z)
    ancestral = set(keep)
    for n in keep:
        ancestral |= nx.ancestors(dag, n)
    sub = dag.subgraph(ancestral)

    moral: dict[object, set] = {n: set() for n in sub.nodes}
    for u, v in sub.edges:
        moral[u].add(v)
        moral[v].add(u)
    for node in sub.nodes:
        parents = list(sub.predecessors(node))
        for a, b in itertools.combinations(parents, 2):
            moral[a].add(b)
            moral[b].add(a)

    blocked = set(z)
    starts = (set(x) - blocked) & set(moral)
    targets = (set(y) - blocked) & set(moral)
    if not starts or not targets:
        return True

    seen = set(starts)
    dq = deque(starts)
    while dq:
        u = dq.popleft()
        if u in targets:
            return False
        for w in moral[u]:
            if w not in blocked and w not in seen:
                seen.add(w)
                dq.append(w)
    return seen.isdisjoint(targets)


def sigma_separated_oracle(
    graph: nx.DiGraph, x: Iterable, y: Iterable, z: Iterable = ()
) -> bool:
    """sigma-separation via acyclification + an independent moral-graph d-separation."""
    xs, ys, zs = set(x), set(y), set(z)
    dag, _latents = acyclify(graph)
    return _d_sep_moral(dag, xs, ys, zs)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #


def _deterministic_nodes(graph: nx.DiGraph) -> dict:
    """``node -> set(parents)`` for every node whose *entire* parent set is definitional.

    Such a node is an algebraic identity (e.g. ``MAP = CO x TPR``): a deterministic function
    of those parents. A node with even one non-definitional (stochastic) parent is **not**
    treated as deterministic (the guard keeps the closure sound under partial annotation).
    """
    det: dict = {}
    for n in graph.nodes:
        preds = list(graph.predecessors(n))
        if preds and all(graph.edges[p, n].get("definitional") for p in preds):
            det[n] = set(preds)
    return det


def _constitutive_deterministic_nodes(pmap: PhysioMap) -> dict:
    """``macro -> set(constituent ids)`` for macro nodes deterministically fixed by an
    **aggregation** (extensive/rate whole = sum of its ``aggregation`` constituents).

    Guarded like :func:`_deterministic_nodes`: the macro must have **no non-definitional causal
    parent** (else it is over-determined / stochastically driven and is not treated as fixed).
    Constitutive edges themselves are never added to the traversal graph -- this only augments the
    Geiger-Verma-Pearl closure so that conditioning on the constituents fixes the whole
    (Krantz-Luce-Suppes-Tversky Ch.3). Ratio identities are handled by
    :func:`_ratio_deterministic_nodes` (they are ternary RatioDefinitions, not constitutive edges).
    """
    from physiomap_core.quantity import QualityKind, load_quality_kinds, quality_kind

    kinds = load_quality_kinds()
    nodes = {n.id: n for n in pmap.nodes}
    by_macro: dict[str, list] = {}
    for e in pmap.material_constitutive_edges:
        by_macro.setdefault(e.macro, []).append(e)
    g = pmap.causal_subgraph()
    det: dict = {}
    for macro, edges in by_macro.items():
        node = nodes.get(macro)
        if node is None:
            continue
        mk = quality_kind(node, kinds)
        composable = mk in (QualityKind.EXTENSIVE, QualityKind.RATE) and all(
            e.relation == "aggregation" for e in edges)
        if not composable:
            continue
        # guard: any non-definitional causal parent makes the macro stochastically driven
        if any(not g.edges[p, macro].get("definitional") for p in g.predecessors(macro)):
            continue
        det[macro] = {e.micro for e in edges} | set(g.predecessors(macro))
    return det


def _ratio_deterministic_nodes(pmap: PhysioMap) -> dict:
    """``ratio -> {numerator, denominator}`` for each RatioDefinition whose ratio node is a clean
    deterministic quotient (its only causal parents are the numerator and denominator, all
    definitional). An over-parented ratio (an extra stochastic parent) is not deterministic --
    exactly as an entangled definitional identity is not (Geiger-Verma-Pearl)."""
    g = pmap.causal_subgraph()
    det: dict = {}
    for r in pmap.ratio_definitions:
        if r.ratio not in g:
            continue
        preds = set(g.predecessors(r.ratio))
        if preds and preds <= {r.numerator, r.denominator} and all(
                g.edges[p, r.ratio].get("definitional") for p in preds):
            det[r.ratio] = set(preds)
    return det


def _all_deterministic_nodes(pmap: PhysioMap, graph: nx.DiGraph) -> dict:
    """Definitional (causal-identity) determinism + aggregation determinism + ratio-identity
    determinism."""
    det = _deterministic_nodes(graph)
    for source in (_constitutive_deterministic_nodes(pmap), _ratio_deterministic_nodes(pmap)):
        for n, parents in source.items():
            det[n] = det.get(n, set()) | parents
    return det


def _det_closure(z: set, det: dict) -> set:
    """Geiger-Verma-Pearl deterministic closure of ``z``: add every node functionally
    determined by the set, to a fixpoint (a node is determined once all its definitional
    parents are in the set)."""
    s = set(z)
    changed = True
    while changed:
        changed = False
        for n, parents in det.items():
            if n not in s and parents <= s:
                s.add(n)
                changed = True
    return s


def deterministic_closure(pmap: PhysioMap, z: Iterable) -> set:
    """The set of nodes functionally determined by ``z`` via PhysioMap's definitional edges.

    Equals ``z`` plus every node all of whose parents are definitional and (recursively) in
    the set, **and** every constitutively-determined macro (an extensive sum or a complete
    ratio of its constituents) once its constituents are in the set. Used to make
    sigma-separation determinism-aware (see :func:`sigma_separated`).
    """
    return _det_closure(set(z), _all_deterministic_nodes(pmap, pmap.causal_subgraph()))


def sigma_separated(
    pmap: PhysioMap, x: Iterable, y: Iterable, z: Iterable = ()
) -> bool:
    """Are node sets ``x`` and ``y`` sigma-separated given ``z`` in ``pmap``?

    Operates on ``pmap.causal_subgraph()`` (constitutive edges are excluded). Uses the
    acyclification reduction (the proven, primary implementation), composed with the
    **Geiger-Verma-Pearl deterministic closure** so that algebraic-identity nodes (those whose
    parents are all ``definitional`` edges, e.g. ``MAP = CO x TPR``) are handled correctly:
    conditioning on the parents of such a node fixes it, blocking paths through it. The
    closure is sound for the forward (determined-by-``z``) direction; backward inference
    through an identity (knowing the output + some inputs pins the remaining input) would
    require invertibility assumptions and is intentionally not made.
    """
    graph = pmap.causal_subgraph()
    z2 = _det_closure(set(z), _all_deterministic_nodes(pmap, graph))
    xs, ys = set(x) - z2, set(y) - z2  # nodes fixed by z are constants -> contribute no dependence
    if not xs or not ys:
        return True
    return sigma_separated_acyclify(graph, xs, ys, z2)
