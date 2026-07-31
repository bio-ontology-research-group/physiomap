#!/usr/bin/env python3
"""Headless-browser smoke test for the generated website and editor."""

from __future__ import annotations

import http.server
import json
import subprocess
import threading
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=ROOT / "web")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        command = ["chromium", "--headless", "--no-sandbox", "--disable-gpu",
                   "--virtual-time-budget=15000", "--dump-dom"]
        viewer = subprocess.run([*command, f"{base}/index.html"], check=True,
                                text=True, capture_output=True, timeout=45).stdout
        payload = json.loads((ROOT / "web" / "physiomap.json").read_text(encoding="utf-8"))
        stats = payload["stats"]
        required = [
            f"{stats['n_nodes']} nodes",
            f"{stats['n_causal']} causal edges",
            f"{stats['n_production']} production",
            f"{stats['n_constitutive']} constitutive",
            f"{stats['n_quantitative']} quantitative",
            f"{stats['n_modulation']} modulation",
            f"whole-body SCC = {stats['big_scc_size']}",
            f"the largest {stats['big_scc_size']}-node homeostatic feedback core",
            f"search-total\">{stats['n_nodes']}",
        ]
        missing = [value for value in required if value not in viewer]
        if missing:
            raise RuntimeError(f"viewer render is missing expected content: {missing}")
        lazy = subprocess.run(
            [*command, f"{base}/index.html?smoke=lazy-payloads"], check=True,
            text=True, capture_output=True, timeout=45,
        ).stdout
        lazy_required = [
            'data-lazy-payload-smoke="ready"',
            'data-lazy-detail-smoke="ready"',
            'data-ontology-search-smoke="ready"',
            "context: fed-state-hepatic-lipogenesis",
        ]
        missing = [value for value in lazy_required if value not in lazy]
        if missing:
            raise RuntimeError(f"lazy web payload render is missing expected content: {missing}")
        editor = subprocess.run([*command, f"{base}/editor.html"], check=True,
                                text=True, capture_output=True, timeout=45).stdout
        for value in ("OWL axiom preview", "local ontology lookup", "Ratio"):
            if value not in editor:
                raise RuntimeError(f"editor render is missing {value!r}")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
    print("headless website and editor rendering: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
