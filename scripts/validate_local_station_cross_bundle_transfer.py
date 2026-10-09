"""Run a privacy-bounded station-side cross-bundle pressure transfer diagnostic.

The input directories and their mappings remain outside the repository.  The
result contains only aggregate cycle statistics and explicit claim boundaries.
It is deliberately separate from the frozen same-site holdout and never
changes runtime parameters.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.confidential_history_profile import _stats  # noqa: E402
from h2station.confidential_pressure_cycle_filtered_holdout import (  # noqa: E402
    causal_median_filter,
)
from h2station.confidential_pressure_cycle_holdout import (  # noqa: E402
    PressureCycleRules,
    detect_pressure_cycles,
)


def _outside_repository(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{label} must remain outside the repository")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_time(value: str, time_format: str) -> float | None:
    try:
        return datetime.strptime(value.strip(), time_format).timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def _read_bundle(
    root: Path,
    *,
    timestamp_index: int,
    pressure_index: int,
    pressure_scale_mpa_per_unit: float,
    time_format: str,
    encoding: str,
    skip_rows_after_header: int,
    rules: PressureCycleRules,
    median_window_samples: int,
) -> dict[str, object]:
    files_read = raw_rows = sampled_rows = filtered_rows = rejected_rows = 0
    reverse_files = mixed_files = 0
    cycles = []
    files_with_cycles = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() != ".csv":
            continue
        samples: list[tuple[float, float]] = []
        try:
            handle = path.open("r", encoding=encoding, newline="")
        except (OSError, UnicodeError):
            continue
        with handle:
            reader = csv.reader(handle)
            try:
                next(reader)
            except StopIteration:
                continue
            for _ in range(skip_rows_after_header):
                try:
                    next(reader)
                except StopIteration:
                    break
            files_read += 1
            for row_number, row in enumerate(reader):
                raw_rows += 1
                if row_number % rules.sample_stride:
                    continue
                if max(timestamp_index, pressure_index) >= len(row):
                    rejected_rows += 1
                    continue
                timestamp = _parse_time(row[timestamp_index], time_format)
                try:
                    pressure = float(row[pressure_index]) * pressure_scale_mpa_per_unit
                except (TypeError, ValueError):
                    pressure = float("nan")
                if timestamp is None or not math.isfinite(pressure):
                    rejected_rows += 1
                    continue
                samples.append((timestamp, pressure))
                sampled_rows += 1
        if len(samples) < 2:
            continue
        increasing = sum(after[0] > before[0] for before, after in zip(samples, samples[1:]))
        decreasing = sum(after[0] < before[0] for before, after in zip(samples, samples[1:]))
        reverse_files += int(decreasing > 0 and increasing == 0)
        mixed_files += int(decreasing > 0 and increasing > 0)
        samples.sort(key=lambda item: item[0])
        chronological: list[tuple[float, float]] = []
        for sample in samples:
            if chronological and sample[0] == chronological[-1][0]:
                chronological[-1] = sample
            else:
                chronological.append(sample)
        filtered = causal_median_filter(chronological, window_samples=median_window_samples)
        filtered_rows += len(filtered)
        detected = detect_pressure_cycles(filtered, rules=rules)
        cycles.extend(detected)
        files_with_cycles += int(bool(detected))
    drops = [cycle.pressure_drop_mpa for cycle in cycles]
    return {
        "files_read": files_read,
        "reverse_chronological_files": reverse_files,
        "mixed_order_files": mixed_files,
        "raw_rows": raw_rows,
        "sampled_rows": sampled_rows,
        "filtered_rows": filtered_rows,
        "rejected_rows": rejected_rows,
        "files_with_cycles": files_with_cycles,
        "cycles": _stats(drops),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration-input", type=Path, required=True)
    parser.add_argument("--transfer-input", type=Path, required=True)
    parser.add_argument("--calibration-timestamp-index", type=int, required=True)
    parser.add_argument("--calibration-pressure-index", type=int, required=True)
    parser.add_argument("--calibration-scale-mpa-per-unit", type=float, required=True)
    parser.add_argument("--calibration-time-format", required=True)
    parser.add_argument("--calibration-encoding", default="utf-8-sig")
    parser.add_argument("--calibration-skip-rows-after-header", type=int, default=0)
    parser.add_argument("--transfer-timestamp-index", type=int, required=True)
    parser.add_argument("--transfer-pressure-index", type=int, required=True)
    parser.add_argument("--transfer-scale-mpa-per-unit", type=float, required=True)
    parser.add_argument("--transfer-time-format", required=True)
    parser.add_argument("--transfer-encoding", default="utf-8-sig")
    parser.add_argument("--transfer-skip-rows-after-header", type=int, default=0)
    parser.add_argument("--protocol", type=Path, default=ROOT / "research/local_station_cross_bundle_transfer_protocol_2026_10_09.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    calibration_input = _outside_repository(args.calibration_input, label="calibration-input")
    transfer_input = _outside_repository(args.transfer_input, label="transfer-input")
    output = args.output.resolve()
    output.relative_to(ROOT.resolve())
    protocol = args.protocol.resolve()
    protocol.relative_to(ROOT.resolve())
    protocol_data = json.loads(protocol.read_text(encoding="utf-8"))
    frozen = dict(protocol_data["frozen_rules"])
    rules = PressureCycleRules(sample_stride=int(protocol_data["method"]["sample_stride"]), **frozen)
    window = int(protocol_data["method"]["median_window_samples"])

    calibration = _read_bundle(
        calibration_input,
        timestamp_index=args.calibration_timestamp_index,
        pressure_index=args.calibration_pressure_index,
        pressure_scale_mpa_per_unit=args.calibration_scale_mpa_per_unit,
        time_format=args.calibration_time_format,
        encoding=args.calibration_encoding,
        skip_rows_after_header=args.calibration_skip_rows_after_header,
        rules=rules,
        median_window_samples=window,
    )
    transfer = _read_bundle(
        transfer_input,
        timestamp_index=args.transfer_timestamp_index,
        pressure_index=args.transfer_pressure_index,
        pressure_scale_mpa_per_unit=args.transfer_scale_mpa_per_unit,
        time_format=args.transfer_time_format,
        encoding=args.transfer_encoding,
        skip_rows_after_header=args.transfer_skip_rows_after_header,
        rules=rules,
        median_window_samples=window,
    )

    candidate = float(protocol_data["method"]["candidate_margin_mpa"])
    transfer_stats = transfer["cycles"]
    median_value = transfer_stats["median"]
    p10 = transfer_stats["p05"]
    p90 = transfer_stats["p95"]
    candidate_inside = bool(
        isinstance(p10, (int, float))
        and isinstance(p90, (int, float))
        and p10 <= candidate <= p90
    )
    relative_error = (
        round(abs(candidate - median_value) / median_value * 100.0, 6)
        if isinstance(median_value, (int, float)) and median_value > 0.0
        else None
    )
    eligibility = {
        "transfer_cycles_minimum_met": int(transfer_stats["count"]) >= int(protocol_data["screens"]["minimum_transfer_cycles"]),
        "transfer_files_minimum_met": int(transfer["files_read"]) >= int(protocol_data["screens"]["minimum_transfer_files"]),
        "transfer_files_have_deterministic_order": int(transfer["mixed_order_files"]) == 0,
    }
    screens = {
        "candidate_inside_transfer_p05_p95": candidate_inside,
        "candidate_relative_transfer_median_error_le_20_percent": bool(relative_error is not None and relative_error <= float(protocol_data["screens"]["candidate_relative_transfer_median_error_percent_max"])),
    }
    report = {
        "schema_version": 1,
        "artifact_type": "local_station_cross_bundle_pressure_transfer_diagnostic",
        "evidence_role": "owner_controlled_station_side_transfer_only",
        "source_identifiers_published": False,
        "source_paths_published": False,
        "source_filenames_published": False,
        "source_headers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "calendar_dates_published": False,
        "roles": ["medium_storage_pressure", "high_storage_pressure"],
        "normalization": {"pressure_unit": "MPa", "explicit_unit_scale_applied": True},
        "method": {
            "calibration_bundle": "bundle_A",
            "transfer_bundle": "bundle_B",
            "candidate_margin_mpa": candidate,
            "sample_stride": rules.sample_stride,
            "median_window_samples": window,
            "outcome_used_for_fit": False,
        },
        "calibration_bundle": calibration,
        "transfer_bundle": transfer,
        "metrics": {
            "candidate_relative_transfer_median_error_percent": relative_error,
        },
        "eligibility": eligibility,
        "screens": screens,
        "decision": {
            "fixed_candidate_corroborated_on_transfer_bundle": bool(all(eligibility.values()) and all(screens.values())),
            "independent_external_validation": False,
            "full_loop_vehicle_validation": False,
            "safety_limit_or_field_certification": False,
            "runtime_parameter_application": False,
            "default_model_parameters_changed": False,
        },
        "claim_boundary": protocol_data["claim_boundary"],
        "protocol": {
            "protocol_id": protocol_data["protocol_id"],
            "protocol_sha256": _sha256(protocol),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "calibration_cycles": calibration["cycles"]["count"],
        "transfer_cycles": transfer["cycles"]["count"],
        "transfer_median_mpa": transfer["cycles"]["median"],
        "decision": report["decision"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
