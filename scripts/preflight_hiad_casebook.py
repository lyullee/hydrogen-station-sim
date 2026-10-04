"""Run machine-only integrity checks on the HIAD approval casebook.

This preflight deliberately does not decide whether a vignette is free of
hindsight leakage and does not approve, freeze, or authorize collection.  It
only catches malformed or incomplete files before a qualified coordinator and
the institution perform the human gates.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_CONTEXT_FIELDS = (
    "title",
    "description",
    "physical_effect",
    "consequence_nature",
    "sub_application",
    "supply_chain_stage",
    "operational_condition",
)
REQUIRED_CASE_FIELDS = (
    "event_id",
    "quality",
    "stratum",
    "input_context",
    "references",
    "narrative_action_leakage_review",
    "expert_vignette_approved",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check(check_id: str, passed: bool, observed: Any, requirement: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "PASS" if passed else "FAIL",
        "observed": observed,
        "requirement": requirement,
    }


def preflight(casebook: dict[str, Any]) -> dict[str, Any]:
    cases = casebook.get("cases")
    cases = cases if isinstance(cases, list) else []
    ids = [str(item.get("event_id", "")).strip() for item in cases if isinstance(item, dict)]

    required_case_fields_ok = bool(cases) and all(
        isinstance(item, dict) and all(field in item for field in REQUIRED_CASE_FIELDS)
        for item in cases
    )
    context_fields_ok = bool(cases) and all(
        isinstance(item, dict)
        and isinstance(item.get("input_context"), dict)
        and all(str(item["input_context"].get(field, "")).strip() for field in REQUIRED_CONTEXT_FIELDS)
        for item in cases
    )
    references_ok = bool(cases) and all(
        isinstance(item, dict)
        and isinstance(item.get("references"), list)
        and all(str(reference).strip() for reference in item["references"])
        for item in cases
    )
    pending_fields_ok = bool(cases) and all(
        str(item.get("narrative_action_leakage_review", "")).upper() == "PENDING"
        and str(item.get("expert_vignette_approved", "")).upper() == "NO"
        for item in cases
        if isinstance(item, dict)
    )

    checks = [
        _check(
            "holdout_split_declared",
            casebook.get("split") == "holdout",
            casebook.get("split"),
            "The approval input must explicitly declare the holdout split.",
        ),
        _check(
            "declared_count_matches_cases",
            casebook.get("holdout_count") == len(cases) and len(cases) == 24,
            {"declared": casebook.get("holdout_count"), "actual": len(cases)},
            "The prepared HIAD holdout must contain exactly 24 cases.",
        ),
        _check(
            "event_ids_unique_and_nonempty",
            len(ids) == len(cases) and len(ids) == len(set(ids)) and all(ids),
            {"count": len(ids), "unique": len(set(ids)), "empty_ids": sum(not value for value in ids)},
            "Every case must have one non-empty unique event identifier.",
        ),
        _check(
            "required_case_fields_present",
            required_case_fields_ok,
            {"required": list(REQUIRED_CASE_FIELDS), "case_count": len(cases)},
            "Every case must retain the fields needed for later human review.",
        ),
        _check(
            "required_context_fields_nonempty",
            context_fields_ok,
            {"required": list(REQUIRED_CONTEXT_FIELDS)},
            "Every case must contain a non-empty incident context for coordinator review.",
        ),
        _check(
            "references_present",
            references_ok,
            {"case_count": len(cases)},
            "Every case must retain at least one provenance/reference entry.",
        ),
        _check(
            "human_gates_remain_unresolved",
            pending_fields_ok,
            {"leakage_review": "PENDING", "expert_vignette_approved": "NO"},
            "Machine preflight must never silently approve or freeze a vignette.",
        ),
    ]
    return {
        "schema_version": 1,
        "kind": "machine_preflight_only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "machine_preflight_pass": all(item["status"] == "PASS" for item in checks),
        "case_count": len(cases),
        "checks": checks,
        "claim_boundary": [
            "This report checks file structure and unresolved human-review markers only.",
            "It is not a leakage review, ethics determination, expert rating, casebook freeze, or holdout collection.",
            "No effectiveness, safety, or publication claim may use this preflight as outcome evidence.",
        ],
        "required_human_gates": [
            "coordinator leakage review for every vignette",
            "institutional ethics or exemption determination",
            "hash-locked approved casebook freeze",
            "masked holdout response collection",
            "independent expert review and safety assessment",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--casebook",
        type=Path,
        default=Path("data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/hiad_casebook_machine_preflight_2026_10_05.json"),
    )
    args = parser.parse_args()
    casebook = json.loads(args.casebook.read_text(encoding="utf-8"))
    report = preflight(casebook)
    report["casebook"] = {
        "path": str(args.casebook),
        "sha256": _sha256(args.casebook),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["machine_preflight_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
