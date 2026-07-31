#!/usr/bin/env python3
"""Import the returned stratified expert-review workbook.

The importer preserves the reviewer cells verbatim, verifies that the 83-item
review inventory was not changed, and derives one explicit three-way status:

* TRUE   -> accepted
* FALSE? -> flagged for further review or investigation
* FALSE  -> rejected

It writes machine-readable records, aggregate counts, and the LaTeX fragments
used by the manuscript. The attached prose analysis is not an input.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "docs/physiomap_expert_gold_review_2026-07-28.xlsx"
RETURNED = ROOT / "docs/physiomap_expert_gold_review_returned_2026-07-30.xlsx"
SAMPLING_FRAME = (
    ROOT / "benchmarks/data/physiomap-scm-expert-review-2026-07-28.json.gz"
)
SAMPLE_JSON = ROOT / "benchmarks/results/expert_gold_sample.json"
SAMPLE_TSV = ROOT / "benchmarks/results/expert_gold_sample.tsv"
OUTPUT_JSON = ROOT / "benchmarks/results/expert_gold_review.json"
OUTPUT_TSV = ROOT / "benchmarks/results/expert_gold_review.tsv"
OUTPUT_SUMMARY = ROOT / "benchmarks/results/expert_gold_review_summary.json"
OUTPUT_MACROS = ROOT / "docs/generated/expert-gold-review-macros.tex"
OUTPUT_TABLE = ROOT / "docs/generated/expert-gold-review-by-type.tex"

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
CORE_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
CELL_REF = re.compile(r"^([A-Z]+)([0-9]+)$")

HEADERS = [
    "review_id",
    "relation_type",
    "stratum",
    "source",
    "target",
    "sign",
    "evidence_class",
    "mechanism",
    "evidence",
    "expert_verdict",
    "expert_comment",
]
IDENTITY_HEADERS = HEADERS[:9]
RELATION_TYPES = [
    ("causal", "Causal influence"),
    ("production", "Production"),
    ("constitution", "Constitution"),
    ("quantitative", "Quantitative identity"),
    ("modulation", "Modulation"),
]
VERDICT_STATUS = {
    "TRUE": "accepted",
    "FALSE?": "flagged",
    "FALSE": "rejected",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def decompressed_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with gzip.open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def column_index(reference: str) -> int:
    match = CELL_REF.match(reference)
    if not match:
        raise ValueError(f"invalid spreadsheet cell reference: {reference}")
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - ord("A") + 1
    return value - 1


def shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def parse_cell(cell: ElementTree.Element, strings: list[str]) -> Any:
    cell_type = cell.get("t")
    value = cell.find(f"{{{MAIN_NS}}}v")
    if cell_type == "inlineStr":
        inline = cell.find(f"{{{MAIN_NS}}}is")
        if inline is None:
            return ""
        return "".join(node.text or "" for node in inline.iter(f"{{{MAIN_NS}}}t"))
    if value is None or value.text is None:
        return None
    if cell_type == "s":
        return strings[int(value.text)]
    if cell_type == "b":
        return "TRUE" if value.text == "1" else "FALSE"
    if cell_type in {"str", "e"}:
        return value.text
    try:
        number = float(value.text)
    except ValueError:
        return value.text
    return int(number) if number.is_integer() else number


def read_sheet(path: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        strings = shared_strings(archive)
        root = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    rows: list[list[Any]] = []
    for row in root.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row"):
        values: list[Any] = [None] * len(HEADERS)
        for cell in row.findall(f"{{{MAIN_NS}}}c"):
            index = column_index(cell.attrib["r"])
            if index >= len(HEADERS):
                raise ValueError(f"unexpected review-sheet column: {cell.attrib['r']}")
            values[index] = parse_cell(cell, strings)
        rows.append(values)
    if not rows or rows[0] != HEADERS:
        raise ValueError(f"unexpected review-sheet headers: {rows[0] if rows else None}")
    return [dict(zip(HEADERS, row, strict=True)) for row in rows[1:]]


def workbook_properties(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("docProps/core.xml"))

    def text(namespace: str, name: str) -> str | None:
        node = root.find(f"{{{namespace}}}{name}")
        return None if node is None else node.text

    return {
        "creator": text(DC_NS, "creator"),
        "last_modified_by": text(CORE_NS, "lastModifiedBy"),
        "created": text(DCTERMS_NS, "created"),
        "modified": text(DCTERMS_NS, "modified"),
    }


def normalized_status(raw_verdict: Any) -> str:
    value = str(raw_verdict or "").strip().upper()
    if value not in VERDICT_STATUS:
        raise ValueError(f"unrecognized expert verdict: {raw_verdict!r}")
    return VERDICT_STATUS[value]


def comparable_cell(value: Any) -> Any:
    """Treat the two spreadsheet representations of an empty cell alike."""
    return "" if value is None else value


def count_rows(records: list[dict[str, Any]]) -> dict[str, Any]:
    def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
        counts = Counter(row["review_status"] for row in rows)
        return {
            "accepted": counts["accepted"],
            "flagged": counts["flagged"],
            "rejected": counts["rejected"],
            "reviewed": len(rows),
        }

    return {
        "overall": status_counts(records),
        "by_relation_type": {
            relation_type: status_counts(
                [row for row in records if row["relation_type"] == relation_type]
            )
            for relation_type, _ in RELATION_TYPES
        },
        "comments": sum(bool(str(row["expert_comment"] or "").strip()) for row in records),
    }


def import_review() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    template_rows = read_sheet(TEMPLATE)
    returned_rows = read_sheet(RETURNED)
    sampled_rows = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    if len(template_rows) != 83 or len(returned_rows) != 83:
        raise ValueError(
            f"expected 83 rows, found {len(template_rows)} template and "
            f"{len(returned_rows)} returned rows"
        )
    if len(sampled_rows) != 83:
        raise ValueError(f"expected 83 sampled rows, found {len(sampled_rows)}")

    records: list[dict[str, Any]] = []
    for index, (sampled, before, after) in enumerate(
        zip(sampled_rows, template_rows, returned_rows, strict=True), start=2
    ):
        for header in IDENTITY_HEADERS:
            if comparable_cell(sampled.get(header)) != comparable_cell(
                before.get(header)
            ):
                raise ValueError(
                    f"sent template differs from sampled JSON at row {index}, "
                    f"column {header}"
                )
            if comparable_cell(before.get(header)) != comparable_cell(
                after.get(header)
            ):
                raise ValueError(
                    f"returned workbook altered review identity at row {index}, "
                    f"column {header}"
                )
        if before["expert_verdict"] not in {None, ""}:
            raise ValueError(f"sent template already had a verdict at row {index}")
        if before["expert_comment"] not in {None, ""}:
            raise ValueError(f"sent template already had a comment at row {index}")

        record = {header: after.get(header) for header in HEADERS}
        record["review_status"] = normalized_status(after["expert_verdict"])
        records.append(record)

    identifiers = [row["review_id"] for row in records]
    if len(set(identifiers)) != 83:
        raise ValueError("review identifiers are not unique")

    counts = count_rows(records)
    payload = {
        "schema_version": "1.0.0",
        "review": {
            "description": "Stratified expert review of released PhysioMap content",
            "reviewer": "Paul N. Schofield",
            "sample_sent_on": "2026-07-28",
            "review_returned_on": "2026-07-30",
            "sampling_seed": 20260728,
            "email_message_id": "290B9FDD-7683-4E05-A9F0-32AB06C3A10A@cam.ac.uk",
        },
        "normalization": {
            "TRUE": "accepted",
            "FALSE?": "flagged for further review or investigation",
            "FALSE": "rejected",
        },
        "sampling_frame": {
            "path": SAMPLING_FRAME.relative_to(ROOT).as_posix(),
            "archive_sha256": sha256(SAMPLING_FRAME),
            "content_sha256": decompressed_sha256(SAMPLING_FRAME),
        },
        "sample": {
            "json_path": SAMPLE_JSON.relative_to(ROOT).as_posix(),
            "json_sha256": sha256(SAMPLE_JSON),
            "tsv_path": SAMPLE_TSV.relative_to(ROOT).as_posix(),
            "tsv_sha256": sha256(SAMPLE_TSV),
        },
        "template": {
            "path": TEMPLATE.relative_to(ROOT).as_posix(),
            "sha256": sha256(TEMPLATE),
            **workbook_properties(TEMPLATE),
        },
        "returned_workbook": {
            "path": RETURNED.relative_to(ROOT).as_posix(),
            "sha256": sha256(RETURNED),
            **workbook_properties(RETURNED),
        },
        "integrity": {
            "items": len(records),
            "identity_columns_unchanged": True,
            "completed_verdicts": sum(
                bool(str(row["expert_verdict"] or "").strip()) for row in records
            ),
            "comments": counts["comments"],
        },
        "counts": counts,
        "records": records,
    }
    return payload, records


def json_text(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def tsv_text(records: list[dict[str, Any]]) -> str:
    from io import StringIO

    def one_line(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        return (
            value.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\n", r"\n")
            .rstrip()
        )

    handle = StringIO()
    writer = csv.DictWriter(
        handle,
        fieldnames=HEADERS + ["review_status"],
        delimiter="\t",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(
        {key: one_line(value) for key, value in record.items()}
        for record in records
    )
    return handle.getvalue()


def macro_name(relation_type: str) -> str:
    return {
        "causal": "Causal",
        "production": "Production",
        "constitution": "Constitution",
        "quantitative": "Quantitative",
        "modulation": "Modulation",
    }[relation_type]


def macros_text(counts: dict[str, Any]) -> str:
    overall = counts["overall"]
    lines = [
        "% Generated by scripts/import_expert_gold_review.py; do not edit.",
        rf"\newcommand{{\PMExpertReviewItems}}{{{overall['reviewed']}}}",
        rf"\newcommand{{\PMExpertReviewAccepted}}{{{overall['accepted']}}}",
        rf"\newcommand{{\PMExpertReviewFlagged}}{{{overall['flagged']}}}",
        rf"\newcommand{{\PMExpertReviewRejected}}{{{overall['rejected']}}}",
        rf"\newcommand{{\PMExpertReviewComments}}{{{counts['comments']}}}",
    ]
    for relation_type, _ in RELATION_TYPES:
        name = macro_name(relation_type)
        row = counts["by_relation_type"][relation_type]
        for status in ("accepted", "flagged", "rejected", "reviewed"):
            suffix = status.capitalize()
            lines.append(
                rf"\newcommand{{\PMExpertReview{name}{suffix}}}"
                rf"{{{row[status]}}}"
            )
    return "\n".join(lines) + "\n"


def table_text(counts: dict[str, Any]) -> str:
    lines = [
        "% Generated by scripts/import_expert_gold_review.py; do not edit.",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"relation type & accepted & flagged & rejected & reviewed\\",
        r"\midrule",
    ]
    for relation_type, label in RELATION_TYPES:
        row = counts["by_relation_type"][relation_type]
        lines.append(
            f"{label} & {row['accepted']} & {row['flagged']} & "
            f"{row['rejected']} & {row['reviewed']} \\\\"
        )
    overall = counts["overall"]
    lines.extend(
        [
            r"\midrule",
            f"Total & {overall['accepted']} & {overall['flagged']} & "
            f"{overall['rejected']} & {overall['reviewed']} \\\\",
            r"\bottomrule",
            r"\end{tabular}",
        ]
    )
    return "\n".join(lines) + "\n"


def write_or_check(path: Path, content: str, check: bool) -> None:
    if check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise SystemExit(f"stale or missing expert-review artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if any versioned derived artifact is stale",
    )
    args = parser.parse_args()

    payload, records = import_review()
    summary = {
        "schema_version": payload["schema_version"],
        "review": payload["review"],
        "normalization": payload["normalization"],
        "sampling_frame": payload["sampling_frame"],
        "sample": payload["sample"],
        "template": payload["template"],
        "returned_workbook": payload["returned_workbook"],
        "integrity": payload["integrity"],
        "counts": payload["counts"],
    }
    write_or_check(OUTPUT_JSON, json_text(payload), args.check)
    write_or_check(OUTPUT_TSV, tsv_text(records), args.check)
    write_or_check(OUTPUT_SUMMARY, json_text(summary), args.check)
    write_or_check(OUTPUT_MACROS, macros_text(payload["counts"]), args.check)
    write_or_check(OUTPUT_TABLE, table_text(payload["counts"]), args.check)

    mode = "Verified" if args.check else "Imported"
    overall = payload["counts"]["overall"]
    print(
        f"{mode} {overall['reviewed']} expert-review rows: "
        f"{overall['accepted']} accepted, {overall['flagged']} flagged, "
        f"{overall['rejected']} rejected"
    )
    print(f"returned workbook sha256={payload['returned_workbook']['sha256']}")


if __name__ == "__main__":
    main()
