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
import re
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

# These keys contain coordinator-only outcome information.  They must never
# be copied into the model-visible input_context during casebook preparation.
FORBIDDEN_MODEL_INPUT_KEYS = {
    "reference_emergency_action",
    "reference_lesson_learnt",
    "reference_corrective_measures",
    "emergency_action",
    "lesson_learnt",
    "corrective_measures",
    "response",
    "outcome",
}

# This is an advisory screen only.  It deliberately does not approve or
# rewrite a vignette; it highlights language a coordinator must inspect.
COMPLETED_ACTION_PATTERN = re.compile(
    r"\b(?:shut(?:down|\s+down)|stopp?ed|isolat(?:ed|ion)|evacuat(?:ed|ion)|"
    r"taken\s+out\s+of\s+(?:service|operation)|replac(?:ed|ement)|repair(?:ed)?|"
    r"install(?:ed|ation)|investigat(?:ed|ion)|inspect(?:ed|ion)|called|"
    r"followed\s+up|remained\s+operational|safety\s+(?:equipment|system)\s+"
    r"(?:operated|performed)|corrective\s+action|returned\s+to\s+service)\b",
    flags=re.IGNORECASE,
)
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", flags=re.IGNORECASE)


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


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("_x000D_", " ").replace("\\n", " ")).strip()


def _tokens(value: object) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(_clean(value))]


def _exact_overlap_tokens(left: object, right: object, minimum: int = 4) -> int:
    """Return the longest exact token span shared by two texts."""
    source = _tokens(left)
    reference = _tokens(right)
    if len(source) < minimum or len(reference) < minimum:
        return 0
    best = 0
    for start in range(len(source) - minimum + 1):
        for ref_start in range(len(reference) - minimum + 1):
            length = 0
            while (
                start + length < len(source)
                and ref_start + length < len(reference)
                and source[start + length] == reference[ref_start + length]
            ):
                length += 1
            if length >= minimum:
                best = max(best, length)
    return best


def _leakage_advisory(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a coordinator-facing advisory without changing human gates."""
    tiers = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    cases_with_action_language = 0
    cases_with_reference_overlap = 0
    forbidden_key_cases: list[str] = []
    per_case: list[dict[str, Any]] = []
    for case in cases:
        context = case.get("input_context") if isinstance(case.get("input_context"), dict) else {}
        description = _clean(context.get("description"))
        action_matches = COMPLETED_ACTION_PATTERN.findall(description)
        forbidden_keys = sorted(FORBIDDEN_MODEL_INPUT_KEYS.intersection(context))
        references = " ".join(
            _clean(case.get(field))
            for field in ("reference_emergency_action", "reference_lesson_learnt", "reference_corrective_measures")
        )
        overlap = _exact_overlap_tokens(description, references)
        if forbidden_keys:
            forbidden_key_cases.append(str(case.get("event_id", "")))
        if action_matches:
            cases_with_action_language += 1
        if overlap:
            cases_with_reference_overlap += 1
        if forbidden_keys or overlap >= 8 or len(action_matches) >= 2:
            tier = "HIGH"
        elif overlap or action_matches:
            tier = "MEDIUM"
        else:
            tier = "LOW"
        tiers[tier] += 1
        per_case.append({
            "event_id": str(case.get("event_id", "")),
            "advisory_tier": tier,
            "completed_action_term_count": len(action_matches),
            "longest_reference_overlap_tokens": overlap,
            "forbidden_model_input_keys": forbidden_keys,
        })
    return {
        "case_count": len(cases),
        "tier_counts": tiers,
        "cases_with_completed_action_language": cases_with_action_language,
        "cases_with_reference_overlap": cases_with_reference_overlap,
        "cases_with_forbidden_model_input_keys": forbidden_key_cases,
        "per_case": per_case,
        "interpretation": "Advisory machine flags only; a qualified non-rating coordinator must decide KEEP or REWRITE for every case.",
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
    model_input_keys_ok = bool(cases) and all(
        isinstance(item, dict)
        and isinstance(item.get("input_context"), dict)
        and not FORBIDDEN_MODEL_INPUT_KEYS.intersection(item["input_context"])
        for item in cases
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
        _check(
            "model_visible_context_has_no_reserved_outcome_fields",
            model_input_keys_ok,
            {
                "forbidden_keys": sorted(FORBIDDEN_MODEL_INPUT_KEYS),
                "cases_with_forbidden_keys": [
                    str(item.get("event_id", ""))
                    for item in cases
                    if isinstance(item, dict)
                    and isinstance(item.get("input_context"), dict)
                    and FORBIDDEN_MODEL_INPUT_KEYS.intersection(item["input_context"])
                ],
            },
            "Model-visible input_context must not contain coordinator-only reference/outcome fields.",
        ),
    ]
    return {
        "schema_version": 1,
        "kind": "machine_preflight_only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "machine_preflight_pass": all(item["status"] == "PASS" for item in checks),
        "case_count": len(cases),
        "checks": checks,
        "leakage_advisory": _leakage_advisory(cases),
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
