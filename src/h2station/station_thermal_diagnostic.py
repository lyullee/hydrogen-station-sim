"""Privacy-bounded compressor/cooler thermal operating diagnostic.

The diagnostic reads owner-controlled rows in memory and exports only
component-level aggregates.  It requires explicit temperature-role/unit and
state-value attestations; it does not guess that a binary logger value means a
cooling system is running.  A chronological suffix checks envelope stability,
but remains a within-record diagnostic rather than external validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping

from .controlled_station_replay import TraceMapping, _finite, _quantile, _sampled_rows


_COMPONENTS = {"compressor", "cooler_inlet", "cooler_outlet"}


def _state(value: object) -> str:
    return str(value or "").strip().casefold()


def _rounded(value: float | None) -> float | None:
    return round(float(value), 6) if value is not None and math.isfinite(value) else None


def _stats(values: list[float]) -> dict[str, float | int | None]:
    ordered = sorted(value for value in values if math.isfinite(value))
    return {
        "count": len(ordered),
        "p05": _rounded(_quantile(ordered, 0.05)),
        "median": _rounded(median(ordered) if ordered else None),
        "p95": _rounded(_quantile(ordered, 0.95)),
    }


@dataclass(frozen=True)
class ComponentTemperatureSummary:
    component: str
    overall_deg_c: Mapping[str, float | int | None]
    cooling_active_deg_c: Mapping[str, float | int | None]
    cooling_inactive_deg_c: Mapping[str, float | int | None]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "overall_degC": dict(self.overall_deg_c),
            "cooling_active_degC": dict(self.cooling_active_deg_c),
            "cooling_inactive_degC": dict(self.cooling_inactive_deg_c),
        }


@dataclass(frozen=True)
class StationThermalDiagnosticSummary:
    files_read: int
    sampled_rows: int
    median_sample_period_s: float | None
    cooling_state_transition_count: int
    cooling_active_duty_cycle: float
    component_temperatures: tuple[ComponentTemperatureSummary, ...]
    cooler_temperature_drop_active_deg_c: Mapping[str, float | int | None]
    cooler_temperature_drop_inactive_deg_c: Mapping[str, float | int | None]
    quality_warnings: tuple[str, ...]

    def to_public_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "raw_rows_persisted": False,
            "source_identifiers_published": False,
            "absolute_timestamps_published": False,
            "files_read": self.files_read,
            "sampled_rows": self.sampled_rows,
            "median_sample_period_s": _rounded(self.median_sample_period_s),
            "cooling_state_transition_count": self.cooling_state_transition_count,
            "cooling_active_duty_cycle": round(self.cooling_active_duty_cycle, 6),
            "component_temperatures": [
                item.to_public_dict() for item in self.component_temperatures
            ],
            "cooler_temperature_drop_active_degC": dict(
                self.cooler_temperature_drop_active_deg_c
            ),
            "cooler_temperature_drop_inactive_degC": dict(
                self.cooler_temperature_drop_inactive_deg_c
            ),
            "quality_warnings": list(self.quality_warnings),
            "claim_boundary": (
                "Owner-attested station-side compressor/cooler operating envelope "
                "only. It is not a vehicle-fill thermal validation, compressor-capacity "
                "fit, safety limit or field-safety certification."
            ),
        }


@dataclass(frozen=True)
class StationThermalStabilityResult:
    calibration_fraction: float
    calibration: StationThermalDiagnosticSummary
    holdout: StationThermalDiagnosticSummary
    component_medians_inside_calibration_p05_p95: Mapping[str, bool]
    cooler_active_drop_median_inside_calibration_p05_p95: bool
    minimum_holdout_rows_met: bool
    stability_supported: bool

    def to_public_dict(self) -> dict[str, object]:
        return {
            "method": "chronological_within_trace_envelope_stability",
            "calibration_fraction": round(self.calibration_fraction, 6),
            "calibration": self.calibration.to_public_dict(),
            "holdout": self.holdout.to_public_dict(),
            "component_medians_inside_calibration_p05_p95": dict(
                self.component_medians_inside_calibration_p05_p95
            ),
            "cooler_active_drop_median_inside_calibration_p05_p95": (
                self.cooler_active_drop_median_inside_calibration_p05_p95
            ),
            "minimum_holdout_rows_met": self.minimum_holdout_rows_met,
            "stability_supported": self.stability_supported,
            "claim_boundary": (
                "Within-record chronological stability diagnostic only; it is not an "
                "independent or prospective validation result."
            ),
        }


def _validated_roles(
    mapping: TraceMapping,
    component_by_temperature_role: Mapping[str, str],
) -> tuple[tuple[str, str, str], ...]:
    columns = dict(mapping.temperature_columns)
    if set(component_by_temperature_role.values()) != _COMPONENTS:
        raise ValueError("component mapping must contain compressor, cooler_inlet and cooler_outlet")
    if len(component_by_temperature_role) != 3:
        raise ValueError("each thermal component must be mapped exactly once")
    rows = []
    for role, component in component_by_temperature_role.items():
        if role not in columns:
            raise ValueError("every component role must reference a mapped temperature role")
        rows.append((str(role), str(component), columns[role]))
    return tuple(rows)


def _observations(
    input_path: Path,
    mapping: TraceMapping,
    *,
    component_roles: tuple[tuple[str, str, str], ...],
    cooling_state_role: str,
    cooling_active_values: set[str],
    stride: int,
    max_rows_per_file: int | None,
) -> dict[Path, list[tuple[float, bool, dict[str, float]]]]:
    state_column = dict(mapping.state_columns)[cooling_state_role]
    grouped: dict[Path, list[tuple[float, bool, dict[str, float]]]] = {}
    for path, time_s, row in _sampled_rows(
        input_path, mapping, stride=stride, max_rows_per_file=max_rows_per_file
    ):
        values: dict[str, float] = {}
        for _, component, column in component_roles:
            value = _finite(row.get(column))
            if value is not None:
                temperature_k = (
                    value * mapping.temperature_scale_k_per_unit
                    + mapping.temperature_offset_k
                )
                if math.isfinite(temperature_k) and temperature_k > 0.0:
                    values[component] = temperature_k - 273.15
        if values:
            grouped.setdefault(path, []).append(
                (
                    float(time_s),
                    _state(row.get(state_column)) in cooling_active_values,
                    values,
                )
            )
    return grouped


def _summarize(
    observations: Mapping[Path, list[tuple[float, bool, dict[str, float]]]],
) -> StationThermalDiagnosticSummary:
    if not observations:
        raise ValueError("no finite thermal observations matched the mapping")
    overall = {component: [] for component in sorted(_COMPONENTS)}
    active_values = {component: [] for component in sorted(_COMPONENTS)}
    inactive_values = {component: [] for component in sorted(_COMPONENTS)}
    active_drop: list[float] = []
    inactive_drop: list[float] = []
    intervals: list[float] = []
    active_seconds = 0.0
    total_seconds = 0.0
    transitions = 0
    sampled_rows = 0
    warnings: set[str] = set()
    for rows in observations.values():
        rows = sorted(rows, key=lambda item: item[0])
        sampled_rows += len(rows)
        for _, active, values in rows:
            for component, value in values.items():
                overall[component].append(value)
                (active_values if active else inactive_values)[component].append(value)
            if "cooler_inlet" in values and "cooler_outlet" in values:
                drop = values["cooler_inlet"] - values["cooler_outlet"]
                (active_drop if active else inactive_drop).append(drop)
        for before, after in zip(rows, rows[1:]):
            dt = after[0] - before[0]
            if dt <= 0.0:
                warnings.add("nonmonotonic_or_duplicate_time")
                continue
            intervals.append(dt)
            total_seconds += dt
            if before[1]:
                active_seconds += dt
            if before[1] != after[1]:
                transitions += 1
    if total_seconds <= 0.0:
        raise ValueError("thermal trace contains no positive time intervals")
    if not active_drop:
        warnings.add("no_cooling_active_temperature_pairs")
    if not inactive_drop:
        warnings.add("no_cooling_inactive_temperature_pairs")
    summaries = tuple(
        ComponentTemperatureSummary(
            component=component,
            overall_deg_c=_stats(overall[component]),
            cooling_active_deg_c=_stats(active_values[component]),
            cooling_inactive_deg_c=_stats(inactive_values[component]),
        )
        for component in sorted(_COMPONENTS)
    )
    return StationThermalDiagnosticSummary(
        files_read=len(observations),
        sampled_rows=sampled_rows,
        median_sample_period_s=median(intervals) if intervals else None,
        cooling_state_transition_count=transitions,
        cooling_active_duty_cycle=active_seconds / total_seconds,
        component_temperatures=summaries,
        cooler_temperature_drop_active_deg_c=_stats(active_drop),
        cooler_temperature_drop_inactive_deg_c=_stats(inactive_drop),
        quality_warnings=tuple(sorted(warnings)),
    )


def summarize_station_thermal_dynamics(
    input_path: Path,
    mapping: TraceMapping,
    *,
    cooling_state_role: str,
    cooling_active_state_values: Iterable[str],
    component_by_temperature_role: Mapping[str, str],
    temperature_semantics_attested: bool,
    state_semantics_attested: bool,
    stride: int = 1,
    max_rows_per_file: int | None = 250_000,
) -> StationThermalDiagnosticSummary:
    if not temperature_semantics_attested:
        raise ValueError("temperature role/unit attestation is required")
    if not state_semantics_attested:
        raise ValueError("cooling-state semantics attestation is required")
    if stride < 1:
        raise ValueError("stride must be at least one")
    if cooling_state_role not in dict(mapping.state_columns):
        raise ValueError("cooling_state_role must be present in mapping.state_columns")
    active = {_state(value) for value in cooling_active_state_values if _state(value)}
    if not active:
        raise ValueError("at least one active cooling-state value is required")
    roles = _validated_roles(mapping, component_by_temperature_role)
    return _summarize(
        _observations(
            input_path,
            mapping,
            component_roles=roles,
            cooling_state_role=cooling_state_role,
            cooling_active_values=active,
            stride=stride,
            max_rows_per_file=max_rows_per_file,
        )
    )


def validate_station_thermal_temporal_stability(
    input_path: Path,
    mapping: TraceMapping,
    *,
    cooling_state_role: str,
    cooling_active_state_values: Iterable[str],
    component_by_temperature_role: Mapping[str, str],
    temperature_semantics_attested: bool,
    state_semantics_attested: bool,
    calibration_fraction: float = 0.70,
    minimum_holdout_rows: int = 100,
    stride: int = 1,
    max_rows_per_file: int | None = 250_000,
) -> StationThermalStabilityResult:
    if not 0.50 <= calibration_fraction < 0.90:
        raise ValueError("calibration_fraction must be in [0.50, 0.90)")
    if minimum_holdout_rows < 1:
        raise ValueError("minimum_holdout_rows must be positive")
    if not temperature_semantics_attested:
        raise ValueError("temperature role/unit attestation is required")
    if not state_semantics_attested:
        raise ValueError("cooling-state semantics attestation is required")
    if cooling_state_role not in dict(mapping.state_columns):
        raise ValueError("cooling_state_role must be present in mapping.state_columns")
    active = {_state(value) for value in cooling_active_state_values if _state(value)}
    if not active:
        raise ValueError("at least one active cooling-state value is required")
    roles = _validated_roles(mapping, component_by_temperature_role)
    source = _observations(
        input_path,
        mapping,
        component_roles=roles,
        cooling_state_role=cooling_state_role,
        cooling_active_values=active,
        stride=stride,
        max_rows_per_file=max_rows_per_file,
    )
    return _temporal_stability_result(
        source,
        calibration_fraction=calibration_fraction,
        minimum_holdout_rows=minimum_holdout_rows,
    )


def _temporal_stability_result(
    source: Mapping[Path, list[tuple[float, bool, dict[str, float]]]],
    *,
    calibration_fraction: float,
    minimum_holdout_rows: int,
) -> StationThermalStabilityResult:
    calibration_rows: dict[Path, list[tuple[float, bool, dict[str, float]]]] = {}
    holdout_rows: dict[Path, list[tuple[float, bool, dict[str, float]]]] = {}
    for path, rows in source.items():
        ordered = sorted(rows, key=lambda item: item[0])
        split = int(len(ordered) * calibration_fraction)
        if split < 2 or len(ordered) - split < 2:
            continue
        calibration_rows[path] = ordered[:split]
        holdout_rows[path] = ordered[split:]
    calibration = _summarize(calibration_rows)
    holdout = _summarize(holdout_rows)
    calibration_by_component = {
        item.component: item for item in calibration.component_temperatures
    }
    holdout_by_component = {item.component: item for item in holdout.component_temperatures}
    median_checks: dict[str, bool] = {}
    for component in sorted(_COMPONENTS):
        bounds = calibration_by_component[component].overall_deg_c
        value = holdout_by_component[component].overall_deg_c["median"]
        median_checks[component] = bool(
            value is not None
            and bounds["p05"] is not None
            and bounds["p95"] is not None
            and float(bounds["p05"]) <= float(value) <= float(bounds["p95"])
        )
    drop_bounds = calibration.cooler_temperature_drop_active_deg_c
    drop_value = holdout.cooler_temperature_drop_active_deg_c["median"]
    drop_check = bool(
        drop_value is not None
        and drop_bounds["p05"] is not None
        and drop_bounds["p95"] is not None
        and float(drop_bounds["p05"]) <= float(drop_value) <= float(drop_bounds["p95"])
    )
    rows_met = holdout.sampled_rows >= minimum_holdout_rows
    supported = bool(
        rows_met
        and all(median_checks.values())
        and drop_check
        and not calibration.quality_warnings
        and not holdout.quality_warnings
    )
    return StationThermalStabilityResult(
        calibration_fraction=calibration_fraction,
        calibration=calibration,
        holdout=holdout,
        component_medians_inside_calibration_p05_p95=median_checks,
        cooler_active_drop_median_inside_calibration_p05_p95=drop_check,
        minimum_holdout_rows_met=rows_met,
        stability_supported=supported,
    )


def diagnose_unattested_station_thermal_stability(
    input_path: Path,
    mapping: TraceMapping,
    *,
    cooling_state_role: str,
    cooling_active_state_values: Iterable[str],
    component_by_temperature_role: Mapping[str, str],
    calibration_fraction: float = 0.70,
    minimum_holdout_rows: int = 100,
    stride: int = 1,
    max_rows_per_file: int | None = 250_000,
) -> dict[str, object]:
    """Run the frozen method while retaining an explicit semantics hold.

    This path exists for post-access diagnostics when a proposed external
    mapping is available but the custodian has not attested channel roles,
    units, state values, or calibration.  It can establish numerical
    stability of the hypothesis only and never promotes runtime parameters.
    """

    if not 0.50 <= calibration_fraction < 0.90:
        raise ValueError("calibration_fraction must be in [0.50, 0.90)")
    if minimum_holdout_rows < 1:
        raise ValueError("minimum_holdout_rows must be positive")
    if stride < 1:
        raise ValueError("stride must be at least one")
    if cooling_state_role not in dict(mapping.state_columns):
        raise ValueError("cooling_state_role must be present in mapping.state_columns")
    active = {_state(value) for value in cooling_active_state_values if _state(value)}
    if not active:
        raise ValueError("at least one active cooling-state value is required")
    roles = _validated_roles(mapping, component_by_temperature_role)
    result = _temporal_stability_result(
        _observations(
            input_path,
            mapping,
            component_roles=roles,
            cooling_state_role=cooling_state_role,
            cooling_active_values=active,
            stride=stride,
            max_rows_per_file=max_rows_per_file,
        ),
        calibration_fraction=calibration_fraction,
        minimum_holdout_rows=minimum_holdout_rows,
    )
    temporal = result.to_public_dict()
    temporal["claim_boundary"] = (
        "Within-record stability of an unattested mapping hypothesis only; "
        "it is not an independent, attested, or runtime validation result."
    )
    for partition in ("calibration", "holdout"):
        temporal[partition]["claim_boundary"] = (
            "Unattested station-side thermal hypothesis only. Channel roles, "
            "units, state semantics and calibration remain unconfirmed."
        )
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_thermal_hypothesis_diagnostic",
        "status": "completed_unattested_post_access_diagnostic",
        "analysis_method": "frozen_chronological_prefix_suffix_envelope",
        "privacy": {
            "source_identifiers_published": False,
            "source_paths_published": False,
            "filenames_published": False,
            "tag_names_published": False,
            "raw_rows_persisted": False,
            "exact_timestamps_published": False,
            "manufacturer_or_model_published": False,
        },
        "mapping_semantics": {
            "temperature_roles_and_units_attested": False,
            "cooling_state_value_semantics_attested": False,
            "calibration_or_quality_metadata_attested": False,
            "mapping_is_hypothesis": True,
        },
        "temporal_stability": temporal,
        "eligibility": {
            "conditional_within_record_stability_observed": result.stability_supported,
            "station_component_thermal_envelope_supported": False,
            "runtime_parameter_application": False,
            "vehicle_fill_thermal_validation": False,
            "full_station_vehicle_validation": False,
            "full_loop_holdout_eligible": False,
            "independent_holdout": False,
            "default_model_parameters_changed": False,
        },
        "next_action": (
            "A data custodian must attest the generic temperature roles and units, "
            "cooling-state value semantics and calibration/quality metadata before "
            "this result can support a station component thermal envelope."
        ),
        "claim_boundary": (
            "Frozen-method numerical diagnostic of an unattested station-side mapping "
            "only. It cannot validate vehicle filling, precooler capacity, a safety "
            "limit, consequence distance, or the complete station loop."
        ),
    }


__all__ = [
    "ComponentTemperatureSummary",
    "StationThermalDiagnosticSummary",
    "StationThermalStabilityResult",
    "diagnose_unattested_station_thermal_stability",
    "summarize_station_thermal_dynamics",
    "validate_station_thermal_temporal_stability",
]
