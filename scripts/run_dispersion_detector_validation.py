"""Evaluate the station detector threshold rule against public measurements.

This is an instrumented-logic evidence run, not a claim that an open-channel
experiment validates an outdoor hydrogen-refuelling station.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import median

from h2station.public_validation import (
    evaluate_dispersion_detector_logic,
    iter_dispersion_experiments,
)


def _median(values: list[float]) -> float | None:
    return float(median(values)) if values else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(
    raw_directory: Path,
    *,
    alarm_threshold_percent: float,
    trip_threshold_percent: float,
    persistence_s: float,
) -> dict:
    evaluations = [
        evaluate_dispersion_detector_logic(
            experiment,
            alarm_threshold_percent=alarm_threshold_percent,
            trip_threshold_percent=trip_threshold_percent,
            persistence_s=persistence_s,
        )
        for experiment in iter_dispersion_experiments(raw_directory)
    ]
    if not evaluations:
        raise ValueError("No dispersion experiments were found")
    alarm = [item["alarm"] for item in evaluations]
    trip = [item["trip"] for item in evaluations]
    return {
        "schema_version": 1,
        "status": "completed_bounded_instrumented_detector_logic_evidence",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "instrumented_detector_logic_evidence",
        "claim_boundary": (
            "Measured concentration channels from the USN/FFI open-ended rectangular "
            "channel dataset are replayed through the declared alarm/trip threshold "
            "and persistence rule. This does not validate outdoor station dispersion, "
            "detector response dynamics, detector placement, ESD effectiveness, or "
            "the complete hydrogen-refuelling process model."
        ),
        "source": {
            "dataset": "Experimental Data of Hydrogen Dispersion in an Open-ended Rectangular Channel",
            "doi": "10.23642/usn.26117989.v2",
            "license": "CC BY 4.0",
            "raw_directory": str(raw_directory),
            "archive_manifest": [
                {
                    "name": archive.name,
                    "bytes": archive.stat().st_size,
                    "sha256": _sha256(archive),
                }
                for archive in sorted(raw_directory.glob("*.zip"))
            ],
            "supporting_file_manifest": [
                {
                    "name": support.name,
                    "bytes": support.stat().st_size,
                    "sha256": _sha256(support),
                }
                for support in sorted(raw_directory.iterdir())
                if support.is_file() and support.suffix.lower() != ".zip"
            ],
        },
        "rule": {
            "alarm_threshold_percent": alarm_threshold_percent,
            "trip_threshold_percent": trip_threshold_percent,
            "persistence_s": persistence_s,
            "sampling_gap_reset": "gap > 1.5 * median positive sample interval",
        },
        "aggregate": {
            "case_count": len(evaluations),
            "sensor_count_per_case": sorted({item["alarm"]["sensor_count"] for item in evaluations}),
            "cases_with_alarm_detection": sum(item["alarm"]["detected_sensor_count"] > 0 for item in evaluations),
            "cases_with_trip_detection": sum(item["trip"]["detected_sensor_count"] > 0 for item in evaluations),
            "mean_alarm_sensor_coverage_fraction": sum(item["alarm"]["coverage_fraction"] for item in evaluations) / len(evaluations),
            "mean_trip_sensor_coverage_fraction": sum(item["trip"]["coverage_fraction"] for item in evaluations) / len(evaluations),
            "median_first_alarm_after_fill_start_s": _median([
                item["alarm"]["first_detection_after_fill_start_s"]
                for item in evaluations
                if item["alarm"]["first_detection_after_fill_start_s"] is not None
            ]),
            "median_first_trip_after_fill_start_s": _median([
                item["trip"]["first_detection_after_fill_start_s"]
                for item in evaluations
                if item["trip"]["first_detection_after_fill_start_s"] is not None
            ]),
        },
        "cases": evaluations,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("data/public_validation/raw/hydrogen_dispersion_channel"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--alarm-threshold-percent", type=float, default=1.0)
    parser.add_argument("--trip-threshold-percent", type=float, default=2.0)
    parser.add_argument("--persistence-s", type=float, default=0.5)
    args = parser.parse_args()
    result = run(
        args.raw,
        alarm_threshold_percent=args.alarm_threshold_percent,
        trip_threshold_percent=args.trip_threshold_percent,
        persistence_s=args.persistence_s,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    aggregate = result["aggregate"]
    print(
        f"completed {aggregate['case_count']} cases; "
        f"alarm coverage={aggregate['mean_alarm_sensor_coverage_fraction']:.3f}; "
        f"trip coverage={aggregate['mean_trip_sensor_coverage_fraction']:.3f}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
