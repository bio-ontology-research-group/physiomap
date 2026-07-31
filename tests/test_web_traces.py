from pathlib import Path

import networkx as nx

from physiomap_core.hpo import build_map, load_disorders
from web.export_traces import (
    DISORDERS,
    OUT,
    check_site,
    index_page,
    largest_scc_size,
    render_site,
    reverse_term_map,
    write_site,
)


class _GraphMap:
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def causal_subgraph(self) -> nx.DiGraph:
        return self.graph


def test_trace_explanation_uses_computed_largest_scc_size():
    graph = nx.DiGraph([(f"n{i}", f"n{(i + 1) % 7}") for i in range(7)])
    graph.add_edge("isolated", "leaf")

    size = largest_scc_size(_GraphMap(graph))
    rendered = index_page([], size)

    assert size == 7
    assert "has exactly 7 nodes" in rendered
    assert "~74-node" not in rendered


def test_trace_freshness_detects_changed_missing_and_obsolete_files(tmp_path: Path):
    expected = {
        Path("index.html"): "current index",
        Path("condition/index.html"): "current condition",
    }
    write_site(expected, tmp_path)
    assert check_site(expected, tmp_path) == []

    (tmp_path / "index.html").write_text("stale", encoding="utf-8")
    (tmp_path / "condition/index.html").unlink()
    (tmp_path / "obsolete.html").write_text("obsolete", encoding="utf-8")

    assert check_site(expected, tmp_path) == [
        Path("condition/index.html"),
        Path("index.html"),
        Path("obsolete.html"),
    ]


def test_committed_trace_pages_match_canonical_model():
    pmap = build_map()
    rendered = render_site(pmap, load_disorders(DISORDERS), reverse_term_map())

    assert largest_scc_size(pmap) == 213
    assert check_site(rendered, OUT) == []
