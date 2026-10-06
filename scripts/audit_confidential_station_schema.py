"""Create a privacy-bounded schema inventory for an owner-controlled CSV bundle.

Only headers, file-size buckets and a few timestamp parse checks are inspected.
Raw rows, paths, filenames, identifiers and calendar values are never written to
the output.  The resulting artifact is suitable for deciding which station-side
model channels can be calibrated and which still require custodian attestation.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Iterable


ROLE_PATTERNS = {
    "pressure": ("pressure", "pt_", "pi_"),
    "temperature": ("temperature", "temp", "tt_"),
    "flow": ("flow", "mfm", "fqi", "mass", "rate"),
    "discrete_state": ("status", "alarm", "xv_", "valve", "run", "load"),
    "lifecycle": ("lifecycle", "cycle", "_cnt", "count"),
}
CHANNEL_FAMILY_PATTERNS = {
    # These are intentionally coarse, privacy-bounded families.  They are
    # used to decide which engineering roles need custodian attestation; the
    # individual tag names never enter the committed artifact.
    "compressor_pressure": ("comp.ai.pt_", "comp.ai.pi_"),
    "compressor_temperature": ("comp.ai.tt_", "comp.ai.temp"),
    "station_pressure": ("sta.pt_", "pi_", "pt_"),
    "station_temperature": ("sta.tt_", "ti_", "tt_", "temp"),
    "flow_rate": ("_rate", "mfm_f", "flow"),
    "flow_totalizer": ("_acc", "total", "mfm"),
    "valve_state": ("status.xv_", "xv_", "valve"),
    "alarm_state": ("alarm",),
    "lifecycle_counter": ("lifecycle", "_cnt", "count"),
    "vehicle_side": (
        "vehicle", "fcv", "nozzle", "receptacle", "dispenser", "car",
        "차량", "수소차", "노즐", "리셉터클", "디스펜서", "충전기",
    ),
}
SIZE_BUCKETS = ("<1MiB", "1-100MiB", "100-500MiB", ">=500MiB")
TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%m/%d/%Y %I:%M:%S %p",
    "%Y %m %d %H:%M:%S",
)


def _encoding_and_header(path: Path) -> tuple[str, list[str]]:
    raw = path.open("rb").read(256 * 1024)
    for encoding in ("utf-8-sig", "cp949", "euc-kr", "latin-1"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        line = text.splitlines()[0] if text.splitlines() else ""
        delimiter = "," if line.count(",") >= line.count(";") else ";"
        fields = next(csv.reader([line], delimiter=delimiter), [])
        if len(fields) > 1:
            return encoding, [field.strip() for field in fields]
    return "utf-8-sig", []


def _sample_rows(path: Path, encoding: str, headers: list[str], limit: int = 6) -> list[list[str]]:
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        first = handle.readline()
        delimiter = "," if first.count(",") >= first.count(";") else ";"
        reader = csv.reader(handle, delimiter=delimiter)
        return [row for _, row in zip(range(limit), reader)]


def _parse_timestamp(value: str) -> bool:
    value = value.strip().strip("\ufeff")
    for fmt in TIMESTAMP_FORMATS:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            pass
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", value))


def _size_bucket(size: int) -> str:
    mib = 1024 * 1024
    if size < mib:
        return "<1MiB"
    if size < 100 * mib:
        return "1-100MiB"
    if size < 500 * mib:
        return "100-500MiB"
    return ">=500MiB"


def _files(root: Path) -> list[tuple[str, Path]]:
    files = sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() == ".csv"
    )
    group_names = []
    for path in files:
        parts = path.parent.relative_to(root).parts
        group_names.append(parts[0] if parts else "__root__")
    groups = sorted(set(group_names))
    group_ids = {name: f"source_bundle_{index + 1}" for index, name in enumerate(groups)}
    return [
        (
            group_ids[
                (path.parent.relative_to(root).parts[0]
                 if path.parent != root else "__root__")
            ],
            path,
        )
        for path in files
    ]


def audit(root: Path) -> dict[str, object]:
    files = _files(root)
    bundles: dict[str, dict[str, object]] = {}
    channel_counts = {role: 0 for role in ROLE_PATTERNS}
    files_with_roles = {role: 0 for role in ROLE_PATTERNS}
    family_counts = {family: 0 for family in CHANNEL_FAMILY_PATTERNS}
    family_file_counts = {family: 0 for family in CHANNEL_FAMILY_PATTERNS}
    timestamp_detected = 0
    timestamp_parseable = 0
    size_buckets = {bucket: 0 for bucket in SIZE_BUCKETS}

    for bundle_id, path in files:
        if path.suffix.lower() not in {".csv", ".csvx", ".txt"}:
            continue
        encoding, headers = _encoding_and_header(path)
        normalized = [header.strip().lower() for header in headers]
        roles_for_file: set[str] = set()
        for role, patterns in ROLE_PATTERNS.items():
            count = sum(
                1 for header in normalized
                if any(pattern in header for pattern in patterns)
            )
            if count:
                channel_counts[role] += count
                files_with_roles[role] += 1
                roles_for_file.add(role)
        for family, patterns in CHANNEL_FAMILY_PATTERNS.items():
            count = sum(
                1 for header in normalized
                if any(pattern in header for pattern in patterns)
            )
            if count:
                family_counts[family] += count
                family_file_counts[family] += 1
        timestamp_index = next(
            (index for index, header in enumerate(normalized)
             if any(token in header for token in ("time", "date", "local"))),
            None,
        )
        rows = _sample_rows(path, encoding, headers)
        if timestamp_index is None and rows:
            timestamp_index = 0
        if timestamp_index is not None:
            timestamp_detected += 1
            if any(timestamp_index < len(row) and _parse_timestamp(row[timestamp_index]) for row in rows):
                timestamp_parseable += 1
        size_buckets[_size_bucket(path.stat().st_size)] += 1
        state = bundles.setdefault(bundle_id, {"file_count": 0, "size_buckets": {bucket: 0 for bucket in SIZE_BUCKETS}, "role_file_counts": {role: 0 for role in ROLE_PATTERNS}})
        state["file_count"] = int(state["file_count"]) + 1
        state["size_buckets"][_size_bucket(path.stat().st_size)] += 1
        for role in roles_for_file:
            state["role_file_counts"][role] += 1

    machine_readable_unit_dictionary = any(
        path.suffix.lower() in {".json", ".yaml", ".yml"} and "unit" in path.name.lower()
        for path in root.rglob("*") if path.is_file()
    )
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_schema_audit",
        "recorded_at": datetime.now().strftime("%Y-%m"),
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "file_count": sum(int(bundle["file_count"]) for bundle in bundles.values()),
        "source_bundle_count": len(bundles),
        "size_buckets": size_buckets,
        "bundles": bundles,
        "signal_inventory": {
            "tagged_channel_counts": channel_counts,
            "files_with_tagged_roles": files_with_roles,
            "privacy_bounded_channel_families": family_counts,
            "files_with_channel_families": family_file_counts,
        },
        "timestamp_screen": {
            "files_with_detectable_timestamp": timestamp_detected,
            "files_with_parseable_timestamp_sample": timestamp_parseable,
            "calendar_values_persisted": False,
        },
        "unit_attestation": {
            "machine_readable_unit_dictionary_found": machine_readable_unit_dictionary,
            "pressure_units_attested": False,
            "temperature_units_attested": False,
            "flow_units_attested": False,
            "state_semantics_attested": False,
            "action": "Require custodian unit and tag-semantics confirmation before fitting untrusted channels.",
        },
        "eligibility": {
            "station_side_schema_intake_supported": bool(channel_counts["pressure"]),
            "station_pressure_calibration_candidate": bool(channel_counts["pressure"]),
            "equipment_state_model_candidate": bool(channel_counts["discrete_state"]),
            "temperature_or_flow_parameter_fit_deferred": True,
            "full_station_vehicle_validation": False,
            "full_loop_holdout_eligible": False,
            "vehicle_side_channel_family_count": family_counts["vehicle_side"],
            "station_side_component_families_present": [
                family for family in (
                    "compressor_pressure", "compressor_temperature",
                    "station_pressure", "station_temperature", "flow_rate",
                    "flow_totalizer", "valve_state", "alarm_state",
                    "lifecycle_counter",
                ) if family_counts[family] > 0
            ],
        },
        "claim_boundary": "Schema and channel-presence intake only. This audit does not attest units, calibration, physical correctness, station safety, vehicle-side accuracy or full-loop validation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
