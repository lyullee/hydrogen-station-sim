"""Audit whether the HIAD holdout is actually ready for human evaluation.

The coordinator pre-screen is deliberately advisory.  This report makes the
remaining gates explicit and never infers approval from populated case data or
from an empty review field.  It is intended to stop a manuscript pipeline from
silently treating a prepared casebook as an evaluated one.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_COORDINATOR_FIELDS = (
    "coordinator_leakage_decision",
    "rewrite_required_yes_no",
    "coordinator_notes",
)


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid: {exc}"
    if not isinstance(value, dict):
        return None, "invalid: top-level value is not an object"
    return value, None


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _case_status(casebook: dict[str, Any] | None) -> dict[str, Any]:
    cases = (casebook or {}).get("cases")
    if not isinstance(cases, list):
        return {
            "case_count": 0,
            "unique_event_ids": False,
            "all_leakage_reviews_pending": False,
            "all_vignettes_unapproved": False,
            "casebook_frozen": False,
        }
    ids = [str(case.get("event_id", "")) for case in cases if isinstance(case, dict)]
    return {
        "case_count": len(cases),
        "unique_event_ids": len(ids) == len(cases) and len(ids) == len(set(ids)) and all(ids),
        "all_leakage_reviews_pending": bool(cases) and all(
            str(case.get("narrative_action_leakage_review", "")).upper() == "PENDING"
            for case in cases
            if isinstance(case, dict)
        ),
        "all_vignettes_unapproved": bool(cases) and all(
            str(case.get("expert_vignette_approved", "")).upper() == "NO"
            for case in cases
            if isinstance(case, dict)
        ),
        "casebook_frozen": False,
    }


def _coordinator_status(path: Path, expected_count: int) -> dict[str, Any]:
    if not path.is_file():
        return {
            "file_present": False,
            "row_count": 0,
            "required_columns_present": False,
            "all_required_decisions_populated": False,
            "review_complete": False,
        }
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error) as exc:
        return {
            "file_present": True,
            "row_count": 0,
            "required_columns_present": False,
            "all_required_decisions_populated": False,
            "review_complete": False,
            "error": str(exc),
        }
    fields = set(rows[0]) if rows else set()
    required_present = set(REQUIRED_COORDINATOR_FIELDS).issubset(fields)
    populated = required_present and len(rows) == expected_count and all(
        all(str(row.get(field, "")).strip() for field in REQUIRED_COORDINATOR_FIELDS)
        for row in rows
    )
    return {
        "file_present": True,
        "row_count": len(rows),
        "required_columns_present": required_present,
        "all_required_decisions_populated": populated,
        "review_complete": bool(populated),
    }


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    casebook_path = root / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json"
    prescreen_path = root / "data/public_validation/results/hiad_coordinator_prescreen/prescreen_manifest.json"
    coordinator_path = root / "data/public_validation/results/hiad_coordinator_prescreen/coordinator_review.csv"
    protocol_path = root / "research/hiad_study_protocol_manifest.json"
    freeze_path = root / "data/public_validation/results/hiad_casebook_frozen/casebook_freeze_manifest.json"
    collection_path = root / "data/public_validation/results/hiad_decision/collection_manifest.json"
    analysis_path = root / "data/public_validation/results/hiad_decision/analysis/expert_review_analysis.json"

    casebook, casebook_error = _read_json(casebook_path)
    prescreen, prescreen_error = _read_json(prescreen_path)
    protocol, protocol_error = _read_json(protocol_path)
    freeze, freeze_error = _read_json(freeze_path)
    collection, collection_error = _read_json(collection_path)
    analysis, analysis_error = _read_json(analysis_path)

    cases = _case_status(casebook)
    cases["casebook_frozen"] = bool(
        freeze
        and freeze.get("case_count") == cases["case_count"]
        and freeze.get("all_frozen_cases_retained") is True
        and freeze.get("all_cases_approved") is True
    )
    coordinator = _coordinator_status(coordinator_path, cases["case_count"])
    prescreen_advisory = bool(
        prescreen
        and prescreen.get("advisory_only") is True
        and prescreen.get("human_review_required_for_every_case") is True
        and prescreen.get("case_count") == cases["case_count"]
    )
    ethics_ready = bool(
        protocol
        and protocol.get("ethics_status") in {"approved", "exempt", "not-required"}
        and protocol.get("ethics_determination_id")
        and protocol.get("reviewer_recruitment_permitted") is True
        and protocol.get("holdout_response_collection_permitted") is True
    )
    collection_ready = bool(
        collection
        and collection.get("response_count") == collection.get("expected_response_count") == 168
        and collection.get("failed_calls_retained_for_blinded_scoring") is True
    )
    review_ready = bool(
        analysis
        and analysis.get("event_count") == 24
        and analysis.get("rater_count") == 3
    )

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_id": (protocol or {}).get("protocol_id"),
        "readiness": {
            "casebook_frozen": cases["casebook_frozen"],
            "ethics_and_collection_permitted": ethics_ready,
            "coordinator_review_complete": coordinator["review_complete"],
            "ready_for_holdout_collection": bool(cases["casebook_frozen"] and ethics_ready),
            "ready_for_independent_review": bool(collection_ready),
            "independent_review_complete": review_ready,
        },
        "casebook": {
            "path": str(casebook_path.relative_to(root)),
            "sha256": _sha256(casebook_path),
            "error": casebook_error,
            **cases,
        },
        "coordinator_prescreen": {
            "manifest_path": str(prescreen_path.relative_to(root)),
            "manifest_sha256": _sha256(prescreen_path),
            "manifest_error": prescreen_error,
            "advisory_only_and_human_review_required": prescreen_advisory,
            "review_csv_path": str(coordinator_path.relative_to(root)),
            "review_csv_sha256": _sha256(coordinator_path),
            **coordinator,
        },
        "protocol": {
            "path": str(protocol_path.relative_to(root)),
            "sha256": _sha256(protocol_path),
            "error": protocol_error,
            "ethics_status": (protocol or {}).get("ethics_status"),
            "ethics_determination_id": (protocol or {}).get("ethics_determination_id"),
            "reviewer_recruitment_permitted": (protocol or {}).get("reviewer_recruitment_permitted"),
            "holdout_response_collection_permitted": (protocol or {}).get("holdout_response_collection_permitted"),
            "unresolved_institution_fields": (protocol or {}).get("unresolved_institution_fields"),
        },
        "downstream_artifacts": {
            "casebook_freeze": {"path": str(freeze_path.relative_to(root)), "present": freeze is not None, "error": freeze_error},
            "collection": {"path": str(collection_path.relative_to(root)), "present": collection is not None, "error": collection_error, "ready": collection_ready},
            "expert_review_analysis": {"path": str(analysis_path.relative_to(root)), "present": analysis is not None, "error": analysis_error, "complete": review_ready},
        },
        "claim_boundary": [
            "The coordinator pre-screen is advisory and does not approve, rewrite, or freeze any case.",
            "No holdout response or expert rating evidence is present until the collection and independent review artifacts pass their own locked checks.",
            "This report does not authorize recruitment, response collection, or publication claims.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = audit(args.root)
    output = args.output or args.root / "research/hiad_evaluation_readiness.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
