#!/usr/bin/env python3
"""Slice a pdftotext -layout dump into per-chapter files via chapter-OPENING pages.

More robust than running headers: a chapter starts on a page bearing an opening anchor
(e.g. Williams/Elsevier "CHAPTER OUTLINE"; West full-caps "CHAPTER N TITLE"). We find every
opening page, read its chapter number (first small integer near the page top) and title, then
slice [start_page, next_start_page) for each chapter.

Usage:  uv run python scripts/slice_chapters.py <full.txt> <out_dir> <slug> <anchor>
  anchor = 'outline'  -> opening page contains 'CHAPTER OUTLINE'; chapter no. = first int in head
         = 'caps'     -> opening line matches '^CHAPTER <n> <TITLE>' (full caps, West/Hall TOC-less)
Writes <out_dir>/<slug>_chNN.txt and <out_dir>/<slug>_manifest.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CAPS = re.compile(r"^\s*CHAPTER\s+(\d{1,3})\s+([A-Z][A-Z0-9 ,’'\-/&]{3,})\s*$", re.M)
LEADNUM = re.compile(r"^\s*(\d{1,3})\b")
TITLE_AFTER_NUM = re.compile(r"^\s*\d{1,3}\s*\|?\s*(.+)$")


def _title_from_head(page: str) -> str | None:
    # First non-empty content line(s) after the leading chapter number (Williams layout:
    # "7 | Neuroendocrinology | AUTHOR ...").  Take text up to the author (ALL-CAPS name).
    head = [l.strip() for l in page.splitlines()[:8] if l.strip()]
    if not head:
        return None
    parts = " ".join(head[:3])
    m = TITLE_AFTER_NUM.match(parts)
    cand = (m.group(1) if m else parts).strip(" |")
    # cut at first ALL-CAPS author token run (e.g. 'RONALD M. LECHAN')
    cand = re.split(r"\s+[A-Z]\.?\s*[A-Z]{2,}", cand)[0]
    cand = re.split(r"\bCHAPTER OUTLINE\b", cand)[0]
    cand = re.sub(r"\s+", " ", cand).strip(" |,-")
    return cand or None


def find_openings_outline(pages: list[str]) -> list[tuple[int, int, str]]:
    out = []
    for i, pg in enumerate(pages):
        if "CHAPTER OUTLINE" not in pg:
            continue
        head = "\n".join(pg.splitlines()[:8])
        m = LEADNUM.search(head)
        if not m:
            continue
        n = int(m.group(1))
        if not (1 <= n <= 120):
            continue
        out.append((n, i, _title_from_head(pg) or f"chapter {n}"))
    return out


def find_openings_caps(pages: list[str]) -> list[tuple[int, int, str]]:
    out = []
    for i, pg in enumerate(pages):
        m = CAPS.search(pg)
        if m:
            out.append((int(m.group(1)), i, m.group(2).title().strip()))
    return out


def main(full_txt: str, out_dir: str, slug: str, anchor: str) -> int:
    pages = Path(full_txt).read_text(encoding="utf-8", errors="ignore").split("\f")
    openings = (find_openings_outline if anchor == "outline" else find_openings_caps)(pages)

    # keep the FIRST opening per chapter number, in page order
    seen: dict[int, tuple[int, int, str]] = {}
    for n, i, t in openings:
        if n not in seen:
            seen[n] = (n, i, t)
    ordered = sorted(seen.values(), key=lambda x: x[1])

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for idx, (n, start, title) in enumerate(ordered):
        end = ordered[idx + 1][1] if idx + 1 < len(ordered) else len(pages)
        body = "\f".join(pages[start:end])
        fn = out / f"{slug}_ch{n:02d}.txt"
        fn.write_text(body, encoding="utf-8")
        manifest.append({"chapter": n, "title": title, "file": str(fn),
                         "start_pdf_page": start + 1, "pages": end - start, "chars": len(body)})
    (out / f"{slug}_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"{slug}: {len(manifest)} chapters")
    for m in manifest:
        print(f"  ch{m['chapter']:>2}  p{m['start_pdf_page']:>4}  {m['pages']:>3}pp  {m['chars']:>7}c  {m['title'][:58]}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(*sys.argv[1:]))
