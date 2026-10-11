"""Run a clearly post-outcome ELVHYS alarm-routing diagnostic.

The v2 prospective cohort failed because test 44 has no usable pre-release
baseline.  This runner deliberately replays only the fourteen cases that the
already-recorded intake diagnostic marked baseline-eligible.  It must never
be used as a validation gate: the case selection is informed by the failed
prospective run and the output is diagnostic evidence for the measured-signal
HAZOP route only.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_elvhys_detector_holdout_v2 import (  # noqa: E402
    _digest,
    _read_numeric_csv,
    baseline_corrected_maximum,
    evaluate_trace,
)


def _replay_case(
    protocol: dict[str, Any],
    raw_directory: Path,
    case: dict[str, Any],
) -> dict[str, Any]:
    test_id = int(case["test_id"])
    manifest = {
        int(item["test_id"]): item
        for item in protocol["source_manifest"]
        if int(item["test_id"]) == test_id
    }
    conc_item = next(item for item in protocol["source_manifest"]
                     if int(item["test_id"]) == test_id and item["kind"] == "CONC")
    pres_item = next(item for item in protocol["source_manifest"]
                     if int(item["test_id"]) == test_id and item["kind"] == "PRES")
    del manifest
    conc_path = raw_directory / str(conc_item["name"])
    pres_path = raw_directory / str(pres_item["name"])
    for item, path in ((conc_item, conc_path), (pres_item, pres_path)):
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != int(item["bytes"]) or _digest(path, "md5") != str(item["md5"]):
            raise ValueError(f"source integrity failure: {path.name}")

    concentration = _read_numeric_csv(conc_path)
    pressure = _read_numeric_csv(pres_path)
    onset_rule = protocol["release_onset_rule"]
    onset_threshold = max(
        float(onset_rule["minimum_pressure_barg"]),
        float(case["nominal_pressure_barg"]) * float(onset_rule["nominal_pressure_fraction"]),
    )
    pressure_time = pressure["Time"]
    nozzle_pressure = pressure[str(onset_rule["pressure_channel"])]
    onset_candidates = np.asarray(
        [
            float(t)
            for t, value in zip(pressure_time, nozzle_pressure, strict=True)
            if np.isfinite(value) and float(value) >= onset_threshold
        ],
        dtype=float,
    )
    if len(onset_candidates) == 0:
        raise ValueError(f"test {test_id}: release onset not found")
    onset = float(onset_candidates[0])
    baseline_rule = protocol["baseline_rule"]
    time, measured_grid_max, sensor_names, missing_data = baseline_corrected_maximum(
        concentration,
        release_onset_s=onset,
        baseline_guard_s=float(baseline_rule["guard_before_release_s"]),
        minimum_baseline_samples=int(baseline_rule["minimum_samples"]),
    )
    valid = np.isfinite(measured_grid_max)
    replay = evaluate_trace(
        time[valid], measured_grid_max[valid],
        release_onset_s=onset,
        thresholds=list(protocol["alarm_contract"]["thresholds"]),
    )
    checks = list(replay["checks"])
    return {
        "test_id": test_id,
        "nominal_pressure_barg": case["nominal_pressure_barg"],
        "nozzle_diameter_mm": case["nozzle_diameter_mm"],
        "ventilation": case["ventilation"],
        "orientation": case["orientation"],
        "release_onset_s_relative": onset,
        "concentration_sensor_count": len(sensor_names),
        "missing_data": missing_data,
        "maximum_baseline_corrected_grid_concentration_volpct_h2": float(np.nanmax(measured_grid_max)),
        "checks": checks,
        "pre_release_events": list(replay["pre_release_events"]),
    }


def run(protocol_path: Path, intake_diagnostic_path: Path, raw_directory: Path) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    intake = json.loads(intake_diagnostic_path.read_text(encoding="utf-8"))
    if intake.get("status") != "COMPLETED_POST_OUTCOME_DIAGNOSTIC":
        raise ValueError("the required post-failure intake diagnostic is unavailable")
    cases = [case for case in intake.get("cases", []) if case.get("case_baseline_eligible") is True]
    if not cases:
        raise ValueError("no baseline-eligible post-failure cases are available")
    by_id = {int(case["test_id"]): case for case in protocol["selected_cases"]}
    replayed = [_replay_case(protocol, raw_directory, by_id[int(case["test_id"])]) for case in cases]
    checks = [check for case in replayed for check in case["checks"]]
    expected = [check for check in checks if check["expected_trigger_time_s"] is not None]
    missed = [check for check in checks if check["missed_expected_trigger"]]
    unexpected = [check for check in checks if check["unexpected_trigger"]]
    errors = [float(check["timing_error_s"]) for check in expected if check["timing_error_s"] is not None]
    pre_release_events = [event for case in replayed for event in case["pre_release_events"]]
    return {
        "schema_version": 1,
        "artifact_type": "elvhys_post_failure_alarm_routing_diagnostic",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "POST_OUTCOME_DIAGNOSTIC_ONLY",
        "outcome_informed": True,
        "prospective_gate_changed": False,
        "runtime_parameter_application": False,
        "protocol": {
            "path": protocol_path.relative_to(ROOT).as_posix(),
            "sha256": _digest(protocol_path),
            "intake_diagnostic": intake_diagnostic_path.relative_to(ROOT).as_posix(),
            "failed_case_id_retained": 44,
        },
        "aggregate": {
            "replayed_case_count": len(replayed),
            "expected_trigger_count": len(expected),
            "missed_expected_trigger_count": len(missed),
            "unexpected_trigger_count": len(unexpected),
            "maximum_trigger_timing_error_s": max(errors, default=0.0),
            "pre_release_event_count": len(pre_release_events),
            "measured_signal_route_diagnostic_pass": not missed and not unexpected,
        },
        "cases": replayed,
        "claim_boundary": "This is an outcome-informed diagnostic of fourteen baseline-eligible ELVHYS cases. It does not replace the failed fifteen-case prospective holdout, validate detector placement, dispersion, concentration prediction, ESD effectiveness, consequence distance or the full station-to-vehicle twin.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=ROOT / "research/elvhys_detector_holdout_protocol_v2_2026_10_07.json")
    parser.add_argument("--intake", type=Path, default=ROOT / "research/elvhys_detector_intake_diagnostic_2026_10_08.json")
    parser.add_argument("--raw", type=Path, default=ROOT / "data/public_validation/raw/elvhys_detector_holdout_v2")
    parser.add_argument("--output", type=Path, default=ROOT / "research/elvhys_post_failure_alarm_diagnostic_2026_10_11.json")
    args = parser.parse_args()
    result = run(args.protocol, args.intake, args.raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["aggregate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
