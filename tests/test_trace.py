"""End-to-end Mendelian-disease tracing: variant do() -> signed path -> endophenotype."""

from __future__ import annotations

from physiomap_core.hpo import build_map
from physiomap_core.model import Sign
from physiomap_core.qualitative import Intervention
from physiomap_core.trace import trace

PM = build_map()


def test_hemochromatosis_determinate_path_to_transferrin_saturation():
    """HFE variant clamps hepcidin low; the chain to ↑transferrin saturation is determinate."""
    iv = Intervention(targets={"hepcidin": Sign.MINUS})
    r = trace(PM, iv, "transferrin_saturation")
    assert r["net_comparative_statics"] is Sign.PLUS      # endophenotype ↑ (compensation-aware)
    assert len(r["paths"]) == 1                            # loop broken by the clamp -> single path
    p = r["paths"][0]
    assert [s.dst for s in p.steps] == ["ferroportin_activity", "plasma_iron", "transferrin_saturation"]
    assert [s.edge_sign.value for s in p.steps] == ["-", "+", "+"]
    assert [s.running.value for s in p.steps] == ["+", "+", "+"]  # ferroportin↑, iron↑, tsat↑
    assert p.net is Sign.PLUS


def test_insulin_receptor_trace_crosses_to_organ_and_loops_to_unknown():
    """Molecular variant: determinate subcellular cascade reaching the organ rate, systemic = ?.

    BFO refactor: peripheral_glucose_uptake is a RATE (occurrent), so the GLUT4→uptake cross-scale
    link is CAUSAL, not a material constitutive lift; the whole path is now causal."""
    iv = Intervention(targets={"insulin_receptor_activity": Sign.MINUS})
    r = trace(PM, iv, "peripheral_glucose_uptake")
    assert r["paths"], "expected a molecular->organ path"
    p = r["paths"][0]
    assert all(s.kind == "causal" for s in p.steps)         # cross-scale link is causal now
    assert r["net_forward"] is Sign.MINUS                   # forward mechanism: ↓ uptake
    assert r["net_comparative_statics"] is Sign.UNKNOWN     # but homeostatic SCC -> ? (the thesis)


def test_trace_handles_unreachable_target():
    iv = Intervention(targets={"hepcidin": Sign.MINUS})
    r = trace(PM, iv, "plasma_phenylalanine")  # disconnected metabolic island
    assert r["paths"] == []
