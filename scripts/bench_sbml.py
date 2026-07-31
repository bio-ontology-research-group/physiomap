#!/usr/bin/env python3
"""Validate PhysioMap edge signs against the actual Guyton ODE models (family 2 extension).

For each curated check, load the vendored Guyton SBML module with libRoadRunner, perturb a
constant input parameter, integrate to steady state, and read the sign of the steady-state
change of an output variable. Compare that ground-truth ODE sign to the sign PhysioMap
encodes for the corresponding causal edge. This validates the (draft) edge signs against the
published quantitative model they were derived from — no human labelling.

Requires libroadrunner (needs LD_LIBRARY_PATH to the uv python's libpython on ws).
Run:  LD_LIBRARY_PATH=... uv run python scripts/bench_sbml.py
Writes benchmarks/results/sbml_edge_validation.{md,json}.
"""

from __future__ import annotations

import json
from pathlib import Path

import roadrunner

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "benchmarks" / "guyton" / "biomodels"

# (module file, input parameter, output variable, PhysioMap edge, expected sign, adaptive?)
# adaptive=True flags a reflex that ADAPTS (its chronic steady-state response is ~0 by
# design); PhysioMap encodes the *acute* sign, so a chronic '0' is expected and informative
# rather than a contradiction.
CHECKS = [
    ("Guyton1972_Angiotensin__MODEL0911342562.xml", "MDFLW", "ANC",
     "renal_perfusion_pressure -> renin (-)  [higher macula densa flow suppresses renin]", "-", False),
    ("Guyton1972_Angiotensin__MODEL0911342562.xml", "MDFLW", "ANM",
     "renal_perfusion_pressure -> (renin->) angiotensin effect (-)", "-", False),
    ("Guyton1972_Aldosterone__MODEL0911376350.xml", "ANM", "AMC",
     "angiotensin_II -> aldosterone (+)", "+", False),
    ("Guyton1972_AntidiureticHormone__MODEL0911309080.xml", "CNA", "ADHC",
     "plasma_osmolality/sodium -> adh (+)", "+", False),
    ("Guyton1972_AtrialNatriureticPeptide__MODEL0911272039.xml", "PRA", "ANPC",
     "blood_volume/atrial pressure -> anp (+)", "+", False),
    ("Guyton1972_Autonomics__MODEL0911270005.xml", "PA", "AU",
     "mean_arterial_pressure -> sympathetic_tone (-)  [ARTERIAL BAROREFLEX — adapts, BAROTC]", "-", True),
    ("Guyton1972_AntidiureticHormone__MODEL0911309080.xml", "PA1", "ADHC",
     "mean_arterial_pressure -> adh (-)  [pressure arm — adaptive]", "-", True),
]

REL_STEP = 0.05
TOL = 1e-6
SIM_T = 3.0e5      # integrate to (numerical) steady state; Guyton modules settle well before
SIM_PTS = 3000

# These CellML->SBML modules carry their state in *parameters* with rate rules (no SBML
# floating species), so we integrate the ODE and read the variable's value directly.


def _settle(rr: roadrunner.RoadRunner) -> None:
    rr.simulate(0, SIM_T, SIM_PTS)


def run_check(module: str, inp: str, out: str, edge: str, expected: str,
              adaptive: bool = False) -> dict:
    path = str(MODELS / module)
    res = {"module": module, "input": inp, "output": out, "edge": edge,
           "expected": expected, "adaptive": adaptive}
    try:
        rr = roadrunner.RoadRunner(path)
        params = set(rr.model.getGlobalParameterIds())
        if inp not in params:
            res["status"] = f"input '{inp}' not a global parameter"
            return res
        base = rr[inp]
        if base == 0:
            base = 1.0
        _settle(rr)
        y0 = float(rr[out])
        rr2 = roadrunner.RoadRunner(path)
        rr2[inp] = base * (1.0 + REL_STEP)
        _settle(rr2)
        y1 = float(rr2[out])
        dy = y1 - y0
        scale = max(abs(y0), abs(y1), 1e-12)
        if abs(dy) / scale < TOL:
            sign = "0"
        else:
            sign = "+" if dy > 0 else "-"
        res.update({"y0": y0, "y1": y1, "numeric_sign": sign,
                    "agrees": sign == expected, "status": "ok"})
    except Exception as e:  # pragma: no cover - environment dependent
        res["status"] = f"error: {type(e).__name__}: {e}"
    return res


def main() -> int:
    results = [run_check(*c) for c in CHECKS]
    ok = [r for r in results if r.get("status") == "ok"]
    static = [r for r in ok if not r["adaptive"]]
    static_agree = [r for r in static if r.get("agrees")]
    adaptive = [r for r in ok if r["adaptive"]]
    adaptive_chronic_zero = [r for r in adaptive if r.get("numeric_sign") == "0"]

    out_dir = ROOT / "benchmarks" / "results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "sbml_edge_validation.json").write_text(json.dumps(results, indent=2))

    lines = ["# Edge-sign validation against the Guyton ODE models (family 2 extension)", ""]
    lines.append("Each row perturbs a constant input of a vendored Guyton SBML module by "
                 f"+{int(REL_STEP*100)}%, integrates the ODE to steady state, and compares "
                 "the sign of the output's steady-state change to the sign PhysioMap encodes.")
    lines.append("")
    lines.append(
        f"- **non-adaptive edges confirmed: {len(static_agree)}/{len(static)}** "
        "(direct sign agreement with the published ODE)"
    )
    lines.append(
        f"- adaptive (reflex) edges: {len(adaptive)} — chronic steady-state ~0 in "
        f"{len(adaptive_chronic_zero)}/{len(adaptive)} (see note)"
    )
    lines.append("")
    lines.append("| module | input | output | ODE sign | PhysioMap | verdict | edge |")
    lines.append("|---|---|---|:--:|:--:|:--:|---|")
    for r in results:
        mod = r["module"].split("__")[0].replace("Guyton1972_", "")
        if r.get("status") != "ok":
            lines.append(f"| {mod} | {r['input']} | {r['output']} | — | {r['expected']} | "
                         f"{r['status']} | {r['edge']} |")
            continue
        if r["adaptive"]:
            verdict = "adaptive" if r["numeric_sign"] == "0" else ("OK" if r["agrees"] else "XX")
        else:
            verdict = "OK" if r["agrees"] else "XX"
        lines.append(f"| {mod} | {r['input']} | {r['output']} | {r['numeric_sign']} | "
                     f"{r['expected']} | {verdict} | {r['edge']} |")
    lines += [
        "",
        "## Note on the adaptive edges",
        "",
        "The arterial baroreflex (`Autonomics`, time constant `BAROTC`) and the ADH "
        "pressure arm **adapt**: their *chronic* steady-state response to a sustained "
        "pressure change is ~0. This is Guyton's own classic result — the arterial "
        "baroreflex does not set long-term arterial pressure (renal pressure-natriuresis "
        "does). PhysioMap's edge encodes the **acute** reflex sign, so a chronic `0` here "
        "is an expected, informative timescale distinction, not a contradiction. It flags "
        "that these edges should carry an acute/chronic annotation for steady-state use.",
    ]
    (out_dir / "sbml_edge_validation.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
