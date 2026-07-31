#!/usr/bin/env python3
"""Materialize checksum-pinned HPO inputs required by the release evaluations."""

from __future__ import annotations

import gzip
import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_DIR = ROOT / "benchmarks/data/hpo-2026-02-16"
CACHE_DIR = ROOT / "ontology/.obo_cache"


@dataclass(frozen=True)
class FrozenInput:
    archive: str
    archive_sha256: str
    output: str
    output_sha256: str


FROZEN_INPUTS = (
    FrozenInput(
        archive="hp.obo.gz",
        archive_sha256="a5b6a4a6988d1cf38202a830e667f215a7bdbd723e6232d7a40e6124ae0169b4",
        output="hp.obo",
        output_sha256="8d6c23798667d4506767ce643fc3c028f0d1c85e7e1d8810e491181a345d53cd",
    ),
    FrozenInput(
        archive="genes_to_phenotype.txt.gz",
        archive_sha256="843a4c74ad782433f1089d42d6b5f92ed901b5875b3eab4e8ed0d7bfe20a3d24",
        output="genes_to_phenotype.txt",
        output_sha256="25d3e5a40203cbb4cc027747c70fcb5431bcfb26283479608a97f3d810285c7d",
    ),
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def materialize(cache_dir: Path = CACHE_DIR) -> list[Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for frozen in FROZEN_INPUTS:
        archive = ARCHIVE_DIR / frozen.archive
        if not archive.is_file():
            raise SystemExit(f"missing frozen release input: {archive.relative_to(ROOT)}")
        if file_sha256(archive) != frozen.archive_sha256:
            raise SystemExit(f"frozen release input checksum mismatch: {frozen.archive}")

        output = cache_dir / frozen.output
        if output.is_file():
            if file_sha256(output) != frozen.output_sha256:
                raise SystemExit(f"cached release input checksum mismatch: {output}")
            outputs.append(output)
            continue

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=cache_dir, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                with gzip.open(archive, "rb") as source:
                    shutil.copyfileobj(source, temporary)
            if file_sha256(temporary_path) != frozen.output_sha256:
                raise SystemExit(f"expanded release input checksum mismatch: {frozen.output}")
            temporary_path.replace(output)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        outputs.append(output)
    return outputs


def main() -> int:
    outputs = materialize()
    names = ", ".join(path.name for path in outputs)
    print(f"frozen HPO release inputs: current ({names})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
