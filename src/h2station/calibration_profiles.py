"""Opt-in, sanitized calibration profiles derived from owner-controlled data.

The runtime reads only the aggregate artifact committed under ``research``.
Raw logger rows, source identifiers and exact dates never enter the simulator.
Profiles are opt-in because a station-boundary calibration is not a vehicle-side
or full-loop validation result.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
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
    observed_pressure_min_pa: float | None = None
    observed_pressure_median_pa: float | None = None
    observed_pressure_max_pa: float | None = None
    pressure_noise_sigma_pa: float | None = None
    positive_pressure_ramp_p95_pa_s: float | None = None
    median_sample_period_s: float | None = None
    maximum_gap_s: float | None = None
    state_transition_count: int | None = None
    quality_warnings: tuple[str, ...] = ()

    def runtime_metadata(self) -> dict[str, object]:
        """Return bounded provenance metadata safe to expose to the runtime/UI."""

        pressure_range = {
            "min_mpa": self.observed_pressure_min_pa / 1.0e6
            if self.observed_pressure_min_pa is not None else None,
            "median_mpa": self.observed_pressure_median_pa / 1.0e6
            if self.observed_pressure_median_pa is not None else None,
            "max_mpa": self.observed_pressure_max_pa / 1.0e6
            if self.observed_pressure_max_pa is not None else None,
        }
        return {
            "id": self.profile_id,
            "evidence_artifact": self.evidence_artifact,
            "sampled_rows": self.sampled_rows,
            "recharge_hysteresis_pa": self.recharge_hysteresis_pa,
            "recharge_restart_margin_pa": self.recharge_restart_margin_pa,
            "observed_pressure_range_mpa": pressure_range,
            "pressure_noise_sigma_pa": self.pressure_noise_sigma_pa,
            "positive_pressure_ramp_p95_pa_s": self.positive_pressure_ramp_p95_pa_s,
            "median_sample_period_s": self.median_sample_period_s,
            "maximum_gap_s": self.maximum_gap_s,
            "state_transition_count": self.state_transition_count,
            "quality_warnings": list(self.quality_warnings),
            "claim_boundary": self.claim_boundary,
        }


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
        pressure = record.get("boundary_pressure_mpa") or {}
        pressure_min_pa = (
            float(pressure["min"]) * 1.0e6
            if pressure.get("min") is not None else None
        )
        pressure_median_pa = (
            float(pressure["median"]) * 1.0e6
            if pressure.get("median") is not None else None
        )
        pressure_max_pa = (
            float(pressure["max"]) * 1.0e6
            if pressure.get("max") is not None else None
        )
        if (
            pressure_min_pa is not None and pressure_max_pa is not None
            and pressure_min_pa > pressure_max_pa
        ):
            return None
        numeric_values = (
            pressure_min_pa, pressure_median_pa, pressure_max_pa,
            float(record["pressure_noise_sigma_pa"])
            if record.get("pressure_noise_sigma_pa") is not None else None,
            float(record["positive_pressure_ramp_p95_pa_s"])
            if record.get("positive_pressure_ramp_p95_pa_s") is not None else None,
            float(record["median_sample_period_s"])
            if record.get("median_sample_period_s") is not None else None,
            float(record["maximum_gap_s"])
            if record.get("maximum_gap_s") is not None else None,
        )
        if any(value is not None and not math.isfinite(value) for value in numeric_values):
            return None
        if any(
            value is not None and value < 0.0
            for value in numeric_values[3:]
        ):
            return None
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
        observed_pressure_min_pa=pressure_min_pa,
        observed_pressure_median_pa=pressure_median_pa,
        observed_pressure_max_pa=pressure_max_pa,
        pressure_noise_sigma_pa=(
            float(record["pressure_noise_sigma_pa"])
            if record.get("pressure_noise_sigma_pa") is not None else None
        ),
        positive_pressure_ramp_p95_pa_s=(
            float(record["positive_pressure_ramp_p95_pa_s"])
            if record.get("positive_pressure_ramp_p95_pa_s") is not None else None
        ),
        median_sample_period_s=(
            float(record["median_sample_period_s"])
            if record.get("median_sample_period_s") is not None else None
        ),
        maximum_gap_s=(
            float(record["maximum_gap_s"])
            if record.get("maximum_gap_s") is not None else None
        ),
        state_transition_count=(
            int(record["state_transition_count"])
            if record.get("state_transition_count") is not None else None
        ),
        quality_warnings=tuple(str(item) for item in (record.get("quality_warnings") or [])),
    )
