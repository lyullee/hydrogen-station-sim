"""Audit the public NIST 1/4-scale helium-garage workbook archive.

The archive is useful for a bounded spatial/ventilation component check.  It is
deliberately not promoted to an HRS or hydrogen validation set: the gas is
helium, and the report does not provide an unambiguous release-start crosswalk
to the workbook-relative time axis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _workbook_summary(path: Path) -> dict[str, Any]:
    try:
        import xlrd  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised by CLI users
        raise RuntimeError(
            "xlrd is required for legacy .xls intake; install the research extra "
            "or run this script in the project research environment"
        ) from exc

    workbook = xlrd.open_workbook(path.as_posix(), on_demand=True)
    sheet = workbook.sheet_by_index(0)
    headers = [str(value).strip() for value in sheet.row_values(0)]
    named_headers = [header for header in headers if header]
    rows = [
        row
        for row in (sheet.row_values(index) for index in range(1, sheet.nrows))
        if _finite(row[0] if row else None) is not None
    ]
    times = [_finite(row[0]) for row in rows]
    clean_times = [value for value in times if value is not None]
    positive_steps = [
        right - left
        for left, right in zip(clean_times, clean_times[1:])
        if right > left
    ]
    channel_indexes = [
        index for index, header in enumerate(headers)
        if header and header.lower() != "time"
    ]
    finite_counts = {
        headers[index]: sum(_finite(row[index]) is not None for row in rows)
        for index in channel_indexes
    }
    return {
        "file": path.name,
        "sha256": _sha256(path),
        "row_count": len(rows),
        "time_start_s": min(clean_times),
        "time_end_s": max(clean_times),
        "median_sample_interval_s": statistics.median(positive_steps),
        "channels": [headers[index] for index in channel_indexes],
        "channel_count": len(named_headers) - 1,
        "channels_with_finite_values": sum(
            count > 0 for count in finite_counts.values()
        ),
        "permanently_empty_channel_count": sum(
            count == 0 for count in finite_counts.values()
        ),
    }


def audit(raw_dir: Path) -> dict[str, Any]:
    archive = raw_dir / "HeliumDispersionDataSets.zip"
    extracted = raw_dir / "extracted"
    if not archive.is_file() or not extracted.is_dir():
        raise FileNotFoundError(
            "HeliumDispersionDataSets.zip and an extracted directory are required"
        )

    workbooks = sorted(extracted.glob("*.xls"))
    summaries = [_workbook_summary(path) for path in workbooks]
    return {
        "schema_version": 1,
        "artifact_type": "nist_helium_garage_public_archive_intake",
        "recorded_at": "2026-10-11",
        "source": {
            "title": "Experimental Characterization of Helium Dispersion in a 1/4-Scale Two-Car Residential Garage",
            "authors": ["William M. Pitts", "Jiann C. Yang", "Marco G. Fernandez"],
            "publisher": "National Institute of Standards and Technology",
            "technical_note": "NIST TN 1694 (March 2011)",
            "doi": "10.6028/NIST.TN.1694",
            "report_url": "https://www.nist.gov/publications/experimental-characterization-helium-dispersion-scale-two-car-residential-garage-nist",
            "archive_url": "https://www.nist.gov/el/fire/hydrogen-flammability-detection-and-fire-safety",
            "workbook_archive_url": "http://www.nist.gov/el/fire_protection/buildings/upload/HeliumDispersionDataSets.zip",
            "test_gas": "helium surrogate for hydrogen",
        },
        "archive": {
            "bytes": archive.stat().st_size,
            "sha256": _sha256(archive),
            "workbook_count": len(workbooks),
            "file_pattern": "{release_duration}-{vent_configuration}-{release_location}.xls",
            "release_durations_s": [3600, 14400],
            "vent_configurations": ["LC", "LR", "UC"],
            "release_locations": ["SLV", "SSV", "ULV"],
            "workbooks": summaries,
        },
        "reported_experiment_boundary": {
            "enclosure_internal_dimensions_m": [1.5, 1.5, 0.75],
            "scaled_from_full_scale": "6.096 m x 6.096 m x 3.048 m two-car garage",
            "nominal_release_volume_flow_l_min": {
                "one_hour": 14.8,
                "four_hour": 3.71,
            },
            "measured_release_volume_flow_l_min": {
                "one_hour": {"value": 14.92, "uncertainty": 0.15},
                "four_hour": {"value": 3.54, "uncertainty": 0.06},
            },
            "vent_options": {
                "LC": "single 2.40 cm square vent, 5.76 cm2",
                "LR": "single 3.05 cm square vent, 9.30 cm2",
                "UC": "two 2.15 cm square vents, total 9.25 cm2",
            },
            "sensor_channels": "eight helium volume-fraction channels and differential pressure",
            "sensor_sampling": "approximately 1 s rows in the workbook archive",
        },
        "eligibility_decision": {
            "schema_integrity_pass": len(workbooks) == 18 and all(
                item["channel_count"] >= 9 for item in summaries
            ),
            "component_spatial_ventilation_candidate": True,
            "prospective_validation_eligible": False,
            "full_loop_hrs_validation_eligible": False,
            "runtime_parameter_application": False,
            "reason": (
                "The archive was opened after the existing spatial protocol was frozen. "
                "The report uses helium, and its 60-second delayed release is not cross-walked "
                "to the workbook-relative time axis. No post-access outcome may be used to tune "
                "detector placement, alarm thresholds, hydrogen concentration conversion, ESD or safety distance."
            ),
        },
        "claim_boundary": (
            "This intake proves archive integrity and records a reproducible reduced-scale "
            "ventilation/spatial component candidate. It does not validate hydrogen magnitude, "
            "outdoor station dispersion, detector hardware dynamics, ignition, ESD, safety distance, "
            "or synchronized station-to-vehicle performance."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data/public_validation/raw/nist_helium_garage_2011",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/nist_helium_garage_2011_intake_2026_10_11.json",
    )
    args = parser.parse_args()
    result = audit(args.raw_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "output": str(args.output),
        "workbook_count": result["archive"]["workbook_count"],
        "schema_integrity_pass": result["eligibility_decision"]["schema_integrity_pass"],
        "prospective_validation_eligible": result["eligibility_decision"]["prospective_validation_eligible"],
    }))


if __name__ == "__main__":
    main()
