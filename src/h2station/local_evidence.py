"""Privacy-bounded local evidence coverage for the runtime API.

The local archive is owner-controlled and is intentionally not read by the
runtime.  Only the committed aggregate audit artifacts are loaded here.  The
result is suitable for an operator or UI to understand which claims the
current run can support without exposing raw rows, source paths, identifiers,
or equipment metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[2]
_DISCOVERY = _ROOT / "research/local_hydrogen_station_data_discovery_recheck_2026_10_09.json"
_DEEP_SCAN = _ROOT / "research/local_data_deep_scan_2026_10_09.json"
_CONTINUITY = _ROOT / "research/local_wide_equipment_continuity_recheck_2026_10_09.json"
_ADJACENT_PROCESS = _ROOT / "research/local_adjacent_hydrogen_data_discovery_2026_10_09.json"
_DOCUDATA_DISCOVERY = _ROOT / "research/local_docudata_full_discovery_2026_10_09.json"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("aggregate evidence artifact must contain an object")
    return value


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_rows_persisted": False,
        "source_paths_published": False,
        "source_filenames_published": False,
        "source_headers_published": False,
        "source_identifiers_published": False,
        "site_company_manufacturer_published": False,
        "calendar_dates_published": False,
    }


def _adjacent_process_summary() -> dict[str, Any] | None:
    """Return only aggregate counts for adjacent hydrogen-process material.

    This corpus is useful for process-context and sequence plausibility, but it
    is not silently treated as HRS station-to-vehicle telemetry.
    """

    try:
        record = _read_json(_ADJACENT_PROCESS)
        privacy = record.get("privacy") or {}
        process = (record.get("collections") or {}).get(
            "high_pressure_hydrogen_process"
        ) or {}
        liquid = (record.get("collections") or {}).get(
            "liquid_hydrogen_centre_context"
        ) or {}
        if (
            record.get("artifact_type")
            != "local_adjacent_hydrogen_process_data_discovery"
            or not all(value is False for value in privacy.values())
            or process.get("csv_event_log_count") != 18
            or process.get("csv_event_row_count") != 2_411_774
            or process.get("domain_classification")
            != "hydrogen_city_or_pipeline_process_context_not_HRS"
            or record.get("eligibility", {}).get(
                "station_side_runtime_parameter_application"
            ) is not False
            or record.get("eligibility", {}).get(
                "synchronized_station_dispenser_vehicle_validation"
            ) is not False
        ):
            return None
        return {
            "evidence_role": "privacy-bounded adjacent hydrogen-process inventory",
            "domain_classification": process.get("domain_classification"),
            "high_pressure_process": {
                "csv_event_log_count": process.get("csv_event_log_count"),
                "csv_event_row_count": process.get("csv_event_row_count"),
                "entity_key_count": process.get("entity_key_count"),
                "logical_key_count": process.get("logical_key_count"),
                "value_family_row_counts": process.get("value_family_row_counts") or {},
                "workbook_count": process.get("workbook_count"),
                "nontrivial_workbook_table_count": process.get(
                    "nontrivial_workbook_table_count"
                ),
                "time_semantics": process.get("time_semantics_documented_in_local_index"),
            },
            "liquid_hydrogen_centre_context": {
                "csv_file_count": liquid.get("csv_file_count"),
                "scenario_row_count": liquid.get("scenario_row_count"),
                "workbook_count": liquid.get("workbook_count"),
                "nontrivial_workbook_table_count": liquid.get(
                    "nontrivial_workbook_table_count"
                ),
            },
            "runtime_parameter_application": False,
            "station_to_vehicle_full_loop_validation": False,
            "claim_limit": record.get("claim_boundary"),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _docudata_discovery_summary() -> dict[str, Any] | None:
    """Return aggregate-only counts from the broad local document scan."""

    try:
        record = _read_json(_DOCUDATA_DISCOVERY)
        privacy = record.get("privacy") or {}
        broad = record.get("broad_scan") or {}
        refined = record.get("refined_header_screen") or {}
        eligibility = record.get("eligibility") or {}
        if (
            record.get("artifact_type") != "local_docudata_full_header_discovery"
            or not all(value is False for value in privacy.values())
            or broad.get("machine_readable_files_screened") != 38_528
            or broad.get("csv_tsv_headers_screened") != 12_804
            or refined.get("vehicle_pressure_temperature_flow_time_candidates") != 0
            or eligibility.get("eligible_synchronized_station_dispenser_vehicle_cohort") != 0
            or eligibility.get("runtime_parameter_application") is not False
        ):
            return None
        return {
            "evidence_role": "privacy-bounded local document discovery",
            "machine_readable_files_screened": broad.get("machine_readable_files_screened"),
            "csv_tsv_headers_screened": broad.get("csv_tsv_headers_screened"),
            "path_keyword_candidates": broad.get("path_keyword_candidates"),
            "vehicle_or_dispenser_keyword_candidates": broad.get(
                "vehicle_or_dispenser_keyword_candidates"
            ),
            "release_rig_or_jet_candidates": broad.get("release_rig_or_jet_candidates"),
            "vehicle_keyword_hits": refined.get("vehicle_keyword_hits"),
            "vehicle_pressure_temperature_flow_time_candidates": refined.get(
                "vehicle_pressure_temperature_flow_time_candidates"
            ),
            "eligible_synchronized_station_dispenser_vehicle_cohort": eligibility.get(
                "eligible_synchronized_station_dispenser_vehicle_cohort"
            ),
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": eligibility.get(
                "full_loop_external_validation_ready"
            ),
            "claim_limit": record.get("claim_boundary"),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def local_station_evidence_summary() -> dict[str, Any]:
    """Return a stable, privacy-bounded view of local evidence coverage.

    Missing or malformed audit artifacts fail closed.  A runtime outage or an
    incomplete checkout must never be interpreted as evidence that a
    station-to-vehicle validation cohort exists.
    """

    try:
        discovery = _read_json(_DISCOVERY)
        deep_scan = _read_json(_DEEP_SCAN)
        continuity = _read_json(_CONTINUITY)

        coverage = discovery["coverage_assessment"]
        measured = deep_scan["measured_station_bundle"]
        deep_decision = deep_scan["full_loop_decision"]
        inventory = continuity["inventory"]
        eligibility = continuity["eligibility"]
        header = discovery["independent_header_recheck"]

        result = {
            "status": "available",
            "evidence_role": "privacy_bounded_local_station_coverage",
            "privacy": _privacy_boundary(),
            "measured_station": {
                "csv_file_count": int(measured["csv_files"]),
                "deduplicated_row_count": int(measured["deduplicated_rows"]),
                "raw_storage_gib_rounded": float(measured["raw_storage_gib_rounded"]),
                "eligible_use": list(measured.get("eligible_use") or []),
            },
            "wide_equipment_continuity": {
                "file_count": int(inventory["wide_file_count"]),
                "row_count": int(inventory["wide_row_count"]),
                "median_sample_period_s": float(inventory["median_positive_interval_s"]),
                "maximum_sample_gap_s": float(inventory["maximum_positive_interval_s"]),
                "timestamp_parse_failures": int(inventory["timestamp_parse_failures"]),
                "negative_interval_count": int(inventory["negative_interval_count"]),
                "state_transition_count": int(inventory["state_transition_count"]),
                "station_equipment_continuity_screen_ready": bool(
                    eligibility["station_equipment_continuity_screen_ready"]
                ),
            },
            "coverage": {
                "local_station_data_is_sparse": bool(
                    coverage["local_station_data_is_sparse"]
                ),
                "station_side_dynamic_evidence_is_substantial": bool(
                    coverage["station_side_dynamic_evidence_is_substantial"]
                ),
                "vehicle_side_full_loop_validation_ready": bool(
                    coverage["vehicle_side_full_loop_validation_ready"]
                ),
                "quantitative_consequence_validation_ready": bool(
                    coverage["quantitative_consequence_validation_ready"]
                ),
                "full_loop_decision": str(deep_decision["decision"]),
                "header_vehicle_or_dispenser_candidates": int(
                    header["candidate_file_counts"]["vehicle_or_dispenser_expanded"]
                ),
            },
            "claim_boundary": (
                "Local evidence supports station-side pressure-cycle, cascade, "
                "recharge and equipment-state screening. It does not support a "
                "synchronized station-to-vehicle full-loop or site-specific "
                "consequence claim until the custodian attests the missing channels."
            ),
        }
        adjacent = _adjacent_process_summary()
        if adjacent is not None:
            result["adjacent_process"] = adjacent
        document_scan = _docudata_discovery_summary()
        if document_scan is not None:
            result["document_archive_discovery"] = document_scan
        return result
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {
            "status": "unavailable",
            "evidence_role": "privacy_bounded_local_station_coverage",
            "privacy": _privacy_boundary(),
            "coverage": {
                "local_station_data_is_sparse": None,
                "station_side_dynamic_evidence_is_substantial": None,
                "vehicle_side_full_loop_validation_ready": False,
                "quantitative_consequence_validation_ready": False,
                "full_loop_decision": "UNAVAILABLE",
            },
            "claim_boundary": (
                "Aggregate local evidence artifacts are unavailable or invalid; "
                "no validation claim is permitted."
            ),
        }
