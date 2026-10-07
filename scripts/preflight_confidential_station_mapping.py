"""Preflight a custodian's restricted station mapping without reading rows.

The station-side calibration tools intentionally accept raw column names only
at runtime.  Before they inspect a measurement row, this command verifies that
the private mapping has no template placeholders, that the selected columns
exist in each controlled CSV/TXT header, and that an optional generic-role
attestation is sufficient for a station-boundary calibration.  Its report
contains aggregate counts and generic roles only: never source paths, original
headers, tag names, timestamps, or measurement values.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Iterable

try:  # Supports both ``python scripts/...`` and test-module imports.
    from audit_controlled_data_schema import _outside_repository
except ModuleNotFoundError:  # pragma: no cover - import style depends on launcher
    from scripts.audit_controlled_data_schema import _outside_repository


_PRIVACY_FLAGS = (
    "source_identifiers_published",
    "raw_rows_persisted",
    "absolute_timestamps_published",
    "tag_names_published",
    "source_paths_published",
)
_ATTESTATION_FLAGS = (
    "timebase_semantics_attested",
    "pressure_role_and_unit_semantics_attested",
    "temperature_role_and_unit_semantics_attested",
    "flow_role_and_unit_semantics_attested",
    "state_semantics_attested",
    "lifecycle_semantics_attested",
    "calibration_metadata_attested",
)
_SCALE_FIELDS = (
    "pressure_scale_pa_per_unit",
    "temperature_scale_k_per_unit",
    "temperature_offset_k",
    "flow_scale_kg_s_per_unit",
    "lifecycle_scale_per_unit",
)


def _placeholder(value: object) -> bool:
    return isinstance(value, str) and "<" in value and ">" in value


def _mapping_pairs(record: dict[str, Any], field: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Return generic role/source pairs while retaining no source name in errors."""

    problems: list[str] = []
    raw = record.get(field, [])
    if raw is None:
        return [], problems
    if not isinstance(raw, list):
        return [], [f"{field}_must_be_a_list"]
    pairs: list[tuple[str, str]] = []
    for item in raw:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
            or not item[0].strip()
            or not item[1].strip()
            or _placeholder(item[0])
            or _placeholder(item[1])
        ):
            problems.append(f"{field}_contains_unresolved_or_invalid_pair")
            continue
        pairs.append((item[0], item[1]))
    return pairs, problems


