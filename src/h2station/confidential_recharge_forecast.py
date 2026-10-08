"""Prospective, privacy-bounded station recharge pressure forecast.

The evaluator intentionally uses only custodian-attested medium/high storage
pressure roles and a compressor loaded/idle state.  A short observed prefix is
used to identify the bank responding to a loaded compressor.  An earlier
chronological partition estimates one bank-specific continuation gain; a later
partition is kept for the prospective holdout.

No source path, filename, timestamp, raw row, tag name, or case-level pressure
value is returned by the public result.  Passing this narrow check supports a
short-horizon station-side pressure-response surrogate only.  It does not
identify compressor capacity, storage volume, vehicle filling performance, or
a safety limit, and it never changes the simulator defaults automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping

from .controlled_station_replay import TraceMapping, _finite, _quantile, _sampled_rows


def _state(value: object) -> str:
    return str(value or "").strip().casefold()


def _rounded(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(float(value), 6)


@dataclass(frozen=True)
class RechargeForecastRules:
    calibration_fraction: float = 0.70
    prefix_duration_s: float = 10.0
    forecast_duration_s: float = 30.0
    maximum_sample_gap_s: float = 2.5
    endpoint_tolerance_s: float = 1.5
    minimum_prefix_rise_mpa: float = 0.10
    minimum_dominance_ratio: float = 1.5
    dominance_floor_mpa: float = 0.05
    minimum_pressure_mpa: float = 10.0
    maximum_pressure_mpa: float = 100.0
    minimum_matching_files: int = 6
    minimum_calibration_cases: int = 100
    minimum_holdout_cases: int = 40
    minimum_holdout_cases_per_bank: int = 10
    maximum_holdout_median_absolute_error_mpa: float = 0.50
    maximum_holdout_p90_absolute_error_mpa: float = 1.50
    minimum_mae_improvement_over_persistence_fraction: float = 0.20
    minimum_positive_direction_fraction: float = 0.90
    maximum_gain_relative_shift: float = 0.50

    def validate(self) -> None:
        if not 0.0 < self.calibration_fraction < 1.0:
            raise ValueError("calibration_fraction must be between zero and one")
        if self.prefix_duration_s <= 0.0 or self.forecast_duration_s <= 0.0:
            raise ValueError("prefix and forecast durations must be positive")
        if self.maximum_sample_gap_s <= 0.0 or self.endpoint_tolerance_s < 0.0:
            raise ValueError("sample-gap limits must be nonnegative")
        if self.minimum_prefix_rise_mpa <= 0.0:
            raise ValueError("minimum_prefix_rise_mpa must be positive")
        if self.minimum_dominance_ratio <= 1.0:
            raise ValueError("minimum_dominance_ratio must exceed one")
        if self.minimum_pressure_mpa <= 0.0 or self.maximum_pressure_mpa <= self.minimum_pressure_mpa:
            raise ValueError("pressure bounds are invalid")
        if min(
            self.minimum_matching_files,
            self.minimum_calibration_cases,
            self.minimum_holdout_cases,
            self.minimum_holdout_cases_per_bank,
        ) < 1:
            raise ValueError("minimum evidence counts must be positive")


@dataclass(frozen=True)
class _Observation:
    time_s: float
    active: bool
    pressures_mpa: tuple[float, float]


@dataclass(frozen=True)
class _Case:
    bank: str
    prefix_rate_mpa_s: float
    future_delta_mpa: float
    future_duration_s: float


def _validated_roles(
    mapping: TraceMapping,
    bank_by_pressure_role: Mapping[str, str],
) -> tuple[tuple[str, str], tuple[str, str]]:
    mapped = {role for role, _ in mapping.pressure_columns}
    pairs = tuple((str(role), str(bank)) for role, bank in bank_by_pressure_role.items())
    if len(pairs) != 2 or {bank for _, bank in pairs} != {"medium", "high"}:
        raise ValueError("exactly one medium and one high pressure role are required")
    if any(role not in mapped for role, _ in pairs):
        raise ValueError("bank roles must reference mapped pressure roles")
    return tuple(sorted(pairs, key=lambda item: (item[1] != "medium", item[0])))  # type: ignore[return-value]


def _load_observations(
    input_path: Path,
    mapping: TraceMapping,
    *,
    role_pairs: tuple[tuple[str, str], tuple[str, str]],
    compressor_state_role: str,
    active_values: set[str],
    stride: int,
    max_rows_per_file: int | None,
) -> tuple[dict[Path, list[_Observation]], int]:
    pressure_columns = dict(mapping.pressure_columns)
    state_columns = dict(mapping.state_columns)
    roles = tuple(role for role, _ in role_pairs)
    observations: dict[Path, list[_Observation]] = {}
    sampled_rows = 0
    for path, time_s, row in _sampled_rows(
        input_path,
        mapping,
        stride=stride,
        max_rows_per_file=max_rows_per_file,
    ):
        sampled_rows += 1
        values: list[float] = []
        for role in roles:
            raw = _finite(row.get(pressure_columns[role]))
            if raw is None:
                break
            pressure_mpa = raw * mapping.pressure_scale_pa_per_unit / 1.0e6
            if not math.isfinite(pressure_mpa):
                break
            values.append(pressure_mpa)
        if len(values) != 2:
            continue
        observations.setdefault(path, []).append(
            _Observation(
                time_s=float(time_s),
                active=_state(row.get(state_columns[compressor_state_role])) in active_values,
                pressures_mpa=(values[0], values[1]),
            )
        )
    return observations, sampled_rows


def _deduplicate_and_sort(rows: list[_Observation]) -> list[_Observation]:
    # Last-in-file wins for duplicate timestamps, matching the deterministic
    # convention used by the other confidential chronological validators.
    by_time = {row.time_s: row for row in rows if math.isfinite(row.time_s)}
    return [by_time[key] for key in sorted(by_time)]


def _endpoint_index(
    rows: list[_Observation],
    start_index: int,
    target_time_s: float,
    tolerance_s: float,
) -> int | None:
    index = start_index
    while index < len(rows) and rows[index].time_s < target_time_s:
        index += 1
    candidates = []
    if index < len(rows):
        candidates.append(index)
    if index - 1 >= start_index:
        candidates.append(index - 1)
    if not candidates:
        return None
    selected = min(candidates, key=lambda item: abs(rows[item].time_s - target_time_s))
    return selected if abs(rows[selected].time_s - target_time_s) <= tolerance_s else None


def _segment_continuous_active(
    rows: list[_Observation],
    start: int,
    stop: int,
    maximum_gap_s: float,
) -> bool:
    if stop <= start or not all(row.active for row in rows[start : stop + 1]):
        return False
    return all(
        0.0 < rows[index + 1].time_s - rows[index].time_s <= maximum_gap_s
        for index in range(start, stop)
    )


def _extract_cases(rows: list[_Observation], rules: RechargeForecastRules) -> list[_Case]:
    cases: list[_Case] = []
    index = 0
    total_duration = rules.prefix_duration_s + rules.forecast_duration_s
    while index < len(rows) - 2:
        first = rows[index]
        if not first.active:
            index += 1
            continue
        prefix_index = _endpoint_index(
            rows,
            index + 1,
            first.time_s + rules.prefix_duration_s,
            rules.endpoint_tolerance_s,
        )
        end_index = _endpoint_index(
            rows,
            index + 1,
            first.time_s + total_duration,
            rules.endpoint_tolerance_s,
        )
        if prefix_index is None or end_index is None or not _segment_continuous_active(
            rows, index, end_index, rules.maximum_sample_gap_s
        ):
            index += 1
            continue
        prefix_elapsed = rows[prefix_index].time_s - first.time_s
        future_elapsed = rows[end_index].time_s - rows[prefix_index].time_s
        if prefix_elapsed <= 0.0 or future_elapsed <= 0.0:
            index += 1
            continue
        prefix_rises = tuple(
            rows[prefix_index].pressures_mpa[bank_index] - first.pressures_mpa[bank_index]
            for bank_index in range(2)
        )
        target_index = 0 if prefix_rises[0] >= prefix_rises[1] else 1
        other_index = 1 - target_index
        target_rise = prefix_rises[target_index]
        other_rise = max(prefix_rises[other_index], rules.dominance_floor_mpa)
        start_pressure = rows[prefix_index].pressures_mpa[target_index]
        if (
            target_rise >= rules.minimum_prefix_rise_mpa
            and target_rise >= rules.minimum_dominance_ratio * other_rise
            and rules.minimum_pressure_mpa <= start_pressure <= rules.maximum_pressure_mpa
        ):
            cases.append(
                _Case(
                    bank="medium" if target_index == 0 else "high",
                    prefix_rate_mpa_s=target_rise / prefix_elapsed,
                    future_delta_mpa=(
                        rows[end_index].pressures_mpa[target_index] - start_pressure
                    ),
                    future_duration_s=future_elapsed,
                )
            )
        # Non-overlapping windows prevent dense 1 s logs from overstating the
        # effective sample count.
        next_time = first.time_s + total_duration
        while index < len(rows) and rows[index].time_s < next_time:
            index += 1
    return cases


def _fit_gain(cases: list[_Case]) -> float | None:
    ratios = [
        (case.future_delta_mpa / case.future_duration_s) / case.prefix_rate_mpa_s
        for case in cases
        if case.prefix_rate_mpa_s > 0.0 and case.future_duration_s > 0.0
        and math.isfinite(case.future_delta_mpa)
    ]
    if not ratios:
        return None
    # Frozen robust bounds prevent an isolated controller transition from
    # creating an arbitrarily large continuation forecast.
    return min(3.0, max(-1.0, median(ratios)))


def _metrics(cases: list[_Case], gain: float | None) -> dict[str, object]:
    if not cases or gain is None:
        return {
            "case_count": len(cases),
            "gain": _rounded(gain),
            "mae_mpa": None,
            "median_absolute_error_mpa": None,
            "p90_absolute_error_mpa": None,
            "persistence_mae_mpa": None,
            "uncalibrated_prefix_mae_mpa": None,
            "mae_improvement_over_persistence_fraction": None,
            "mae_improvement_over_uncalibrated_prefix_fraction": None,
            "positive_direction_fraction": None,
        }
    predicted = [
        case.prefix_rate_mpa_s * case.future_duration_s * gain for case in cases
    ]
    observed = [case.future_delta_mpa for case in cases]
    errors = [abs(value - truth) for value, truth in zip(predicted, observed)]
    persistence = [abs(truth) for truth in observed]
    uncalibrated = [
        abs(case.prefix_rate_mpa_s * case.future_duration_s - truth)
        for case, truth in zip(cases, observed)
    ]
    mae = sum(errors) / len(errors)
    persistence_mae = sum(persistence) / len(persistence)
    uncalibrated_mae = sum(uncalibrated) / len(uncalibrated)
    direction = sum(
        (prediction > 0.0 and truth > 0.0)
        or (prediction == 0.0 and truth == 0.0)
        or (prediction < 0.0 and truth < 0.0)
        for prediction, truth in zip(predicted, observed)
    ) / len(observed)
    return {
        "case_count": len(cases),
        "gain": _rounded(gain),
        "mae_mpa": _rounded(mae),
        "median_absolute_error_mpa": _rounded(median(errors)),
        "p90_absolute_error_mpa": _rounded(_quantile(sorted(errors), 0.90)),
        "persistence_mae_mpa": _rounded(persistence_mae),
        "uncalibrated_prefix_mae_mpa": _rounded(uncalibrated_mae),
        "mae_improvement_over_persistence_fraction": _rounded(
            1.0 - mae / persistence_mae if persistence_mae > 0.0 else None
        ),
        "mae_improvement_over_uncalibrated_prefix_fraction": _rounded(
            1.0 - mae / uncalibrated_mae if uncalibrated_mae > 0.0 else None
        ),
        "positive_direction_fraction": _rounded(direction),
    }


def validate_recharge_pressure_forecast(
    input_path: Path,
    mapping: TraceMapping,
    *,
    compressor_state_role: str,
    active_state_values: Iterable[str],
    bank_by_pressure_role: Mapping[str, str],
    pressure_semantics_attested: bool,
    state_semantics_attested: bool,
    rules: RechargeForecastRules = RechargeForecastRules(),
    stride: int = 1,
    max_rows_per_file: int | None = None,
) -> dict[str, object]:
    """Fit on earlier rows and score a later, previously hidden partition."""

    rules.validate()
    if not pressure_semantics_attested:
        raise ValueError("pressure semantics attestation is required")
    if not state_semantics_attested:
        raise ValueError("compressor-state semantics attestation is required")
    if stride < 1:
        raise ValueError("stride must be at least one")
    if compressor_state_role not in dict(mapping.state_columns):
        raise ValueError("compressor_state_role must be mapped")
    active_values = {_state(value) for value in active_state_values if _state(value)}
    if not active_values:
        raise ValueError("at least one active compressor-state value is required")
    role_pairs = _validated_roles(mapping, bank_by_pressure_role)
    observations, sampled_rows = _load_observations(
        input_path,
        mapping,
        role_pairs=role_pairs,
        compressor_state_role=compressor_state_role,
        active_values=active_values,
        stride=stride,
        max_rows_per_file=max_rows_per_file,
    )

    calibration_cases: list[_Case] = []
    holdout_cases: list[_Case] = []
    files_with_calibration_cases = 0
    files_with_holdout_cases = 0
    usable_files = 0
    for rows in observations.values():
        ordered = _deduplicate_and_sort(rows)
        if len(ordered) < 4:
            continue
        split = max(2, min(len(ordered) - 2, int(len(ordered) * rules.calibration_fraction)))
        earlier = _extract_cases(ordered[:split], rules)
        later = _extract_cases(ordered[split:], rules)
        if earlier or later:
            usable_files += 1
        if earlier:
            files_with_calibration_cases += 1
            calibration_cases.extend(earlier)
        if later:
            files_with_holdout_cases += 1
            holdout_cases.extend(later)

    gains = {
        bank: _fit_gain([case for case in calibration_cases if case.bank == bank])
        for bank in ("medium", "high")
    }
    calibration_by_bank = {
        bank: _metrics(
            [case for case in calibration_cases if case.bank == bank], gains[bank]
        )
        for bank in ("medium", "high")
    }
    holdout_by_bank = {
        bank: _metrics([case for case in holdout_cases if case.bank == bank], gains[bank])
        for bank in ("medium", "high")
    }
    # Combined metrics require one gain per bank, so calculate their aggregates
    # explicitly rather than pretending both banks share one fitted parameter.
    combined_predictions: list[tuple[float, float, float, float]] = []
    for case in holdout_cases:
        gain = gains[case.bank]
        if gain is None:
            continue
        prediction = case.prefix_rate_mpa_s * case.future_duration_s * gain
        combined_predictions.append(
            (
                prediction,
                case.future_delta_mpa,
                case.prefix_rate_mpa_s * case.future_duration_s,
                case.future_duration_s,
            )
        )
    if combined_predictions:
        absolute_errors = [abs(pred - truth) for pred, truth, _, _ in combined_predictions]
        persistence_errors = [abs(truth) for _, truth, _, _ in combined_predictions]
        uncalibrated_errors = [abs(raw - truth) for _, truth, raw, _ in combined_predictions]
        mae = sum(absolute_errors) / len(absolute_errors)
        persistence_mae = sum(persistence_errors) / len(persistence_errors)
        raw_mae = sum(uncalibrated_errors) / len(uncalibrated_errors)
        combined = {
            "case_count": len(combined_predictions),
            "mae_mpa": _rounded(mae),
            "median_absolute_error_mpa": _rounded(median(absolute_errors)),
            "p90_absolute_error_mpa": _rounded(_quantile(sorted(absolute_errors), 0.90)),
            "persistence_mae_mpa": _rounded(persistence_mae),
            "uncalibrated_prefix_mae_mpa": _rounded(raw_mae),
            "mae_improvement_over_persistence_fraction": _rounded(
                1.0 - mae / persistence_mae if persistence_mae > 0.0 else None
            ),
            "mae_improvement_over_uncalibrated_prefix_fraction": _rounded(
                1.0 - mae / raw_mae if raw_mae > 0.0 else None
            ),
            "positive_direction_fraction": _rounded(
                sum(
                    (pred > 0.0 and truth > 0.0)
                    or (pred == 0.0 and truth == 0.0)
                    or (pred < 0.0 and truth < 0.0)
                    for pred, truth, _, _ in combined_predictions
                ) / len(combined_predictions)
            ),
        }
    else:
        combined = _metrics([], None)

    holdout_oracle_gains = {
        bank: _fit_gain([case for case in holdout_cases if case.bank == bank])
        for bank in ("medium", "high")
    }
    relative_gain_shift = {}
    for bank in ("medium", "high"):
        fitted, oracle = gains[bank], holdout_oracle_gains[bank]
        relative_gain_shift[bank] = _rounded(
            abs(oracle - fitted) / max(abs(fitted), 1.0e-12)
            if fitted is not None and oracle is not None else None
        )

    eligibility = {
        "minimum_files_met": usable_files >= rules.minimum_matching_files,
        "minimum_calibration_cases_met": len(calibration_cases) >= rules.minimum_calibration_cases,
        "minimum_holdout_cases_met": len(holdout_cases) >= rules.minimum_holdout_cases,
        "minimum_holdout_cases_per_bank_met": all(
            holdout_by_bank[bank]["case_count"] >= rules.minimum_holdout_cases_per_bank
            for bank in ("medium", "high")
        ),
    }
    screens = {
        "holdout_median_absolute_error_met": (
            combined.get("median_absolute_error_mpa") is not None
            and combined["median_absolute_error_mpa"]
            <= rules.maximum_holdout_median_absolute_error_mpa
        ),
        "holdout_p90_absolute_error_met": (
            combined.get("p90_absolute_error_mpa") is not None
            and combined["p90_absolute_error_mpa"]
            <= rules.maximum_holdout_p90_absolute_error_mpa
        ),
        "persistence_improvement_met": (
            combined.get("mae_improvement_over_persistence_fraction") is not None
            and combined["mae_improvement_over_persistence_fraction"]
            >= rules.minimum_mae_improvement_over_persistence_fraction
        ),
        "positive_direction_met": (
            combined.get("positive_direction_fraction") is not None
            and combined["positive_direction_fraction"]
            >= rules.minimum_positive_direction_fraction
        ),
        "gain_stability_met": all(
            relative_gain_shift[bank] is not None
            and relative_gain_shift[bank] <= rules.maximum_gain_relative_shift
            for bank in ("medium", "high")
        ),
    }
    passed = all(eligibility.values()) and all(screens.values())
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_recharge_pressure_forecast_holdout",
        "evidence_role": "same_site_short_horizon_station_pressure_response",
        "source_identifiers_published": False,
        "source_paths_published": False,
        "source_filenames_published": False,
        "source_headers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "calendar_dates_published": False,
        "tag_names_published": False,
        "manufacturer_or_model_published": False,
        "sampled_rows": sampled_rows,
        "files_read": len(observations),
        "usable_files": usable_files,
        "files_with_calibration_cases": files_with_calibration_cases,
        "files_with_holdout_cases": files_with_holdout_cases,
        "channel_attestation": {
            "pressure_role_and_unit_semantics_attested": True,
            "compressor_state_semantics_attested": True,
            "temperature_semantics_used": False,
            "mass_flow_semantics_used": False,
            "valve_state_semantics_used": False,
        },
        "rules": {
            key: value for key, value in rules.__dict__.items()
        },
        "calibration": {
            "case_count": len(calibration_cases),
            "fitted_continuation_gain_by_bank": {
                bank: _rounded(value) for bank, value in gains.items()
            },
            "by_bank": calibration_by_bank,
        },
        "holdout": {
            "case_count": len(holdout_cases),
            "combined": combined,
            "by_bank": holdout_by_bank,
            "oracle_gain_by_bank_diagnostic_only": {
                bank: _rounded(value) for bank, value in holdout_oracle_gains.items()
            },
            "relative_gain_shift_by_bank": relative_gain_shift,
        },
        "eligibility": eligibility,
        "screens": screens,
        "decision": {
            "short_horizon_station_pressure_forecast_supported": passed,
            "runtime_parameter_application": False,
            "default_model_parameters_changed": False,
            "compressor_capacity_validated": False,
            "storage_geometry_validated": False,
            "vehicle_fill_validation": False,
            "full_loop_holdout_eligible": False,
            "independent_external_validation": False,
        },
        "claim_boundary": (
            "Same-site short-horizon medium/high storage pressure-response holdout "
            "using a causal 10 s prefix and a 30 s forecast. It is a de-identified "
            "station-side empirical surrogate, not a compressor-capacity or vessel-"
            "geometry fit, vehicle-fill validation, safety limit, accident-frequency "
            "estimate, independent-site validation, or field certification."
        ),
    }


__all__ = ["RechargeForecastRules", "validate_recharge_pressure_forecast"]
