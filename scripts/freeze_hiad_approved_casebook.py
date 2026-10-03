"""Validate and cryptographically freeze a coordinator-approved HIAD casebook."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from prepare_hiad_coordinator_review import REFERENCE_FIELDS, _clean, _screen


CONTEXT_FIELDS = (
    "title",
    "description",
    "initiating_system",
    "physical_effect",
    "consequence_nature",
    "sub_application",
    "supply_chain_stage",
    "operational_condition",
)
IMMUTABLE_CASE_FIELDS = ("event_id", "quality", "stratum", "references", *REFERENCE_FIELDS)
IMMUTABLE_TOP_FIELDS = (
    "source", "split", "development_count", "holdout_count",
)
CONFIRMATION = "response/lesson leakage removed without adding facts"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _case_map(casebook: dict, label: str) -> tuple[list[str], dict[str, dict]]:
    cases = casebook.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SystemExit(f"{label} casebook must contain a non-empty cases list")
    ids = [str(case.get("event_id", "")) for case in cases]
    if "" in ids or len(ids) != len(set(ids)):
        raise SystemExit(f"{label} casebook event IDs must be non-empty and unique")
    return ids, {str(case["event_id"]): case for case in cases}


def _same_text(first: object, second: object) -> bool:
    return _clean(first) == _clean(second)


def _validate(source: dict, approved: dict) -> list[dict[str, object]]:
    source_ids, source_by_id = _case_map(source, "Source")
    approved_ids, approved_by_id = _case_map(approved, "Approved")
    if approved_ids != source_ids:
        raise SystemExit(
            "Approved casebook must retain every frozen event in original order; "
            f"source={source_ids}, approved={approved_ids}"
        )
    for field in IMMUTABLE_TOP_FIELDS:
        if approved.get(field) != source.get(field):
            raise SystemExit(f"Approved casebook changed immutable top-level field: {field}")

    metadata = approved.get("coordinator_review_metadata") or {}
    coordinator_code = str(metadata.get("coordinator_code") or "").strip()
    if not coordinator_code:
        raise SystemExit("Approved casebook has no coded coordinator identity")
    if metadata.get("all_frozen_cases_retained") is not True:
        raise SystemExit("Coordinator export did not confirm retention of all frozen cases")

    changes = []
    for event_id in source_ids:
        original = source_by_id[event_id]
        candidate = approved_by_id[event_id]
        for field in IMMUTABLE_CASE_FIELDS:
            if candidate.get(field) != original.get(field):
                raise SystemExit(
                    f"Event {event_id} changed immutable case/reference field: {field}"
                )
        original_context = original.get("input_context") or {}
        candidate_context = candidate.get("input_context") or {}
        missing = [field for field in CONTEXT_FIELDS if field not in candidate_context]
        if missing:
            raise SystemExit(
                f"Event {event_id} is missing model-input fields: {', '.join(missing)}"
            )
        for field in CONTEXT_FIELDS[2:]:
            if candidate_context.get(field) != original_context.get(field):
                raise SystemExit(
                    f"Event {event_id} changed non-editable model field: {field}"
                )
        review = candidate.get("coordinator_review") or {}
        decision = str(review.get("decision") or "").upper()
        if decision not in {"KEEP", "REWRITE"}:
            raise SystemExit(f"Event {event_id} has no valid KEEP/REWRITE decision")
        if str(review.get("coordinator_code") or "").strip() != coordinator_code:
            raise SystemExit(f"Event {event_id} coordinator code is inconsistent")
        if review.get("confirmation") != CONFIRMATION:
            raise SystemExit(f"Event {event_id} lacks the required review confirmation")
        if str(candidate.get("narrative_action_leakage_review") or "").upper() != "PASS":
            raise SystemExit(f"Event {event_id} leakage review is not PASS")
        if str(candidate.get("expert_vignette_approved") or "").upper() != "YES":
            raise SystemExit(f"Event {event_id} vignette approval is not YES")

        title_changed = not _same_text(
            candidate_context["title"], original_context.get("title")
        )
        description_changed = not _same_text(
            candidate_context["description"], original_context.get("description")
        )
        changed = title_changed or description_changed
        if decision == "KEEP" and changed:
            raise SystemExit(f"Event {event_id} is marked KEEP but model text changed")
        if decision == "REWRITE" and not changed:
            raise SystemExit(f"Event {event_id} is marked REWRITE but model text is unchanged")

        residual_case = dict(candidate)
        residual = _screen(residual_case, min_overlap_tokens=4)
        notes = str(review.get("notes") or "").strip()
        if residual["advisory_tier"] != "LOW" and not notes:
            raise SystemExit(
                f"Event {event_id} retains {residual['advisory_tier']} advisory flags; "
                "coordinator rationale is required"
            )
        changes.append({
            "event_id": event_id,
            "decision": decision,
            "title_changed": title_changed,
            "description_changed": description_changed,
            "original_title": _clean(original_context.get("title")),
            "approved_title": _clean(candidate_context.get("title")),
            "original_description": _clean(original_context.get("description")),
            "approved_description": _clean(candidate_context.get("description")),
            "residual_advisory_tier": residual["advisory_tier"],
            "residual_exact_overlap_phrases": " || ".join(
                residual["exact_overlap_phrases"]
            ),
            "residual_action_sentences": " || ".join(
                residual["possible_completed_action_sentences"]
            ),
            "coordinator_notes": notes,
        })
    return changes


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    approved = json.loads(args.approved.read_text(encoding="utf-8"))
    changes = _validate(source, approved)

    args.output.mkdir(parents=True, exist_ok=True)
    frozen = dict(approved)
    frozen["freeze_metadata"] = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_casebook_sha256": _sha256(args.source),
        "submitted_approved_casebook_sha256": _sha256(args.approved),
        "source_commit": _git_commit(),
        "case_count": len(changes),
    }
    frozen_path = args.output / "approved_casebook_frozen.json"
    frozen_path.write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    change_path = args.output / "casebook_change_log.csv"
    _write_csv(change_path, changes)
    decisions = {
        decision: sum(row["decision"] == decision for row in changes)
        for decision in ("KEEP", "REWRITE")
    }
    residual_tiers = {
        tier: sum(row["residual_advisory_tier"] == tier for row in changes)
        for tier in ("HIGH", "MEDIUM", "LOW")
    }
    manifest = {
        "schema_version": 1,
        "frozen_at_utc": frozen["freeze_metadata"]["frozen_at_utc"],
        "source_commit": frozen["freeze_metadata"]["source_commit"],
        "case_count": len(changes),
        "all_frozen_cases_retained": True,
        "all_cases_approved": True,
        "decision_counts": decisions,
        "residual_advisory_tier_counts": residual_tiers,
        "file_sha256": {
            "source_casebook": _sha256(args.source),
            "submitted_approved_casebook": _sha256(args.approved),
            frozen_path.name: _sha256(frozen_path),
            change_path.name: _sha256(change_path),
        },
    }
    manifest_path = args.output / "casebook_freeze_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
