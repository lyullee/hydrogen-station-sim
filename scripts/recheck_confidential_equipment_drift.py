"""Compare a restricted equipment-log aggregate with a retained profile.

The raw logger and mapping stay outside the repository.  This command emits
only generic aggregates and an explicit decision not to replace the runtime
profile automatically when a new window differs from the retained profile.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from calibrate_confidential_station_data import _mapping
from h2station.controlled_station_replay import fit_station_boundary


_FIELDS = (
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
    "recharge_restart_margin_pa",
    "state_transition_count",
)


def _get(value: dict[str, Any], dotted: str) -> Any:
    current: Any = value
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _compare(fresh: dict[str, Any], retained: dict[str, Any]) -> dict[str, Any]:
    expected = retained.get("calibration", retained)
    # The retained operational profile stores pressure in MPa while the
    # runtime aggregate emits Pa.  Normalize only the generic aggregate
    # fields; no source tag or path is needed.
    if "boundary_pressure_pa" not in expected and "boundary_pressure_mpa" in expected:
        pressure = expected.get("boundary_pressure_mpa") or {}
        expected = dict(expected)
        expected["boundary_pressure_pa"] = {
            key: (float(value) * 1.0e6 if value is not None else None)
            for key, value in pressure.items()
        }
        expected["recharge_restart_margin_pa"] = expected.get(
            "recommended_recharge_restart_margin_pa"
        )
        expected["boundary_pressure_pa"]["noise_sigma"] = expected.get(
            "pressure_noise_sigma_pa"
        )
        expected["boundary_pressure_pa"]["positive_ramp_p95"] = expected.get(
            "positive_pressure_ramp_p95_pa_s"
        )
        expected["state_transition_count"] = expected.get("state_transition_count")
    mismatches: list[dict[str, Any]] = []
    compared: list[str] = []
    for field in _FIELDS:
        observed = _get(fresh, field)
        reference = _get(expected, field)
        if observed is None or reference is None:
            continue
        compared.append(field)
        if isinstance(observed, (int, float)) and isinstance(reference, (int, float)):
            equal = abs(float(observed) - float(reference)) <= max(
                1.0e-9, abs(float(reference)) * 1.0e-9
            )
        else:
            equal = observed == reference
        if not equal:
            mismatches.append({"field": field, "fresh": observed, "retained": reference})
    return {
        "matches": not mismatches,
        "fields_compared": compared,
        "mismatches": mismatches,
    }


def build_record(fresh: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_equipment_drift_recheck",
        "recorded_at": date.today().isoformat(),
        "source_scope": "owner-controlled equipment logger; generic aggregate only",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "source_paths_published": False,
        "fresh_calibration": fresh,
        "comparison": comparison,
        "runtime_decision": {
            "profile_replaced": False,
            "default_model_parameters_changed": False,
            "measured_boundary_calibration_remains_opt_in": True,
            "mismatch_requires_custodian_review": bool(comparison["mismatches"]),
        },
        "eligibility": {
            "equipment_drift_recheck_supported": True,
            "temperature_or_flow_parameter_fit_supported": False,
            "full_station_vehicle_validation": False,
            "full_loop_holdout_eligible": False,
        },
        "claim_boundary": (
            "De-identified equipment-window drift check only. A mismatch is a "
            "review signal, not a new safety limit, calibration update, or "
            "station-to-vehicle validation result."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--retained-profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=60)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    args = parser.parse_args()
    if args.stride < 1 or args.max_rows_per_file < 1:
        parser.error("stride and max-rows-per-file must be positive")
    fresh = fit_station_boundary(
        args.input,
        _mapping(args.mapping),
        stride=args.stride,
        max_rows_per_file=args.max_rows_per_file,
    ).to_public_dict()
    retained = json.loads(args.retained_profile.read_text(encoding="utf-8"))
    result = build_record(fresh, _compare(fresh, retained))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
