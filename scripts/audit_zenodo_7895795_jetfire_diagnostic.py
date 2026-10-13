"""Summarise the public HyTunnel-CS high-pressure hydrogen jet-fire archive.

The archive was opened after the repository's prospective-validation freezes.
This runner is therefore deliberately a post-access diagnostic.  It extracts
published pressure decay and thermal-distance trends without fitting a release
coefficient, changing runtime parameters, or claiming independent validation.
Raw workbooks remain outside the repository.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

import numpy as np
from openpyxl import load_workbook
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "research/zenodo_7895795_jetfire_postaccess_diagnostic_2026_10_14.json"

# Values and test metadata are stated in the publisher's metadata document.
TEST_META: dict[int, dict[str, Any]] = {
    1: {"kind": "free_jet", "nozzle_mm": 2.1, "volume_l": 49, "pressure_bar": 700},
    2: {"kind": "free_jet", "nozzle_mm": 0.57, "volume_l": 49, "pressure_bar": 700},
    3: {"kind": "impeded_temperature_plate", "nozzle_mm": 2.1, "volume_l": 49, "stand_off_m": 0.95, "pressure_bar": 700},
    4: {"kind": "impeded_temperature_plate", "nozzle_mm": 0.57, "volume_l": 49, "stand_off_m": 1.0, "pressure_bar": 700},
    5: {"kind": "impeded_pressure_plate", "nozzle_mm": 2.1, "volume_l": 49, "stand_off_m": 0.972, "pressure_bar": 700},
    7: {"kind": "impeded_concrete", "nozzle_mm": 2.1, "volume_l": 98, "stand_off_m": 1.06, "pressure_bar": 700},
    9: {"kind": "impeded_concrete_pp_fibre", "nozzle_mm": 2.1, "volume_l": 98, "stand_off_m": 1.06, "pressure_bar": 700},
    11: {"kind": "concrete_core_indicative", "nozzle_mm": 2.1, "volume_l": 49, "stand_off_m": 1.09, "pressure_bar": 700},
    12: {"kind": "impeded_temperature_plate", "nozzle_mm": 5.0, "volume_l": 49, "stand_off_m": 3.3, "pressure_bar": 350},
}


def _number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _test_id(path: Path) -> int:
    match = re.search(r"HSE(\d{3})", path.name)
    if not match:
        raise ValueError(f"cannot determine test id from {path.name}")
    return int(match.group(1))


def _series(values: list[object]) -> list[float]:
    return [number for value in values if (number := _number(value)) is not None]


def _pressure_summary(rows: list[tuple[object, ...]], headers: list[object]) -> dict[str, Any] | None:
    candidates = [
        index for index, value in enumerate(headers)
        if value is not None and "pressure" in str(value).lower() and "vessel" in str(value).lower()
    ]
    if not candidates:
        return None
    values = _series([row[candidates[0]] if candidates[0] < len(row) else None for row in rows])
    if len(values) < 10:
        return {"available": False, "reason": "fewer than ten numeric vessel-pressure rows"}
    first = float(np.median(values[: max(3, min(20, len(values) // 20))]))
    last = float(np.median(values[-max(3, min(20, len(values) // 20)) :]))
    half_target = last + 0.5 * (first - last)
    half_index = next((i for i, value in enumerate(values) if value <= half_target), None)
    return {
        "available": True,
        "channel": str(headers[candidates[0]]),
        "unit": "published pressure scale (metadata describes bar)",
        "sample_count": len(values),
        "initial_median": first,
        "final_median": last,
        "drop": first - last,
        "half_pressure_sample_index": half_index,
        "half_pressure_time_s": float(half_index + 1) if half_index is not None else None,
    }


def _thermal_channels(headers: list[object]) -> list[tuple[int, str, float | None]]:
    channels: list[tuple[int, str, float | None]] = []
    for index, value in enumerate(headers):
        if value is None:
            continue
        label = str(value)
        if not (
            "temperature" in label.lower()
            or "temp " in label.lower()
            or "temp n-type" in label.lower()
            or "temp r-type" in label.lower()
            or re.match(r"^R\d+\s*\(", label, re.I)
        ):
            continue
        distance_match = re.search(r"\(([0-9]+(?:\.[0-9]+)?)\s*m\s*from\s*nozzle\)", label, re.I)
        distance = float(distance_match.group(1)) if distance_match else None
        channels.append((index, label, distance))
    return channels


def _thermal_summary(rows: list[tuple[object, ...]], headers: list[object]) -> dict[str, Any]:
    channels = _thermal_channels(headers)
    results: list[dict[str, Any]] = []
    for index, label, distance in channels:
        values = _series([row[index] if index < len(row) else None for row in rows])
        if len(values) < 5:
            continue
        baseline_count = max(3, min(20, len(values) // 10))
        baseline = float(np.median(values[:baseline_count]))
        peak = float(max(values))
        results.append({
            "channel": label,
            "distance_m": distance,
            "sample_count": len(values),
            "baseline_median": baseline,
            "peak": peak,
            "peak_delta": peak - baseline,
        })
    ordered = [item for item in results if item["distance_m"] is not None and item["peak_delta"] >= 0]
    trend: dict[str, Any] = {"available": False, "reason": "fewer than three channels with published axial distances"}
    if len(ordered) >= 3:
        distances = np.asarray([item["distance_m"] for item in ordered], dtype=float)
        peaks = np.asarray([item["peak_delta"] for item in ordered], dtype=float)
        rho = spearmanr(distances, peaks).statistic
        trend = {
            "available": True,
            "distance_peak_delta_spearman": float(rho),
            "expected_decreasing_with_distance": bool(rho < 0),
            "channel_count": len(ordered),
        }
    return {"channels": results, "distance_trend": trend}


def _read_workbook(path: Path) -> dict[str, Any]:
    test_id = _test_id(path)
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheets: list[dict[str, Any]] = []
    for sheet in workbook.worksheets:
        iterator = sheet.iter_rows(values_only=True)
        headers = list(next(iterator, ()))
        rows = [tuple(row) for row in iterator if any(value is not None for value in row)]
        if not headers or not rows:
            continue
        pressure = _pressure_summary(rows, headers)
        thermal = _thermal_summary(rows, headers)
        if pressure is None and not thermal["channels"]:
            continue
        sheets.append({
            "sheet": sheet.title,
            "row_count": len(rows),
            "pressure": pressure,
            "thermal": thermal,
        })
    return {
        "test_id": test_id,
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "publisher_test_metadata": TEST_META.get(test_id),
        "sheets": sheets,
    }


def build(raw_dir: Path) -> dict[str, Any]:
    files = sorted(raw_dir.glob("*.xlsx"))
    if not files:
        raise ValueError(f"no xlsx files found in {raw_dir}")
    tests = [_read_workbook(path) for path in files]
    free_jet = [
        sheet["thermal"]["distance_trend"]
        for test in tests
        if test["publisher_test_metadata"] and test["publisher_test_metadata"]["kind"] == "free_jet"
        for sheet in test["sheets"]
        if sheet["thermal"]["distance_trend"]["available"]
    ]
    return {
        "schema_version": 1,
        "artifact_type": "post_access_zenodo_7895795_hydrogen_jetfire_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "POST_ACCESS_THERMAL_PRESSURE_DIAGNOSTIC_NOT_INDEPENDENT_VALIDATION",
        "source": {
            "dataset_doi": "10.5281/zenodo.7895795",
            "landing_page": "https://zenodo.org/records/7895795",
            "title": "Effects of hydrogen jet fires on the erosion of tunnel road materials and lining materials",
            "publisher": "HyTunnel-CS / HSE Science and Research Centre",
            "license": "CC BY 4.0",
            "actual_hydrogen": True,
            "publisher_reported_scope": "700 bar TPRD-mimicking ignited releases with 2.1 mm and 0.57 mm nozzles; one 350 bar, 5 mm test",
            "raw_files_external_only": True,
        },
        "provenance_boundary": {
            "raw_accessed_before_this_artifact": True,
            "independent_holdout": False,
            "prospective_validation": False,
            "parameter_fitting": False,
            "runtime_parameter_change": False,
            "readiness_gate_effect": False,
            "reason": "The publisher workbooks were opened before this artifact was created, so the result is a post-access diagnostic and cannot be used as a new independent holdout.",
        },
        "analysis_contract": {
            "pressure": "publisher vessel-pressure channel; median initial/final values and descriptive half-pressure sample index",
            "temperature": "published thermocouple channels; peak minus first-window median; free-jet axial trend only where distances are explicitly published",
            "units": "pressure retained on the publisher scale described as bar; temperatures retained as published degrees C where identified",
            "no_fit_or_interpolation": True,
        },
        "tests": tests,
        "aggregate": {
            "workbook_count": len(tests),
            "free_jet_distance_trend_count": len(free_jet),
            "free_jet_distance_trend_expected_decreasing_count": sum(item["expected_decreasing_with_distance"] for item in free_jet),
            "pressure_workbook_count": sum(1 for test in tests if any(sheet["pressure"] and sheet["pressure"].get("available") for sheet in test["sheets"])),
            "thermal_workbook_count": sum(1 for test in tests if any(sheet["thermal"]["channels"] for sheet in test["sheets"])),
        },
        "decision": {
            "descriptive_replay": "PASS",
            "independent_validation": "NOT_ASSESSED",
            "runtime_risk_distance_calibration": False,
            "fire_heat_flux_validation": False,
            "gate_changed": False,
        },
        "claim_boundary": "This artifact inventories and replays publisher-reported pressure and thermal trends from actual-hydrogen jet-fire experiments. It does not validate HyRAM heat flux, radiation, overpressure, HRS release coefficients, detector placement, safety distance, structural failure, ESD effectiveness or station-to-vehicle behavior.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build(args.raw_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "workbook_count": result["aggregate"]["workbook_count"],
        "pressure_workbook_count": result["aggregate"]["pressure_workbook_count"],
        "thermal_workbook_count": result["aggregate"]["thermal_workbook_count"],
        "status": result["status"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
