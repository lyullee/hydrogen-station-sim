"""Validate a privacy-bounded station-to-receiving-vessel pilot bundle.

The custodian keeps the source CSV files outside the repository. This module
returns only schema checks, channel-presence flags, file digests and aggregate
time-span metrics. It deliberately does not emit source paths, filenames,
rows, timestamps, site identifiers or equipment identifiers.

The pilot check is a data-quality gate; it is not a validation score and never
fits model parameters. A frozen evaluation protocol must be applied after a
bundle passes this intake check.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


PILOT_REQUIRED_COLUMNS = (
    "elapsed_time_s",
    "station_pressure_mpa",
    "delivered_gas_temperature_c",
    "protocol_phase",
)
MASS_COLUMNS = ("mass_flow_g_s", "transferred_mass_kg")
VEHICLE_COLUMNS = ("vehicle_pressure_mpa", "vehicle_temperature_c")
OPTIONAL_COLUMNS = (
    "selected_cascade_bank",
    "precooler_outlet_temperature_c",
    "esd_state",
    "fault_state",
)
FORBIDDEN_IDENTITY_TOKENS = (
    "site",
    "company",
    "manufacturer",
    "serial",
    "asset",
    "location",
    "address",
    "calendar",
    "timestamp",
    "datetime",
)


@dataclass(frozen=True)
class PilotIntakeRules:
    minimum_event_count: int = 3
    minimum_rows_per_event: int = 2
    require_vehicle_boundary: bool = False

    def __post_init__(self) -> None:
        if self.minimum_event_count <= 0 or self.minimum_rows_per_event < 2:
            raise ValueError("Pilot intake counts must be positive")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_float(value: str, *, column: str, row_number: int) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{column} at row {row_number} is not numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{column} at row {row_number} is not finite")
    return number


def _read_event(path: Path, rules: PilotIntakeRules) -> dict[str, Any]:
    """Inspect one event without returning its filename or rows."""

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = tuple(str(value or "").strip() for value in (reader.fieldnames or ()))
        normalized = {header.lower() for header in headers if header}
        rows = list(reader)

    identity_columns = sorted(
        header for header in headers
        if any(token in header.lower() for token in FORBIDDEN_IDENTITY_TOKENS)
    )
    missing_required = [
        column for column in PILOT_REQUIRED_COLUMNS if column not in normalized
    ]
    mass_present = [column for column in MASS_COLUMNS if column in normalized]
    vehicle_present = [column for column in VEHICLE_COLUMNS if column in normalized]
    errors: list[str] = []
    if identity_columns:
        errors.append("forbidden_identity_or_calendar_column")
    if missing_required:
        errors.append("missing_required_column")
    if not mass_present:
        errors.append("missing_mass_flow_or_transferred_mass")
    if len(rows) < rules.minimum_rows_per_event:
        errors.append("too_few_rows")

    time_values: list[float] = []
    mass_values: list[float] = []
    if not missing_required and not identity_columns:
        try:
            by_lower = {header.lower(): header for header in headers}
            for row_number, row in enumerate(rows, start=2):
                if "elapsed_time_s" in normalized:
                    time_values.append(_finite_float(
                        row.get(by_lower["elapsed_time_s"], ""),
                        column="elapsed_time_s", row_number=row_number,
                    ))
                if "mass_flow_g_s" in normalized:
                    mass_values.append(_finite_float(
                        row.get(by_lower["mass_flow_g_s"], ""),
                        column="mass_flow_g_s", row_number=row_number,
                    ))
                elif "transferred_mass_kg" in normalized:
                    mass_values.append(_finite_float(
                        row.get(by_lower["transferred_mass_kg"], ""),
                        column="transferred_mass_kg", row_number=row_number,
                    ))
                for column in (
                    "station_pressure_mpa",
                    "delivered_gas_temperature_c",
                    "vehicle_pressure_mpa",
                    "vehicle_temperature_c",
                ):
                    if column in normalized:
                        _finite_float(
                            row.get(by_lower[column], ""),
                            column=column, row_number=row_number,
                        )
        except ValueError as exc:
            errors.append(str(exc))

    if time_values and any(
        later <= earlier for earlier, later in zip(time_values, time_values[1:])
    ):
        errors.append("elapsed_time_not_strictly_increasing")
    if time_values and not math.isclose(time_values[0], 0.0, abs_tol=1.0e-9):
        errors.append("elapsed_time_does_not_start_at_zero")
    if (
        "mass_flow_g_s" in normalized
        and mass_values
        and any(value < 0.0 for value in mass_values)
    ):
        errors.append("negative_mass_flow")
    if (
        "transferred_mass_kg" in normalized
        and mass_values
        and any(later < earlier for earlier, later in zip(mass_values, mass_values[1:]))
    ):
        errors.append("transferred_mass_not_monotonic")
    if rules.require_vehicle_boundary and len(vehicle_present) != len(VEHICLE_COLUMNS):
        errors.append("missing_vehicle_boundary_channel")

    return {
        "schema_valid": not errors,
        "row_count": len(rows),
        "elapsed_time_s": {
            "start": float(time_values[0]) if time_values else None,
            "end": float(time_values[-1]) if time_values else None,
            "duration": (
                float(time_values[-1] - time_values[0])
                if len(time_values) >= 2 else None
            ),
            "strictly_increasing": bool(
                len(time_values) >= 2
                and all(
                    later > earlier
                    for earlier, later in zip(time_values, time_values[1:])
                )
            ),
            "starts_at_zero": bool(
                time_values and math.isclose(time_values[0], 0.0, abs_tol=1.0e-9)
            ),
        },
        "channel_presence": {
            "pilot_required": sorted(
                set(PILOT_REQUIRED_COLUMNS).intersection(normalized)
            ),
            "mass": mass_present,
            "vehicle_boundary": vehicle_present,
            "optional": sorted(set(OPTIONAL_COLUMNS).intersection(normalized)),
        },
        "forbidden_identity_columns_detected": bool(identity_columns),
        "forbidden_identity_column_count": len(identity_columns),
        "errors": errors,
        "source_sha256": _sha256(path),
    }


def validate_privacy_safe_pilot_bundle(
    paths: Sequence[Path | str],
    *,
    rules: PilotIntakeRules | None = None,
) -> dict[str, Any]:
    """Return an aggregate, raw-row-free intake report for event CSV files."""

    selected = rules or PilotIntakeRules()
    if not paths:
        raise ValueError("At least one event CSV is required")
    event_reports = [_read_event(Path(path), selected) for path in paths]
    pilot_ready = (
        len(event_reports) >= selected.minimum_event_count
        and all(report["schema_valid"] for report in event_reports)
    )
    vehicle_complete_count = sum(
        len(report["channel_presence"]["vehicle_boundary"]) == len(VEHICLE_COLUMNS)
        for report in event_reports
    )
    vehicle_boundary_complete = (
        pilot_ready
        and vehicle_complete_count == len(event_reports)
    )
    common_elapsed_time_axis = bool(
        event_reports
        and all(
            report["elapsed_time_s"]["starts_at_zero"]
            and report["elapsed_time_s"]["strictly_increasing"]
            for report in event_reports
        )
    )
    if not pilot_ready:
        readiness_status = "SCHEMA_INCOMPLETE"
    elif vehicle_boundary_complete:
        readiness_status = "READY_FOR_FULL_LOOP_PROTOCOL_FREEZE"
    else:
        readiness_status = "READY_FOR_PROTOCOL_FREEZE"
    return {
        "schema_version": 1,
        "artifact_type": "privacy_safe_full_loop_pilot_intake",
        "status": readiness_status,
        "raw_rows_persisted": False,
        "source_paths_published": False,
        "source_filenames_published": False,
        "site_company_manufacturer_published": False,
        "calendar_dates_published": False,
        "event_count": len(event_reports),
        "valid_event_count": sum(
            report["schema_valid"] for report in event_reports
        ),
        "vehicle_boundary_complete_event_count": vehicle_complete_count,
        "full_loop_readiness": {
            "station_boundary_ready": pilot_ready,
            "common_elapsed_time_axis": common_elapsed_time_axis,
            "vehicle_boundary_required_for_full_loop": True,
            "vehicle_boundary_complete": vehicle_boundary_complete,
            "missing_vehicle_boundary_event_count": max(
                len(event_reports) - vehicle_complete_count, 0
            ),
            "full_loop_protocol_freeze_candidate": vehicle_boundary_complete,
            "claim_supported": False,
            "claim_limit": (
                "A complete station-to-vehicle validation still requires a frozen "
                "protocol, independent outcomes and pre-declared scoring; schema "
                "readiness alone is not validation."
            ),
        },
        "event_reports": [
            {
                "event_id": f"event_{index:03d}",
                **report,
            }
            for index, report in enumerate(event_reports, start=1)
        ],
        "decision": {
            "pilot_bundle_ready": pilot_ready,
            "full_loop_validation_scored": False,
            "parameter_fitting_performed": False,
            "next_step": (
                "freeze model and scoring protocol before reading outcomes"
                if vehicle_boundary_complete
                else (
                    "obtain synchronized vehicle_pressure_mpa and "
                    "vehicle_temperature_c channels before full-loop freeze"
                    if pilot_ready
                    else "repair schema or channel-role attestations"
                )
            ),
        },
        "claim_boundary": (
            "This is a privacy-safe schema and quality intake. It does not score "
            "the digital twin, establish a safety limit, or support a full-loop "
            "claim until a separately frozen evaluation is run."
        ),
    }


def build_privacy_safe_freeze_manifest(
    paths: Sequence[Path | str],
    *,
    protocol_path: Path | str,
    model_path: Path | str,
    evaluator_path: Path | str,
    channel_roles: Mapping[str, str],
    rules: PilotIntakeRules | None = None,
) -> dict[str, Any]:
    """Create a hash-only pre-access freeze record for an intake bundle.

    The function deliberately stops at protocol freeze.  It never reads model
    outcomes, fits parameters, selects cases by performance, or marks a
    bundle as full-loop validation.  The custodian can keep the source files
    private while a reviewer receives a reproducible digest and role map.
    """

    selected = rules or PilotIntakeRules()
    intake = validate_privacy_safe_pilot_bundle(paths, rules=selected)
    if intake["status"] not in {
        "READY_FOR_PROTOCOL_FREEZE",
        "READY_FOR_FULL_LOOP_PROTOCOL_FREEZE",
    }:
        raise ValueError("Cannot freeze an incomplete privacy-safe intake bundle")
    required_roles = set(PILOT_REQUIRED_COLUMNS) | {"mass_or_transferred_mass"}
    missing_roles = sorted(required_roles - set(channel_roles))
    if missing_roles:
        raise ValueError("Missing channel-role attestations: " + ", ".join(missing_roles))
    vehicle_roles_attested = sorted(
        set(VEHICLE_COLUMNS).intersection(channel_roles)
    )
    full_loop_candidate = bool(
        intake["full_loop_readiness"]["full_loop_protocol_freeze_candidate"]
        and len(vehicle_roles_attested) == len(VEHICLE_COLUMNS)
    )

    return {
        "schema_version": 1,
        "artifact_type": "privacy_safe_full_loop_preaccess_freeze_manifest",
        "status": "FROZEN_BEFORE_OUTCOME_ACCESS",
        "freeze": {
            "outcomes_accessed_before_freeze": False,
            "parameter_fitting_performed": False,
            "case_selection_by_model_performance": False,
            "post_freeze_parameter_tuning_prohibited": True,
            "custodian_attestation_required": True,
        },
        "locked_files": {
            "protocol_sha256": _sha256(Path(protocol_path)),
            "model_sha256": _sha256(Path(model_path)),
            "evaluator_sha256": _sha256(Path(evaluator_path)),
        },
        "channel_roles": dict(sorted(channel_roles.items())),
        "bundle": {
            "event_count": intake["event_count"],
            "valid_event_count": intake["valid_event_count"],
            "event_sha256": {
                report["event_id"]: report["source_sha256"]
                for report in intake["event_reports"]
            },
            "vehicle_boundary_complete_event_count": intake[
                "vehicle_boundary_complete_event_count"
            ],
        },
        "eligibility": {
            "preaccess_protocol_freeze_ready": True,
            "full_loop_protocol_freeze_candidate": full_loop_candidate,
            "vehicle_boundary_roles_attested": vehicle_roles_attested,
            "missing_vehicle_boundary_roles": sorted(
                set(VEHICLE_COLUMNS) - set(vehicle_roles_attested)
            ),
            "model_scoring_performed": False,
            "full_loop_external_validation_supported": False,
            "safety_claim_supported": False,
        },
        "claim_boundary": (
            "This manifest proves only that a privacy-safe input bundle and the "
            "declared protocol, model and evaluator were hash-locked before "
            "outcome access. It is not a validation result or a safety claim."
        ),
    }


__all__ = [
    "MASS_COLUMNS",
    "OPTIONAL_COLUMNS",
    "PILOT_REQUIRED_COLUMNS",
    "PilotIntakeRules",
    "VEHICLE_COLUMNS",
    "build_privacy_safe_freeze_manifest",
    "validate_privacy_safe_pilot_bundle",
]
