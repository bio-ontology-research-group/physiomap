#!/usr/bin/env python3
"""PhysioMap knockout service — a tiny stdlib HTTP API for *dynamic* synthetic knockouts.

The web viewer is static (nginx). This process loads the canonical released SCM through the
compatibility adapter **once** and then
answers ``POST /knockout {node, sign}`` in ~0.1 s by running the comparative-statics solver live
(:func:`physiomap_core.knockout.knockout`) — so the viewer can knock out *any* node on demand and
overlay the derived phenotypes, instead of a fixed list of precomputed interventions.

No third-party deps (stdlib ``http.server`` only) so it runs as a one-line systemd unit. nginx
reverse-proxies ``/physiomap/api/`` to this port; the handler matches on the path *suffix*, so it
works whether or not nginx strips the ``/physiomap/api`` prefix.

Run:  ``python -m web.api [--host 127.0.0.1] [--port 8081]``
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from physiomap_core.curation import (
    Submission,
    SubmissionStore,
    contribution_to_fragment,
    axiom_preview,
    make_submission_id,
    ontology_lookup,
    validate_contribution,
)
from physiomap_core.hpo import build_map
from physiomap_core.knockout import knockout_multi, trace_many_multi
from physiomap_core.model import Sign

# composed once at startup, shared (read-only) across worker threads
PMAP = None
NODE_LABELS: dict[str, str] = {}
STORE: SubmissionStore | None = None

MAX_TRACE_PHENOTYPES = 14   # attach signed traces for at most this many derived phenotypes
MAX_BODY = 1_000_000        # 1 MB cap on request bodies

# Curation auth (fail-closed): a capability is DISABLED unless its token env var is set.
#   PHYSIOMAP_EDIT_TOKEN  — required to submit a contribution (curators: George, Paul, …)
#   PHYSIOMAP_ADMIN_TOKEN — required to deep-validate / approve / export a fragment (maintainer)
EDIT_TOKEN = os.environ.get("PHYSIOMAP_EDIT_TOKEN", "").strip()
ADMIN_TOKEN = os.environ.get("PHYSIOMAP_ADMIN_TOKEN", "").strip()
CURATION_DIR = os.environ.get("PHYSIOMAP_CURATION_DIR", "curation/submissions")


def _load() -> None:
    global PMAP, NODE_LABELS, STORE
    t0 = time.time()
    PMAP = build_map()
    NODE_LABELS = {n.id: n.label for n in PMAP.nodes}
    STORE = SubmissionStore(CURATION_DIR)
    print(f"[physiomap-api] canonical SCM: {len(PMAP.nodes)} nodes in {time.time() - t0:.1f}s",
          flush=True)
    print(f"[physiomap-api] curation store: {CURATION_DIR}  "
          f"edit-token={'set' if EDIT_TOKEN else 'UNSET (submissions disabled)'}  "
          f"admin-token={'set' if ADMIN_TOKEN else 'UNSET (review disabled)'}", flush=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _knockout_payload(
    do: dict[str, str],
    with_traces: bool = True,
    contexts: list[str] | None = None,
) -> dict:
    r = knockout_multi(PMAP, do, contexts=contexts)
    out = r.model_dump()
    if r.error or not with_traces:
        return out
    # attach a short signed trace to each determinate phenotype and affected trait (the UI uses it
    # to explain the sign / show how the trait is reached)
    targets = ([h.node for h in r.phenotypes[:MAX_TRACE_PHENOTYPES]]
               + [h.node for h in r.affected[:MAX_TRACE_PHENOTYPES]])
    out["traces"] = trace_many_multi(PMAP, do, targets, contexts=contexts)
    return out


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter logging
        print(f"[physiomap-api] {self.address_string()} {fmt % args}", flush=True)

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # CORS preflight
        self._send(204, {})

    def _query(self) -> dict[str, str]:
        from urllib.parse import parse_qs, urlsplit
        return {k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()}

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > MAX_BODY:
            raise ValueError(f"request body too large ({length} > {MAX_BODY})")
        return json.loads(self.rfile.read(length) or b"{}")

    def _authed(self, expected: str) -> bool:
        """True iff the request carries the expected token (and the token is configured)."""
        if not expected:
            return False  # capability disabled (fail-closed)
        sent = (self.headers.get("X-Edit-Token") or "").strip()
        return sent == expected

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path.endswith("/health"):
            self._send(200, {"ok": True, "nodes": len(PMAP.nodes) if PMAP else 0,
                             "curation": {"submit_enabled": bool(EDIT_TOKEN),
                                          "review_enabled": bool(ADMIN_TOKEN)}})
        elif path.endswith("/nodes"):
            self._send(200, {"nodes": [{"id": i, "label": l} for i, l in NODE_LABELS.items()]})
        elif path.endswith("/influences"):
            self._send(200, {"influences": [
                {
                    "id": edge.id,
                    "source": edge.source,
                    "target": edge.target,
                    "sign": edge.sign.value,
                    "context_id": edge.context.id if edge.context else None,
                    "context": edge.context.label if edge.context else None,
                }
                for edge in (PMAP.causal_edges if PMAP else [])
            ]})
        elif path.endswith("/contexts"):
            self._send(200, {"contexts": [
                context.model_dump(mode="json") for context in (PMAP.contexts if PMAP else [])
            ]})
        elif path.endswith("/ontology/lookup"):
            self._send(200, {"terms": ontology_lookup(self._query().get("q", ""))})
        elif path.endswith("/curate/submissions"):
            self._send(200, {"submissions": [
                {"id": s.id, "curator": s.curator, "created": s.created, "status": s.status,
                 "title": s.title, "ok": bool(s.report and s.report.ok),
                 "counts": (s.report.counts if s.report else {})} for s in STORE.list()]})
        elif path.endswith("/curate/submission"):
            try:
                self._send(200, {"submission": STORE.load(self._query()["id"]).model_dump(
                    mode="json", exclude_none=True)})
            except (KeyError, FileNotFoundError):
                self._send(404, {"error": "no such submission"})
        elif path.endswith("/curate/fragment"):
            if not self._authed(ADMIN_TOKEN):
                self._send(403, {"error": "admin token required"})
                return
            try:
                self._send(200, {"fragment": contribution_to_fragment(STORE.load(self._query()["id"]))})
            except (KeyError, FileNotFoundError):
                self._send(404, {"error": "no such submission"})
        else:
            self._send(404, {"error": f"no such endpoint: {path}"})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        try:
            if path.endswith("/knockout"):
                return self._knockout()
            if path.endswith("/curate/validate"):
                return self._curate_validate()
            if path.endswith("/curate/preview"):
                req = self._body()
                return self._send(200, {"axioms": axiom_preview(req.get("contribution") or {})})
            if path.endswith("/curate/submit"):
                return self._curate_submit()
            if path.endswith("/curate/deep-validate"):
                return self._curate_deep()
            if path.endswith("/curate/review"):
                return self._curate_review()
            self._send(404, {"error": f"no such endpoint: {path}"})
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        except json.JSONDecodeError as exc:
            self._send(400, {"error": f"bad JSON: {exc}"})
        except Exception as exc:  # noqa: BLE001 - surface errors to the client
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

    # --- knockout ----------------------------------------------------------
    def _knockout(self):
        """Clamp one or several nodes and return the derived phenotypes.

        Accepts either the legacy single-node form ``{"node": ..., "sign": "+|-"}`` or a
        multi-node form ``{"targets": [{"node": ..., "sign": "+|-"}, ...]}`` (equivalently a
        ``{"do": {node: "+|-"}}`` map). All clamps are imposed in one comparative-statics solve.
        """
        req = self._body()
        do: dict[str, str] = {}
        if isinstance(req.get("do"), dict):
            do = {str(k): str(v) for k, v in req["do"].items()}
        elif isinstance(req.get("targets"), list):
            for t in req["targets"]:
                if isinstance(t, dict) and t.get("node"):
                    do[str(t["node"])] = str(t.get("sign", "+"))
        elif req.get("node"):
            do[str(req["node"])] = str(req.get("sign", "+"))
        if not do:
            return self._send(400, {"error": "missing 'node' or 'targets'"})
        bad = {n: s for n, s in do.items() if s not in ("+", "-")}
        if bad:
            return self._send(400, {"error": f"each sign must be '+' or '-'; got {bad}"})
        t0 = time.time()
        raw_contexts = req.get("contexts")
        if raw_contexts is not None and not isinstance(raw_contexts, list):
            raise ValueError("'contexts' must be a list of context IDs")
        contexts = [str(value) for value in raw_contexts] if raw_contexts is not None else None
        payload = _knockout_payload(
            do, bool(req.get("traces", True)), contexts=contexts
        )
        payload["solve_ms"] = round((time.time() - t0) * 1000)
        self._send(404 if payload.get("error") else 200, payload)

    # --- curation ----------------------------------------------------------
    def _curate_validate(self):
        req = self._body()
        deep = bool(req.get("deep")) and self._authed(ADMIN_TOKEN)  # deep gated (expensive)
        report = validate_contribution(PMAP, req.get("contribution") or {}, deep=deep)
        self._send(200, {"report": report.model_dump(mode="json"),
                         "deep_ran": deep, "deep_requires_admin": bool(req.get("deep")) and not deep})

    def _curate_submit(self):
        if not self._authed(EDIT_TOKEN):
            return self._send(403, {"error": "valid edit token required to submit"})
        req = self._body()
        curator = (req.get("curator") or "").strip()
        contribution = req.get("contribution") or {}
        if not curator:
            return self._send(400, {"error": "missing 'curator' (your name, for provenance)"})
        report = validate_contribution(PMAP, contribution)
        if not report.ok:
            return self._send(422, {"error": "contribution failed validation; fix before submitting",
                                    "report": report.model_dump(mode="json")})
        created = _now()
        title = (req.get("title") or "").strip()
        sub = Submission(id=make_submission_id(curator, created, title), curator=curator,
                         created=created, title=title, note=req.get("note"),
                         contribution=contribution, report=report, status="pending")
        STORE.save(sub)
        self._send(200, {"id": sub.id, "status": sub.status, "report": report.model_dump(mode="json")})

    def _curate_deep(self):
        if not self._authed(ADMIN_TOKEN):
            return self._send(403, {"error": "admin token required for deep validation"})
        sub = STORE.load(self._body()["id"])
        report = validate_contribution(PMAP, sub.contribution, deep=True)
        STORE.update(sub.id, report=report, status=("validated" if report.ok else "pending"))
        self._send(200, {"id": sub.id, "report": report.model_dump(mode="json")})

    def _curate_review(self):
        if not self._authed(ADMIN_TOKEN):
            return self._send(403, {"error": "admin token required to review"})
        req = self._body()
        status = req.get("status")
        if status not in ("approved", "rejected", "validated", "pending", "merged"):
            return self._send(400, {"error": "bad status"})
        sub = STORE.update(req["id"], status=status, review_note=req.get("review_note"))
        self._send(200, {"id": sub.id, "status": sub.status})


def main() -> int:
    ap = argparse.ArgumentParser(description="PhysioMap dynamic-knockout HTTP service")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8081)
    args = ap.parse_args()
    _load()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"[physiomap-api] listening on http://{args.host}:{args.port}  "
          f"(POST /knockout, /curate/*, GET /health, /nodes, /curate/submissions)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[physiomap-api] shutting down", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
