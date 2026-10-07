"""Replay prospectively selected ELVHYS concentration traces through HAZOP.

The selected concentration and pressure files must remain outside Git.  The
protocol fixes the cases, source digests, release-onset rule, baseline rule and
alarm screens before any selected outcome file is downloaded.  This validates
only measured-signal alarm/response routing; it does not validate dispersion,
detector placement, gaseous-H70 transfer, or consequence distance.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import urllib.request

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.hazop.database import load_catalog  # noqa: E402
from h2station.hazop.engine import RuleEngine  # noqa: E402
from h2station.hazop.response import structured_guidance  # noqa: E402


def _digest(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_numeric_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "Time" not in reader.fieldnames:
            raise ValueError(f"{path.name}: Time column is required")
        rows = list(reader)
        columns: dict[str, np.ndarray] = {}
        for name in reader.fieldnames:
            try:
                values = np.asarray([float(row[name]) for row in rows], dtype=float)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{path.name}: nonnumeric column {name}") from exc
            if np.any(~np.isfinite(values)):
                raise ValueError(f"{path.name}: nonfinite values in {name}")
            columns[name] = values
    time = columns["Time"]
    if len(time) < 2 or np.any(np.diff(time) <= 0.0):
        raise ValueError(f"{path.name}: Time must be strictly increasing")
    return columns


def first_sustained_time(
    time_s: np.ndarray,
    values: np.ndarray,
    *,
    threshold: float,
    persistence_s: float,
) -> float | None:
    """Return the first threshold crossing retained for the fixed duration."""

    since: float | None = None
    for time, value in zip(time_s, values, strict=True):
        if value >= threshold:
            if since is None:
                since = float(time)
            if float(time) - since + 1.0e-9 >= persistence_s:
                return float(time)
        else:
            since = None
    return None


def baseline_corrected_maximum(
    concentration: dict[str, np.ndarray],
    *,
    release_onset_s: float,
    baseline_guard_s: float,
    minimum_baseline_samples: int,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    time = concentration["Time"]
    sensor_names = sorted(name for name in concentration if name.startswith("H2"))
    if not sensor_names:
        raise ValueError("no H2 concentration channels")
    baseline_mask = time <= release_onset_s - baseline_guard_s
    if int(np.count_nonzero(baseline_mask)) < minimum_baseline_samples:
        raise ValueError("insufficient pre-release baseline samples")
    baselines = np.asarray(
        [np.median(concentration[name][baseline_mask]) for name in sensor_names],
        dtype=float,
    )
    corrected = np.column_stack(
        [concentration[name] - baseline for name, baseline in zip(sensor_names, baselines, strict=True)]
    )
    return time, np.maximum(np.max(corrected, axis=1), 0.0), sensor_names


def _gas_rule_catalog() -> dict[str, Any]:
    catalog = load_catalog()
    selected = [
        rule for rule in catalog["rules"]
        if rule.get("sensor_id") == "GD-0101" and rule.get("rule_id") in {
            "HZ-141", "HZ-142", "HZ-143",
        }
    ]
    if len(selected) != 3:
        raise RuntimeError("expected GD-0101 gas rule set is unavailable")
    return {**catalog, "rules": selected}


def evaluate_trace(
    time_s: np.ndarray,
    concentration_volpct: np.ndarray,
    *,
    release_onset_s: float,
    thresholds: list[dict[str, Any]],
) -> dict[str, Any]:
    engine = RuleEngine(_gas_rule_catalog())
    actual: dict[str, float] = {}
    pre_release_events: list[dict[str, Any]] = []
    for time, value in zip(time_s, concentration_volpct, strict=True):
        outcome = engine.evaluate({
            "time_s": float(time),
            "signals": {
                "GD-0101": {
                    "value": float(value),
                    "unit": "vol%_H2",
                    "quality": "GOOD",
                    "time_s": float(time),
                    "origin": "ELVHYS_MEASURED_GRID_MAX_REPLAY",
                },
            },
            "modes": {"station.monitoring": True},
        })
        for event in outcome["events"]:
            if event["classification"] != "ACCIDENT_CANDIDATE":
                continue
            if float(event["time_s"]) < release_onset_s:
                pre_release_events.append({
                    "rule_id": event["rule_id"],
                    "time_s": float(event["time_s"]),
                })
            else:
                actual.setdefault(event["rule_id"], float(event["time_s"]))

    checks = []
    for threshold in thresholds:
        expected = first_sustained_time(
            time_s[time_s >= release_onset_s],
            concentration_volpct[time_s >= release_onset_s],
            threshold=float(threshold["threshold_volpct_h2"]),
            persistence_s=float(threshold["persistence_s"]),
        )
        observed = actual.get(str(threshold["rule_id"]))
        checks.append({
            "rule_id": threshold["rule_id"],
            "threshold_volpct_h2": threshold["threshold_volpct_h2"],
            "persistence_s": threshold["persistence_s"],
            "expected_trigger_time_s": expected,
            "rule_engine_trigger_time_s": observed,
            "missed_expected_trigger": expected is not None and observed is None,
            "unexpected_trigger": expected is None and observed is not None,
            "timing_error_s": (
                abs(observed - expected)
                if observed is not None and expected is not None else None
            ),
        })
    return {"checks": checks, "pre_release_events": pre_release_events}


def _download(files: list[dict[str, Any]], raw_directory: Path) -> None:
    raw_directory.mkdir(parents=True, exist_ok=True)
    for item in files:
        path = raw_directory / str(item["name"])
        if path.is_file() and path.stat().st_size == int(item["bytes"]):
            if _digest(path, "md5") == str(item["md5"]):
                continue
        url = f"https://dataverse.no/api/access/datafile/{int(item['datafile_id'])}"
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
        path.write_bytes(data)
        if path.stat().st_size != int(item["bytes"]) or _digest(path, "md5") != str(item["md5"]):
            path.unlink(missing_ok=True)
            raise ValueError(f"download integrity failure: {item['name']}")


def run(protocol_path: Path, raw_directory: Path, *, download: bool = False) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    files = list(protocol["source_manifest"])
    if download:
        _download(files, raw_directory)
    runner_expected = str(protocol["frozen_implementation"]["runner_sha256"])
    runner_actual = _digest(Path(__file__))
    if runner_actual != runner_expected:
        raise ValueError("runner differs from the prospectively frozen implementation")

    by_test: dict[int, dict[str, dict[str, Any]]] = {}
    for item in files:
        path = raw_directory / str(item["name"])
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != int(item["bytes"]) or _digest(path, "md5") != str(item["md5"]):
            raise ValueError(f"source integrity failure: {path.name}")
        by_test.setdefault(int(item["test_id"]), {})[str(item["kind"])] = {
            **item, "path": path,
        }

    cases = []
    threshold_rows = list(protocol["alarm_contract"]["thresholds"])
    onset_rule = protocol["release_onset_rule"]
    baseline_rule = protocol["baseline_rule"]
    for case in protocol["selected_cases"]:
        test_id = int(case["test_id"])
        pair = by_test[test_id]
        concentration = _read_numeric_csv(pair["CONC"]["path"])
        pressure = _read_numeric_csv(pair["PRES"]["path"])
        pressure_time = pressure["Time"]
        nozzle_pressure = pressure[str(onset_rule["pressure_channel"])]
        onset_threshold = max(
            float(onset_rule["minimum_pressure_barg"]),
            float(case["nominal_pressure_barg"]) * float(onset_rule["nominal_pressure_fraction"]),
        )
        onset = first_sustained_time(
            pressure_time,
            nozzle_pressure,
            threshold=onset_threshold,
            persistence_s=float(onset_rule["persistence_s"]),
        )
        if onset is None:
            raise ValueError(f"test {test_id}: release onset not found")
        time, measured_grid_max, sensor_names = baseline_corrected_maximum(
            concentration,
            release_onset_s=onset,
            baseline_guard_s=float(baseline_rule["guard_before_release_s"]),
            minimum_baseline_samples=int(baseline_rule["minimum_samples"]),
        )
        replay = evaluate_trace(
            time, measured_grid_max,
            release_onset_s=onset,
            thresholds=threshold_rows,
        )
        cases.append({
            "test_id": test_id,
            "nominal_pressure_barg": case["nominal_pressure_barg"],
            "nozzle_diameter_mm": case["nozzle_diameter_mm"],
            "ventilation": case["ventilation"],
            "orientation": case["orientation"],
            "release_onset_s_relative": onset,
            "concentration_sensor_count": len(sensor_names),
            "maximum_baseline_corrected_grid_concentration_volpct_h2": float(np.max(measured_grid_max)),
            **replay,
        })

    checks = [check for case in cases for check in case["checks"]]
    expected = [check for check in checks if check["expected_trigger_time_s"] is not None]
    missed = [check for check in checks if check["missed_expected_trigger"]]
    unexpected = [check for check in checks if check["unexpected_trigger"]]
    timing_errors = [float(check["timing_error_s"]) for check in expected if check["timing_error_s"] is not None]
    false_events = [event for case in cases for event in case["pre_release_events"]]
    response = structured_guidance("gas_release")
    response_ready = bool(
        response.get("emergency_response")
        and response.get("safety_management")
        and response.get("public_accident_precedents")
    )
    criteria = protocol["primary_acceptance"]
    sample_bound = float(criteria["maximum_trigger_timing_error_s"])
    contract_pass = bool(
        len(cases) >= int(criteria["minimum_case_count"])
        and not missed
        and not unexpected
        and (max(timing_errors, default=0.0) <= sample_bound + 1.0e-9)
        and response_ready
    )
    return {
        "schema_version": 1,
        "artifact_type": "elvhys_measured_signal_hazop_holdout",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if contract_pass else "FAIL",
        "protocol": {
            "path": protocol_path.relative_to(ROOT).as_posix(),
            "sha256": _digest(protocol_path),
            "runner_sha256": runner_actual,
            "outcomes_accessed_before_freeze": False,
        },
        "aggregate": {
            "case_count": len(cases),
            "expected_trigger_count": len(expected),
            "missed_expected_trigger_count": len(missed),
            "unexpected_trigger_count": len(unexpected),
            "maximum_trigger_timing_error_s": max(timing_errors, default=0.0),
            "pre_release_event_count": len(false_events),
            "gas_release_response_ready": response_ready,
            "primary_contract_pass": contract_pass,
        },
        "cases": cases,
        "claim_boundary": protocol["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol", type=Path,
        default=ROOT / "research/elvhys_detector_holdout_protocol_2026_10_07.json",
    )
    parser.add_argument(
        "--raw", type=Path,
        default=ROOT / "data/public_validation/raw/elvhys_detector_holdout",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "research/elvhys_detector_holdout_result_2026_10_07.json",
    )
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    result = run(args.protocol, args.raw, download=args.download)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["aggregate"], ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
