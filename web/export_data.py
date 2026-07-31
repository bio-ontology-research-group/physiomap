#!/usr/bin/env python3
"""Export the canonical SCM (+ analyses) to web/physiomap.json for the viewer.

Loads the released SCM, tags each node with TWO orthogonal facets — its physiological
``system`` (what it is) and the legacy source fragment that introduced it (where the evidence
came from) — exposes causal, production, constitution, quantitative, and modulation layers,
computes SCCs, and precomputes every benchmark intervention overlay.

Run:  uv run python web/export_data.py
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import shutil
import subprocess
from collections import deque
from pathlib import Path
from typing import Any

import yaml

from physiomap_core import __version__ as PHYSIOMAP_VERSION
from physiomap_core.knockout import knockout_multi, trace_many_multi
from physiomap_core.model import Sign
from physiomap_core.modulation import interaction_sign, regime_conditional_signs
from physiomap_core.multiscale import constitutive_graph
from physiomap_core.scm import ScmManifest, canonical_scm_path

MAX_TRACE_PHENOTYPES = 14  # cap signed traces attached per intervention overlay (matches web.api)

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "benchmarks"
WEB = ROOT / "web"

WEB_PAYLOAD_FORMAT = "2.0.0"
BUCKETS = "0123456789abcdef"
BOOTSTRAP_GZIP_LIMIT = 200_000

# Fields needed to draw/filter/search the graph immediately.  Rich ontology, evidence, and
# projection metadata is losslessly kept in small lazy-loaded detail buckets instead of blocking
# first paint.  ``prov_source`` stays in the bootstrap because source-facet filtering uses it.
DETAIL_COLLECTIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "nodes": (
        "node",
        ("id", "label", "scale", "system", "source", "entity_iri", "quality_iri",
         "scc", "in_big_scc", "x", "y"),
    ),
    "causal_edges": (
        "causal",
        ("id", "source", "target", "sign", "kind", "context", "context_id", "definitional",
         "modulated", "prov_source"),
    ),
    "production_edges": (
        "production",
        ("id", "source", "target", "sign", "kind", "prov_source"),
    ),
    "quantitative_definitions": (
        "quantitative",
        ("id", "kind", "origin", "result", "arguments", "prov_source"),
    ),
    "modulation_edges": (
        "modulation",
        ("id", "modulator", "edge_source", "edge_target", "sign", "kind", "influence_id",
         "can_flip_sign", "interaction_sign", "regime", "prov_source"),
    ),
}


def _json_bytes(value: Any) -> bytes:
    """Stable, reviewable JSON bytes used for every generated web payload."""
    return (json.dumps(value, indent=1, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _gzip_bytes(value: bytes) -> bytes:
    """Deterministic gzip stream (no filename or wall-clock timestamp in the header)."""
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", compresslevel=9, mtime=0, fileobj=output) as stream:
        stream.write(value)
    return output.getvalue()


def _bucket(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[0]


def _record_key(kind: str, identifier: str) -> str:
    return f"{kind}:{identifier}"


def split_web_payload(payload: dict[str, Any], data_subdir: str = "data",
                      bootstrap_name: str = "physiomap.json") -> dict[Path, bytes]:
    """Return the lossless sharded representation consumed by the static viewer.

    The bootstrap contains only rendering/search fields.  Sixteen detail buckets preserve every
    omitted field and sixteen intervention buckets preserve every precomputed overlay.  A fixed
    number of buckets avoids thousands of tiny files while bounding every on-demand request.
    """
    bootstrap = {key: value for key, value in payload.items()
                 if key not in DETAIL_COLLECTIONS and key != "interventions"}
    bootstrap["web_payload_format"] = WEB_PAYLOAD_FORMAT
    bootstrap["payloads"] = {
        "details": f"{data_subdir}/details/{{bucket}}.json",
        "interventions": f"{data_subdir}/interventions/{{bucket}}.json",
    }

    detail_buckets: dict[str, dict[str, Any]] = {
        bucket: {"web_payload_format": WEB_PAYLOAD_FORMAT, "records": {}}
        for bucket in BUCKETS
    }
    for collection, (kind, fields) in DETAIL_COLLECTIONS.items():
        compact_records = []
        for record in payload.get(collection, []):
            identifier = str(record["id"])
            key = _record_key(kind, identifier)
            bucket = _bucket(key)
            compact = {field: record[field] for field in fields if field in record}
            compact["_detail_bucket"] = bucket
            compact_records.append(compact)
            detail_buckets[bucket]["records"][key] = {
                field: value for field, value in record.items() if field not in fields
            }
        bootstrap[collection] = compact_records

    intervention_buckets: dict[str, dict[str, Any]] = {
        bucket: {"web_payload_format": WEB_PAYLOAD_FORMAT, "interventions": {}}
        for bucket in BUCKETS
    }
    intervention_index = []
    for intervention in payload.get("interventions", []):
        identifier = str(intervention["id"])
        bucket = _bucket(_record_key("intervention", identifier))
        index_record = {
            field: intervention[field]
            for field in ("id", "label", "benchmark", "contexts")
            if field in intervention
        }
        index_record["_intervention_bucket"] = bucket
        intervention_index.append(index_record)
        intervention_buckets[bucket]["interventions"][identifier] = {
            field: value for field, value in intervention.items() if field not in index_record
        }
    bootstrap["interventions"] = intervention_index

    objects: dict[Path, Any] = {Path(bootstrap_name): bootstrap}
    objects.update({Path(data_subdir) / "details" / f"{bucket}.json": value
                    for bucket, value in detail_buckets.items()})
    objects.update({Path(data_subdir) / "interventions" / f"{bucket}.json": value
                    for bucket, value in intervention_buckets.items()})
    files: dict[Path, bytes] = {}
    for path, value in objects.items():
        encoded = _json_bytes(value)
        files[path] = encoded
        files[path.with_suffix(path.suffix + ".gz")] = _gzip_bytes(encoded)
    boot_gz = Path(bootstrap_name + ".gz")
    if len(files[boot_gz]) > BOOTSTRAP_GZIP_LIMIT:
        raise RuntimeError(
            "compressed viewer bootstrap exceeds the first-paint budget: "
            f"{len(files[boot_gz])} > {BOOTSTRAP_GZIP_LIMIT} bytes"
        )
    return files


def sync_web_payload(files: dict[Path, bytes], output_dir: Path = WEB, *, check: bool = False) -> None:
    """Write generated shards, or fail when any committed shard is stale/obsolete."""
    expected = set(files)
    managed = {Path("physiomap.json"), Path("physiomap.json.gz")}
    for directory in (output_dir / "data/details", output_dir / "data/interventions"):
        if directory.is_dir():
            managed.update(path.relative_to(output_dir) for path in directory.iterdir()
                           if path.is_file() and path.suffix in {".json", ".gz"})
    stale = sorted(
        path for path in expected | managed
        if path not in files or not (output_dir / path).is_file()
        or (path in files and (output_dir / path).read_bytes() != files[path])
    )
    if check:
        if stale:
            raise RuntimeError("generated web payload is stale: " + ", ".join(map(str, stale)))
        return
    for path in managed - expected:
        (output_dir / path).unlink()
    for path, content in files.items():
        target = output_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def load_exported_web_payload(output_dir: Path = WEB) -> dict[str, Any]:
    """Reconstruct the full logical export from its transport shards (tests/golden baseline)."""
    bootstrap = json.loads((output_dir / "physiomap.json").read_text(encoding="utf-8"))
    payload = {key: value for key, value in bootstrap.items()
               if key not in {"web_payload_format", "payloads"}}
    details: dict[str, dict[str, Any]] = {}
    for collection, (kind, _fields) in DETAIL_COLLECTIONS.items():
        reconstructed = []
        for compact in bootstrap.get(collection, []):
            bucket = compact["_detail_bucket"]
            if bucket not in details:
                details[bucket] = json.loads(
                    (output_dir / "data/details" / f"{bucket}.json").read_text(encoding="utf-8")
                )["records"]
            record = {key: value for key, value in compact.items() if key != "_detail_bucket"}
            record.update(details[bucket][_record_key(kind, str(record["id"]))])
            reconstructed.append(record)
        payload[collection] = reconstructed

    interventions: dict[str, dict[str, Any]] = {}
    reconstructed_interventions = []
    for compact in bootstrap.get("interventions", []):
        bucket = compact["_intervention_bucket"]
        if bucket not in interventions:
            interventions[bucket] = json.loads(
                (output_dir / "data/interventions" / f"{bucket}.json").read_text(encoding="utf-8")
            )["interventions"]
        record = {key: value for key, value in compact.items()
                  if key != "_intervention_bucket"}
        record.update(interventions[bucket][str(record["id"])])
        reconstructed_interventions.append(record)
    payload["interventions"] = reconstructed_interventions
    return payload


# the viewer wraps node labels to ~90px at font-size 9 (see web/app.js node style)
_LABEL_MAX_PX = 90
_CHAR_PX = 5.2          # approx glyph advance at font-size 9
_LINE_PX = 11           # wrapped line height
_PX_PER_INCH = 72.0     # graphviz works in inches; -Tplain emits inches


def _label_footprint_in(label: str) -> tuple[float, float]:
    """Approximate the on-screen footprint (inches) of a node + its wrapped label.

    Returns ``(width_in, height_in)`` padded with margin, so that when graphviz removes overlaps
    on boxes of this size the labels (not just the dots) no longer collide in the viewer.
    """
    import math

    chars = max(len(label or ""), 3)
    text_w = min(_LABEL_MAX_PX, chars * _CHAR_PX)
    lines = max(1, math.ceil(chars * _CHAR_PX / _LABEL_MAX_PX))
    text_h = 14 + lines * _LINE_PX        # the 26px node + wrapped label lines
    # generous margin so adjacent labels keep clear air between them
    return (round((text_w + 40) / _PX_PER_INCH, 3), round((text_h + 26) / _PX_PER_INCH, 3))


def _precompute_positions(pmap: PhysioMap) -> dict[str, dict[str, float]]:
    """Lay out the full graph **once** with graphviz ``sfdp`` so the viewer can use the instant
    ``preset`` layout (no in-browser force-directed pass). Returns ``node id -> {x, y}``.

    The previous viewer ran ``cose`` over about 1,700 nodes on every group toggle
    (approximately O(n²), more than 1 min). By
    shipping stable coordinates, toggling a system just shows/hides nodes at fixed positions —
    instant. Degrades gracefully (empty dict) if ``sfdp`` is unavailable; the viewer then falls
    back to its in-browser layout. Layout is over the undirected causal+constitutive skeleton.

    Each node is declared at its **label-sized footprint** (not a point), and prism overlap removal
    runs with an extra separation margin, so the spread-out coordinates leave room for the wrapped
    labels — fixing the "dense / overlapping labels" look of the earlier point-based layout.
    """
    if not shutil.which("sfdp"):
        print("[export] sfdp not found — skipping precomputed layout (viewer will use fcose)")
        return {}
    g = pmap.causal_subgraph()
    cg = constitutive_graph(pmap)
    node_ids = set(g.nodes()) | set(cg.nodes())
    labels = {n.id: n.label for n in pmap.nodes}
    # -GK lengthens the ideal spring; -Gsep adds margin around each node during overlap removal
    lines = ['graph G {',
             '  graph [overlap="prism", overlap_scaling="4", sep="+18", K="1.2", start="42"];',
             '  node [shape=box, fixedsize=true];']
    for n in sorted(node_ids):
        w, h = _label_footprint_in(labels.get(n, n))
        lines.append(f'"{n}" [width={w}, height={h}];')
    skeleton: set[tuple[str, str]] = set()
    for u, v in list(g.edges()) + list(cg.edges()):
        key = tuple(sorted((u, v)))
        if u != v:
            skeleton.add(key)
    for u, v in sorted(skeleton):
        lines.append(f'"{u}" -- "{v}";')
    lines.append("}")
    try:
        out = subprocess.run(
            ["sfdp", "-Tplain"],
            input="\n".join(lines), capture_output=True, text=True, timeout=240, check=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:  # pragma: no cover
        print(f"[export] sfdp layout failed ({exc}) — viewer will use fcose")
        return {}
    pos: dict[str, dict[str, float]] = {}
    for line in out.stdout.splitlines():
        if not line.startswith("node "):
            continue
        # `node <name> <x> <y> <w> <h> <label> ...` ; name is quoted iff it contained spaces
        rest = line[5:]
        if rest.startswith('"'):
            end = rest.index('"', 1)
            name, coords = rest[1:end], rest[end + 1:].split()
        else:
            parts = rest.split()
            name, coords = parts[0], parts[1:]
        # inches -> px at the same scale the footprints were declared in (1:1 with label sizes)
        pos[name] = {"x": round(float(coords[0]) * _PX_PER_INCH),
                     "y": round(float(coords[1]) * -_PX_PER_INCH)}
    # Graphviz's component packer can move edge-free singleton components by a sub-pixel amount
    # across processes even with a fixed start seed.  Put those few nodes on a deterministic row;
    # their exact location has no graph semantics, but byte-stable generation does.
    connected = {node for edge in skeleton for node in edge}
    isolated = sorted(node_ids - connected)
    if isolated:
        connected_x = [point["x"] for node, point in pos.items() if node in connected]
        connected_y = [point["y"] for node, point in pos.items() if node in connected]
        anchor_x = (max(connected_x) if connected_x else 0) + 180
        anchor_y = min(connected_y) if connected_y else 0
        for index, node in enumerate(isolated):
            pos[node] = {"x": anchor_x, "y": anchor_y + index * 90}
    return pos


INTERVENTION_DIRS = ["guyton", "human", "drug_panel", "human_multiscale"]


# ── Faceted classification: SYSTEM (what it is) × SOURCE (where the evidence came from) ──────────
# A node's source is NOT its system. The viewer filters on both facets independently (scale is the
# third, pre-existing facet). A textbook-extracted thyroid node belongs to `Endocrine` (system) AND
# `Williams` (source). The physiological system is seeded per-fragment for mono-topic fragments and
# then graph-propagated to the remaining (multi-topic / textbook-extracted) nodes from their curated
# neighbours; a node reachable from no seed is honestly "Unassigned".

CV = "Cardiovascular–renal"; EN = "Endocrine"; ME = "Metabolic / hepatic"; MB = "Mineral / bone"
FE = "Fluid / electrolyte"; RA = "Respiratory / acid–base"; HE = "Hematologic"
IM = "Immune / inflammation"; NT = "Neuro / thermal"; UN = "Unassigned"
PHYS_SYSTEMS = [CV, EN, ME, MB, FE, RA, HE, IM, NT, UN]   # display order; Unassigned last

# fragment basename -> confident physiological system (mono-topic fragments only used as BFS seeds)
FRAGMENT_SYSTEM: dict[str, str] = {
    "guyton_cv_core.yaml": CV, "cardiac_function.yaml": CV, "autonomic_baroreflex.yaml": CV,
    "george_heart_rate.yaml": CV,
    "adrenal_cortisol.yaml": EN, "thyroid.yaml": EN, "reproductive_hpg.yaml": EN,
    "growth_hormone_igf1.yaml": EN,
    "glucose_insulin.yaml": ME, "lipid_metabolism.yaml": ME, "energy_balance_appetite.yaml": ME,
    "gi_incretin.yaml": ME, "aminoacid_metabolism.yaml": ME, "purine_urate_metabolism.yaml": ME,
    "intermediary_metabolism.yaml": ME, "bilirubin_liver_function.yaml": ME, "trace_metals.yaml": ME,
    "calcium_pth.yaml": MB, "phosphate_fgf23.yaml": MB,
    "body_fluids_osmolality.yaml": FE, "potassium_homeostasis.yaml": FE,
    "respiratory_acidbase.yaml": RA, "oxygen_transport.yaml": RA,
    "hematology_epo.yaml": HE, "iron_hepcidin.yaml": HE, "coagulation_hemostasis.yaml": HE,
    "inflammation_cytokine.yaml": IM, "thermoregulation.yaml": NT,
    # HPO themed gap-fill (causally-island leaf analytes — placed by their fragment theme)
    "hpo_amino_acids.yaml": ME, "hpo_carbohydrate_metabolites.yaml": ME,
    "hpo_coagulation_factors.yaml": HE, "hpo_csf_markers.yaml": NT,
    "hpo_fatty_acid_oxidation.yaml": ME, "hpo_hematology_indices.yaml": HE,
    "hpo_immunoglobulins_complement.yaml": IM, "hpo_lipids_lipoproteins.yaml": ME,
    "hpo_liver_function_enzymes.yaml": ME, "hpo_lysosomal_enzymes.yaml": ME,
    "hpo_mitochondrial_enzymes.yaml": ME, "hpo_neurotransmitter_metabolites.yaml": NT,
    "hpo_organic_acids.yaml": ME, "hpo_other_endocrine_hormones.yaml": EN,
    "hpo_pulmonary_bloodgas.yaml": RA, "hpo_purine_pyrimidine.yaml": ME,
    "hpo_renal_function_markers.yaml": CV, "hpo_trace_metals.yaml": ME, "hpo_vitamins_cofactors.yaml": ME,
    # molecular / cellular verticals (mapped to their physiological system; the SCALE facet keeps
    # the molecular layer separable independently)
    "vascular_tone.yaml": CV, "beta_adrenergic.yaml": CV, "cardiomyocyte_calcium.yaml": CV,
    "jga_cellcomm.yaml": CV, "endothelium_smc.yaml": CV,
    "epo_jak_stat.yaml": HE, "hepcidin_signaling.yaml": HE, "hepcidin_bmp_smad_axis.yaml": HE,
    "erythroblastic_island.yaml": HE, "hif_epo_oxygen_sensing.yaml": HE,
    "insulin_signaling.yaml": ME, "islet_paracrine.yaml": ME, "gr_gluconeogenesis.yaml": ME,
    "srebp_ldlr_pcsk9_axis.yaml": ME, "leptin_melanocortin_appetite.yaml": ME,
    "bone_remodeling.yaml": MB, "casr_pth_secretion.yaml": MB, "tshr_thyroid_synthesis.yaml": EN,
    "immune_paracrine.yaml": IM,
    # mono-topic textbook (West is respiratory physiology end-to-end)
    "west_extracted.yaml": RA,
}
# weaker per-fragment fallback for multi-topic extraction fragments — applied ONLY to nodes still
# unplaced after propagation (better than Unassigned where the fragment clearly leans one way)
FRAGMENT_SYSTEM_FALLBACK: dict[str, str] = {
    "williams_extracted.yaml": EN, "hall_extracted.yaml": CV,
    "hpo_other_metabolites.yaml": ME, "hpo_plasma_proteins.yaml": ME, "hpo_muscle_enzymes.yaml": ME,
    "signor_metabolism_import.yaml": EN, "aopwiki_import.yaml": EN,
}

# SOURCE / evidence-provenance facet, in display order
SOURCE_ORDER = [
    "Guyton core (curated)", "Curated system fragment", "Curated (G. Gkoutos)",
    "Curated modulation (gains)", "Curated bridges", "Connect-isolated (curated)",
    "Phenotype-connection fan-out", "Molecular/cellular module", "IEM-enzyme connections",
    "West (respiratory textbook)", "Williams (endocrinology)", "Guyton-Hall textbook",
    "Guyton & Hall extraction", "Textbook extraction (A&P/Wong/Biochem)",
    "HPO gap-fill (lab analytes)", "SIGNOR import", "AOP-Wiki import", "Other",
]
# sources hidden by default (draft / large coverage-frontier imports) — the curated core opens first
DEFAULT_HIDDEN_SOURCES = [
    "IEM-enzyme connections", "West (respiratory textbook)", "Williams (endocrinology)",
    "Guyton-Hall textbook", "Guyton & Hall extraction", "Textbook extraction (A&P/Wong/Biochem)",
    "HPO gap-fill (lab analytes)", "SIGNOR import", "AOP-Wiki import",
]


def source_of(rel: str) -> str:
    """The SOURCE/provenance facet of the fragment that first introduced a node."""
    b = Path(rel).name
    if rel == "guyton/guyton_cv_core.yaml":
        return "Guyton core (curated)"
    if b == "george_heart_rate.yaml":
        return "Curated (G. Gkoutos)"
    if b == "modulation_gains.yaml":
        return "Curated modulation (gains)"
    if b == "component_bridges.yaml":
        return "Curated bridges"
    if b == "connect_isolated_v2.yaml":
        return "Connect-isolated (curated)"
    if b == "isolated_connections.yaml":
        return "IEM-enzyme connections"
    if b == "phenotype_connections.yaml":
        return "Phenotype-connection fan-out"
    if b == "guyton_extracted.yaml":
        return "Guyton & Hall extraction"
    if b == "textbook_extracted.yaml":
        return "Textbook extraction (A&P/Wong/Biochem)"
    if b.startswith("hpo_"):
        return "HPO gap-fill (lab analytes)"
    if b == "west_extracted.yaml":
        return "West (respiratory textbook)"
    if b == "williams_extracted.yaml":
        return "Williams (endocrinology)"
    if b == "hall_extracted.yaml":
        return "Guyton-Hall textbook"
    if b == "signor_metabolism_import.yaml":
        return "SIGNOR import"
    if b == "aopwiki_import.yaml":
        return "AOP-Wiki import"
    if rel.startswith("multiscale/"):
        return "Molecular/cellular module"
    if rel.startswith("human/systems/"):
        return "Curated system fragment"
    return "Other"


def assign_systems(pmap: PhysioMap, node_frag: dict[str, str]) -> dict[str, str]:
    """Physiological SYSTEM per node: per-fragment seed → nearest-seed graph propagation →
    per-fragment fallback → Unassigned. Propagation runs over the undirected causal+constitutive
    skeleton, so an extracted node inherits the system of the curated subsystem it wired into.
    """
    import networkx as nx

    g = pmap.causal_subgraph()
    cg = constitutive_graph(pmap)
    ug = nx.Graph()
    ug.add_nodes_from(node_frag)
    for u, v in list(g.edges()) + list(cg.edges()):
        if u != v:
            ug.add_edge(u, v)
    system: dict[str, str] = {n: FRAGMENT_SYSTEM[Path(r).name] for n, r in node_frag.items()
                              if Path(r).name in FRAGMENT_SYSTEM}
    dq = deque(system)
    while dq:                                   # multi-source BFS = nearest-seed label propagation
        u = dq.popleft()
        for v in ug.neighbors(u):
            if v not in system:
                system[v] = system[u]
                dq.append(v)
    for n, r in node_frag.items():              # fallback for still-unplaced multi-topic nodes
        if n not in system and Path(r).name in FRAGMENT_SYSTEM_FALLBACK:
            system[n] = FRAGMENT_SYSTEM_FALLBACK[Path(r).name]
    return {n: system.get(n, UN) for n in node_frag}


def _build_date() -> str:
    """The date the snapshot was generated (UTC, ISO yyyy-mm-dd) — a build stamp for the viewer."""
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def _load_synonyms() -> dict[str, list[str]]:
    """The curated physiology abbreviation/synonym lexicon, shipped to the viewer for search.

    Same source the de-dup reconciler uses (ontology/node_synonyms.yaml): canonical phrase ->
    surface variants/abbreviations. Lets the viewer's search expand "MAP" -> mean arterial
    pressure, "PaO2" -> partial pressure of oxygen, etc.
    """
    p = ROOT / "ontology" / "node_synonyms.yaml"
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("synonyms", {}) or {}


def main(argv: list[str] | None = None) -> int:
    import glob

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if any committed bootstrap/detail/intervention shard is stale")
    parser.add_argument("--data-subdir", default="data",
                        help="subdir for detail/intervention shards (use data/<version> for a snapshot)")
    parser.add_argument("--bootstrap", default="physiomap.json",
                        help="bootstrap filename to write (use physiomap-<version>.json for a snapshot)")
    args = parser.parse_args(argv)

    # compose EVERY fragment (same set as physiomap_core.hpo.build_map): guyton + all human
    # systems + all multiscale verticals, including the gap-fill and textbook-extracted fragments.
    frag_rel = (
        ["guyton/guyton_cv_core.yaml"]
        + [f"human/systems/{Path(p).name}" for p in sorted(glob.glob(str(BENCH / "human/systems/*.yaml")))]
        + [f"human/curated/{Path(p).name}" for p in sorted(glob.glob(str(BENCH / "human/curated/*.yaml")))]
        + [f"multiscale/{Path(p).name}" for p in sorted(glob.glob(str(BENCH / "multiscale/*.yaml")))]
    )
    # node / edge / modulation -> owning fragment (first fragment that introduces it wins). The edge
    # provenance is what lets the viewer show "where a curator (e.g. Gkoutos) added things" even when
    # the edge connects nodes that already existed in an earlier (e.g. Guyton) fragment.
    node_frag: dict[str, str] = {}
    edge_frag: dict[tuple, str] = {}
    production_frag: dict[tuple, str] = {}
    mod_frag: dict[tuple, str] = {}
    for rel in frag_rel:
        data = yaml.safe_load((BENCH / rel).read_text()) or {}
        for nd in data.get("nodes", []) or []:
            node_frag.setdefault(nd["id"], rel)
        for e in data.get("causal_edges", []) or []:
            edge_frag.setdefault((e["source"], e["target"], e.get("sign")), rel)
        for e in data.get("production_edges", []) or []:
            production_frag.setdefault((e["source"], e["target"], e.get("sign")), rel)
        for m in data.get("modulation_edges", []) or []:
            key = m.get("influence_id") or (m.get("edge_source"), m.get("edge_target"))
            mod_frag.setdefault((m["modulator"], key), rel)

    # The viewer is now exported from the approved canonical SCM. YAML is read above only
    # for curator/source attribution metadata and is not the runtime model authority.
    scm_path = canonical_scm_path()
    scm = ScmManifest.from_json(scm_path)
    pmap = scm.to_physiomap()
    migration_report = json.loads(
        (scm_path.parent / "migration-report.json").read_text(encoding="utf-8"))
    trait_migration = {r["node_id"]: r for r in migration_report["traits"]}
    projected_edges = {
        (edge.source, edge.target, edge.sign.value, edge.mechanism or ""): influence
        for edge, influence in zip(pmap.causal_edges, scm.influences, strict=True)
    }
    projected_modulation = {
        (edge.modulator, edge.influence_id): modulation
        for edge, modulation in zip(pmap.modulation_edges, scm.modulation, strict=True)
    }
    projected_production = {
        (edge.source, edge.target, edge.sign.value): relation
        for edge, relation in zip(
            pmap.production_edges, scm.production_relations, strict=True
        )
    }
    traces = {trace.trace_id: trace for trace in scm.projection_traces}

    node_system = assign_systems(pmap, node_frag)
    node_source = {n: source_of(r) for n, r in node_frag.items()}

    def edge_source_label(s: str, t: str, sign: str) -> str:
        rel = edge_frag.get((s, t, sign))
        return source_of(rel) if rel else "Other"

    def mod_source_label(mod: str, influence_id: str | None) -> str:
        rel = mod_frag.get((mod, influence_id))
        return source_of(rel) if rel else "Other"

    def production_source_label(source: str, target: str, sign: str) -> str:
        rel = production_frag.get((source, target, sign))
        return source_of(rel) if rel else "Other"

    sccs = sorted(pmap.sccs(), key=len, reverse=True)
    scc_index = {n: i for i, comp in enumerate(sccs) for n in comp}
    big_scc = set(sccs[0]) if sccs else set()

    positions = _precompute_positions(pmap)
    nodes = [
        {
            "id": n.id,
            "label": n.label,
            "scale": n.scale.value,
            "system": node_system.get(n.id, UN),
            "source": node_source.get(n.id, "Other"),
            "entity_iri": n.entity_iri,
            "quality_iri": n.quality_iri,
            "trait_iri": trait_migration[n.id]["trait_iri"],
            "migration_status": trait_migration[n.id]["migration_status"],
            "verified_terms": trait_migration[n.id]["verified_terms"],
            "asserted_axioms": trait_migration[n.id]["asserted_axioms"],
            "inferred_axioms": trait_migration[n.id]["inferred_parents"],
            "satisfiable": trait_migration[n.id]["satisfiable"],
            "scc": scc_index.get(n.id, -1),
            "in_big_scc": n.id in big_scc,
            **({"x": positions[n.id]["x"], "y": positions[n.id]["y"]} if n.id in positions else {}),
        }
        for n in pmap.nodes
    ]
    # Self-loops (source == target, i.e. explicit self-regulation) live in the YAML and are
    # used by the solver, but are excluded from the *drawn* graph: Cytoscape's edge
    # control-point math crashes on a self-loop, and a node-on-itself arrow adds little to the
    # diagram. The edge id includes the sign so a same-pair/different-sign pair never collides.
    # causal edges that a modulation (gain) edge acts on — flagged so the figure can show, at a
    # glance, which edges carry a multiplicative gain (not just on click).
    modulated_pairs = {(m.edge_source, m.edge_target) for m in pmap.modulation_edges}
    causal = [
        {"id": projected_edges[(e.source, e.target, e.sign.value, e.mechanism or "")].id,
         "source": e.source, "target": e.target, "sign": e.sign.value,
         "mechanism": e.mechanism, "evidence": e.evidence, "kind": "causal",
         "evidence_status": projected_edges[
             (e.source, e.target, e.sign.value, e.mechanism or "")].evidence_status,
         "context": (
             projected_edges[(e.source, e.target, e.sign.value, e.mechanism or "")]
             .context.label
             if projected_edges[(e.source, e.target, e.sign.value, e.mechanism or "")].context
             else None
         ),
         "context_id": (
             projected_edges[(e.source, e.target, e.sign.value, e.mechanism or "")]
             .context.id
             if projected_edges[(e.source, e.target, e.sign.value, e.mechanism or "")].context
             else None
         ),
         "definitional": e.definitional,
         "modulated": (e.source, e.target) in modulated_pairs,
         "prov_source": edge_source_label(e.source, e.target, e.sign.value),
         "projection_pattern": "causal-collection-v2",
         "projection_entailment": traces[
             projected_edges[(e.source, e.target, e.sign.value, e.mechanism or "")].trace_ids[0]
         ].entailment,
         "structural_interpretation": "signed first derivative"}
        for e in pmap.causal_edges
        if e.source != e.target
    ]
    n_self = sum(1 for e in pmap.causal_edges if e.source == e.target)
    constitutive = [
        {"micro": e.micro, "macro": e.macro, "sign": e.sign.value,
         "relation": e.relation, "kind": "constitutive"}
        for e in pmap.constitutive_edges
    ]
    production = [
        {
            "id": projected_production[(edge.source, edge.target, edge.sign.value)].id,
            "source": edge.source,
            "target": edge.target,
            "sign": edge.sign.value,
            "mechanism": edge.mechanism,
            "evidence": edge.evidence,
            "production_evidence": edge.production_evidence.value,
            "evidence_status": projected_production[
                (edge.source, edge.target, edge.sign.value)
            ].evidence_status,
            "kind": "production",
            "prov_source": production_source_label(
                edge.source, edge.target, edge.sign.value
            ),
            "projection_pattern": "production-collection-v2",
            "projection_entailment": traces[
                projected_production[(edge.source, edge.target, edge.sign.value)].trace_ids[0]
            ].entailment,
            "structural_interpretation": "signed process output",
        }
        for edge in pmap.production_edges
    ]
    quantitative = [
        {
            "id": expression.id,
            "kind": expression.kind,
            "origin": expression.origin,
            "result": expression.result,
            "arguments": [argument.model_dump(mode="json") for argument in expression.arguments],
            "mechanism": expression.mechanism,
            "evidence": expression.evidence,
            "prov_source": source_of(node_frag.get(expression.result)),
            "projection_pattern": traces[expression.trace_ids[0]].pattern_id,
            "projection_entailment": traces[expression.trace_ids[0]].entailment,
            "structural_interpretation": "signed derivative of typed quantitative identity",
        }
        for expression in scm.quantitative_expressions
    ]
    # modulation (multiplicative / gain) edges: a node scales the strength of a causal edge.
    # Drawn as a dashed "gain" link from the modulator to the modulated edge's target (it sits
    # alongside that edge's first-order shadow); the popup names the modulated edge.
    def _iota(m):
        i = interaction_sign(pmap, m)
        return i.value if i in (Sign.PLUS, Sign.MINUS) else "?"

    modulation = [
        {"id": projected_modulation[(m.modulator, m.influence_id)].id,
         "modulator": m.modulator, "edge_source": m.edge_source,
         "edge_target": m.edge_target, "sign": m.sign.value,
         "influence_id": projected_modulation[(m.modulator, m.influence_id)].influence_id,
         "projection_pattern": "multiplicative-modulation-v2",
         "can_flip_sign": m.can_flip_sign, "mechanism": m.mechanism,
         "evidence": m.evidence, "kind": "modulation",
         # intrinsic 2nd-order interaction sign (iota = mu . sigma) + sign-flip regime case-analysis
         "interaction_sign": _iota(m),
         "regime": regime_conditional_signs(pmap, m),
         "prov_source": mod_source_label(m.modulator, m.influence_id)}
        for m in pmap.modulation_edges
    ]

    interventions = []
    seen = set()
    for dname in INTERVENTION_DIRS:
        spec = yaml.safe_load((BENCH / dname / "interventions.yaml").read_text())
        for case in spec["interventions"]:
            if case["id"] in seen:
                continue
            seen.add(case["id"])
            do = {k: Sign(v) for k, v in case["do"].items()}
            contexts = case.get("contexts")
            # reuse the knockout machinery so a benchmark intervention's overlay carries the same
            # derived-phenotype + signed-trace payload the dynamic knockout does (shown on the right)
            try:
                ko = knockout_multi(
                    pmap, {k: v.value for k, v in do.items()}, contexts=contexts
                )
                trace_targets = ([h.node for h in ko.phenotypes[:MAX_TRACE_PHENOTYPES]]
                                 + [h.node for h in ko.affected[:MAX_TRACE_PHENOTYPES]])
                traces = trace_many_multi(pmap, do, trace_targets, contexts=contexts)
            except ValueError as exc:
                # A curated edge can place a constitutive vertical inside a feedback loop, which the
                # multiscale solver rejects (constitution is assumed acyclic). Skip that overlay
                # rather than fail the whole export; the graph itself is unaffected.
                print(f"  [skip overlay] {case['id']}: {exc}", flush=True)
                continue
            interventions.append({
                "id": case["id"],
                "label": case.get("label", case["id"]),
                "benchmark": dname,
                "contexts": ko.contexts,
                "do": {k: v.value for k, v in do.items()},
                "do_labels": ko.do_labels,
                "predicted": ko.predicted,
                "phenotypes": [h.model_dump() for h in ko.phenotypes],
                "affected": [h.model_dump() for h in ko.affected],
                "gain_changes": [g.model_dump() for g in ko.gain_changes],
                "synergies": [s.model_dump() for s in ko.synergies],
                "traces": traces,
            })

    present_systems = set(node_system.values())
    present_sources = set(node_source.values())
    out = {
        "version": scm.physiomap_version,
        "data_version": scm.physiomap_version,
        "software_version": PHYSIOMAP_VERSION,
        "generated": _build_date(),
        "data_revision": hashlib.sha256(scm_path.read_bytes()).hexdigest()[:12],
        "ontology": scm.ontology_provenance,
        "projection_version": scm.projection_version,
        "nodes": nodes,
        "causal_edges": causal,
        "production_edges": production,
        "constitutive_edges": constitutive,
        "quantitative_definitions": quantitative,
        "modulation_edges": modulation,
        "interventions": interventions,
        # two orthogonal node facets the viewer filters on independently (scale is the third)
        "systems": [s for s in PHYS_SYSTEMS if s in present_systems],
        "sources": [s for s in SOURCE_ORDER if s in present_sources]
                   + sorted(present_sources - set(SOURCE_ORDER)),
        "default_hidden_sources": [s for s in DEFAULT_HIDDEN_SOURCES if s in present_sources],
        "synonyms": _load_synonyms(),
        "scales": ["molecular", "subcellular", "cellular", "tissue", "organ",
                   "organ_system", "organism"],
        "stats": {
            "n_nodes": len(nodes),
            "n_causal": len(causal),
            "n_production": len(production),
            "n_constitutive": len(constitutive),
            "n_quantitative": len(quantitative),
            "n_modulation": len(modulation),
            "n_sccs": len(sccs),
            "big_scc_size": len(big_scc),
        },
    }
    snapshot = args.data_subdir != "data" or args.bootstrap != "physiomap.json"
    files = split_web_payload(out, data_subdir=args.data_subdir, bootstrap_name=args.bootstrap)
    if snapshot:
        for path, content in files.items():
            target = WEB / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    else:
        sync_web_payload(files, check=args.check)
    n_unassigned = sum(1 for v in node_system.values() if v == UN)
    verb = "verified" if args.check else "wrote"
    bootstrap_size = len(files[Path(args.bootstrap + ".gz")])
    print(f"{verb} sharded web payload: {len(nodes)} nodes, {len(causal)} drawn causal edges "
          f"({n_self} self-loops excluded from drawing), {len(production)} production, "
          f"{len(constitutive)} constitutive, {len(quantitative)} quantitative, "
          f"{len(modulation)} modulation, {len(interventions)} interventions, "
          f"{bootstrap_size} byte compressed bootstrap, "
          f"big SCC = {len(big_scc)}; {len(present_systems)} systems / {len(present_sources)} sources "
          f"({n_unassigned} nodes Unassigned to a system)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
