"""Assess a privacy-bounded private full-loop channel attestation.

The assessor joins only aggregate schema coverage with a custodian-supplied
attestation.  It never reads measurement rows, persists original headers, or
turns an attestation into a validation result.  Its purpose is to make the
highest-priority data gap explicit before an external holdout is frozen.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from full_loop_schema_contract import CONTRACT_REQUIRED


def _bool(value: object) -> bool:
    return value is True


def assess(schema_report: dict[str, Any], attestation: dict[str, Any]) -> dict[str, Any]:
    """Return a redacted readiness assessment without admitting a holdout."""

    schema_scope = schema_report.get("scope") or {}
    privacy = attestation.get("privacy_boundary") or {}
    privacy_boundary_ok = all(
        privacy.get(key) is False
        for key in (
            "raw_rows_in_repository",
            "original_column_names_in_repository",
            "source_paths_in_repository",
            "site_or_company_identity_in_repository",
            "exact_dates_in_repository",
            "equipment_manufacturer_or_serials_in_repository",
        )
    ) and schema_scope.get("raw_rows_persisted") is False and schema_scope.get(
        "original_headers_persisted"
    ) is False

    schema_aggregate = schema_report.get("aggregate") or {}
    observed_schema_roles = set(schema_aggregate.get("observed_full_loop_contract_groups") or [])
    observed_schema_roles &= set(CONTRACT_REQUIRED)

    rows = [
        row for row in (attestation.get("channel_attestations") or [])
        if isinstance(row, dict) and row.get("role") in CONTRACT_REQUIRED
    ]
    attested_roles = {
        str(row.get("role"))
        for row in rows
        if _bool(row.get("required")) and _bool(row.get("present"))
    }
    missing_schema_roles = sorted(CONTRACT_REQUIRED - observed_schema_roles)
    missing_attestation_roles = sorted(CONTRACT_REQUIRED - attested_roles)

    required_metadata_checks = {
        "custodian_authorized": _bool(
            (attestation.get("custodian_attestation") or {}).get("authorized_data_owner")
        ),
        "research_rights_attested": _bool(
            (attestation.get("custodian_attestation") or {}).get("release_rights_for_research")
        ),
        "common_clock_attested": False,
        "calibration_attested": True,
        "split_manifest_present": bool(
            (attestation.get("holdout_controls") or {}).get("split_manifest_hash")
        ),
        "model_frozen_before_outcome_access": _bool(
            (attestation.get("holdout_controls") or {}).get(
                "model_and_parameters_frozen_before_outcome_access"
            )
        ),
        "independent_reviewer_confirmed": _bool(
            (attestation.get("holdout_controls") or {}).get("independent_reviewer_confirmed")
        ),
    }
    for row in rows:
        role = row.get("role")
        if role == "common_time":
            required_metadata_checks["common_clock_attested"] = bool(
                row.get("clock_alignment_method")
            ) and row.get("clock_alignment_uncertainty_s") is not None
        if role in {"station_pressure", "delivered_temperature", "mass_flow", "vehicle_pressure", "vehicle_temperature"}:
            if not row.get("unit") or not row.get("calibration_status") or row.get("uncertainty") is None:
                required_metadata_checks["calibration_attested"] = False

    required_metadata_complete = all(required_metadata_checks.values())
    schema_role_match = not missing_schema_roles and not missing_attestation_roles
    candidate_ready_for_review = bool(privacy_boundary_ok and schema_role_match and required_metadata_complete)
    controls = attestation.get("holdout_controls") or {}
    event_count_ok = int(controls.get("minimum_independent_events") or 0) >= 3

    return {
        "schema_version": 1,
        "artifact_type": "privacy_bounded_private_full_loop_attestation_assessment",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "privacy_boundary_ok": privacy_boundary_ok,
        "observed_schema_role_count": len(observed_schema_roles),
        "attested_role_count": len(attested_roles),
        "missing_schema_roles": missing_schema_roles,
        "missing_attestation_roles": missing_attestation_roles,
        "metadata_checks": required_metadata_checks,
        "schema_role_match": schema_role_match,
        "candidate_ready_for_independent_review": candidate_ready_for_review,
        "holdout_controls": {
            "minimum_event_count_met": event_count_ok,
            "model_freeze_attested": required_metadata_checks["model_frozen_before_outcome_access"],
            "independent_reviewer_attested": required_metadata_checks["independent_reviewer_confirmed"],
        },
        "external_holdout_eligibility": False,
        "validation_gate_effect": "none",
        "next_actions": (
            []
            if candidate_ready_for_review
            else [
                "attest every required station/dispenser/vehicle channel role",
                "provide units, calibration status and uncertainty for numeric channels",
                "attest common-clock alignment and masked event linkage",
                "freeze model and split before outcome access, then obtain independent review",
            ]
        ),
        "claim_boundary": (
            "This is a privacy-bounded intake assessment only. It does not validate the model, "
            "close the full-loop gate, or establish safety or regulatory compliance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-report", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assess(
        json.loads(args.schema_report.read_text(encoding="utf-8")),
        json.loads(args.attestation.read_text(encoding="utf-8")),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