def _mapping_preconditions(record: dict[str, Any]) -> tuple[dict[str, object], list[str], list[str]]:
    """Check private-map shape, yielding only generic roles and safe issues."""

    problems: list[str] = []
    placeholders: list[str] = []
    time_column = record.get("time_column")
    time_index = record.get("time_column_index")
    if isinstance(time_column, str) and time_column.strip() and not _placeholder(time_column):
        mapped_time_column: str | None = time_column
    else:
        mapped_time_column = None
        if _placeholder(time_column):
            placeholders.append("time_column")
        if not isinstance(time_index, int) or time_index < 0:
            problems.append("time_column_or_nonnegative_time_column_index_required")
    pressure, pair_problems = _mapping_pairs(record, "pressure_columns")
    problems.extend(pair_problems)
    if not pressure:
        problems.append("at_least_one_pressure_column_required")
    temperature, pair_problems = _mapping_pairs(record, "temperature_columns")
    problems.extend(pair_problems)
    states, pair_problems = _mapping_pairs(record, "state_columns")
    problems.extend(pair_problems)
    lifecycle, pair_problems = _mapping_pairs(record, "lifecycle_columns")
    problems.extend(pair_problems)
    flow = record.get("flow_column")
    if flow is not None and (not isinstance(flow, str) or not flow.strip() or _placeholder(flow)):
        if _placeholder(flow):
            placeholders.append("flow_column")
        else:
            problems.append("flow_column_must_be_a_nonempty_string_or_null")
        flow = None
    for field in _SCALE_FIELDS:
        value = record.get(field)
        if _placeholder(value):
            placeholders.append(field)
            continue
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            problems.append(f"{field}_must_be_an_explicit_number")
        elif field != "temperature_offset_k" and float(value) <= 0.0:
            problems.append(f"{field}_must_be_positive")
    encoding = record.get("encoding")
    if not isinstance(encoding, str) or not encoding.strip() or _placeholder(encoding):
        if _placeholder(encoding):
            placeholders.append("encoding")
        else:
            problems.append("encoding_must_be_explicit")
        encoding = None
    time_format = record.get("time_format")
    time_is_absolute = record.get("time_is_absolute") is True
    if time_format is not None and (not isinstance(time_format, str) or not time_format.strip() or _placeholder(time_format)):
        if _placeholder(time_format):
            placeholders.append("time_format")
        else:
            problems.append("time_format_must_be_a_string_or_null")
        time_format = None
    if time_format is None and not time_is_absolute:
        problems.append("time_format_or_absolute_time_attestation_required")
    roles = ["station_pressure"] + [role for role, _ in temperature]
    authorized = record.get("authorized_boundary_roles")
    if not isinstance(authorized, list) or not all(isinstance(item, str) for item in authorized):
        problems.append("authorized_boundary_roles_must_be_a_string_list")
        authorized_roles: list[str] = []
    else:
        authorized_roles = list(authorized)
        if len(set(authorized_roles)) != len(authorized_roles):
            problems.append("authorized_boundary_roles_must_be_unique")
        unknown = set(authorized_roles) - set(roles)
        if unknown:
            problems.append("authorized_boundary_roles_include_unmapped_generic_role")
    if "station_pressure" not in authorized_roles:
        problems.append("station_pressure_must_be_an_authorized_boundary_role")
    columns = [column for _, column in pressure + temperature + states + lifecycle]
    if isinstance(flow, str):
        columns.append(flow)
    if mapped_time_column is not None:
        columns.append(mapped_time_column)
    return {
        "encoding": encoding,
        "time_column": mapped_time_column,
        "time_column_index": time_index if mapped_time_column is None else None,
        "source_columns": columns,
        "mapped_channel_families": [
            family for family, present in (
                ("pressure", bool(pressure)),
                ("temperature", bool(temperature)),
                ("flow", isinstance(flow, str)),
                ("discrete_state", bool(states)),
                ("lifecycle", bool(lifecycle)),
            ) if present
        ],
        "authorized_boundary_roles": authorized_roles,
        "temperature_boundary_role": record.get("temperature_boundary_role"),
        "time_format_present": isinstance(time_format, str),
        "time_is_absolute": time_is_absolute,
    }, problems, sorted(set(placeholders))


def _trace_files(input_data: Path) -> list[Path]:
    if input_data.is_file() and input_data.suffix.lower() in {".csv", ".txt"}:
        return [input_data]
    if input_data.is_dir():
        return sorted(
            item for item in input_data.rglob("*")
            if item.is_file() and item.suffix.lower() in {".csv", ".txt"}
        )
    return []


def _header(path: Path, encoding: str) -> tuple[str, ...] | None:
    try:
        with path.open("r", encoding=encoding, errors="strict", newline="") as handle:
            return tuple(next(csv.reader(handle), ()))
    except (OSError, UnicodeError, csv.Error):
        return None


def _attestation_status(
    record: dict[str, object] | None,
    authorized_roles: list[str],
) -> dict[str, object]:
    if record is None:
        return {
            "provided": False,
            "privacy_flags_all_false": False,
            "authorized_roles_match": False,
            "station_boundary_calibration_supported": False,
        }
    privacy_ok = all(record.get(key) is False for key in _PRIVACY_FLAGS)
    roles = record.get("authorized_boundary_roles")
    roles_match = isinstance(roles, list) and roles == authorized_roles
    flags = {field: record.get(field) is True for field in _ATTESTATION_FLAGS}
    station_supported = (
        privacy_ok
        and roles_match
        and flags["timebase_semantics_attested"]
        and flags["pressure_role_and_unit_semantics_attested"]
        and flags["calibration_metadata_attested"]
        and "station_pressure" in authorized_roles
    )
    return {
        "provided": True,
        "privacy_flags_all_false": privacy_ok,
        "authorized_roles_match": roles_match,
        **flags,
        "station_boundary_calibration_supported": station_supported,
    }


