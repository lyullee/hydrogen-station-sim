"""Normalize public J2601 experiments and HIAD HRS records for evaluation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from h2station.public_validation import (
    iter_dispersion_experiments,
    iter_h2protocol_traces,
    read_hiad_hrs_cases,
)


TRACE_FIELDS = (
    "time_s", "pressure_mpa", "soc_percent", "mass_flow_g_s",
    "tank_temperature_mean_c", "tank_temperature_max_c",
    "inlet_gas_temperature_c", "chamber_temperature_c",
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def prepare_h2protocol(raw: Path, output: Path) -> dict:
    summaries = []
    trace_root = output / "h2protocol_traces"
    trace_root.mkdir(parents=True, exist_ok=True)
    for trace in iter_h2protocol_traces(raw):
        summaries.append(trace.summary())
        rows = [
            {name: float(getattr(trace, name)[index]) for name in TRACE_FIELDS}
            for index in range(len(trace.time_s))
        ]
        _write_csv(trace_root / f"{trace.case_id}.csv", rows)
        print(f"prepared {trace.case_id}: {trace.metadata.test_code}", flush=True)
    _write_csv(output / "h2protocol_cases.csv", summaries)
    capacities: dict[str, int] = {}
    for item in summaries:
        key = str(item["tank_capacity_kg"])
        capacities[key] = capacities.get(key, 0) + 1
    return {"case_count": len(summaries), "tank_capacity_counts": capacities}


def prepare_hiad(path: Path, output: Path) -> dict:
    cases = read_hiad_hrs_cases(path)
    destination = output / "hiad_hrs_cases.jsonl"
    with destination.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case.to_dict(), ensure_ascii=False) + "\n")
    return {
        "case_count": len(cases),
        "with_emergency_action": sum(bool(case.emergency_action) for case in cases),
        "with_lesson_learnt": sum(bool(case.lesson_learnt) for case in cases),
        "with_corrective_measures": sum(bool(case.corrective_measures) for case in cases),
    }


def prepare_dispersion(raw: Path, output: Path) -> dict:
    summaries = [experiment.summary() for experiment in iter_dispersion_experiments(raw)]
    _write_csv(output / "dispersion_channel_cases.csv", summaries)
    return {
        "case_count": len(summaries),
        "mass_flow_range_g_s": [
            min(item["mean_mass_flow_g_s"] for item in summaries),
            max(item["mean_mass_flow_g_s"] for item in summaries),
        ],
        "sensor_count_values": sorted({item["sensor_count"] for item in summaries}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("data/public_validation/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument(
        "--datasets", nargs="+",
        choices=("h2protocol", "hiad", "dispersion"),
        default=("h2protocol", "hiad", "dispersion"),
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    inventory_path = args.output / "inventory.json"
    inventory = (
        json.loads(inventory_path.read_text(encoding="utf-8"))
        if inventory_path.exists() else {"schema_version": 1}
    )
    if "h2protocol" in args.datasets:
        inventory["h2protocol"] = prepare_h2protocol(
            args.raw / "h2protocol_j2601_tables", args.output
        )
    if "hiad" in args.datasets:
        inventory["hiad"] = prepare_hiad(
            args.raw / "hiad_2_2" / "HIAD 2.2.xlsx", args.output
        )
    if "dispersion" in args.datasets:
        inventory["dispersion_channel"] = prepare_dispersion(
            args.raw / "hydrogen_dispersion_channel", args.output
        )
    inventory_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output / "inventory.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
