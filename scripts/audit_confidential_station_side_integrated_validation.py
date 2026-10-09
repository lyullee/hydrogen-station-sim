"""Build a privacy-bounded station-side validation integration record.

The local archive does not contain a synchronized station-to-vehicle trace.
This audit therefore combines only already-frozen, de-identified station-side
holdouts.  It deliberately does not fit parameters, inspect raw rows, or
promote the result to a full-loop or field-safety claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(root: Path, relative: str) -> tuple[Path, dict[str, Any]]:
    path = root / relative
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{relative} must contain a JSON object")
    return path, payload


def _privacy_false(payload: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return all(payload.get(key) is False for key in keys)


def build_record(root: Path) -> dict[str, Any]:
    envelope_path, envelope = _read(
        root,
        "research/confidential_operational_envelope_holdout_replay_2026_10_06.json",
    )
    cascade_path, cascade = _read(
        root,
        "research/confidential_station_cascade_sequence_holdout_2026_10_08.json",
    )
    forecast_path, forecast = _read(
        root,
        "research/confidential_station_recharge_pressure_forecast_holdout_2026_10_08.json",
    )
    lifecycle_path, lifecycle = _read(
        root,
        "research/confidential_station_lifecycle_pressure_alignment_holdout_2026_10_09.json",
    )

    envelope_privacy = _privacy_false(
        envelope,
        ("source_identifiers_published", "raw_rows_persisted"),
    )
    cascade_privacy = _privacy_false(
        cascade,
        (
            "source_identifiers_published",
            "source_paths_published",
            "source_filenames_published",
            "source_headers_published",
            "raw_rows_persisted",
            "absolute_timestamps_published",
            "calendar_dates_published",
        ),
    )
    forecast_privacy = _privacy_false(
        forecast,
        (
            "source_identifiers_published",
            "source_paths_published",
            "source_filenames_published",
            "source_headers_published",
            "raw_rows_persisted",
            "absolute_timestamps_published",
            "calendar_dates_published",
            "tag_names_published",
            "manufacturer_or_model_published",
        ),
    )
    lifecycle_privacy = all((lifecycle.get("privacy") or {}).get(key) is False for key in (
        "source_identifiers_published",
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "per_file_hashes_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "calendar_dates_published",
        "site_company_location_manufacturer_published",
    ))

    envelope_eligibility = envelope.get("eligibility") or {}
    envelope_split = envelope.get("split") or {}
    envelope_replay = envelope.get("replay") or {}
    cascade_decision = cascade.get("decision") or {}
    cascade_holdout = cascade.get("holdout") or {}
    forecast_decision = forecast.get("decision") or {}
    forecast_holdout = forecast.get("holdout") or {}
    forecast_metrics = forecast_holdout.get("combined") or {}
    lifecycle_decision = lifecycle.get("decision") or {}
    lifecycle_screens = lifecycle.get("screens") or {}

    pressure_boundary_supported = bool(
        envelope.get("artifact_type") == "confidential_operational_envelope_holdout_replay"
        and envelope_privacy
        and envelope_split.get("fit_used_holdout") is False
        and envelope_split.get("outcome_used_for_fit") is False
        and envelope_replay.get("trajectory_completed") is True
        and envelope_eligibility.get("time_ordered_measured_boundary_holdout_supported") is True
        and envelope_eligibility.get("independent_full_loop_validation_supported") is False
    )
    cascade_supported = bool(
        cascade.get("artifact_type") == "confidential_station_cascade_sequence_holdout"
        and cascade_privacy
        and all((cascade.get("eligibility") or {}).values())
        and all((cascade.get("screens") or {}).values())
        and cascade_decision.get("cascade_controller_structure_supported") is True
        and cascade_decision.get("runtime_parameter_application") is False
        and cascade_decision.get("vehicle_fill_validation") is False
        and cascade_decision.get("full_loop_holdout_eligible") is False
    )
    recharge_forecast_supported = bool(
        forecast.get("artifact_type") == "confidential_station_recharge_pressure_forecast_holdout"
        and forecast_privacy
        and all((forecast.get("eligibility") or {}).values())
        and all((forecast.get("screens") or {}).values())
        and forecast_decision.get("short_horizon_station_pressure_forecast_supported") is True
        and forecast_decision.get("runtime_parameter_application") is False
        and forecast_decision.get("vehicle_fill_validation") is False
        and forecast_decision.get("full_loop_holdout_eligible") is False
    )
    lifecycle_negative = bool(
        lifecycle.get("artifact_type") == "confidential_station_lifecycle_pressure_alignment_holdout"
        and lifecycle_privacy
        and lifecycle_screens.get("holdout_counter_recall_met") is False
        and lifecycle_screens.get("recall_stability_met") is False
        and lifecycle_decision.get("pressure_completion_counter_alignment_supported") is False
        and lifecycle_decision.get("recharge_event_detector_corroborated") is False
    )

    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_side_integrated_validation",
        "recorded_at": "2026-10-09",
        "evidence_role": "same-site station-side integrated validation bundle",
        "source_scope": "confidential owner-controlled station operational traces",
        "privacy": {
            "source_identifiers_published": False,
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "raw_rows_persisted": False,
            "absolute_timestamps_published": False,
            "calendar_dates_published": False,
            "site_company_location_manufacturer_published": False,
        },
        "inputs": [
            {"id": "pressure_boundary_holdout", "artifact": envelope_path.relative_to(root).as_posix(), "sha256": _sha256(envelope_path)},
            {"id": "cascade_sequence_holdout", "artifact": cascade_path.relative_to(root).as_posix(), "sha256": _sha256(cascade_path)},
            {"id": "recharge_pressure_forecast_holdout", "artifact": forecast_path.relative_to(root).as_posix(), "sha256": _sha256(forecast_path)},
            {"id": "lifecycle_alignment_holdout", "artifact": lifecycle_path.relative_to(root).as_posix(), "sha256": _sha256(lifecycle_path)},
        ],
        "checks": {
            "pressure_boundary": {
                "supported": pressure_boundary_supported,
                "calibration_points": envelope_split.get("calibration_points"),
                "holdout_points": envelope_split.get("holdout_points"),
                "holdout_duration_s": envelope_split.get("holdout_duration_s"),
                "replay_completed": envelope_replay.get("trajectory_completed") is True,
                "recharge_restart_margin_pa": (envelope.get("calibration") or {}).get("recharge_restart_margin_pa"),
            },
            "cascade_sequence": {
                "supported": cascade_supported,
                "calibration_pairs": (cascade.get("calibration") or {}).get("paired_episode_count"),
                "holdout_pairs": cascade_holdout.get("paired_episode_count"),
                "holdout_pair_coverage": cascade_holdout.get("pair_coverage_fraction"),
                "holdout_sequential_fraction": cascade_holdout.get("sequential_fraction"),
                "median_handoff_gap_s": (cascade_holdout.get("handoff_gap_s") or {}).get("median"),
            },
            "recharge_pressure_forecast": {
                "supported": recharge_forecast_supported,
                "calibration_cases": (forecast.get("calibration") or {}).get("case_count"),
                "holdout_cases": forecast_holdout.get("case_count"),
                "holdout_mae_mpa": forecast_metrics.get("mae_mpa"),
                "holdout_p90_absolute_error_mpa": forecast_metrics.get("p90_absolute_error_mpa"),
                "positive_direction_fraction": forecast_metrics.get("positive_direction_fraction"),
            },
            "lifecycle_alignment": {
                "negative_result_retained": lifecycle_negative,
                "counter_monotonicity_met": (lifecycle.get("eligibility") or {}).get("counter_monotonicity_met"),
                "holdout_counter_recall": (lifecycle.get("holdout", {}).get("combined") or {}).get("counter_event_recall"),
                "holdout_pressure_precision": (lifecycle.get("holdout", {}).get("combined") or {}).get("pressure_event_precision"),
            },
        },
        "decision": {
            "station_side_integrated_validation_supported": (
                pressure_boundary_supported and cascade_supported and recharge_forecast_supported
            ),
            "pressure_boundary_holdout_supported": pressure_boundary_supported,
            "cascade_sequence_holdout_supported": cascade_supported,
            "recharge_pressure_forecast_supported": recharge_forecast_supported,
            "lifecycle_counter_alignment_supported": False,
            "runtime_parameter_application": False,
            "default_model_parameters_changed": False,
            "vehicle_fill_validation": False,
            "full_loop_external_validation_supported": False,
            "site_specific_safety_distance_validation": False,
            "independent_external_validation": False,
        },
        "claim_boundary": (
            "Same-site station-side holdout integration only. The bundle supports bounded "
            "pressure-boundary replay, medium/high cascade sequence context, and short-horizon "
            "recharge-pressure advisory. It does not validate vehicle filling, mass closure, "
            "field safety distance, accident frequency, SAGA effectiveness, or certification. "
            "The retained lifecycle-counter result is negative and must not be treated as a "
            "validated recharge detector."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/confidential_station_side_integrated_validation_2026_10_09.json",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    record = build_record(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record["decision"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