def preflight(
    input_data: Path,
    mapping_path: Path,
    *,
    attestation_path: Path | None = None,
) -> dict[str, object]:
    """Return an aggregate mapping-readiness report without reading data rows."""

    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        mapping = None
    if not isinstance(mapping, dict):
        return {
            "schema_version": 1,
            "artifact_type": "confidential_station_mapping_preflight",
            "mapping_parseable": False,
            "preflight_pass": False,
            "claim_boundary": "No measurement rows were read; mapping could not be parsed.",
        }
    description, problems, placeholders = _mapping_preconditions(mapping)
    attestation: dict[str, object] | None = None
    if attestation_path is not None:
        try:
            candidate = json.loads(attestation_path.read_text(encoding="utf-8"))
            attestation = candidate if isinstance(candidate, dict) else None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            problems.append("attestation_must_be_valid_json")
    files = _trace_files(input_data)
    encoding = description.get("encoding")
    # Do not inspect even a header once the mapping itself is incomplete.  A
    # missing encoding or placeholder should be fixed by the custodian first;
    # otherwise an unresolved template could misleadingly look like a logger
    # decoding failure.
    header_check_attempted = not problems and not placeholders and isinstance(encoding, str)
    headers = (
        [_header(path, str(encoding)) for path in files]
        if header_check_attempted
        else []
    )
    source_columns = description.get("source_columns") or []
    time_index = description.get("time_column_index")
    compatible = 0
    unreadable = 0
    for fields in headers:
        if fields is None:
            unreadable += 1
            continue
        has_columns = all(column in fields for column in source_columns)
        index_ok = not isinstance(time_index, int) or time_index < len(fields)
        if has_columns and index_ok:
            compatible += 1
    if not files:
        problems.append("no_csv_or_txt_trace_files_found")
    if header_check_attempted and unreadable:
        problems.append("one_or_more_trace_headers_unreadable_with_declared_encoding")
    if header_check_attempted and files and compatible != len(files):
        problems.append("mapping_columns_not_present_in_every_trace_header")
    attestation_status = _attestation_status(
        attestation,
        list(description.get("authorized_boundary_roles") or []),
    )
    preflight_pass = not problems and not placeholders and compatible == len(files) and bool(files)
    return {
        "schema_version": 1,
        "artifact_type": "confidential_station_mapping_preflight",
        "source_identifiers_published": False,
        "original_headers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "mapping_parseable": True,
        "trace_file_count": len(files),
        "header_check_attempted": header_check_attempted,
        "header_compatible_file_count": compatible,
        "unreadable_header_count": unreadable,
        "template_placeholder_fields": placeholders,
        "preflight_issues": sorted(set(problems)),
        "mapped_channel_families": description["mapped_channel_families"],
        "authorized_boundary_roles": description["authorized_boundary_roles"],
        "time_format_present": description["time_format_present"],
        "time_is_absolute": description["time_is_absolute"],
        "preflight_pass": preflight_pass,
        "attestation": attestation_status,
        "eligibility": {
            "station_boundary_calibration_supported": (
                preflight_pass
                and attestation_status["station_boundary_calibration_supported"] is True
            ),
            "temperature_boundary_supported": False,
            "recharge_state_calibration_supported": False,
            "full_station_vehicle_validation": False,
            "full_loop_holdout_eligible": False,
        },
        "claim_boundary": (
            "Header and private-map consistency only. This preflight reads no "
            "measurement rows and does not attest source units, physical role "
            "meaning, calibration, model accuracy, safety, or full-loop validation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight a private station mapping without reading logger rows."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attestation", type=Path)
    args = parser.parse_args()
    input_data = _outside_repository(args.input, label="input data")
    mapping = _outside_repository(args.mapping, label="mapping")
    output = _outside_repository(args.output, label="output")
    attestation = (
        _outside_repository(args.attestation, label="attestation")
        if args.attestation is not None else None
    )
    report = preflight(input_data, mapping, attestation_path=attestation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
