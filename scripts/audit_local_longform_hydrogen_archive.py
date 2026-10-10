"""Create a privacy-bounded screen of a long-form hydrogen-system archive.

The input is a private local export with one measurement per row.  This audit
only retains aggregate counts and coarse duration.  It deliberately drops
paths, filenames, identifiers, channel names, raw values, and calendar dates
so that the result can be committed as research evidence without disclosing
the source organization or site.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {
    "entity_type",
    "entity_id",
    "key",
    "ts",
    "bool_v",
    "long_v",
    "dbl_v",
    "str_v",
}

FAMILY_PATTERNS = {
    "hydrogen_process": re.compile(r"h2|hydrogen|수소", re.I),
    "pressure": re.compile(r"press|pressure|압력", re.I),
    "temperature": re.compile(r"temp|temperature|온도", re.I),
    "flow_or_mass": re.compile(r"flow|mass|rate|유량|질량", re.I),
    "vehicle_or_dispenser": re.compile(r"vehicle|car|disp|nozzle|fuel|차량|디스펜|노즐", re.I),
    "controller_or_esd": re.compile(r"controller|valve|esd|trip|pcv|차단|밸브", re.I),
    "leak_or_fire": re.compile(r"leak|fire|flame|gas|누출|화재|가스", re.I),
}


def _present(value: str | None) -> bool:
    return (value or "").strip().lower() not in {"", "null", "none", "nan"}


def _parse_timestamp(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        # A few operational exports use integer milliseconds or seconds.
        try:
            number = float(value)
        except ValueError:
            return None
        if number > 10**12:
            number /= 1000.0
        try:
            parsed = datetime.fromtimestamp(number, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def audit_archive(source: Path) -> dict[str, Any]:
    row_count = 0
    entity_types: set[str] = set()
    entity_ids: set[str] = set()
    keys: set[str] = set()
    value_counts = {"bool_v": 0, "long_v": 0, "dbl_v": 0, "str_v": 0}
    family_key_counts = {family: 0 for family in FAMILY_PATTERNS}
    min_ts: datetime | None = None
    max_ts: datetime | None = None

    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise ValueError(f"long-form schema missing required columns: {missing}")
        for row in reader:
            row_count += 1
            entity_types.add((row.get("entity_type") or "").strip())
            entity_ids.add((row.get("entity_id") or "").strip())
            key = (row.get("key") or "").strip()
            keys.add(key)
            for field in value_counts:
                if _present(row.get(field)):
                    value_counts[field] += 1
            parsed = _parse_timestamp(row.get("ts") or "")
            if parsed is not None:
                min_ts = parsed if min_ts is None or parsed < min_ts else min_ts
                max_ts = parsed if max_ts is None or parsed > max_ts else max_ts

    for key in keys:
        for family, pattern in FAMILY_PATTERNS.items():
            if pattern.search(key):
                family_key_counts[family] += 1

    span_hours = None
    if min_ts is not None and max_ts is not None:
        span_hours = round((max_ts - min_ts).total_seconds() / 3600.0, 3)

    return {
        "schema_version": 1,
        "artifact_type": "privacy_bounded_local_longform_hydrogen_archive_screen",
        "recorded_at": "2026-10-11",
        "archive_alias": "local_longform_hydrogen_system_archive_anon_01",
        "decision": "COMPONENT_OR_STATION_SIDE_CANDIDATE_ONLY",
        "aggregate": {
            "row_count": row_count,
            "unique_entity_type_count": len(entity_types - {""}),
            "unique_entity_count": len(entity_ids - {""}),
            "unique_key_count": len(keys - {""}),
            "numeric_value_counts": {
                "long_v": value_counts["long_v"],
                "dbl_v": value_counts["dbl_v"],
            },
            "other_value_counts": {
                "bool_v": value_counts["bool_v"],
                "str_v": value_counts["str_v"],
            },
            "observed_span_hours": span_hours,
            "candidate_key_family_counts": family_key_counts,
        },
        "eligibility": {
            "real_local_measurement_archive": True,
            "station_or_component_side_diagnostics_supported": True,
            "synchronized_vehicle_receiving_vessel_trace_attested": False,
            "station_controller_cascade_esd_state_attested": False,
            "independent_full_loop_hrs_validation_eligible": False,
            "prospective_holdout_eligible": False,
            "runtime_parameter_application": False,
        },
        "coverage_effect": {
            "new_validation_gate_opened": False,
            "readiness_effect": "no_change",
            "reason": (
                "The archive contains long-form hydrogen-system measurements and is useful for "
                "component/station-side context, but the retained aggregate screen does not "
                "establish a synchronized station-to-vehicle receiving-vessel trace or an "
                "attested controller/ESD boundary."
            ),
        },
        "privacy": {
            "local_source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "entity_ids_published": False,
            "raw_rows_persisted": False,
            "absolute_timestamps_published": False,
            "calendar_dates_or_site_identity_published": False,
            "company_or_manufacturer_published": False,
        },
        "claim_boundary": (
            "This artifact is an aggregate screening record. It does not identify the source, "
            "publish raw measurements, attest engineering units or channel semantics, validate "
            "a vehicle fill, establish safety distances, or support field certification."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit_archive(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
