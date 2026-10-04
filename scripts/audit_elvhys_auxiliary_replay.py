#!/usr/bin/env python3
"""Freeze and audit a bounded ELVHYS 4.2 pressure-peaking data subset.

This is deliberately a provenance/replay audit, not a predictive validation
runner.  The public experiment is a cryogenic 1 m3 transfer-connection-space
campaign, so its records cannot be promoted to H70 station full-loop evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


SOURCE = {
    "doi": "10.18710/JXJP0H",
    "landing_page": "https://dataverse.no/dataset.xhtml?persistentId=doi:10.18710/JXJP0H",
    "api_record": "https://dataverse.no/api/datasets/:persistentId/?persistentId=doi%3A10.18710%2FJXJP0H",
    "license": "CC0 1.0",
}

TESTS = {
    "029": {
        "pressure_file_id": 254217,
        "pressure_file": "ELE402HSE029PRES20251115.csv",
        "flow_file_id": 254364,
        "flow_file": "ELE402HSE029FLMT20251115.csv",
        "nominal_source_pressure_barg": 2.0,
        "nozzle_diameter_mm": 25.4,
        "vent_configuration": "4 VAV plates",
    },
    "030": {
        "pressure_file_id": 254355,
        "pressure_file": "ELE402HSE030PRES20251118.csv",
        "flow_file_id": 254251,
        "flow_file": "ELE402HSE030FLMT20251118.csv",
        "nominal_source_pressure_barg": 2.0,
        "nozzle_diameter_mm": 25.4,
        "vent_configuration": "2 blanks, 2 VAV plates (top)",
    },
    "031": {
        "pressure_file_id": 254246,
        "pressure_file": "ELE402HSE031PRES20251118.csv",
        "flow_file_id": 254255,
        "flow_file": "ELE402HSE031FLMT20251118.csv",
        "nominal_source_pressure_barg": 2.0,
        "nozzle_diameter_mm": 25.4,
        "vent_configuration": "3 blanks, 1 VAV plate (top left)",
    },
}

CONCENTRATION_TEST = {
    "test_no": "045",
    "concentration_file_id": 254344,
    "concentration_file": "ELE402HSE045CONC20251128.csv",
    "pressure_file_id": 254277,
    "pressure_file": "ELE402HSE045PRES20251128.csv",
    "flow_file_id": 254224,
    "flow_file": "ELE402HSE045FLMT20251128.csv",
    "nominal_source_pressure_barg": 8.0,
    "nozzle_diameter_mm": 1.0,
    "orientation": "upwards (500, 93, 250)",
    "ventilation": "Passive",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _stats(rows: list[dict[str, str]], column: str) -> dict[str, float | None]:
    values = [float(row[column]) for row in rows if row.get(column) not in (None, "")]
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def _time_stats(rows: list[dict[str, str]]) -> dict[str, float | int | bool | None]:
    times = [float(row["Time"]) for row in rows]
    deltas = [b - a for a, b in zip(times, times[1:]) if b > a]
    return {
        "row_count": len(times),
        "start_s": times[0] if times else None,
        "end_s": times[-1] if times else None,
        "monotonic_strict": bool(times) and all(b > a for a, b in zip(times, times[1:])),
        "median_sample_interval_s": sorted(deltas)[len(deltas) // 2] if deltas else None,
    }


def _threshold_first_time(rows: list[dict[str, str]], column: str, threshold: float) -> float | None:
    for row in rows:
        if float(row[column]) >= threshold:
            return float(row["Time"])
    return None


def run(raw_dir: Path, output: Path) -> dict[str, object]:
    cases: list[dict[str, object]] = []
    all_files: list[dict[str, object]] = []
    for test_no, descriptor in TESTS.items():
        pressure_path = raw_dir / descriptor["pressure_file"]
        flow_path = raw_dir / descriptor["flow_file"]
        if not pressure_path.is_file() or not flow_path.is_file():
            raise FileNotFoundError(f"missing frozen ELVHYS file for test {test_no}")
        pressure_fields, pressure_rows = read_csv(pressure_path)
        flow_fields, flow_rows = read_csv(flow_path)
        required_pressure = {"Time", "PT1ReleaseRig", "PT2Nozzle", "Var4", "Var5"}
        required_flow = {"Time", "FanFlowMeter"}
        if not required_pressure.issubset(pressure_fields):
            raise ValueError(f"unexpected pressure columns for test {test_no}: {pressure_fields}")
        if not required_flow.issubset(flow_fields):
            raise ValueError(f"unexpected flow columns for test {test_no}: {flow_fields}")
        pressure_time = _time_stats(pressure_rows)
        flow_time = _time_stats(flow_rows)
        if not pressure_time["monotonic_strict"] or not flow_time["monotonic_strict"]:
            raise ValueError(f"non-monotonic timebase in test {test_no}")
        file_records = []
        for role, file_id, path in (
            ("pressure", descriptor["pressure_file_id"], pressure_path),
            ("flow", descriptor["flow_file_id"], flow_path),
        ):
            record = {
                "role": role,
                "dataverse_file_id": file_id,
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            file_records.append(record)
            all_files.append(record)
        cases.append(
            {
                "test_no": test_no,
                "source_conditions": {
                    key: descriptor[key]
                    for key in ("nominal_source_pressure_barg", "nozzle_diameter_mm", "vent_configuration")
                },
                "pressure_file": descriptor["pressure_file"],
                "flow_file": descriptor["flow_file"],
                "pressure_time": pressure_time,
                "flow_time": flow_time,
                "pressure_channels": {
                    "release_rig_barg": _stats(pressure_rows, "PT1ReleaseRig"),
                    "nozzle_barg": _stats(pressure_rows, "PT2Nozzle"),
                    "tcs_pressure_1_mbar": _stats(pressure_rows, "Var4"),
                    "tcs_pressure_2_mbar": _stats(pressure_rows, "Var5"),
                },
                "ventilation_flow_channel": _stats(flow_rows, "FanFlowMeter"),
                "files": file_records,
            }
        )

    concentration_path = raw_dir / CONCENTRATION_TEST["concentration_file"]
    concentration_pressure_path = raw_dir / CONCENTRATION_TEST["pressure_file"]
    concentration_flow_path = raw_dir / CONCENTRATION_TEST["flow_file"]
    if not all(path.is_file() for path in (concentration_path, concentration_pressure_path, concentration_flow_path)):
        raise FileNotFoundError("missing frozen ELVHYS concentration test files")
    concentration_fields, concentration_rows = read_csv(concentration_path)
    pressure_fields, pressure_rows = read_csv(concentration_pressure_path)
    flow_fields, flow_rows = read_csv(concentration_flow_path)
    concentration_channels = [field for field in concentration_fields if field.startswith("H2")]
    if not concentration_channels or "Time" not in concentration_fields:
        raise ValueError("unexpected ELVHYS concentration columns")
    concentration_time = _time_stats(concentration_rows)
    if not concentration_time["monotonic_strict"]:
        raise ValueError("non-monotonic concentration timebase in test 045")
    if _time_stats(pressure_rows)["row_count"] != concentration_time["row_count"] or _time_stats(flow_rows)["row_count"] != concentration_time["row_count"]:
        raise ValueError("ELVHYS test 045 channels are not aligned")
    concentration_summary = {}
    for channel in concentration_channels:
        stats = _stats(concentration_rows, channel)
        stats["first_at_or_above_0_2_vol_percent_s"] = _threshold_first_time(concentration_rows, channel, 0.2)
        stats["first_at_or_above_4_vol_percent_s"] = _threshold_first_time(concentration_rows, channel, 4.0)
        concentration_summary[channel] = stats
    concentration_files = []
    for role, file_id, path in (
        ("concentration", CONCENTRATION_TEST["concentration_file_id"], concentration_path),
        ("pressure", CONCENTRATION_TEST["pressure_file_id"], concentration_pressure_path),
        ("flow", CONCENTRATION_TEST["flow_file_id"], concentration_flow_path),
    ):
        record = {
            "role": role,
            "dataverse_file_id": file_id,
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        concentration_files.append(record)
        all_files.append(record)

    result = {
        "schema_version": 1,
        "status": "completed_post_access_auxiliary_replay",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "public_consequence_auxiliary_provenance_and_replay",
        "source": SOURCE,
        "selection": {
            "rule": "All three ELVHYS 4.2 pressure-peaking tests (29-31) plus vertical dispersion test 45, selected by test type before interpreting the replay statistics.",
            "raw_files_committed": False,
            "local_raw_directory": "data/public_validation/raw/elvhys_4_2",
            "outcomes_accessed_before_freeze": True,
        },
        "dataset_scope": {
            "facility": "1 m3 cryogenic hydrogen transfer-connection space",
            "experiment_type": "unignited pressure peaking",
            "source_reported_campaign": "ELVHYS WP4.2",
            "units": "PT1/PT2 barg, TCS pressure Var4/Var5 mbar, ventilation flow channel as recorded",
        },
        "cases": cases,
        "concentration_cases": [
            {
                "test_no": CONCENTRATION_TEST["test_no"],
                "source_conditions": {
                    key: CONCENTRATION_TEST[key]
                    for key in ("nominal_source_pressure_barg", "nozzle_diameter_mm", "orientation", "ventilation")
                },
                "time": concentration_time,
                "channel_count": len(concentration_channels),
                "channels": concentration_summary,
                "files": concentration_files,
            }
        ],
        "file_manifest": all_files,
        "claims": {
            "provenance_integrity_pass": True,
            "predictive_model_validation_permitted": False,
            "full_loop_station_vehicle_validation_permitted": False,
            "claim_boundary": "The replay verifies accessible source files, timebase integrity and pressure-peaking observations only. It does not validate the H70 station fueling loop, gaseous outdoor dispersion, HyRAM distances, ignition, emergency response or SAGA effectiveness.",
            "reason_predictive_validation_not_claimed": "The repository has no pre-access frozen cryogenic enclosure model and the raw outcomes were inspected before this replay record was frozen.",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/public_validation/raw/elvhys_4_2"))
    parser.add_argument("--output", type=Path, default=Path("research/elvhys_auxiliary_replay.json"))
    args = parser.parse_args()
    result = run(args.raw_dir, args.output)
    print(json.dumps({"status": result["status"], "case_count": len(result["cases"]), "file_count": len(result["file_manifest"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
