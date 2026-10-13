"""Compare MC tank states with the measured thermocouple envelope.

The public MC Default workbooks expose two or three independent in-tank
temperature channels per case.  Historical validation reduced those channels
to one mean trace before comparing it with the uniform-gas model state.  This
post-outcome diagnostic keeps the already defined leave-one-case-out geometry
rule and asks a narrower question: do the gas, liner, shell, or fixed
liner/shell-mean states lie inside the simultaneous measured sensor range?

No observation operator is selected, no thermal parameter is fitted, and no
raw measurement row is written to the output.  The result is development
evidence only and cannot promote a validation or runtime gate.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

from h2station.public_validation import H2ProtocolTrace, iter_mc_default_traces
from h2station.vehicle import CompositeTankFitParameters

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_mc_capacity_geometry_leave_one_out import (  # noqa: E402
    DEFAULT_PROCESSED,
    DEFAULT_PROTOCOL,
    _display,
    _git_commit,
    _inferred_volume_ratio,
    _read_csv,
    _sha256,
)
from run_mc_temperature_observation_diagnostic import (  # noqa: E402
    TEMPERATURE_OBSERVATIONS,
    _replay_case,
    _thermal_observations,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / (
    "data/public_validation/raw/h2protocol_mc_default/"
    "SAE J2601 MC Default Bench Test Data.zip"
)
DEFAULT_OUTPUT = (
    ROOT / "research/mc_temperature_sensor_envelope_2026_10_14.json"
)
DEFAULT_REPORT = (
    ROOT / "research/MC_TEMPERATURE_SENSOR_ENVELOPE_2026_10_14.md"
)


def _is_independent_temperature_channel(name: str) -> bool:
    lowered = name.casefold()
    return "_ave" not in lowered and "_avg" not in lowered


def _sensor_stack(trace: H2ProtocolTrace) -> np.ndarray:
    channels = [
        np.asarray(values, dtype=float)
        for name, values in trace.tank_temperature_channels_c
        if _is_independent_temperature_channel(name)
    ]
    if not channels:
        raise ValueError(f"{trace.case_id}: no independent temperature channel")
    stack = np.vstack(channels)
    if stack.shape[1] != len(trace.time_s) or not np.all(np.isfinite(stack)):
        raise ValueError(f"{trace.case_id}: invalid temperature-channel matrix")
    return stack


def sensor_envelope_metrics(
    prediction_c: np.ndarray,
    sensor_stack_c: np.ndarray,
) -> dict[str, float | int]:
    """Score a state against a simultaneous multi-sensor interval."""

    prediction = np.asarray(prediction_c, dtype=float)
    sensors = np.asarray(sensor_stack_c, dtype=float)
    if sensors.ndim != 2 or sensors.shape[1] != len(prediction):
        raise ValueError("sensor matrix must be channels by prediction samples")
    if len(prediction) < 2 or not np.all(np.isfinite(prediction)):
        raise ValueError("prediction requires at least two finite samples")
    if sensors.shape[0] < 1 or not np.all(np.isfinite(sensors)):
        raise ValueError("at least one finite sensor channel is required")

    lower = np.min(sensors, axis=0)
    upper = np.max(sensors, axis=0)
    observed_mean = np.mean(sensors, axis=0)
    below = np.maximum(lower - prediction, 0.0)
    above = np.maximum(prediction - upper, 0.0)
    outside_distance = below + above
    mean_error = prediction - observed_mean
    inside = outside_distance == 0.0
    spread = upper - lower
    return {
        "sample_count": int(len(prediction)),
        "sensor_channel_count": int(sensors.shape[0]),
        "mean_trace_rmse_c": float(np.sqrt(np.mean(np.square(mean_error)))),
        "mean_trace_mae_c": float(np.mean(np.abs(mean_error))),
        "envelope_rmse_c": float(
            np.sqrt(np.mean(np.square(outside_distance)))
        ),
        "envelope_mae_c": float(np.mean(outside_distance)),
        "envelope_peak_outside_distance_c": float(np.max(outside_distance)),
        "inside_envelope_fraction": float(np.mean(inside)),
        "sensor_spread_mean_c": float(np.mean(spread)),
        "sensor_spread_p95_c": float(np.percentile(spread, 95)),
        "sensor_spread_peak_c": float(np.max(spread)),
    }


def _mean(cases: list[dict[str, Any]], operator: str, metric: str) -> float:
    return float(
        np.mean(
            [case["temperature_states"][operator][metric] for case in cases]
        )
    )


def _aggregate(cases: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for operator in TEMPERATURE_OBSERVATIONS:
        samples = sum(
            int(case["temperature_states"][operator]["sample_count"])
            for case in cases
        )
        inside = sum(
            float(case["temperature_states"][operator]["inside_envelope_fraction"])
            * int(case["temperature_states"][operator]["sample_count"])
            for case in cases
        )
        mean_rmse = _mean(cases, operator, "mean_trace_rmse_c")
        envelope_rmse = _mean(cases, operator, "envelope_rmse_c")
        result[operator] = {
            "case_count": len(cases),
            "sample_count": samples,
            "mean_trace_rmse_c_case_mean": mean_rmse,
            "envelope_rmse_c_case_mean": envelope_rmse,
            "envelope_mae_c_case_mean": _mean(
                cases, operator, "envelope_mae_c"
            ),
            "inside_envelope_fraction_case_mean": _mean(
                cases, operator, "inside_envelope_fraction"
            ),
            "inside_envelope_fraction_pooled": inside / samples,
            "case_count_envelope_rmse_le_10c": sum(
                float(case["temperature_states"][operator]["envelope_rmse_c"])
                <= 10.0
                for case in cases
            ),
            "mean_to_envelope_rmse_reduction_percent": (
                100.0 * (mean_rmse - envelope_rmse) / mean_rmse
                if mean_rmse > 0.0
                else 0.0
            ),
        }
    return result


def build_report(
    archive: Path = DEFAULT_ARCHIVE,
    processed: Path = DEFAULT_PROCESSED,
    protocol_path: Path = DEFAULT_PROTOCOL,
) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    selected = list(protocol["selected_workbooks"])
    if len(selected) != 8 or len(set(selected)) != 8:
        raise ValueError("MC sensor-envelope diagnostic requires eight unique cases")
    expected_archive_hash = str(protocol["source"]["archive_sha256"])
    archive_hash = _sha256(archive)
    if archive_hash != expected_archive_hash:
        raise ValueError("MC source archive checksum does not match frozen protocol")

    summaries = {
        row["source_member"]: row
        for row in _read_csv(processed / "mc_default_cases.csv")
    }
    processed_rows: dict[str, list[dict[str, str]]] = {}
    volume_diagnostics: dict[str, dict[str, float]] = {}
    for member in selected:
        summary = summaries[member]
        rows = _read_csv(
            processed / "mc_default_traces" / f"{summary['case_id']}.csv"
        )
        processed_rows[member] = rows
        volume_diagnostics[member] = _inferred_volume_ratio(summary, rows)

    source_traces = {
        trace.source_member: trace
        for trace in iter_mc_default_traces(archive, selected)
    }
    fixed_ua = float(protocol["frozen_model"]["gas_liner_ua_multiplier"])
    cases: list[dict[str, Any]] = []
    for held_out_member in selected:
        training_members = [item for item in selected if item != held_out_member]
        volume_multiplier = float(
            np.median(
                [
                    volume_diagnostics[item]["inferred_volume_ratio"]
                    for item in training_members
                ]
            )
        )
        summary = summaries[held_out_member]
        replay = _replay_case(
            summary,
            processed_rows[held_out_member],
            fit=CompositeTankFitParameters(
                effective_volume_multiplier=volume_multiplier,
                gas_liner_ua_multiplier=fixed_ua,
            ),
            source_pressure_column="pressure_mpa",
        )
        trace = source_traces[held_out_member]
        if not np.allclose(replay.time_s, trace.time_s, rtol=0.0, atol=1.0e-9):
            raise ValueError(f"{trace.case_id}: processed/raw clocks differ")
        sensors = _sensor_stack(trace)
        cases.append(
            {
                "case_id": trace.case_id,
                "training_case_count": 7,
                "held_out_case_used_for_geometry_fit": False,
                "training_volume_ratio_median": volume_multiplier,
                "temperature_sensor_channel_count": int(sensors.shape[0]),
                "temperature_states": {
                    name: sensor_envelope_metrics(prediction, sensors)
                    for name, prediction in _thermal_observations(replay).items()
                },
            }
        )

    aggregate = _aggregate(cases)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "artifact_type": "mc_temperature_sensor_envelope_diagnostic",
        "evidence_role": "post_outcome_within_campaign_development_diagnostic",
        "post_outcome": True,
        "external_validation": False,
        "prospective_validation": False,
        "parameter_fitting": True,
        "parameter_fit_scope": "geometry from seven training cases per fold; thermal parameter frozen",
        "observation_operator_selection_performed": False,
        "runtime_parameter_changed": False,
        "validation_gate_changed": False,
        "promotion_to_validation_prohibited": True,
        "raw_experimental_rows_persisted": False,
        "method": {
            "case_count": len(cases),
            "geometry_split": "leave-one-case-out, seven training plus one held-out case",
            "held_out_temperature_used_for_geometry_fit": False,
            "thermal_parameter_policy": "retain frozen public Type-IV gas-liner UA multiplier",
            "observation_interval": "simultaneous minimum and maximum of independent in-tank temperature channels",
            "candidate_states": TEMPERATURE_OBSERVATIONS,
            "selection_rule": "none; every predefined state is reported",
        },
        "aggregate": aggregate,
        "cases": cases,
        "source": {
            "archive_alias": "public_mc_default_bench_archive",
            "archive_sha256": archive_hash,
            "expected_archive_sha256": expected_archive_hash,
            "protocol_artifact": _display(protocol_path),
            "protocol_sha256": _sha256(protocol_path),
        },
        "interpretation": (
            "The sensor envelope distinguishes spatial thermocouple spread from "
            "model-state error without choosing a favorable observation operator. "
            "A low envelope error would support a sensor-location explanation; a "
            "large error for all states would retain the heat-transfer-model limitation."
        ),
        "limitations": [
            "All outcomes belong to one previously inspected public campaign.",
            "Thermocouple coordinates, response time, uncertainty and state mapping are unavailable.",
            "An interval score is less strict than matching a predeclared sensor location.",
            "The geometry rule is training-fold fitted and has not been prospectively confirmed.",
        ],
        "claim_boundary": (
            "This is a privacy-safe, post-outcome sensor-envelope diagnostic. It "
            "cannot select a temperature observation operator, calibrate heat "
            "transfer, change runtime behavior, close an external-validation gate, "
            "or support a vehicle or field-safety claim."
        ),
    }


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# MC temperature sensor-envelope diagnostic",
        "",
        "This post-outcome development diagnostic compares predefined tank states with the simultaneous range of the public in-tank thermocouples. It does not select an observation operator or change runtime parameters.",
        "",
        "## Aggregate result",
        "",
        "| State | Mean-trace RMSE | Sensor-envelope RMSE | Inside envelope | Cases ≤ 10 °C |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in TEMPERATURE_OBSERVATIONS:
        row = report["aggregate"][name]
        lines.append(
            f"| {name} | {row['mean_trace_rmse_c_case_mean']:.3f} °C | "
            f"{row['envelope_rmse_c_case_mean']:.3f} °C | "
            f"{100.0 * row['inside_envelope_fraction_pooled']:.1f}% | "
            f"{row['case_count_envelope_rmse_le_10c']}/8 |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            "## Claim boundary",
            "",
            report["claim_boundary"],
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = build_report(args.archive, args.processed, args.protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_markdown(report, args.report)
    print(json.dumps(report["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
