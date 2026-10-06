"""Opt-in, sanitized calibration profiles derived from owner-controlled data.

The runtime reads only the aggregate artifact committed under ``research``.
Raw logger rows, source identifiers and exact dates never enter the simulator.
Profiles are opt-in because a station-boundary calibration is not a vehicle-side
or full-loop validation result.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
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
    pressure_semantics_attested: bool = False
    lifecycle_counter_semantics_attested: bool = False
    temperature_boundary_role_attested: bool = False
    mass_flow_units_attested: bool = False

    def pressure_envelope_comparison(
        self, current_pressure_mpa: float | None,
    ) -> dict[str, object]:
        """Compare a simulated station-boundary pressure with the measured range.

        This is a scope diagnostic only.  The private archive is a station
        boundary, not a bank identity or vehicle-side validation set, so the
        comparison must never be interpreted as a safety limit or controller
        trip criterion.
        """

        pressure = (
            float(current_pressure_mpa)
            if current_pressure_mpa is not None
            else float("nan")
        )
        lower = (
            self.observed_pressure_min_pa / 1.0e6
            if self.observed_pressure_min_pa is not None else None
        )
        upper = (
            self.observed_pressure_max_pa / 1.0e6
            if self.observed_pressure_max_pa is not None else None
        )
        result: dict[str, object] = {
            "status": "unavailable",
            "current_pressure_mpa": None,
            "observed_range_mpa": {"min": lower, "max": upper},
            "margin_to_nearest_limit_mpa": None,
            "outside_by_mpa": None,
            "claim_limit": (
                "비식별 station-boundary envelope의 범위 점검이며, "
                "안전 한계·차단 설정값·뱅크 식별 또는 차량 검증이 아님"
            ),
        }
        if not math.isfinite(pressure) or lower is None or upper is None:
            return result
        result["current_pressure_mpa"] = pressure
        if lower <= pressure <= upper:
            result["status"] = "within_measured_envelope"
            result["margin_to_nearest_limit_mpa"] = min(
                pressure - lower, upper - pressure
            )
        elif pressure < lower:
            result["status"] = "below_measured_envelope"
            result["outside_by_mpa"] = lower - pressure
        else:
            result["status"] = "above_measured_envelope"
            result["outside_by_mpa"] = pressure - upper
        return result

    def runtime_metadata(
        self, *, current_boundary_pressure_mpa: float | None = None,
    ) -> dict[str, object]:
        """Return bounded provenance metadata safe to expose to the runtime/UI."""

        pressure_range = {
            "min_mpa": self.observed_pressure_min_pa / 1.0e6
            if self.observed_pressure_min_pa is not None else None,
            "median_mpa": self.observed_pressure_median_pa / 1.0e6
            if self.observed_pressure_median_pa is not None else None,
            "max_mpa": self.observed_pressure_max_pa / 1.0e6
            if self.observed_pressure_max_pa is not None else None,
        }
        result = {
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
            "channel_attestation": {
                "pressure_boundary_semantics_attested": self.pressure_semantics_attested,
                "lifecycle_counter_semantics_attested": self.lifecycle_counter_semantics_attested,
                "temperature_boundary_role_attested": self.temperature_boundary_role_attested,
                "mass_flow_units_attested": self.mass_flow_units_attested,
            },
            "claim_boundary": self.claim_boundary,
        }
        if current_boundary_pressure_mpa is not None:
            result["current_boundary_pressure_comparison"] = (
                self.pressure_envelope_comparison(current_boundary_pressure_mpa)
            )
        return result


@dataclass(frozen=True)
class BankPressureEnvelopeProfile:
    """Privacy-bounded measured ranges for generic medium/high bank roles.

    This profile is a diagnostic comparison only.  It never supplies a
    controller setpoint, trip threshold or universal safety limit.
    """

    artifact: str
    profiles: tuple[dict[str, object], ...]
    bank_role_mapping_attested: bool
    pressure_scale_mapping_attested: bool
    claim_boundary: str

    def compare(self, bank_pressures_mpa: dict[str, float] | None) -> dict[str, object]:
        values = bank_pressures_mpa or {}
        result: dict[str, object] = {
            "status": "diagnostic_only",
            "artifact": self.artifact,
            "bank_role_mapping_attested": self.bank_role_mapping_attested,
            "pressure_scale_mapping_attested": self.pressure_scale_mapping_attested,
            "banks": {},
            "runtime_parameter_application": False,
            "claim_boundary": self.claim_boundary,
        }
        # Use the robust P05/P95 envelope across anonymized profiles.  The
        # profile minimum/maximum may include idle/sentinel samples and are
        # intentionally excluded from runtime interpretation.
        for role, runtime_name in (
            ("medium_storage_pressure", "medium"),
            ("high_storage_pressure", "high"),
        ):
            observations: list[dict[str, float]] = []
            for profile in self.profiles:
                row = (profile.get("bank_roles") or {}).get(role)
                if not isinstance(row, dict):
                    continue
                pressure = row.get("pressure_mpa") or {}
                if all(isinstance(pressure.get(key), (int, float)) for key in ("p05", "p95")):
                    observations.append({
                        "p05": float(pressure["p05"]),
                        "p95": float(pressure["p95"]),
                    })
            current = values.get(runtime_name)
            if not observations or not isinstance(current, (int, float)):
                continue
            lower = min(item["p05"] for item in observations)
            upper = max(item["p95"] for item in observations)
            pressure = float(current)
            row: dict[str, object] = {
                "current_pressure_mpa": pressure,
                "observed_robust_range_mpa": {"p05": lower, "p95": upper},
                "comparison": "within_observed_robust_range"
                if lower <= pressure <= upper
                else ("below_observed_robust_range" if pressure < lower else "above_observed_robust_range"),
            }
            if pressure < lower:
                row["outside_by_mpa"] = lower - pressure
            elif pressure > upper:
                row["outside_by_mpa"] = pressure - upper
            else:
                row["margin_to_nearest_observed_bound_mpa"] = min(
                    pressure - lower, upper - pressure
                )
            result["banks"][runtime_name] = row
        if not result["banks"]:
            result["status"] = "unavailable"
        return result


@dataclass(frozen=True)
class StationRechargeDynamicsCalibrationProfile:
    """Reviewed station-side compressor restart dwell.

    This profile can only alter an opt-in dwell after a chronological holdout
    check.  It does not alter flow capacity, vessel geometry, safety limits,
    or the reference model defaults.
    """

    profile_id: str
    evidence_artifact: str
    minimum_recharge_off_time_s: float
    sampled_rows: int
    calibration_fraction: float
    holdout_completed_off_to_on_intervals: int
    holdout_minimum_off_to_on_s: float
    claim_boundary: str

    def runtime_metadata(self) -> dict[str, object]:
        return {
            "status": "active",
            "id": self.profile_id,
            "evidence_artifact": self.evidence_artifact,
            "minimum_recharge_off_time_s": self.minimum_recharge_off_time_s,
            "sampled_rows": self.sampled_rows,
            "temporal_holdout": {
                "method": "chronological_within_trace_holdout",
                "calibration_fraction": self.calibration_fraction,
                "completed_off_to_on_intervals": self.holdout_completed_off_to_on_intervals,
                "minimum_off_to_on_s": self.holdout_minimum_off_to_on_s,
            },
            "default_model_parameters_changed": False,
            "claim_boundary": self.claim_boundary,
        }

_ROOT = Path(__file__).resolve().parents[2]
_PROFILE_PATHS = (
    _ROOT / "research" / "confidential_operational_envelope_calibration_summary_2026_10_06.json",
    _ROOT / "research" / "confidential_station_boundary_calibration_summary_2026_10_06.json",
)

_BANK_ENVELOPE_PATH = (
    _ROOT / "research" / "confidential_bank_role_pressure_envelopes_2026_10_06.json"
)

_RECHARGE_DYNAMICS_PROFILE_PATH = (
    _ROOT / "research" / "confidential_station_recharge_dynamics_calibration_2026_10_06.json"
)


@lru_cache(maxsize=1)
def load_bank_pressure_envelopes() -> BankPressureEnvelopeProfile | None:
    """Load the de-identified bank-role envelope once per process."""

    try:
        record = json.loads(_BANK_ENVELOPE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.get("artifact_type") != "confidential_bank_role_pressure_envelopes"
        or record.get("evidence_role")
        != "privacy_bounded_bank_role_pressure_diagnostic"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("exact_source_dates_published") is not False
        or record.get("tag_names_published") is not False
        or record.get("manufacturer_or_model_published") is not False
    ):
        return None
    profiles: list[dict[str, object]] = []
    for profile in record.get("profiles") or []:
        if not isinstance(profile, dict):
            continue
        roles: dict[str, object] = {}
        for role in ("medium_storage_pressure", "high_storage_pressure"):
            row = (profile.get("bank_roles") or {}).get(role)
            if not isinstance(row, dict):
                continue
            pressure = row.get("pressure_mpa") or {}
            if not all(
                isinstance(pressure.get(key), (int, float))
                and math.isfinite(float(pressure[key]))
                for key in ("p05", "p95")
            ):
                continue
            roles[role] = {
                "pressure_mpa": {
                    "p05": float(pressure["p05"]),
                    "p95": float(pressure["p95"]),
                }
            }
        if roles:
            profiles.append({
                "profile_id": str(profile.get("profile_id") or ""),
                "bank_roles": roles,
            })
    if not profiles:
        return None
    attestation = record.get("attestation") or {}
    return BankPressureEnvelopeProfile(
        artifact="research/confidential_bank_role_pressure_envelopes_2026_10_06.json",
        profiles=tuple(profiles),
        bank_role_mapping_attested=attestation.get("bank_role_mapping_attested") is True,
        pressure_scale_mapping_attested=attestation.get("pressure_scale_mapping_attested") is True,
        claim_boundary=str(record.get("claim_boundary") or ""),
    )


@lru_cache(maxsize=1)
def load_station_recharge_dynamics_calibration(
    path: Path | None = None,
) -> StationRechargeDynamicsCalibrationProfile | None:
    """Load a privacy-bounded dwell only after temporal verification.

    The strict schema intentionally rejects a merely descriptive aggregate.
    A profile must prove that a dwell fitted on earlier data is no longer than
    every complete OFF-to-ON interval in the later holdout segment.
    """

    candidate = path or _RECHARGE_DYNAMICS_PROFILE_PATH
    try:
        record = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    try:
        calibration = record["calibration"]
        holdout = record["temporal_holdout"]
        eligibility = record["eligibility"]
        channel_attestation = record["channel_attestation"]
        dwell = float(calibration["recommended_minimum_recharge_off_time_s"])
        sampled_rows = int(calibration["sampled_rows"])
        calibration_fraction = float(holdout["calibration_fraction"])
        interval_count = int(holdout["holdout_completed_off_to_on_intervals"])
        holdout_minimum = float(holdout["holdout_minimum_off_to_on_s"])
        warnings = tuple(str(item) for item in (calibration.get("quality_warnings") or []))
        holdout_warnings = tuple(str(item) for item in (holdout.get("quality_warnings") or []))
        safe_numbers = (dwell, calibration_fraction, holdout_minimum)
        if (
            record.get("artifact_type") != "confidential_station_recharge_dynamics_calibration"
            or record.get("source_identifiers_published") is not False
            or record.get("raw_rows_persisted") is not False
            or record.get("absolute_timestamps_published") is not False
            or record.get("source_paths_published") is not False
            or record.get("tag_names_published") is not False
            or record.get("manufacturer_or_model_published") is not False
            or channel_attestation.get("pressure_role_and_unit_semantics_attested") is not True
            or channel_attestation.get("compressor_state_semantics_attested") is not True
            or eligibility.get("station_recharge_dynamics_calibration_supported") is not True
            or eligibility.get("runtime_parameter_application") is not True
            or eligibility.get("full_station_vehicle_validation") is not False
            or eligibility.get("full_loop_holdout_eligible") is not False
            or eligibility.get("default_model_parameters_changed") is not False
            or holdout.get("method") != "chronological_within_trace_holdout"
            or holdout.get("dwell_consistent") is not True
            or warnings or holdout_warnings
            or sampled_rows < 1
            or interval_count < 3
            or not all(math.isfinite(value) for value in safe_numbers)
            or not 0.0 < dwell <= 600.0
            or not 0.50 <= calibration_fraction < 0.90
            or holdout_minimum < dwell
        ):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    try:
        artifact = candidate.relative_to(_ROOT).as_posix()
    except ValueError:
        artifact = candidate.name
    return StationRechargeDynamicsCalibrationProfile(
        profile_id=str(record.get("profile_id") or "owner_station_recharge_dynamics_v1"),
        evidence_artifact=artifact,
        minimum_recharge_off_time_s=dwell,
        sampled_rows=sampled_rows,
        calibration_fraction=calibration_fraction,
        holdout_completed_off_to_on_intervals=interval_count,
        holdout_minimum_off_to_on_s=holdout_minimum,
        claim_boundary=str(record.get("claim_boundary") or "station recharge-dynamics calibration only"),
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
        attestation = record.get("channel_attestation") or {}
        quality_warnings = tuple(
            str(item) for item in (record.get("quality_warnings") or [])
        )
        median_period = numeric_values[5]
        maximum_gap = numeric_values[6]
        # A calibration profile is a control-boundary input, so silently
        # accepting a profile with sentinel exclusions or a sparse logger gap
        # would turn missing data into an operating margin.  Keep the runtime
        # conservative: such files remain available for offline review but are
        # never applied through the opt-in switch.
        if "nonpositive_pressure_excluded" in quality_warnings:
            return None
        if (
            median_period is not None
            and maximum_gap is not None
            and median_period > 0.0
            and maximum_gap > max(10.0 * median_period, median_period + 600.0)
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
            or (
                record.get("artifact_type")
                == "confidential_operational_envelope_calibration_summary"
                and attestation.get("pressure_boundary_semantics_attested") is not True
            )
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
        quality_warnings=quality_warnings,
        pressure_semantics_attested=attestation.get(
            "pressure_boundary_semantics_attested") is True,
        lifecycle_counter_semantics_attested=attestation.get(
            "lifecycle_counter_semantics_attested") is True,
        temperature_boundary_role_attested=attestation.get(
            "temperature_boundary_role_attested") is True,
        mass_flow_units_attested=attestation.get(
            "mass_flow_units_attested") is True,
    )
