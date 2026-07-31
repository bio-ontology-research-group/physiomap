#!/usr/bin/env python3
"""Gate an *imported* PhysioMap fragment on CAUSAL (interventional) evidence.

PhysioMap edges are interventional (``do(source)->Δtarget``), not associations. When edges
come from external resources (gene-regulatory networks, ODE/whole-cell models, pathway
databases) this gate refuses any edge whose evidence is merely associational
(co-expression, TF-binding, observational) or unspecified — only edges with an
interventional :class:`~physiomap_core.model.CausalEvidenceClass` (perturbation,
pharmacological, genetic LoF/GoF, Mendelian randomization, mechanistic ODE, or
mechanism-curated pathway statement) are admitted.

Run on each imported fragment in addition to ``validate_fragment.py`` (schema + provenance):

    uv run python scripts/validate_causal_evidence.py benchmarks/multiscale/foo.yaml

Exit 0 = every causal edge carries an admissible interventional class.
Exit 1 = at least one edge is associational / unclassified (must fix or drop the edge).
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from physiomap_core.causal_evidence import (  # noqa: E402
    INTERVENTIONAL,
    admit,
    admit_modulation,
)
from physiomap_core.model import (  # noqa: E402
    CausalEdge,
    CausalEvidenceClass,
    ModulationEdge,
    ProductionEdge,
    ProductionEvidenceClass,
)


def main(path_str: str) -> int:
    path = Path(path_str)
    data = yaml.safe_load(path.read_text()) or {}
    raw_edges = data.get("causal_edges", []) or []

    errors: list[str] = []
    ok_count = 0
    for i, e in enumerate(raw_edges):
        src, tgt = e.get("source"), e.get("target")
        if src == tgt:
            continue  # self-regulation (implicit dissipation); not an imported relation
        ce = e.get("causal_evidence")
        if ce is None:
            errors.append(
                f"causal_edge[{i}] {src}->{tgt}: MISSING causal_evidence "
                "(imported edges must declare an interventional evidence class)"
            )
            continue
        try:
            edge = CausalEdge.model_validate(e)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"causal_edge[{i}] {src}->{tgt}: invalid ({exc})")
            continue
        admitted, reason = admit(edge)
        if admitted:
            ok_count += 1
        else:
            errors.append(f"causal_edge[{i}] {src}->{tgt}: {reason}")

    # modulation (multiplicative / gain) edges — gated harder: a class is always required.
    raw_mods = data.get("modulation_edges", []) or []
    mod_ok = 0
    for i, m in enumerate(raw_mods):
        label = f"{m.get('modulator')} scales {m.get('influence_id') or (m.get('edge_source'), m.get('edge_target'))}"
        try:
            mod = ModulationEdge.model_validate(m)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"modulation_edge[{i}] {label}: invalid ({exc})")
            continue
        admitted, reason = admit_modulation(mod)
        if admitted:
            mod_ok += 1
        else:
            errors.append(f"modulation_edge[{i}] {label}: {reason}")

    # Typed production/process-output relations use a separate controlled vocabulary. An
    # explicit legacy value is permitted (and counted) so migration debt is visible rather
    # than silently promoted to an interventional causal class.
    raw_production = data.get("production_edges", []) or []
    production_controlled = 0
    production_legacy = 0
    for i, raw in enumerate(raw_production):
        label = f"{raw.get('source')}->{raw.get('target')}"
        try:
            edge = ProductionEdge.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"production_edge[{i}] {label}: invalid ({exc})")
            continue
        if edge.production_evidence is ProductionEvidenceClass.LEGACY_UNCLASSIFIED:
            production_legacy += 1
        else:
            production_controlled += 1

    n = sum(1 for e in raw_edges if e.get("source") != e.get("target"))
    print(f"fragment: {path}")
    print(f"  interventional vocabulary: {sorted(c.value for c in INTERVENTIONAL)}")
    print(f"  causal edges: {n}   admitted (interventional): {ok_count}")
    if raw_mods:
        print(f"  modulation (gain) edges: {len(raw_mods)}   admitted (interaction): {mod_ok}")
    if raw_production:
        print(
            f"  production edges: {len(raw_production)}   controlled: "
            f"{production_controlled}   legacy-unclassified: {production_legacy}"
        )
    for er in errors:
        print(f"  ERROR {er}")
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
