#!/usr/bin/env python3
"""Cut a PhysioMap release: bump the version, promote the changelog, commit, and git-tag.

Single source of truth for the version lives in two files kept in lock-step
(`tests/test_version.py` asserts they agree):

  * ``pyproject.toml``            -> ``version = "X.Y.Z"``
  * ``physiomap_core/__init__.py`` -> ``__version__ = "X.Y.Z"``

This script:
  1. reads the current version,
  2. computes the next version (``--bump {major,minor,patch}`` or explicit ``--set X.Y.Z``),
  3. rewrites both files,
  4. promotes the ``## [Unreleased]`` section of ``CHANGELOG.md`` to ``## [X.Y.Z] - <date>``
     (a fresh empty ``[Unreleased]`` is left on top),
  5. unless ``--no-git``: ``git add`` the three files, commit ``Release vX.Y.Z``, and create
     an annotated tag ``vX.Y.Z`` whose message is the new release's changelog body.

The date is required (``--date YYYY-MM-DD``) because this environment has no wall clock;
pass today's date explicitly. Run ``--check`` to only verify version consistency.

Usage:
  python scripts/release.py --check
  python scripts/release.py --bump minor --date 2026-06-04
  python scripts/release.py --set 1.0.0 --date 2026-06-04 --no-git
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
INIT = ROOT / "physiomap_core" / "__init__.py"
CHANGELOG = ROOT / "CHANGELOG.md"

_PY_RE = re.compile(r'^(version\s*=\s*")(\d+\.\d+\.\d+)(")', re.M)
_INIT_RE = re.compile(r'^(__version__\s*=\s*")(\d+\.\d+\.\d+)(")', re.M)
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def read_versions() -> dict[str, str]:
    py = _PY_RE.search(PYPROJECT.read_text())
    ini = _INIT_RE.search(INIT.read_text())
    if not py or not ini:
        raise SystemExit("could not find version in pyproject.toml / __init__.py")
    return {"pyproject.toml": py.group(2), "physiomap_core/__init__.py": ini.group(2)}


def current_version() -> str:
    vs = read_versions()
    if len(set(vs.values())) != 1:
        raise SystemExit(f"version mismatch across files: {vs}")
    return next(iter(vs.values()))


def bump(version: str, part: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit(f"unknown bump part {part!r}")


def write_version(new: str) -> None:
    PYPROJECT.write_text(_PY_RE.sub(rf"\g<1>{new}\g<3>", PYPROJECT.read_text(), count=1))
    INIT.write_text(_INIT_RE.sub(rf"\g<1>{new}\g<3>", INIT.read_text(), count=1))


def promote_changelog(new: str, date: str) -> str:
    """Move `## [Unreleased]` body under `## [new] - date`; return the promoted body."""
    text = CHANGELOG.read_text()
    m = re.search(r"^## \[Unreleased\]\s*\n(.*?)(?=^## \[|\Z)", text, re.S | re.M)
    if not m:
        raise SystemExit("CHANGELOG.md has no '## [Unreleased]' section")
    body = m.group(1).strip("\n")
    replacement = (
        "## [Unreleased]\n\n"
        f"## [{new}] — {date}\n\n" + (body + "\n\n" if body else "")
    )
    CHANGELOG.write_text(text[: m.start()] + replacement + text[m.end():])
    return body or "(no changelog entries)"


def git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only verify version consistency")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--bump", choices=["major", "minor", "patch"])
    g.add_argument("--set", dest="set_to", metavar="X.Y.Z")
    ap.add_argument("--date", help="release date YYYY-MM-DD (required unless --check)")
    ap.add_argument("--no-git", action="store_true", help="edit files but do not commit/tag")
    args = ap.parse_args(argv)

    cur = current_version()
    if args.check:
        print(f"version OK: {cur}")
        return 0

    if args.set_to:
        if not _SEMVER.match(args.set_to):
            raise SystemExit(f"--set must be X.Y.Z, got {args.set_to!r}")
        new = args.set_to
    elif args.bump:
        new = bump(cur, args.bump)
    else:
        raise SystemExit("specify --bump {major,minor,patch} or --set X.Y.Z (or --check)")
    if not args.date:
        raise SystemExit("--date YYYY-MM-DD is required (no wall clock in this environment)")

    write_version(new)
    body = promote_changelog(new, args.date)
    print(f"{cur} -> {new}  ({args.date})")

    if args.no_git:
        print("(--no-git: files edited, not committed)")
        return 0
    git("add", "pyproject.toml", "physiomap_core/__init__.py", "CHANGELOG.md")
    git("commit", "-m", f"Release v{new}")
    git("tag", "-a", f"v{new}", "-m", f"PhysioMap v{new} ({args.date})\n\n{body}")
    print(f"committed + tagged v{new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
