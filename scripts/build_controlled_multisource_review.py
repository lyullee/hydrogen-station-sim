"""Write a *private* workbook mapping-review record outside the repository.

Unlike the public-safe schema inventory, this custodian utility retains source
paths, worksheet names, and header labels in its output so an authorised
reviewer can construct a semantic mapping.  It never reads measurement rows.
The output is intentionally rejected inside the Git worktree and must never be
committed, published, or attached to a manuscript.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

from audit_controlled_data_schema import (
    FULL_LOOP_REQUIRED,
    HEADER_SEARCH_MAX_ROWS,
    _classify_header,
    _outside_repository,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _workbooks(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if root.is_file() and root.suffix.casefold() in {".xlsx", ".xlsm"}:
            yield root
        elif root.is_dir():
            yield from (
                path for path in root.rglob("*")
                if path.is_file() and path.suffix.casefold() in {".xlsx", ".xlsm"}
            )


def _best_header(worksheet) -> tuple[int, tuple[str, ...], frozenset[str]] | None:
    selected: tuple[tuple[int, int, int], int, tuple[str, ...], frozenset[str]] | None = None
    for row_number, row in enumerate(
        worksheet.iter_rows(min_row=1, max_row=HEADER_SEARCH_MAX_ROWS, values_only=True), start=1,
    ):
        labels = tuple(str(value or "").strip() for value in row)
        coverage = _classify_header(labels)
        textual = sum(bool(label) and not label.replace(".", "", 1).isdigit() for label in labels)
        score = (len(coverage), textual, -row_number)
        if selected is None or score > selected[0]:
            selected = (score, row_number, labels, coverage)
    if selected is None:
        return None
    _, row_number, labels, coverage = selected
    return row_number, labels, coverage


def build_review(input_roots: Iterable[Path]) -> dict[str, object]:
    """Return private worksheet details for co-located semantic candidates."""

    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("openpyxl is required for controlled workbook review") from exc
    candidates: list[dict[str, object]] = []
    unreadable = 0
    for path in _workbooks(input_roots):
        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
        except Exception:
            unreadable += 1
            continue
        try:
            sources = []
            union: set[str] = set()
            for worksheet in workbook.worksheets:
                selected = _best_header(worksheet)
                if selected is None:
                    continue
                header_row, labels, coverage = selected
                if not coverage:
                    continue
                sources.append({
                    "worksheet": worksheet.title,
                    "header_row": header_row,
                    "header": list(labels),
                    "semantic_channels": sorted(coverage),
                })
                union.update(coverage)
            if len(sources) > 1 and FULL_LOOP_REQUIRED.issubset(union):
                candidates.append({
                    "source_path": str(path.resolve()),
                    "source_sha256": _sha256(path),
                    "source_format": path.suffix.casefold().lstrip("."),
                    "review_status": "requires_custodian_mapping_and_synchronization_attestation",
                    "candidate_type": "co_located_semantic_channels_only",
                    "semantic_union": sorted(union),
                    "sources": sources,
                })
        finally:
            workbook.close()
    return {
        "schema_version": 1,
        "artifact_type": "controlled_private_multisource_mapping_review",
        "publication_prohibited": True,
        "repository_storage_prohibited": True,
        "measurement_rows_read": False,
        "candidate_count": len(candidates),
        "unreadable_workbook_count": unreadable,
        "candidates": candidates,
        "claim_boundary": (
            "Co-located labels only. A custodian must attest same-event selection, "
            "units, state meanings, and time synchronization before export."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = [_outside_repository(path, label="input root") for path in args.input_root]
    if not all(path.exists() for path in inputs):
        parser.error("every input root must exist")
    output = _outside_repository(args.output, label="output")
    output.parent.mkdir(parents=True, exist_ok=True)
    review = build_review(inputs)
    output.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Deliberately do not disclose source names, worksheet names, or headers.
    print(json.dumps({
        "candidate_count": review["candidate_count"],
        "unreadable_workbook_count": review["unreadable_workbook_count"],
        "output_written": True,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
