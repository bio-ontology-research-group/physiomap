# Deploying the PhysioMap knockout API (dynamic synthetic knockouts)

The viewer at `bio2vec.net/physiomap/` is **static** (nginx). The *dynamic knockout* feature needs a
small always-on Python service that loads the canonical released SCM once and answers `POST /knockout` live
(`web/api.py`, stdlib only — no FastAPI/Flask). nginx reverse-proxies `/physiomap/api/` to it.

Without the service the site still works fully; the knockout panel just shows "service unreachable".

The static location must also enable precompressed payloads using
`web/deploy/nginx-physiomap-location.conf`. The generated graph is losslessly split into a sub-200 kB
compressed bootstrap plus lazy detail/intervention buckets; serving the `.gz` siblings is part of the
deployment contract and is covered by the release gate.

## One-time server setup (on the Hetzner box, as root)

1. **Get the code** on the server (the service needs `physiomap_core/`, `web/`, `benchmarks/`):
   ```bash
   git clone <repo> /opt/physiomap          # or rsync the repo to /opt/physiomap
   cd /opt/physiomap
   python3 -m venv .venv
   .venv/bin/pip install pydantic pyyaml networkx numpy
   ```
   (If you skip the venv, edit the `ExecStart` in the unit to use `/usr/bin/python3`.)

2. **Install & start the service:**
   ```bash
   cp web/deploy/physiomap-api.service /etc/systemd/system/
   systemctl daemon-reload
   systemctl enable --now physiomap-api
   systemctl status physiomap-api          # expect: canonical SCM: 1695 nodes
   curl -s http://127.0.0.1:8081/health    # {"ok": true, "nodes": 1557}
   ```

3. **Wire nginx** (add the proxy to the existing bio2vec.net server block):
   ```bash
   cp web/deploy/nginx-physiomap-api.conf /etc/nginx/snippets/physiomap-api.conf
   # inside the bio2vec.net `server { }` add:  include snippets/physiomap-api.conf;
   nginx -t && systemctl reload nginx
   curl -s https://bio2vec.net/physiomap/api/health   # {"ok": true, ...}
   ```

## Curation editor (optional — enables `editor.html`)

The editor validates contributions with no auth (read-only), but **submitting** and **reviewing**
require tokens. Fail-closed: without the tokens the editor still validates but nothing can be written.

1. **Tokens + writable store** (the unit already sets `PHYSIOMAP_CURATION_DIR=/var/lib/physiomap/curation`
   and `StateDirectory=physiomap`, and reads `/etc/physiomap-api.env`):
   ```bash
   cp web/deploy/physiomap-api.env.example /etc/physiomap-api.env
   # edit it: set PHYSIOMAP_EDIT_TOKEN (give to curators) and PHYSIOMAP_ADMIN_TOKEN (maintainer)
   #   openssl rand -hex 24   # to generate each
   chmod 600 /etc/physiomap-api.env
   systemctl daemon-reload && systemctl restart physiomap-api
   curl -s http://127.0.0.1:8081/health   # -> "curation":{"submit_enabled":true,"review_enabled":true}
   ```
   The server also needs `ontology/partof.yaml` + `ontology/verified_ids.yaml` under `/opt/physiomap`
   (rsync the `ontology/` dir, excluding the big `.obo_cache/`).

2. **Merge workflow** (a contribution never reaches the live map automatically):
   curator submits in the editor → stored under `/var/lib/physiomap/curation` (status *pending*) →
   maintainer reviews, runs **deep-validate** (soundness regression), **approves**, and downloads the
   **fragment** → on the workstation run the full pre-deploy suite and commit:
   ```bash
   python scripts/curation_merge.py <downloaded>.yaml --place   # runs all gates, copies into benchmarks/human/curated/
   python -m pytest -q && python web/export_data.py             # tests + regenerate viewer data
   git add benchmarks/human/curated web/physiomap.json && git commit
   # then redeploy (below) and restart the service
   ```

## Updating after a map/code change

```bash
cd /opt/physiomap && git pull        # or rsync the changed files
systemctl restart physiomap-api      # reloads the canonical SCM
```
The static viewer assets (`web/*.js,*.css,*.html`, `physiomap.json*`, `data/`, and `traces/`) deploy as
described in `web/README.md`. Preserve archived `physiomap-*.json` files in `/var/www/physiomap/`.

## Smoke test

```bash
curl -s -X POST https://bio2vec.net/physiomap/api/knockout \
  -H 'Content-Type: application/json' -d '{"node":"hepcidin","sign":"+"}' | python3 -m json.tool
```
Expect `transferrin_saturation → -`, `plasma_iron → -`, `total_iron_binding_capacity → +`.

## Notes

- The service binds `127.0.0.1:8081` only; nginx is the public edge.
- A single solve is ~0.1 s; with phenotype traces ~0.3–0.7 s. `ThreadingHTTPServer` handles
  concurrent requests; the canonical SCM adapter is read-only and shared across threads.
- CORS is open (`Access-Control-Allow-Origin: *`) so the page also works when served from another
  origin during development (`?api=http://127.0.0.1:8081`).
