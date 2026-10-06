"""Recheck a restricted station calibration against the committed profile.

The command is intended to run only in the custodian-controlled environment.
It reads a private CSV bundle and a private mapping, then writes an aggregate
comparison containing no source path, tag name, row, identifier, or timestamp.
The committed profile is never replaced automatically: a mismatch is a
review signal and the process exits non-zero unless ``--allow-mismatch`` is
explicitly supplied for diagnostic collection.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from typing import Any

from h2station.controlled_station_replay import fit_station_boundary

try:  # package import for tests; direct import when invoked as a script
    from .calibrate_confidential_station_data import _mapping
except ImportError:  # pragma: no cover - exercised by the CLI invocation
    from calibrate_confidential_station_data import _mapping


_CORE_FIELDS = (
    "files_read",
    "sampled_rows",
    "duration_s",
    "median_sample_period_s",
    "maximum_gap_s",
    "boundary_pressure_pa.min",
    "boundary_pressure_pa.median",
    "boundary_pressure_pa.max",
    "boundary_pressure_pa.noise_sigma",
    "boundary_pressure_pa.positive_ramp_p95",
    "recharge_hysteresis_pa",
    "recharge_restart_margin_pa",
)


def _get(record: dict[str, Any], dotted: str) -> Any:
    value: Any = record
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _canonical_expected(record: dict[str, Any]) -> dict[str, Any]:
    """Normalise the committed profile's public units to fresh-summary units."""

    value = record.get("calibration", record)
    if "boundary_pressure_pa" in value:
        return value
    # The committed operational profile stores pressure in MPa under
    # ``boundary_pressure_mpa`` while ``StationCalibrationSummary`` emits Pa.
    pressure = value.get("boundary_pressure_mpa") or {}
    return {
        "files_read": value.get("files_read"),
        "sampled_rows": value.get("sampled_rows"),
        "duration_s": value.get("duration_s"),
        "median_sample_period_s": value.get("median_sample_period_s"),
        "maximum_gap_s": value.get("maximum_gap_s"),
        "boundary_pressure_pa": {
            "min": (float(pressure["min"]) * 1.0e6 if pressure.get("min") is not None else None),
            "median": (float(pressure["median"]) * 1.0e6 if pressure.get("median") is not None else None),
            "max": (float(pressure["max"]) * 1.0e6 if pressure.get("max") is not None else None),
            "noise_sigma": value.get("pressure_noise_sigma_pa"),
            "positive_ramp_p95": value.get("positive_pressure_ramp_p95_pa_s"),
        },
        "recharge_hysteresis_pa": value.get("recommended_recharge_hysteresis_pa"),
        "recharge_restart_margin_pa": value.get("recommended_recharge_restart_margin_pa"),
        "channel_roles": value.get("channel_roles", []),
    }


def compare_aggregate(
    fresh: dict[str, Any], expected_profile: dict[str, Any],
) -> dict[str, Any]:
    """Compare only the fields supported by the supplied private mapping.

    Optional channels (temperature, flow, discrete states) are deliberately
    reported as omitted when the mapping does not attest them.  They must not
    be treated as matching merely because the public profile contains a
    value.
    """

    expected = _canonical_expected(expected_profile)
    fresh_roles = set(fresh.get("channel_roles") or [])
    fields = list(_CORE_FIELDS)
    omitted: list[str] = []
    if "discrete_state" not in fresh_roles:
        omitted.append("state_transition_count")
    if "station_temperature" not in fresh_roles:
        omitted.extend(
            "boundary_temperature_degC." + key for key in ("min", "median", "max")
        )
    if "mass_flow" not in fresh_roles:
        omitted.append("flow_p95_kg_s")

    compared: list[str] = []
    mismatches: list[dict[str, Any]] = []
    for field in fields:
        observed = _get(fresh, field)
        reference = _get(expected, field)
        if observed is None or reference is None:
            omitted.append(field)
            continue
        compared.append(field)
        if isinstance(observed, (int, float)) and isinstance(reference, (int, float)):
            equal = abs(float(observed) - float(reference)) <= max(
                1.0e-9, abs(float(reference)) * 1.0e-9
            )
        else:
            equal = observed == reference
        if not equal:
            mismatches.append({"field": field, "fresh": observed, "expected": reference})

    return {
        "matches": not mismatches,
        "fields_compared": compared,
        "fields_omitted_without_attestation": sorted(set(omitted)),
        "mismatches": mismatches,
        "fresh_channel_roles": sorted(fresh_roles),
        "expected_channel_roles": expected.get("channel_roles", []),
    }


def build_recheck_record(
    fresh: dict[str, Any], comparison: dict[str, Any],
) -> dict[str, Any]:
    """Build the public-safe recheck artifact."""

    return {
        "schema_version": 1,
        "artifact_type": "confidential_operational_envelope_recheck",
        "recorded_at": date.today().isoformat(),
        "source_scope": "owner-controlled station logger; aggregate recheck only",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "source_paths_published": False,
        "fresh_calibration": fresh,
        "committed_profile_comparison": comparison,
        "runtime_decision": {
            "committed_profile_replaced": False,
            "default_model_parameters_changed": False,
            "measured_boundary_calibration_remains_opt_in": True,
            "mismatch_requires_custodian_review": True,
        },
        "claim_boundary": (
            "This is a de-identified aggregate consistency recheck. It supports "
            "station-boundary calibration provenance only; it is not vehicle-side "
            "validation, full-loop accuracy, safety certification or a universal limit."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="restricted raw CSV file or directory")
    parser.add_argument("--mapping", type=Path, required=True, help="restricted custodian mapping JSON")
    parser.add_argument("--expected-profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    parser.add_argument("--allow-mismatch", action="store_true")
    args = parser.parse_args()

    mapping = _mapping(args.mapping)
    fresh = fit_station_boundary(
        args.input,
        mapping,
        stride=args.stride,
        max_rows_per_file=args.max_rows_per_file,
    ).to_public_dict()
    expected = json.loads(args.expected_profile.read_text(encoding="utf-8"))
    comparison = compare_aggregate(fresh, expected)
    record = build_recheck_record(fresh, comparison)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    if not comparison["matches"] and not args.allow_mismatch:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
