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
_ASSET_SCREEN = _ROOT / "research/local_station_asset_screen_2026_10_09.json"
_REVALIDATION = _ROOT / "research/local_station_data_revalidation_2026_10_09.json"


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


def _station_asset_context_summary() -> dict[str, Any] | None:
    """Return aggregate operational/context assets without source identity.

    The station archive includes procedure tables, reconstructed trend sheets,
    engineering references and video.  They are useful for virtual response
    and topology work, but must not be presented as synchronized telemetry or
    independent validation.  Keep this projection deliberately aggregate so
    the API and LLM can explain the evidence boundary without exposing paths,
    tags or raw rows.
    """

    try:
        record = _read_json(_ASSET_SCREEN)
        privacy = record.get("privacy") or {}
        if (
            record.get("artifact_type") != "local_station_asset_screen"
            or not privacy
            or not all(value is False for value in privacy.values())
        ):
            return None

        bundles = {
            str(item.get("id")): item
            for item in record.get("station_specific_bundles") or []
            if isinstance(item, dict) and item.get("id")
        }
        scenario = bundles.get("local_liquid_hydrogen_operational_scenario_matrix") or {}
        operation = bundles.get("local_tank_operation_sequence_logs") or {}
        minute = bundles.get("local_tank_minute_trend_logs") or {}
        timestamp = bundles.get("local_timestamp_differential_logs") or {}
        recovered = bundles.get("local_video_recovered_storage_logs") or {}
        engineering = bundles.get("local_engineering_reference_bundle") or {}
        equipment_media = bundles.get("local_equipment_media_bundle") or {}
        video = bundles.get("local_operational_video_collection") or {}
        coverage = record.get("coverage_assessment") or {}

        return {
            "evidence_role": "privacy-bounded local station asset context",
            "scenario_matrix": {
                "scenario_table_count": scenario.get("csv_file_count"),
                "scenario_step_count": scenario.get("scenario_step_rows"),
                "hazard_fields_populated": scenario.get("nonempty_consequence_fields") or {},
                "eligible_use": scenario.get("eligible_use") or [],
            },
            "operational_logs": {
                "operation_workbook_count": operation.get("workbook_count"),
                "operation_sheet_count": operation.get("sheet_count"),
                "operation_row_count": operation.get("nonempty_rows"),
                "minute_trend_workbook_count": minute.get("workbook_count"),
                "minute_trend_sheet_count": minute.get("sheet_count"),
                "minute_trend_row_count": minute.get("nonempty_rows"),
                "timestamp_differential_sheet_count": timestamp.get("sheet_count"),
                "timestamp_differential_row_count": timestamp.get("nonempty_rows"),
                "recovered_storage_sheet_count": recovered.get("sheet_count"),
                "recovered_storage_row_count": recovered.get("nonempty_rows"),
                "eligible_use": sorted({
                    str(value)
                    for bundle in (operation, minute, timestamp, recovered)
                    for value in bundle.get("eligible_use") or []
                }),
            },
            "engineering_and_visual_context": {
                "engineering_document_count": engineering.get("document_count"),
                "engineering_pdf_count": engineering.get("pdf_count"),
                "engineering_image_count": engineering.get("image_count"),
                "equipment_image_count": equipment_media.get("image_count"),
                "equipment_video_count": equipment_media.get("video_count"),
                "operational_video_count": video.get("file_count"),
                "operational_video_complete_count": video.get("complete_container_count"),
                "operational_video_incomplete_count": video.get("incomplete_or_unreadable_container_count"),
                "eligible_use": sorted({
                    str(value)
                    for bundle in (engineering, equipment_media, video)
                    for value in bundle.get("eligible_use") or []
                }),
            },
            "claim_boundary": str(record.get("claim_boundary") or ""),
            "coverage": {
                "local_station_data_is_sparse": coverage.get("local_station_data_is_sparse"),
                "station_side_dynamic_evidence_is_substantial": coverage.get(
                    "station_side_dynamic_evidence_is_substantial"
                ),
                "local_hazop_scenario_coverage_is_substantial": coverage.get(
                    "local_hazop_scenario_coverage_is_substantial"
                ),
                "vehicle_side_full_loop_validation_ready": coverage.get(
                    "vehicle_side_full_loop_validation_ready"
                ),
                "quantitative_consequence_validation_ready": coverage.get(
                    "quantitative_consequence_validation_ready"
                ),
            },
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _local_station_revalidation_summary() -> dict[str, Any] | None:
    """Expose the latest aggregate revalidation without reading raw rows.

    This is intentionally a second integrity boundary in addition to the
    discovery index.  The runtime must fail closed if the revalidation record
    is stale, malformed, or contains any privacy surface.  A passing record
    strengthens station-side evidence visibility only; it never enables a
    vehicle/full-loop claim or changes model parameters.
    """

    try:
        record = _read_json(_REVALIDATION)
        privacy = record.get("privacy") or {}
        measured = record.get("measured_station_bundle") or {}
        sampled = record.get("sampled_candidate_manifest") or {}
        broad = record.get("broader_local_screen") or {}
        decision = record.get("decision") or {}
        if (
            record.get("artifact_type") != "local_station_data_revalidation"
            or record.get("status") != "repeat_audit_matches_committed_inventory"
            or not privacy
            or not all(value is False for value in privacy.values())
            or measured.get("csv_files") != 33
            or measured.get("total_csv_gib") != 4.749
            or measured.get("physical_rows") != 59_272_300
            or measured.get("deduplicated_rows") != 56_854_143
            or measured.get("vehicle_or_dispenser_header_candidates") != 0
            or sampled.get("sampled_table_count") != 20
            or sampled.get("sampled_rows_per_table") != 2_000
            or broad.get("machine_readable_files_screened") != 38_528
            or broad.get("csv_tsv_headers_screened") != 12_804
            or broad.get("refined_csv_files_screened") != 13_050
            or broad.get("synchronized_station_dispenser_vehicle_candidates") != 0
            or decision.get("local_data_is_sparse") is not False
            or decision.get("station_side_replay_and_chronological_holdouts_supported") is not True
            or decision.get("full_loop_external_validation_supported") is not False
            or decision.get("runtime_parameter_application") is not False
        ):
            return None
        return {
            "evidence_role": "privacy-bounded repeated local HRS data revalidation",
            "generated_at": record.get("generated_at"),
            "inventory": {
                "csv_file_count": measured.get("csv_files"),
                "storage_gib": measured.get("total_csv_gib"),
                "physical_row_count": measured.get("physical_rows"),
                "deduplicated_row_count": measured.get("deduplicated_rows"),
                "schema_width_file_counts": measured.get("schema_width_file_counts") or {},
            },
            "sampled_candidate_manifest": {
                "sampled_table_count": sampled.get("sampled_table_count"),
                "sampled_rows_per_table": sampled.get("sampled_rows_per_table"),
                "coverage_classes": sampled.get("coverage_classes") or {},
            },
            "broader_local_screen": {
                "machine_readable_files_screened": broad.get("machine_readable_files_screened"),
                "csv_tsv_headers_screened": broad.get("csv_tsv_headers_screened"),
                "refined_csv_files_screened": broad.get("refined_csv_files_screened"),
                "synchronized_station_dispenser_vehicle_candidates": broad.get(
                    "synchronized_station_dispenser_vehicle_candidates"
                ),
            },
            "decision": {
                "local_data_is_sparse": decision.get("local_data_is_sparse"),
                "station_side_replay_and_chronological_holdouts_supported": decision.get(
                    "station_side_replay_and_chronological_holdouts_supported"
                ),
                "full_loop_external_validation_supported": decision.get(
                    "full_loop_external_validation_supported"
                ),
                "runtime_parameter_application": decision.get(
                    "runtime_parameter_application"
                ),
            },
            "claim_boundary": str(record.get("claim_boundary") or ""),
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
        asset_context = _station_asset_context_summary()
        if asset_context is not None:
            result["station_asset_context"] = asset_context
        revalidation = _local_station_revalidation_summary()
        if revalidation is not None:
            result["station_data_revalidation"] = revalidation
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
