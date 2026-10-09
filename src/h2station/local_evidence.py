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
_DATA_COVERAGE = _ROOT / "research/data_coverage_summary_2026_10_10.json"
_VALIDATION_GAP_TRIAGE = _ROOT / "research/validation_gap_triage_2026_10_10.json"
_KHK_ACCIDENTS = _ROOT / "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json"
_ACCIDENTAL_RELEASE = _ROOT / "research/accidental_self_ignition_public_evidence_2026_10_04.json"
_EXPERIMENTAL_BENCHMARKS = _ROOT / "research/public_experimental_benchmarks_2026_10_06.json"
_CARB_BENCHMARK = _ROOT / "research/carb_2024_hrs_inuse_field_benchmark_2026_10_08.json"
_STRIEDNIG_DIAGNOSTIC = _ROOT / "research/striednig_hyddown_diagnostic_result_2026_10_10.json"
_NREL_HDVS_BOUNDARY = _ROOT / "research/nrel_hdvs_raw_trace_boundary_2026_10_05.json"
_NREL_HDVS_RESULT = _ROOT / "research/nrel_hdvs_boundary_screen_2026_10_10.json"


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


def validation_evidence_summary() -> dict[str, Any]:
    """Return the public/privacy-safe validation surface for the operator UI.

    This is deliberately separate from ``local_station_evidence_summary``:
    the latter describes the owner-controlled archive, while this view joins
    the public/component evidence ledger with the unresolved-gate triage.  It
    contains no raw rows, source paths, filenames, site identity, or model
    parameters and never upgrades a diagnostic result to a validation claim.
    """

    privacy = {
        "raw_rows_persisted": False,
        "source_paths_published": False,
        "source_filenames_published": False,
        "source_identifiers_published": False,
        "site_company_manufacturer_published": False,
        "calendar_dates_published": False,
    }
    try:
        coverage = _read_json(_DATA_COVERAGE)
        triage = _read_json(_VALIDATION_GAP_TRIAGE)
        readiness = coverage.get("readiness") or {}
        overall = triage.get("overall") or {}
        interpretation = triage.get("interpretation") or {}
        if (
            coverage.get("artifact_type") != "privacy_bounded_data_coverage_summary"
            or triage.get("schema_version") != 1
            or not isinstance(coverage.get("validated_or_actionable_now"), list)
            or not isinstance(triage.get("unresolved_gates"), list)
            or overall.get("full_user_objective_ready") is not False
        ):
            raise ValueError("validation evidence artifacts failed provenance checks")

        usable = []
        for item in coverage["validated_or_actionable_now"]:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            usable.append({
                "id": str(item["id"]),
                "status": str(item.get("status") or "UNKNOWN"),
                "coverage": item.get("coverage") or {},
                "allowed_claim": str(item.get("allowed_claim") or ""),
                "not_allowed": str(item.get("not_allowed") or ""),
            })
        unresolved = []
        for item in triage["unresolved_gates"]:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            unresolved.append({
                "id": str(item["id"]),
                "status": str(item.get("status") or "UNKNOWN"),
                "bucket": str(item.get("bucket") or "UNKNOWN"),
                "next_action": str(item.get("next_action") or ""),
                "claim_boundary": str(item.get("claim_boundary") or ""),
            })
        return {
            "status": "available",
            "evidence_role": "privacy_bounded_validation_surface",
            "privacy": privacy,
            "readiness": {
                "ijhe_gate_counts": readiness.get("ijhe_gate_counts") or {},
                "bounded_submission_ready": readiness.get("bounded_submission_ready") is True,
                "full_user_objective_ready": overall.get("full_user_objective_ready") is True,
            },
            "interpretation": {
                "data_volume_is_primary_blocker": interpretation.get(
                    "data_volume_is_primary_blocker"
                ) is True,
                "primary_blocker": str(interpretation.get("primary_blocker") or ""),
            },
            "validated_or_actionable_now": usable,
            "unresolved_gates": unresolved,
            "minimum_next_input": coverage.get("minimum_next_input") or {},
            "evidence_inventory": public_evidence_inventory_summary(),
            "claim_boundary": str(coverage.get("claim_boundary") or ""),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {
            "status": "unavailable",
            "evidence_role": "privacy_bounded_validation_surface",
            "privacy": privacy,
            "readiness": {
                "ijhe_gate_counts": {},
                "bounded_submission_ready": False,
                "full_user_objective_ready": False,
            },
            "interpretation": {
                "data_volume_is_primary_blocker": None,
                "primary_blocker": "validation evidence artifacts unavailable",
            },
            "validated_or_actionable_now": [],
            "unresolved_gates": [],
            "minimum_next_input": {},
            "evidence_inventory": public_evidence_inventory_summary(),
            "claim_boundary": "Evidence artifacts are unavailable; no validation claim is permitted.",
        }


def public_evidence_inventory_summary() -> dict[str, Any]:
    """Return counts and claim-bounded roles for public evidence sources.

    The UI needs to show which evidence families were used, but it must not
    expose local source identity or imply that an accident inventory is a
    probability estimate.  Missing artifacts fail closed individually.
    """

    result: dict[str, Any] = {
        "public_accident_reports": {
            "status": "unavailable",
            "report_count": 0,
            "incident_code_count": 0,
            "station_relevant_incident_code_count": 0,
            "qualitative_grounding_eligible": False,
            "full_loop_holdout_eligible": False,
        },
        "public_accidental_release": {
            "status": "unavailable",
            "experiment_count": 0,
            "ignition_observed_case_count": 0,
            "no_ignition_case_count": 0,
            "source_doi": None,
            "consequence_grounding_eligible": False,
            "full_loop_holdout_eligible": False,
        },
        "public_experimental_benchmarks": {
            "status": "unavailable",
            "source_count": 0,
            "actual_hydrogen_archive_count": 0,
            "actual_hydrogen_rows_screened": 0,
            "aggregate_operating_context": [],
            "full_loop_holdout_eligible": False,
        },
        "public_field_benchmark": {
            "status": "unavailable",
            "stations_tested": 0,
            "stations_passing_all_fueling_metrics": 0,
            "full_loop_holdout_eligible": False,
        },
        "public_type_i_filling_diagnostic": {
            "status": "unavailable",
            "case_count": 0,
            "gas_temperature_rmse_k": [],
            "gas_temperature_peak_absolute_error_k": [],
            "runtime_parameter_application": False,
            "full_loop_holdout_eligible": False,
        },
        "public_station_tank_boundary": {
            "status": "unavailable",
            "sample_count": 0,
            "duration_s": None,
            "tank_count": 0,
            "hose_pressure_temperature_present": False,
            "tank_pressure_temperature_mass_present": False,
            "partial_station_to_tank_boundary_eligible": False,
            "full_loop_holdout_eligible": False,
            "rights_limited": False,
            "screening_status": "unavailable",
            "screening_pass_count": None,
            "screening_pass_fraction": None,
            "pressure_rmse_mpa": None,
            "temperature_rmse_c": None,
            "mass_rmse_kg": None,
            "pressure_final_error_mpa": None,
            "parameter_tuning": None,
        },
    }
    try:
        record = _read_json(_KHK_ACCIDENTS)
        coverage = record.get("coverage") or {}
        eligibility = record.get("eligibility") or {}
        if record.get("status") == "public_khk_accident_report_inventory_captured":
            result["public_accident_reports"] = {
                "status": "available",
                "report_count": int(coverage.get("pdf_report_count") or 0),
                "incident_code_count": int(coverage.get("incident_code_count") or 0),
                "station_relevant_incident_code_count": int(
                    coverage.get("station_relevant_incident_code_count") or 0
                ),
                "qualitative_grounding_eligible": eligibility.get(
                    "qualitative_scenario_grounding_eligible"
                ) is True,
                "full_loop_holdout_eligible": eligibility.get(
                    "full_loop_station_vehicle_holdout_eligible"
                ) is True,
            }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass
    try:
        record = _read_json(_ACCIDENTAL_RELEASE)
        source = record.get("source") or {}
        findings = record.get("reported_findings") or {}
        eligibility = record.get("eligibility") or {}
        if record.get("status") == "public_accidental_release_ignition_evidence_captured":
            result["public_accidental_release"] = {
                "status": "available",
                "experiment_count": int(findings.get("experiment_count") or 0),
                "ignition_observed_case_count": int(
                    findings.get("ignition_observed_case_count") or 0
                ),
                "no_ignition_case_count": int(findings.get("no_ignition_case_count") or 0),
                "source_doi": str(source.get("zenodo_doi") or "") or None,
                "consequence_grounding_eligible": eligibility.get(
                    "consequence_and_ignition_grounding_eligible"
                ) is True,
                "full_loop_holdout_eligible": eligibility.get(
                    "full_loop_station_vehicle_holdout_eligible"
                ) is True,
            }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass
    try:
        record = _read_json(_EXPERIMENTAL_BENCHMARKS)
        sources = record.get("sources") or []
        actual = next(
            (item for item in sources if item.get("id") == "USN_OPEN_CHANNEL_ACTUAL_H2_2025"),
            {},
        )
        aggregate = actual.get("aggregate") or {}
        if record.get("status") == "citation_bounded_aggregate_benchmarks":
            # Keep this projection compact enough for the operator evidence
            # panel while retaining the actual published operating ranges.
            # It deliberately excludes raw rows, private source identity and
            # any parameter-fit claim.
            context_fields = {
                "NREL_HDVS_2022_TANK_HOSE_TRACE": (
                    "sample_count", "duration_s", "tank_count",
                    "reported_transfer_kg", "reported_start_pressure_mpa",
                    "reported_end_pressure_mpa", "ambient_temperature_c",
                ),
                "KGS_HRS_SIX_SCENARIO_AGGREGATE_2025": (
                    "reported_scenario_count", "temperature_accuracy_r2_mean_percent",
                    "pressure_accuracy_r2_mean_percent", "reported_final_temperature_mean_c",
                    "reported_final_pressure_mean_mpa", "reported_fueling_time_mean_s",
                    "reported_fueling_time_min_s", "reported_fueling_time_max_s",
                ),
                "NREL_HD_FAST_FLOW_2024_REPORT": (
                    "mass_transfer_kg", "total_fill_time_s", "fueling_time_s",
                    "average_mass_flow_g_s", "peak_mass_flow_g_s", "aprr_mpa_min",
                    "starting_pressure_mpa", "ending_pressure_mpa", "ambient_temperature_c",
                    "protocol",
                ),
                "NIU_FULL_SCALE_HRS_LEAKAGE_2025": (
                    "release_pressure_mpa_levels", "nozzle_geometry_classes",
                    "parallel_dispenser_count", "canopy_height_m",
                    "wind_observation_h2_volpct_threshold",
                ),
                "USN_OPEN_CHANNEL_ACTUAL_H2_2025": (
                    "archive_count", "total_rows_screened", "sensor_count_per_archive",
                    "median_sample_interval_s", "median_experiment_duration_s",
                    "peak_mass_flow_g_s_range", "maximum_filling_pressure_bar_range",
                    "maximum_sensor_h2_volpct_range",
                ),
                "FCH2RAIL_D61_350BAR_REPORT": (
                    "average_flow_min_g_s", "average_flow_max_g_s",
                    "average_refuelling_speed_min_kg_min", "average_refuelling_speed_max_kg_min",
                    "supply_pressure_mpa",
                ),
            }
            aggregate_context = []
            for source in sources:
                if not isinstance(source, dict) or not source.get("id"):
                    continue
                fields = context_fields.get(str(source["id"]))
                aggregate = source.get("aggregate") or {}
                if not fields or not isinstance(aggregate, dict):
                    continue
                selected = {
                    field: aggregate[field]
                    for field in fields
                    if field in aggregate
                    and isinstance(aggregate[field], (str, int, float, list))
                    and not isinstance(aggregate[field], bool)
                }
                if selected:
                    aggregate_context.append({
                        "id": str(source["id"]),
                        "title": str(source.get("title") or ""),
                        "url": str(source.get("url") or ""),
                        "raw_rows_public": source.get("raw_rows_public") is True,
                        "aggregate": selected,
                        "eligible_for": [
                            str(value) for value in source.get("eligible_for") or []
                        ],
                        "not_eligible_for": [
                            str(value) for value in source.get("not_eligible_for") or []
                        ],
                    })
            result["public_experimental_benchmarks"] = {
                "status": "available",
                "source_count": len(sources),
                "actual_hydrogen_archive_count": int(aggregate.get("archive_count") or 0),
                "actual_hydrogen_rows_screened": int(aggregate.get("total_rows_screened") or 0),
                "aggregate_operating_context": aggregate_context,
                "full_loop_holdout_eligible": any(
                    item.get("id") == "USN_OPEN_CHANNEL_ACTUAL_H2_2025"
                    and "station-to-vehicle or full-loop holdout" not in " ".join(
                        item.get("not_eligible_for") or []
                    ).lower()
                    for item in sources
                ),
            }
            # The source is deliberately a component/dispersion dataset.  Keep
            # this false even if a malformed source description contains an
            # ambiguous phrase.
            result["public_experimental_benchmarks"]["full_loop_holdout_eligible"] = False
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass
    try:
        record = _read_json(_CARB_BENCHMARK)
        population = record.get("population") or {}
        eligibility = record.get("eligibility") or {}
        if record.get("artifact_type") == "public_real_station_field_benchmark":
            result["public_field_benchmark"] = {
                "status": "available",
                "stations_tested": int(population.get("stations_tested") or 0),
                "stations_passing_all_fueling_metrics": int(
                    population.get("stations_passing_all_nine_fueling_performance_metrics") or 0
                ),
                "full_loop_holdout_eligible": eligibility.get(
                    "full_loop_external_holdout"
                ) is True,
            }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass
    try:
        record = _read_json(_STRIEDNIG_DIAGNOSTIC)
        eligibility = record.get("eligibility") or {}
        cases = record.get("cases") or []
        if (
            record.get("artifact_type") == "public_type_i_filling_thermal_diagnostic"
            and record.get("evidence_role") == "post_access_public_component_diagnostic"
            and isinstance(cases, list)
            and len(cases) == 3
            and eligibility.get("runtime_parameter_application") is False
            and eligibility.get("full_loop_station_vehicle_validation_eligible") is False
            and all(isinstance(case, dict) for case in cases)
        ):
            result["public_type_i_filling_diagnostic"] = {
                "status": "available",
                "case_count": len(cases),
                "gas_temperature_rmse_k": [
                    float((case.get("metrics") or {}).get("gas_temperature_rmse_k"))
                    for case in cases
                ],
                "gas_temperature_peak_absolute_error_k": [
                    float((case.get("metrics") or {}).get("gas_temperature_peak_absolute_error_k"))
                    for case in cases
                ],
                "runtime_parameter_application": False,
                "full_loop_holdout_eligible": False,
            }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass
    try:
        record = _read_json(_NREL_HDVS_BOUNDARY)
        source = record.get("source") or {}
        experiment = record.get("experiment") or {}
        boundary = record.get("boundary_check") or {}
        eligibility = record.get("eligibility") or {}
        rights = str(source.get("license") or "").casefold()
        if (
            record.get("status") == "NREL_HDVS_RAW_TRACE_BOUNDARY_RECHECKED"
            and boundary.get("workbook_present_and_hash_verified") is True
            and boundary.get("physical_measurement_trace") is True
            and boundary.get("hose_pressure_and_temperature_present") is True
            and boundary.get("tank_pressure_temperature_mass_present") is True
            and eligibility.get("partial_station_to_tank_boundary_eligible") is True
        ):
            result["public_station_tank_boundary"] = {
                "status": "available",
                "sample_count": int(experiment.get("nonempty_timed_row_count") or 0),
                "duration_s": float((experiment.get("time_range_s") or [0, 0])[-1]),
                "tank_count": len(experiment.get("tank_ids") or []),
                "hose_pressure_temperature_present": True,
                "tank_pressure_temperature_mass_present": True,
                "partial_station_to_tank_boundary_eligible": True,
                "full_loop_holdout_eligible": boundary.get(
                    "full_loop_external_holdout_eligible"
                ) is True,
                "rights_limited": "internal-use-only" in rights,
                "screening_status": "not_loaded",
                "screening_pass_count": None,
                "screening_pass_fraction": None,
                "pressure_rmse_mpa": None,
                "temperature_rmse_c": None,
                "mass_rmse_kg": None,
                "pressure_final_error_mpa": None,
                "parameter_tuning": None,
            }
            try:
                screen = _read_json(_NREL_HDVS_RESULT)
                aggregate = screen.get("aggregate") or {}
                frozen_model = screen.get("frozen_model") or {}
                screening_limits = screen.get("screening_limits") or {}
                geometry = screen.get("geometry_diagnostic") or {}
                if (
                    screen.get("artifact_type")
                    == "privacy_bounded_nrel_hdvs_boundary_screen"
                    and screen.get("raw_rows_persisted") is False
                    and screen.get("evidence_role")
                    == "independent_tank_thermal_external_validation"
                    and screen.get("boundary_channel_screen", {}).get(
                        "partial_station_to_tank_boundary_eligible"
                    ) is True
                    and frozen_model.get("post_access_parameter_tuning") is False
                    and all(
                        isinstance(aggregate.get(key), (int, float))
                        and not isinstance(aggregate.get(key), bool)
                        for key in (
                            "screening_pass_count",
                            "screening_pass_fraction",
                            "pressure_rmse_mpa",
                            "temperature_rmse_c",
                            "mass_rmse_kg",
                            "pressure_final_error_mpa",
                        )
                    )
                ):
                    result["public_station_tank_boundary"].update({
                        "screening_status": (
                            "diagnostic_only_failed_screen"
                            if aggregate.get("screening_pass_count") == 0
                            else "diagnostic_only_partial_screen"
                        ),
                        "screening_pass_count": int(aggregate["screening_pass_count"]),
                        "screening_pass_fraction": float(aggregate["screening_pass_fraction"]),
                        "pressure_rmse_mpa": float(aggregate["pressure_rmse_mpa"]),
                        "temperature_rmse_c": float(aggregate["temperature_rmse_c"]),
                        "mass_rmse_kg": float(aggregate["mass_rmse_kg"]),
                        "pressure_final_error_mpa": float(aggregate["pressure_final_error_mpa"]),
                        "parameter_tuning": False,
                        "screening_limits": {
                            "pressure_rmse_mpa_max": screening_limits.get(
                                "pressure_rmse_mpa_max"
                            ),
                            "temperature_rmse_c_max": screening_limits.get(
                                "temperature_rmse_c_max"
                            ),
                            "mass_final_abs_error_kg_max": screening_limits.get(
                                "mass_final_abs_error_kg_max"
                            ),
                        },
                        "geometry_ratio_to_frozen_effective_volume": geometry.get(
                            "ratio_to_frozen_effective_volume_median"
                        ),
                    })
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass
    return result
