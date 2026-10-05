"""Opt-in, sanitized calibration profiles derived from owner-controlled data.

The runtime reads only the aggregate artifact committed under ``research``.
Raw logger rows, source identifiers and exact dates never enter the simulator.
Profiles are opt-in because a station-boundary calibration is not a vehicle-side
or full-loop validation result.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class MeasuredBoundaryCalibrationProfile:
    """Sanitized station-pressure calibration values accepted by the runtime."""

    profile_id: str
    evidence_artifact: str
    recharge_hysteresis_pa: float
    recharge_restart_margin_pa: float
    sampled_rows: int
    source_scope: str
    claim_boundary: str


_ROOT = Path(__file__).resolve().parents[2]
_PROFILE_PATHS = (
    _ROOT / "research" / "confidential_operational_envelope_calibration_summary_2026_10_06.json",
    _ROOT / "research" / "confidential_station_boundary_calibration_summary_2026_10_06.json",
)


def load_measured_boundary_calibration(
    path: Path | None = None,
) -> MeasuredBoundaryCalibrationProfile | None:
    """Load the sanitized owner-controlled profile after integrity checks."""

    profile_paths = (path,) if path is not None else _PROFILE_PATHS
    record: dict[str, object] | None = None
    profile_path: Path | None = None
    for candidate in profile_paths:
        try:
            candidate_record = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(candidate_record, dict):
            record = candidate_record
            profile_path = candidate
            break
    if record is None or profile_path is None:
        return None
    try:
        eligibility = record["eligibility"]
        hysteresis = float(record["recommended_recharge_hysteresis_pa"])
        restart_margin = float(record["recommended_recharge_restart_margin_pa"])
        sampled_rows = int(record["sampled_rows"])
        if (
            record.get("artifact_type") not in {
                "confidential_station_boundary_calibration_summary",
                "confidential_operational_envelope_calibration_summary",
            }
            or record.get("source_identifiers_published") is not False
            or record.get("raw_rows_persisted") is not False
            or record.get("exact_source_dates_published") is not False
            or eligibility.get("station_boundary_calibration_supported") is not True
            or eligibility.get("full_station_vehicle_validation") is not False
            or not 0.0 < hysteresis <= 20.0e6
            or not 0.0 < restart_margin <= 20.0e6
            or sampled_rows < 1
        ):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    try:
        artifact = profile_path.relative_to(_ROOT).as_posix()
    except ValueError:
        artifact = profile_path.name
    return MeasuredBoundaryCalibrationProfile(
        profile_id=str(
            record.get("profile_id")
            or "owner_measured_station_boundary_v1"
        ),
        evidence_artifact=artifact,
        recharge_hysteresis_pa=hysteresis,
        recharge_restart_margin_pa=restart_margin,
        sampled_rows=sampled_rows,
        source_scope=str(record.get("source_scope", "owner-controlled station boundary")),
        claim_boundary=str(record.get("claim_boundary", "station-boundary calibration only")),
    )
