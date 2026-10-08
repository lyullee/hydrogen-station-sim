"""Privacy-bounded recharge-flow screening for controlled station logs.

The audit consumes an external, owner-controlled tag mapping in memory.  Its
serialized result contains no source path, filename, tag, timestamp, or raw
row.  Totalizer engineering units remain a hypothesis until a custodian
attests them, so the comparison cannot update runtime parameters by itself.
"""

from __future__ import annotations

import math
from pathlib import Path
from statistics import median
from typing import Mapping

import numpy as np

from .confidential_signal_consistency import (
    _compare_pair,
    _finite,
    _indices,
    _iter_rows,
    _monotonic_fraction,
    _parse_time,
    _variable,
    _FLOW_TAG,
    _FLOW_TERMS,
)
from .tabulated import PropsSI


_REFERENCE_SUCTION_PRESSURE_PA = 20.0e6
_REFERENCE_SUCTION_TEMPERATURE_K = 298.15
_REFERENCE_SWEPT_VOLUME_RATE_M3_S = 8.0e-4
_REFERENCE_VOLUMETRIC_EFFICIENCY = 0.75


def _summary(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {
        "median": float(np.median(array)),
        "p10": float(np.quantile(array, 0.10)),
        "p90": float(np.quantile(array, 0.90)),
        "mean": float(np.mean(array)),
    }


def _mapped_tags(mapping: Mapping[str, object]) -> tuple[tuple[str, ...], str]:
    pressure_entries = mapping.get("pressure_columns") or []
    state_entries = mapping.get("state_columns") or []
    pressure_tags = tuple(
        str(entry[1]) for entry in pressure_entries
        if isinstance(entry, (list, tuple)) and len(entry) >= 2
    )
    load_tags = [
        str(entry[1]) for entry in state_entries
        if isinstance(entry, (list, tuple))
        and len(entry) >= 2
        and str(entry[0]) == "compressor_load"
    ]
    if not pressure_tags or len(load_tags) != 1:
        raise ValueError(
            "mapping requires pressure_columns and one compressor_load state"
        )
    return pressure_tags, load_tags[0]


def _reference_initial_flow_g_s() -> tuple[float, float]:
    density = float(
        PropsSI(
            "Dmass",
            "P",
            _REFERENCE_SUCTION_PRESSURE_PA,
            "T",
            _REFERENCE_SUCTION_TEMPERATURE_K,
            "Hydrogen",
        )
    )
    flow_g_s = (
        density
        * _REFERENCE_SWEPT_VOLUME_RATE_M3_S
        * _REFERENCE_VOLUMETRIC_EFFICIENCY
        * 1000.0
    )
    return density, flow_g_s


def audit_confidential_recharge_flow(
    root: Path,
    mapping: Mapping[str, object],
    *,
    max_rows_per_file: int = 200_000,
    minimum_event_duration_s: float = 10.0,
    minimum_compressor_load_fraction: float = 0.80,
) -> dict[str, object]:
    """Screen compressor-on flow episodes and return aggregate evidence only."""

    if (
        max_rows_per_file < 100
        or minimum_event_duration_s <= 0.0
        or not 0.0 <= minimum_compressor_load_fraction <= 1.0
    ):
        raise ValueError("invalid audit limits")
    pressure_tags, load_tag = _mapped_tags(mapping)
    files = sorted(path for path in root.rglob("*.csv") if path.is_file())
    eligible_tables = 0
    sampled_rows = 0
    durations: list[float] = []
    totalizer_deltas: list[float] = []
    closure_ratios: list[float] = []
    conditional_flows_g_s: list[float] = []
    all_event_load_fractions: list[float] = []
    all_flow_episode_count = 0
    selected_scales: list[float] = []
    selected_windows: list[float] = []
    valve_modes: set[tuple[int, ...]] = set()
    valve_mode_counts: dict[tuple[int, ...], int] = {}

    for path in files:
        streamed = _iter_rows(path)
        try:
            header, rows = next(streamed)
        except StopIteration:
            continue
        try:
            if any(tag not in header for tag in pressure_tags) or load_tag not in header:
                continue
            time_indices = tuple(
                index for index, value in enumerate(header)
                if any(term in value.strip().casefold() for term in (
                    "time", "date", "timestamp", "clock", "local", "시간", "일시", "시각"
                ))
            )
            time_index = time_indices[0] if time_indices else 0
            pressure_indices = tuple(header.index(tag) for tag in pressure_tags)
            load_index = header.index(load_tag)
            flow_indices = _indices(header, _FLOW_TERMS, _FLOW_TAG)
            valve_indices = tuple(
                index for index, value in enumerate(header)
                if "status" in value.casefold() and "xv" in value.casefold()
            )
            if len(flow_indices) < 2:
                continue
            maximum = max(
                time_index, load_index, *pressure_indices, *flow_indices,
                *(valve_indices or (0,)),
            )
            times: list[float] = []
            flows: list[list[float]] = [[] for _ in flow_indices]
            loads: list[float] = []
            valves: list[list[float]] = [[] for _ in valve_indices]
            for row in rows:
                if len(times) >= max_rows_per_file:
                    break
                if len(row) <= maximum:
                    continue
                timestamp = _parse_time(row[time_index])
                flow_values = [_finite(row[index]) for index in flow_indices]
                load = _finite(row[load_index])
                valve_values = [_finite(row[index]) for index in valve_indices]
                if timestamp is None or load is None:
                    continue
                times.append(timestamp)
                loads.append(load)
                for target, value in zip(flows, flow_values):
                    target.append(float("nan") if value is None else value)
                for target, value in zip(valves, valve_values):
                    target.append(float("nan") if value is None else value)
            if len(times) < 40:
                continue
            order = np.argsort(np.asarray(times, dtype=float), kind="stable")
            time = np.asarray(times, dtype=float)[order]
            flow_arrays = tuple(np.asarray(values, dtype=float)[order] for values in flows)
            load_array = np.asarray(loads, dtype=float)[order]
            valve_arrays = tuple(np.asarray(values, dtype=float)[order] for values in valves)
            variable = tuple(values for values in flow_arrays if _variable(values))
            cumulative = tuple(
                values for values in variable if _monotonic_fraction(values) >= 0.995
            )
            instantaneous = tuple(
                values for values in variable if _monotonic_fraction(values) < 0.995
            )
            candidates = []
            for totalizer in cumulative:
                for signal in instantaneous:
                    result = _compare_pair(time, totalizer, signal)
                    if result is not None and result.strong:
                        candidates.append((result, totalizer, signal))
            if not candidates:
                continue
            result, totalizer, signal = min(
                candidates,
                key=lambda item: (
                    item[0].normalized_rmse_percent,
                    -item[0].correlation,
                ),
            )
            eligible_tables += 1
            sampled_rows += len(time)
            selected_scales.append(result.scale)
            selected_windows.append(result.aggregation_window_seconds)
            finite_signal = signal[np.isfinite(signal)]
            threshold = max(
                float(np.nanpercentile(np.abs(finite_signal), 20)), 1.0e-12
            )
            active = np.isfinite(signal) & (signal > threshold)
            positive_steps = np.diff(time)
            base_step = float(np.median(positive_steps[positive_steps > 0.0]))
            start: int | None = None
            for index, is_active in enumerate(active):
                contiguous = (
                    index > 0
                    and active[index - 1]
                    and 0.0 < time[index] - time[index - 1] <= 1.5 * base_step
                )
                if is_active and start is None:
                    start = index
                if start is None:
                    continue
                at_end = index == len(active) - 1
                next_breaks = (
                    not at_end
                    and (
                        not active[index + 1]
                        or not 0.0 < time[index + 1] - time[index] <= 1.5 * base_step
                    )
                )
                if not is_active or (not at_end and not next_breaks):
                    continue
                end = index if is_active else index - 1
                elapsed = float(time[end] - time[start])
                delta = float(totalizer[end] - totalizer[start])
                if elapsed >= minimum_event_duration_s and delta > 0.0:
                    load_fraction = float(
                        np.mean(load_array[start : end + 1] > 0.5)
                    )
                    all_flow_episode_count += 1
                    all_event_load_fractions.append(load_fraction)
                    if load_fraction < minimum_compressor_load_fraction:
                        start = None
                        continue
                    predicted_delta = float(
                        np.trapezoid(signal[start : end + 1], time[start : end + 1])
                        * result.scale
                    )
                    durations.append(elapsed)
                    totalizer_deltas.append(delta)
                    closure_ratios.append(predicted_delta / delta)
                    conditional_flows_g_s.append(delta / elapsed * 1000.0)
                    if valve_arrays:
                        signature = tuple(
                            int(np.nanmean(values[start : end + 1]) >= 0.5)
                            for values in valve_arrays
                        )
                        valve_modes.add(signature)
                        valve_mode_counts[signature] = valve_mode_counts.get(signature, 0) + 1
                start = None
        finally:
            streamed.close()

    density, reference_flow_g_s = _reference_initial_flow_g_s()
    conditional_flow_summary = _summary(conditional_flows_g_s)
    within_range = bool(
        conditional_flow_summary
        and conditional_flow_summary["p10"] <= reference_flow_g_s
        <= conditional_flow_summary["p90"]
    )
    relative_to_median = (
        100.0 * (reference_flow_g_s / conditional_flow_summary["median"] - 1.0)
        if conditional_flow_summary else None
    )
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_recharge_flow_screen",
        "analysis_status": "post_access_conditional_internal_diagnostic",
        "evidence_scope": "owner_controlled_confidential_station_side_archive",
        "privacy": {
            "source_identifiers_published": False,
            "source_paths_published": False,
            "filenames_published": False,
            "tag_names_published": False,
            "raw_rows_persisted": False,
            "exact_timestamps_published": False,
            "manufacturer_or_model_published": False,
        },
        "screen": {
            "csv_files_discovered": len(files),
            "eligible_equipment_tables": eligible_tables,
            "sampled_rows": sampled_rows,
            "all_eligible_flow_episodes": all_flow_episode_count,
            "eligible_recharge_episodes": len(durations),
            "recharge_selection": {
                "minimum_duration_s": minimum_event_duration_s,
                "minimum_compressor_load_fraction": (
                    minimum_compressor_load_fraction
                ),
            },
            "anonymous_valve_mode_count": len(valve_modes),
            "anonymous_valve_mode_episode_counts_descending": sorted(
                valve_mode_counts.values(), reverse=True
            ),
            "duration_s": _summary(durations),
            "totalizer_delta_source_units": _summary(totalizer_deltas),
            "integrated_signal_to_totalizer_ratio": _summary(closure_ratios),
            "conditional_average_mass_flow_g_s_if_totalizer_unit_is_kg": (
                conditional_flow_summary
            ),
            "all_flow_episode_compressor_load_fraction": _summary(
                all_event_load_fractions
            ),
            "derivative_to_signal_scale": _summary(selected_scales),
            "aggregation_window_seconds": _summary(selected_windows),
        },
        "reference_model": {
            "suction_pressure_mpa_abs": _REFERENCE_SUCTION_PRESSURE_PA / 1.0e6,
            "suction_temperature_k": _REFERENCE_SUCTION_TEMPERATURE_K,
            "hydrogen_density_kg_m3": density,
            "swept_volume_rate_m3_s": _REFERENCE_SWEPT_VOLUME_RATE_M3_S,
            "volumetric_efficiency": _REFERENCE_VOLUMETRIC_EFFICIENCY,
            "predicted_initial_mass_flow_g_s": reference_flow_g_s,
            "inside_conditional_observed_p10_p90": within_range,
            "relative_to_conditional_observed_median_percent": relative_to_median,
        },
        "attestation": {
            "flow_channel_roles_attested": False,
            "instantaneous_flow_units_attested": False,
            "totalizer_units_attested": False,
            "calibration_status_attested": False,
        },
        "eligibility": {
            "conditional_reference_compressor_flow_consistency_supported": within_range,
            "runtime_parameter_update_permitted": False,
            "absolute_compressor_capacity_validation": False,
            "vehicle_fill_validation": False,
            "full_station_vehicle_validation": False,
            "independent_holdout": False,
        },
        "next_action": (
            "Obtain custodian attestation for the generic instantaneous/totalizer "
            "roles, units, reset/sign convention and calibration status before using "
            "the conditional mass-flow values to fit compressor capacity."
        ),
        "claim_boundary": (
            "Post-access station-side recharge diagnostic only. The conditional mass-flow "
            "comparison assumes the cumulative channel unit is kg and cannot validate a "
            "vehicle fill, safety limit, consequence distance or complete station loop."
        ),
    }
