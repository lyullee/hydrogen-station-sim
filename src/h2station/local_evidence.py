"""Privacy-bounded local evidence coverage for the runtime API.

The local archive is owner-controlled and is intentionally not read by the
runtime.  Only the committed aggregate audit artifacts are loaded here.  The
result is suitable for an operator or UI to understand which claims the
current run can support without exposing raw rows, source paths, identifiers,
or equipment metadata.
"""

from __future__ import annotations

import json
import hashlib
from functools import lru_cache
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
_DATA_COVERAGE_CANDIDATES = (
    _ROOT / "research/data_coverage_summary_2026_10_11.json",
    _ROOT / "research/data_coverage_summary_2026_10_10.json",
)
_DATA_COVERAGE = next(
    (path for path in _DATA_COVERAGE_CANDIDATES if path.is_file()),
    _DATA_COVERAGE_CANDIDATES[-1],
)
_VALIDATION_GAP_TRIAGE = _ROOT / "research/validation_gap_triage_2026_10_10.json"
_PRIVATE_FULL_LOOP_SCHEMA = _ROOT / "research/private_full_loop_schema_recheck_2026_10_10.json"
_PRIVATE_RECHARGE_SCHEMA = _ROOT / "research/private_recharge_multitrace_schema_recheck_2026_10_10.json"
_KHK_ACCIDENTS = _ROOT / "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json"
_ACCIDENTAL_RELEASE = _ROOT / "research/accidental_self_ignition_public_evidence_2026_10_04.json"
_EXPERIMENTAL_BENCHMARKS = _ROOT / "research/public_experimental_benchmarks_2026_10_06.json"
_CARB_BENCHMARK = _ROOT / "research/carb_2024_hrs_inuse_field_benchmark_2026_10_08.json"
_STRIEDNIG_DIAGNOSTIC = _ROOT / "research/striednig_hyddown_diagnostic_result_2026_10_10.json"
_NREL_HDVS_BOUNDARY = _ROOT / "research/nrel_hdvs_raw_trace_boundary_2026_10_05.json"
_NREL_HDVS_RESULT = _ROOT / "research/nrel_hdvs_boundary_screen_2026_10_10.json"
_NREL_NFCTEC_ACCESS_BOUNDARY = _ROOT / (
    "research/nrel_nfctec_public_access_boundary_2026_10_11.json"
)
_H2SAFE_SPATIAL_DIAGNOSTIC = _ROOT / (
    "research/h2safe_spatial_response_diagnostic_2026_10_08.json"
)
_H2SAFE_HVAC_INPUT_READINESS = _ROOT / (
    "research/h2safe_hvac_input_readiness_2026_10_12.json"
)
_H2SAFE_GEOMETRY_CONTAINMENT = _ROOT / (
    "research/h2safe_geometry_sensor_containment_2026_10_12.json"
)
_PUBLIC_STATION_VEHICLE_SEARCH_RECHECK = _ROOT / (
    "research/public_station_vehicle_search_recheck_2026_10_12.json"
)
_PUBLIC_ACTUAL_H2_CHANNEL_DATASET = _ROOT / (
    "research/public_actual_h2_channel_dataset_inventory_2026_10_12.json"
)
_PUBLIC_ELVHYS_DATASET = _ROOT / (
    "research/elvhys_4_2_public_dataset_inventory_2026_10_12.json"
)
_LOCAL_HRS_CANDIDATE_SCAN = _ROOT / (
    "research/local_hydrogen_station_sim_candidate_scan_2026_10_10.json"
)
_LOCAL_DOCUDATA_CANDIDATE_SCAN = _ROOT / (
    "research/local_docudata_candidate_scan_2026_10_10.json"
)
_CLOSED_LOOP_CALIBRATED_DIAGNOSTIC = _ROOT / (
    "research/closed_loop_calibrated_confirmatory_diagnostic_2026_10_10.json"
)
_MC_GEOMETRY_TRANSFER_DIAGNOSTIC = _ROOT / (
    "research/mc_geometry_transfer_diagnostic_2026_10_08.json"
)
_MC_TANK_BOUNDARY_DIAGNOSTIC = _ROOT / (
    "research/mc_tank_boundary_diagnostic_2026_10_05.json"
)
_MC_CUMULATIVE_MASS_SENSITIVITY = _ROOT / (
    "research/mc_cumulative_mass_sensitivity_2026_10_10.json"
)
_MC_SOC_BOUNDARY_DIAGNOSTIC = _ROOT / (
    "research/mc_soc_boundary_diagnostic_2026_10_10.json"
)
_MC_SOURCE_PRESSURE_BOUNDARY_DIAGNOSTIC = _ROOT / (
    "research/mc_source_pressure_boundary_diagnostic_2026_10_10.json"
)
_DICKENS_GEOMETRY_FOLLOWUP = _ROOT / (
    "research/dickens_typeiii_geometry_resolved_followup_2026_10_10.json"
)
_MHC_COMPONENT_SCREEN = _ROOT / (
    "research/public_mhc_experiment16_screen_2026_10_12.json"
)
_INCIDENT_TRACEABILITY = _ROOT / (
    "research/incident_evidence_traceability_2026_10_12.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("aggregate evidence artifact must contain an object")
    return value


def _public_incident_traceability_summary() -> dict[str, Any] | None:
    """Load the public incident traceability ledger without exposing raw records.

    HIAD and KHK are response-grounding evidence, not accident reconstructions
    or consequence/risk validation.  The committed source hashes are checked so
    a stale or partially copied ledger fails closed before entering an LLM
    evidence envelope.
    """

    try:
        record = _read_json(_INCIDENT_TRACEABILITY)
        sources = record.get("sources") or []
        root = _ROOT.resolve()
        hashes_verified = bool(sources) and all(
            isinstance(item, dict)
            and isinstance(item.get("path"), str)
            and isinstance(item.get("sha256"), str)
            and len(item["sha256"]) == 64
            and (candidate := (root / item["path"]).resolve()).is_file()
            and root in candidate.parents
            and hashlib.sha256(candidate.read_bytes()).hexdigest()
            == item["sha256"]
            for item in sources
        )
        hiad = record.get("hiad") or {}
        khk = record.get("khk") or {}
        response = record.get("response_grounding") or {}
        valid = (
            record.get("schema_version") == 1
            and record.get("artifact_type")
            == "public_incident_evidence_traceability_summary"
            and hashes_verified
            and hiad.get("case_count") == 34
            and hiad.get("trace_pass_count") == 34
            and hiad.get("direct_physical_replay_cases") == 29
            and hiad.get("proxy_partial_replay_cases") == 4
            and hiad.get("response_only_cases") == 1
            and hiad.get("passed_family_recipes") == 9
            and khk.get("public_report_count") == 23
            and khk.get("incident_code_count") == 26
            and khk.get("in_scope_report_count") == 22
            and khk.get("in_scope_incident_code_count") == 25
            and khk.get("direct_canonical_replay_reports") == 12
            and khk.get("proxy_partial_replay_reports") == 10
            and khk.get("passed_family_recipes") == 8
            and response.get("case_count") == 34
            and response.get("cases_with_public_action_categories") == 33
            and response.get("action_category_count") == 8
            and response.get("covered_action_category_count") == 8
            and response.get("active_action_category_count") == 5
            and response.get("executable_case_category_count") == 72
            and response.get("executable_uncovered_case_category_count") == 0
            and response.get("virtual_actions_are_simulation_only") is True
            and response.get("external_notification_performed") is False
            and response.get("contract_pass") is True
        )
        if not valid:
            return None
        return {
            "status": "available",
            "evidence_role": "public incident traceability for grounded decision support",
            "source_count": len(sources),
            "source_hashes_verified": True,
            "hiad": {
                "case_count": 34,
                "trace_pass_count": 34,
                "direct_physical_replay_cases": 29,
                "proxy_partial_replay_cases": 4,
                "response_only_cases": 1,
                "passed_family_recipes": 9,
            },
            "khk": {
                "public_report_count": 23,
                "incident_code_count": 26,
                "in_scope_report_count": 22,
                "in_scope_incident_code_count": 25,
                "direct_canonical_replay_reports": 12,
                "proxy_partial_replay_reports": 10,
                "passed_family_recipes": 8,
            },
            "response_grounding": {
                "case_count": 34,
                "cases_with_public_action_categories": 33,
                "action_category_count": 8,
                "covered_action_category_count": 8,
                "active_action_category_count": 5,
                "executable_case_category_count": 72,
                "executable_uncovered_case_category_count": 0,
                "virtual_actions_are_simulation_only": True,
                "external_notification_performed": False,
                "contract_pass": True,
            },
            "runtime_parameter_application": False,
            "full_loop_holdout_eligible": False,
            "claim_limit": (
                "Public incident metadata are mapped to registered staged response families, "
                "and active categories expose simulation-only commands for grounded "
                "decision-support prompts. Virtual notification contacts no external service. "
                "This does not establish accident "
                "reconstruction, frequency or calibrated risk, site consequence distance, "
                "or operator effectiveness."
            ),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _role_aware_full_loop_schema_summary() -> dict[str, Any] | None:
    """Expose the current station/vehicle schema boundary without raw labels.

    The header scanner is an intake guard, not validation evidence.  Keeping
    this aggregate in the evidence envelope prevents an assistant from
    interpreting generic pressure/temperature columns as a synchronized
    station-to-vehicle trace.
    """
    try:
        external = _read_json(_PRIVATE_FULL_LOOP_SCHEMA)
        station = _read_json(_PRIVATE_RECHARGE_SCHEMA)
        external_scope = external.get("scope") or {}
        station_scope = station.get("scope") or {}
        if any(value is not False for value in (
            external_scope.get("raw_rows_persisted"),
            external_scope.get("original_headers_persisted"),
            external_scope.get("filenames_and_source_paths_persisted"),
            external_scope.get("absolute_timestamps_persisted"),
            station_scope.get("raw_rows_persisted"),
            station_scope.get("original_headers_persisted"),
            station_scope.get("filenames_and_source_paths_persisted"),
            station_scope.get("absolute_timestamps_persisted"),
            station_scope.get("absolute_timestamps_persisted"),
        )):
            return None
        external_aggregate = external.get("aggregate") or {}
        station_aggregate = station.get("aggregate") or {}
        return {
            "status": "available",
            "evidence_role": "privacy-bounded role-aware full-loop schema boundary",
            "external_candidate_files_seen": int(external_aggregate.get("csv_files_seen") or 0),
            "external_readable_files": int(external_aggregate.get("readable_csv_files") or 0),
            "external_role_aware_contract_files": int(
                external_aggregate.get("files_with_full_loop_contract_groups") or 0
            ),
            "station_side_recharge_files_seen": int(station_aggregate.get("csv_files_seen") or 0),
            "station_side_role_aware_contract_files": int(
                station_aggregate.get("files_with_full_loop_contract_groups") or 0
            ),
            "required_role_groups": [
                "common_time", "vehicle_pressure", "vehicle_temperature",
                "station_pressure", "delivered_temperature", "mass_flow",
                "cascade_or_storage", "controller_state", "vehicle_identity",
            ],
            "external_missing_role_groups": list(
                external_aggregate.get("missing_full_loop_contract_groups") or []
            ),
            "station_side_missing_role_groups": list(
                station_aggregate.get("missing_full_loop_contract_groups") or []
            ),
            "full_loop_external_validation_supported": False,
            "claim_limit": (
                "Header coverage is an intake guard only. No synchronized station-to-vehicle "
                "holdout, calibration attestation, reviewer rights or numerical validation "
                "claim is established by this scan."
            ),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _scientific_container_discovery_summary() -> dict[str, Any] | None:
    """Expose only aggregate MAT/HDF5 screening counts to the LLM.

    The scanner deliberately persists no paths, filenames, headers, values or
    identifiers.  This projection keeps that privacy boundary while making it
    explicit that scientific containers were checked and did not yield a
    promotable synchronized station-to-vehicle cohort.
    """

    archives = (
        ("project_archive", _LOCAL_HRS_CANDIDATE_SCAN),
        ("adjacent_document_archive", _LOCAL_DOCUDATA_CANDIDATE_SCAN),
    )
    safe_archives: list[dict[str, Any]] = []
    try:
        for scope, path in archives:
            record = _read_json(path)
            privacy = record.get("privacy") or {}
            scan = record.get("scan") or {}
            eligibility = record.get("eligibility") or {}
            if (
                record.get("artifact_type")
                != "privacy_bounded_local_workspace_candidate_scan"
                or record.get("status") != "discovery_only"
                or not privacy
                or not all(value is False for value in privacy.values())
                or scan.get("scientific_inspection_enabled") is not True
                or not isinstance(scan.get("scientific_headers_screened"), int)
                or not isinstance(scan.get("scientific_header_parse_errors"), int)
                or not isinstance(eligibility.get("full_loop_candidate_count"), int)
                or not isinstance(eligibility.get("partial_loop_candidate_count"), int)
            ):
                return None
            safe_archives.append({
                "scope": scope,
                "machine_readable_files": int(scan.get("machine_readable_files") or 0),
                "scientific_headers_screened": int(
                    scan.get("scientific_headers_screened") or 0
                ),
                "scientific_header_parse_errors": int(
                    scan.get("scientific_header_parse_errors") or 0
                ),
                "full_loop_candidate_count": int(
                    eligibility.get("full_loop_candidate_count") or 0
                ),
                "partial_loop_candidate_count": int(
                    eligibility.get("partial_loop_candidate_count") or 0
                ),
            })
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    full_loop_count = sum(item["full_loop_candidate_count"] for item in safe_archives)
    partial_count = sum(item["partial_loop_candidate_count"] for item in safe_archives)
    return {
        "evidence_role": "privacy-bounded scientific-container discovery",
        "archives": safe_archives,
        "scientific_headers_screened_total": sum(
            item["scientific_headers_screened"] for item in safe_archives
        ),
        "full_loop_candidate_count": full_loop_count,
        "partial_loop_candidate_count": partial_count,
        "runtime_parameter_application": False,
        "full_loop_external_validation_ready": False,
        "claim_limit": (
            "MAT/HDF5 헤더와 제한된 메타데이터를 집계한 발견 결과입니다. "
            "동기화·경계·권리 확인 전에는 실측 full-loop 검증이나 런타임 보정으로 사용할 수 없습니다."
        ),
    }


def _closed_loop_calibrated_diagnostic_summary() -> dict[str, Any] | None:
    """Expose aggregate closed-loop development evidence with a hard claim fence."""

    try:
        record = _read_json(_CLOSED_LOOP_CALIBRATED_DIAGNOSTIC)
        aggregate = record.get("diagnostic_aggregate") or {}
        metrics = aggregate.get("metrics_mean") or {}
        required = (
            record.get("artifact_type")
            == "post_outcome_closed_loop_calibrated_confirmatory_diagnostic",
            record.get("evidence_role") == "model-development diagnostic only",
            record.get("post_outcome") is True,
            record.get("parameter_fitting") is False,
            record.get("production_default_changed") is False,
            record.get("validation_gate_effect") == "none",
            aggregate.get("case_count") == 11,
            isinstance(aggregate.get("screening_pass_count"), int),
            isinstance(aggregate.get("screening_pass_fraction"), (int, float)),
            all(
                isinstance(metrics.get(key), (int, float))
                and not isinstance(metrics.get(key), bool)
                for key in (
                    "pressure_rmse_mpa",
                    "temperature_rmse_c",
                    "soc_rmse_percentage_points",
                )
            ),
            isinstance(record.get("claim_boundary"), str)
            and "not a new independent holdout" in record["claim_boundary"].lower(),
        )
        if not all(required):
            return None
        return {
            "status": "diagnostic_only",
            "evidence_role": str(record["evidence_role"]),
            "case_count": int(aggregate["case_count"]),
            "screening_pass_count": int(aggregate["screening_pass_count"]),
            "screening_pass_fraction": float(aggregate["screening_pass_fraction"]),
            "mean_metrics": {
                key: float(metrics[key])
                for key in (
                    "pressure_rmse_mpa",
                    "temperature_rmse_c",
                    "soc_rmse_percentage_points",
                )
            },
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _mc_geometry_transfer_diagnostic_summary() -> dict[str, Any] | None:
    """Expose aggregate MC geometry sensitivity without selecting a rule."""

    try:
        record = _read_json(_MC_GEOMETRY_TRANSFER_DIAGNOSTIC)
        runs = record.get("runs") or []
        required = (
            record.get("schema_version") == 1,
            record.get("diagnostic_type")
            == "MC Default Type-IV geometry-transfer sensitivity",
            record.get("post_outcome") is True,
            record.get("parameter_fitting") is False,
            record.get("runtime_geometry_changed") is False,
            record.get("geometry_rule_selection_prohibited") is True,
            len(runs) == 3,
            all(
                isinstance(item, dict)
                and isinstance(item.get("geometry_rule"), str)
                and item.get("case_count") == 8
                and isinstance(item.get("joint_screening_pass_count"), int)
                and isinstance(item.get("aggregate"), dict)
                for item in runs
            ),
            isinstance(record.get("claim_boundary"), str),
        )
        if not all(required):
            return None
        safe_runs = []
        for item in runs:
            aggregate = item["aggregate"]
            safe_runs.append({
                "geometry_rule": item["geometry_rule"],
                "effective_volume_multiplier": float(
                    item["effective_volume_multiplier"]
                ),
                "case_count": 8,
                "joint_screening_pass_count": int(
                    item["joint_screening_pass_count"]
                ),
                "aggregate": {
                    key: float(aggregate[key])
                    for key in (
                        "pressure_rmse_mpa_mean",
                        "temperature_rmse_c_mean",
                        "soc_rmse_percentage_points_mean",
                        "soc_final_abs_error_percentage_points_mean",
                    )
                },
            })
        identifiability = record.get("outcome_derived_identifiability") or {}
        return {
            "status": "diagnostic_only",
            "evidence_role": str(record.get("evidence_role") or ""),
            "runs": safe_runs,
            "outcome_derived_identifiability": {
                key: identifiability.get(key)
                for key in (
                    "case_count",
                    "effective_volume_ratio_min",
                    "effective_volume_ratio_median",
                    "effective_volume_ratio_max",
                    "use_for_parameter_selection_prohibited",
                )
            },
            "runtime_geometry_changed": False,
            "geometry_rule_selection_prohibited": True,
            "full_loop_external_validation_ready": False,
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _mc_tank_boundary_diagnostic_summary() -> dict[str, Any] | None:
    """Expose the retained negative MC tank replay without trace rows."""

    try:
        record = _read_json(_MC_TANK_BOUNDARY_DIAGNOSTIC)
        aggregate = record.get("aggregate") or {}
        required = (
            record.get("schema_version") == 2,
            record.get("diagnostic_type")
            == "MC Default measured-boundary vehicle-tank replay",
            record.get("evidence_role") == "development_diagnostic_only",
            record.get("post_outcome") is True,
            record.get("parameter_fitting") is False,
            aggregate.get("case_count") == 8,
            aggregate.get("joint_screening_pass_count") == 0,
            aggregate.get("joint_screening_pass_fraction") == 0.0,
            isinstance(record.get("claim_boundary"), str),
        )
        if not all(required):
            return None
        return {
            "status": "diagnostic_only",
            "case_count": 8,
            "joint_screening_pass_count": 0,
            "joint_screening_pass_fraction": 0.0,
            "aggregate": {
                key: float(aggregate[key])
                for key in (
                    "pressure_rmse_mpa_mean",
                    "temperature_rmse_c_mean",
                    "soc_rmse_percentage_points_mean",
                )
            },
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _mc_cumulative_mass_sensitivity_summary() -> dict[str, Any] | None:
    """Expose the post-outcome MC mass-path sensitivity without promotion."""

    try:
        record = _read_json(_MC_CUMULATIVE_MASS_SENSITIVITY)
        aggregate = record.get("aggregate") or {}
        required = (
            record.get("schema_version") == 1,
            record.get("artifact_type") == "mc_cumulative_mass_boundary_sensitivity",
            record.get("evidence_role") == "development_diagnostic_only",
            record.get("post_outcome") is True,
            record.get("parameter_fitting") is False,
            record.get("runtime_parameter_updated") is False,
            aggregate.get("case_count") == 8,
            aggregate.get("joint_screening_pass_count") == 0,
            isinstance(record.get("source_limitation"), str)
            and "no independent mass channel" in record["source_limitation"].lower(),
            isinstance(record.get("claim_boundary"), str)
            and "does not revise the frozen mc result" in record["claim_boundary"].lower(),
        )
        if not all(required):
            return None
        metric_keys = (
            "pressure_rmse_mpa_mean",
            "temperature_rmse_c_mean",
            "soc_rmse_percentage_points_mean",
            "soc_final_error_percentage_points_mean",
        )
        if not all(
            isinstance(aggregate.get(key), (int, float))
            and not isinstance(aggregate.get(key), bool)
            for key in metric_keys
        ):
            return None
        return {
            "status": "diagnostic_only",
            "evidence_role": str(record["evidence_role"]),
            "case_count": 8,
            "joint_screening_pass_count": 0,
            "joint_screening_pass_fraction": float(
                aggregate.get("joint_screening_pass_fraction", 0.0)
            ),
            "mass_boundary_mode": "cumulative_trapezoid_of_measured_mass_flow",
            "aggregate": {key: float(aggregate[key]) for key in metric_keys},
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
            "source_limitation": str(record["source_limitation"]),
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _mc_soc_boundary_diagnostic_summary() -> dict[str, Any] | None:
    """Expose the SOC/EOS boundary check without exposing trace rows."""

    try:
        record = _read_json(_MC_SOC_BOUNDARY_DIAGNOSTIC)
        aggregate = record.get("aggregate") or {}
        required = (
            record.get("schema_version") == 1,
            record.get("artifact_type") == "mc_soc_and_mass_boundary_diagnostic",
            record.get("evidence_role") == "development_diagnostic_only",
            record.get("post_outcome") is True,
            record.get("parameter_fitting") is False,
            record.get("runtime_parameter_updated") is False,
            record.get("case_count") == 8,
            isinstance(record.get("claim_boundary"), str),
            isinstance(aggregate.get("soc_definition_screen_pass_count"), int),
        )
        if not all(required):
            return None
        return {
            "status": "diagnostic_only",
            "case_count": 8,
            "aggregate": {
                key: float(aggregate[key])
                for key in (
                    "soc_definition_rmse_percentage_points_mean",
                    "soc_definition_rmse_percentage_points_max",
                    "soc_definition_final_abs_error_percentage_points_mean",
                    "soc_definition_final_abs_error_percentage_points_max",
                    "inferred_volume_ratio_median",
                    "inferred_volume_ratio_p10",
                    "inferred_volume_ratio_p90",
                )
            },
            "soc_definition_screen_pass_count": int(
                aggregate["soc_definition_screen_pass_count"]
            ),
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _mc_source_pressure_boundary_diagnostic_summary() -> dict[str, Any] | None:
    """Expose source-pressure boundary sensitivity without trace rows."""

    try:
        record = _read_json(_MC_SOURCE_PRESSURE_BOUNDARY_DIAGNOSTIC)
        runs = record.get("runs") or []
        required = (
            record.get("schema_version") == 1,
            record.get("artifact_type") == "mc_source_pressure_boundary_diagnostic",
            record.get("evidence_role") == "development_diagnostic_only",
            record.get("post_outcome") is True,
            record.get("parameter_fitting") is False,
            record.get("runtime_parameter_updated") is False,
            record.get("case_count") == 8,
            len(runs) == 3,
            isinstance(record.get("interpretation"), str),
            isinstance(record.get("claim_boundary"), str),
            all(
                isinstance(item, dict)
                and isinstance(item.get("boundary_label"), str)
                and isinstance(item.get("boundary_source"), str)
                and item.get("case_count") == 8
                and item.get("screening_pass_count") == 0
                and isinstance(item.get("aggregate"), dict)
                for item in runs
            ),
        )
        if not all(required):
            return None
        metric_keys = (
            "pressure_rmse_mpa",
            "temperature_rmse_c",
            "soc_rmse_percentage_points",
            "simulation_coverage_fraction",
        )
        safe_runs = []
        for item in runs:
            aggregate = item["aggregate"]
            if not all(
                isinstance(aggregate.get(key), (int, float))
                and not isinstance(aggregate.get(key), bool)
                for key in metric_keys
            ):
                return None
            safe_runs.append({
                "boundary_label": item["boundary_label"],
                "boundary_source": item["boundary_source"],
                "case_count": 8,
                "screening_pass_count": 0,
                "aggregate": {
                    key: float(aggregate[key]) for key in metric_keys
                },
            })
        return {
            "status": "diagnostic_only",
            "evidence_role": str(record["evidence_role"]),
            "case_count": 8,
            "runs": safe_runs,
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
            "interpretation": str(record["interpretation"]),
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _h2safe_spatial_diagnostic_summary() -> dict[str, Any] | None:
    """Expose the negative H2SAFE spatial screen without sensor rows."""

    try:
        record = _read_json(_H2SAFE_SPATIAL_DIAGNOSTIC)
        source = record.get("source") or {}
        method = record.get("method") or {}
        results = record.get("results") or {}
        primary = results.get("Y_as_elevation") or {}
        aggregate = primary.get("aggregate") or {}
        decision = record.get("decision") or {}
        screens = aggregate.get("screens") or {}
        required = (
            record.get("artifact_type") == "post_access_h2safe_spatial_response_diagnostic",
            source.get("test_gas") == "helium surrogate",
            method.get("status") == "POST_ACCESS_DEVELOPMENT_DIAGNOSTIC_NOT_VALIDATION",
            aggregate.get("experiment_count") == 5,
            isinstance(aggregate.get("median_spearman"), (int, float)),
            isinstance(aggregate.get("mean_top5_recall"), (int, float)),
            isinstance(aggregate.get("nearest_in_response_quartile_fraction"), (int, float)),
            len(screens) == 4,
            decision.get("joint_spatial_screen_pass") is False,
            decision.get("runtime_use", "").startswith("Do not apply"),
            isinstance(record.get("claim_boundary"), str),
        )
        if not all(required):
            return None
        return {
            "status": "diagnostic_only_failed_screen",
            "evidence_role": "post_access_spatial_diagnostic",
            "source_doi": str(source.get("doi") or ""),
            "test_gas": "helium surrogate",
            "experiment_count": 5,
            "median_spearman": float(aggregate["median_spearman"]),
            "mean_top5_recall": float(aggregate["mean_top5_recall"]),
            "nearest_sensor_response_quartile_fraction": float(
                aggregate["nearest_in_response_quartile_fraction"]
            ),
            "screens": {
                str(key): bool(value) for key, value in screens.items()
            },
            "joint_spatial_screen_pass": False,
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _h2safe_hvac_input_readiness_summary() -> dict[str, Any] | None:
    """Expose the H2SAFE spatial-input boundary without raw trace metadata.

    This is a provenance/readiness record, not a detector calibration result.
    Keeping it in the evidence inventory makes the LLM state exactly why a
    directional/obstruction-aware candidate is still prohibited from runtime.
    """

    try:
        record = _read_json(_H2SAFE_HVAC_INPUT_READINESS)
        source = record.get("source") or {}
        parsed = record.get("parsed_metadata") or {}
        decision = record.get("decision") or {}
        required = record.get("required_common_frame_inputs") or {}
        if not (
            record.get("artifact_type") == "h2safe_hvac_spatial_input_readiness_audit"
            and source.get("doi") == "10.7799/17118570"
            and source.get("test_gas") == "helium surrogate"
            and isinstance(source.get("metadata_sha256"), str)
            and len(source["metadata_sha256"]) == 64
            and decision.get("status") == "NOT_READY_FOR_PREACCESS_SPATIAL_VALIDATION"
            and decision.get("runtime_application") is False
            and set(decision.get("missing_inputs") or {}) == {
                "release_direction_vector",
                "ventilation_velocity_vectors",
                "obstruction_geometry",
                "release_to_trace_time_crosswalk",
            }
            and all(isinstance(required.get(key), dict) for key in (
                "release_direction_vector",
                "ventilation_velocity_vectors",
                "obstruction_geometry",
                "release_to_trace_time_crosswalk",
            ))
        ):
            return None
        return {
            "status": str(decision["status"]),
            "evidence_role": "public HVAC/spatial input readiness boundary",
            "source_doi": str(source["doi"]),
            "test_gas": str(source["test_gas"]),
            "release_test_count": sum(
                len(parsed.get(key) or []) for key in ("release_tests",)
            ) if isinstance(parsed.get("release_tests"), list) else sum(
                len((parsed.get("release_tests") or {}).get(key) or [])
                for key in ("lab_1", "lab_2")
            ),
            "lab_1_vent_count": int(parsed.get("lab_1_vent_count") or 0),
            "lab_2_duct_count": int(parsed.get("lab_2_duct_count") or 0),
            "lab_2_recirculation_fan_count": int(
                parsed.get("lab_2_recirculation_fan_count") or 0
            ),
            "missing_inputs": [str(item) for item in decision["missing_inputs"]],
            "runtime_parameter_application": False,
            "development_candidate_use": str(
                decision.get("development_candidate_use") or ""
            ),
            "promotion_prohibited": True,
            "claim_limit": str(record.get("claim_boundary") or ""),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _h2safe_geometry_containment_summary() -> dict[str, Any] | None:
    """Expose public mesh/sensor containment without implying registration."""

    try:
        record = _read_json(_H2SAFE_GEOMETRY_CONTAINMENT)
        source = record.get("source") or {}
        summary = record.get("summary") or {}
        decision = record.get("decision") or {}
        if not (
            record.get("artifact_type") == "h2safe_geometry_sensor_containment_diagnostic"
            and source.get("doi") == "10.7799/17118570"
            and summary.get("status") == "CONTAINMENT_CONFIRMED_REGISTRATION_UNPROVEN"
            and summary.get("all_sensor_points_inside_mesh_bounds") is True
            and summary.get("all_release_points_inside_mesh_bounds") is True
            and isinstance(summary.get("sensor_count"), int)
            and isinstance(summary.get("sensor_containment_fraction"), (int, float))
            and decision.get("runtime_application") is False
            and decision.get("preaccess_spatial_validation_ready") is False
            and isinstance(record.get("claim_boundary"), str)
        ):
            return None
        return {
            "status": str(summary["status"]),
            "evidence_role": "public H2SAFE geometry/sensor containment diagnostic",
            "source_doi": str(source["doi"]),
            "sensor_count": int(summary["sensor_count"]),
            "sensor_containment_fraction": float(summary["sensor_containment_fraction"]),
            "all_sensor_points_inside_mesh_bounds": True,
            "all_release_points_inside_mesh_bounds": True,
            "runtime_parameter_application": False,
            "preaccess_spatial_validation_ready": False,
            "promotion_prohibited": True,
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _public_station_vehicle_search_recheck_summary() -> dict[str, Any] | None:
    """Expose the latest public station-to-vehicle availability boundary.

    The record is a search/access audit, not a numerical validation result.
    Only publication-level metadata are projected so the validation endpoint
    and the LLM grounding layer cannot accidentally disclose raw rows or
    private source locations.
    """

    try:
        record = _read_json(_PUBLIC_STATION_VEHICLE_SEARCH_RECHECK)
        scope = record.get("search_scope") or {}
        impact = record.get("primary_goal_impact") or {}
        sources = record.get("sources") or []
        if not (
            record.get("artifact_type") == "station_to_vehicle_public_search_recheck"
            and record.get("decision")
            == "NO_NEW_ELIGIBLE_PUBLIC_RAW_STATION_TO_VEHICLE_SET_IDENTIFIED"
            and impact.get("full_loop_external_validation") == "OUT_OF_SCOPE"
            and isinstance(impact.get("reentry_condition"), str)
            and isinstance(scope.get("eligibility_rule"), str)
            and isinstance(sources, list)
            and sources
            and all(
                isinstance(source, dict)
                and isinstance(source.get("name"), str)
                and isinstance(source.get("decision"), str)
                and isinstance(source.get("reason"), str)
                and isinstance(source.get("url"), str)
                and not any(
                    token in source
                    for token in ("raw_rows", "local_path", "source_path", "headers")
                )
                for source in sources
            )
        ):
            return None
        return {
            "status": str(record["decision"]),
            "recorded_at": record.get("recorded_at"),
            "evidence_role": "public station-to-vehicle data availability boundary",
            "source_count": len(sources),
            "sources": [
                {
                    key: source.get(key)
                    for key in ("name", "doi", "url", "observed_role", "decision", "reason")
                    if source.get(key) is not None
                }
                for source in sources
            ],
            "full_loop_external_validation_supported": False,
            "prospective_holdout_eligible": False,
            "runtime_parameter_application": False,
            "claim_supported": False,
            "reentry_condition": impact.get("reentry_condition"),
            "claim_boundary": str(record.get("claim_boundary") or ""),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _public_actual_h2_channel_dataset_summary() -> dict[str, Any] | None:
    """Expose the actual-H2 component dataset as a bounded candidate only."""

    try:
        record = _read_json(_PUBLIC_ACTUAL_H2_CHANNEL_DATASET)
        source = record.get("source") or {}
        scope = record.get("dataset_scope") or {}
        eligibility = record.get("eligibility") or {}
        if not (
            record.get("artifact_type") == "public_actual_h2_channel_dataset_inventory"
            and str(source.get("doi") or "").lower() == "10.23642/usn.26117989.v2"
            and source.get("article_doi") == "10.1016/j.jlp.2025.105669"
            and source.get("license") == "CC BY 4.0"
            and scope.get("experiment_count") == 22
            and scope.get("sensor_count") == 29
            and eligibility.get("schema_screen_pass") is True
            and eligibility.get("independent_actual_hydrogen_component_candidate") is True
            and eligibility.get("station_to_vehicle_full_loop") is False
            and eligibility.get("runtime_parameter_application") is False
            and eligibility.get("validation_gate_promoted") is False
            and isinstance(record.get("claim_boundary"), str)
        ):
            return None
        return {
            "status": "PUBLIC_ACTUAL_H2_DISPERSION_INVENTORY",
            "evidence_role": "independent public actual-hydrogen component dataset candidate",
            "source_doi": str(source["doi"]),
            "article_doi": str(source["article_doi"]),
            "license": str(source["license"]),
            "experiment_count": int(scope["experiment_count"]),
            "sensor_count": int(scope["sensor_count"]),
            "channel_families": [str(item) for item in scope.get("channel_families") or []],
            "geometry_context": str(scope.get("geometry_context") or ""),
            "schema_screen_pass": True,
            "independent_actual_hydrogen_component_candidate": True,
            "station_to_vehicle_full_loop": False,
            "runtime_parameter_application": False,
            "validation_gate_promoted": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _public_elvhys_dataset_summary() -> dict[str, Any] | None:
    """Expose public actual-cryogenic-hydrogen evidence without raw files."""

    try:
        record = _read_json(_PUBLIC_ELVHYS_DATASET)
        source = record.get("source") or {}
        scope = record.get("dataset_scope") or {}
        families = scope.get("file_family_counts") or {}
        eligibility = record.get("eligibility") or {}
        if not (
            record.get("artifact_type")
            == "public_elvhys_4_2_actual_cryogenic_hydrogen_inventory"
            and source.get("doi") == "10.18710/JXJP0H"
            and source.get("license") == "CC0 1.0"
            and scope.get("actual_cryogenic_hydrogen") is True
            and scope.get("published_test_plan_count") == 48
            and scope.get("case_id_count_with_public_data") == 40
            and families.get("concentration") == 40
            and families.get("pressure") == 40
            and families.get("temperature") == 40
            and eligibility.get(
                "independent_actual_cryogenic_hydrogen_component_candidate"
            ) is True
            and eligibility.get("station_to_vehicle_full_loop") is False
            and eligibility.get("runtime_parameter_application") is False
            and eligibility.get("validation_gate_promoted") is False
            and isinstance(record.get("claim_boundary"), str)
        ):
            return None
        return {
            "status": "PUBLIC_ELVHYS_ACTUAL_CRYOGENIC_H2_INVENTORY",
            "evidence_role": "independent public actual-cryogenic-hydrogen component dataset candidate",
            "source_doi": str(source["doi"]),
            "license": str(source["license"]),
            "experimental_campaign": str(scope.get("experimental_campaign") or ""),
            "transfer_connection_space_volume_m3": float(
                scope.get("transfer_connection_space_volume_m3") or 0.0
            ),
            "data_file_count": int(scope.get("data_file_count") or 0),
            "case_id_count_with_public_data": int(
                scope.get("case_id_count_with_public_data") or 0
            ),
            "published_test_plan_count": int(
                scope.get("published_test_plan_count") or 0
            ),
            "test_plan_type_counts": {
                str(key): int(value)
                for key, value in (scope.get("test_plan_type_counts") or {}).items()
            },
            "measured_channel_families": [
                str(item) for item in scope.get("measured_channel_families") or []
            ],
            "schema_screen_pass": True,
            "independent_actual_cryogenic_hydrogen_component_candidate": True,
            "dispersion_candidate": bool(eligibility.get("dispersion_candidate")),
            "pressure_peaking_candidate": bool(
                eligibility.get("pressure_peaking_candidate")
            ),
            "ignition_consequence_candidate": bool(
                eligibility.get("ignition_consequence_candidate")
            ),
            "station_to_vehicle_full_loop": False,
            "runtime_parameter_application": False,
            "validation_gate_promoted": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _dickens_geometry_followup_summary() -> dict[str, Any] | None:
    """Expose the source-grounded follow-up candidate without promotion."""

    try:
        record = _read_json(_DICKENS_GEOMETRY_FOLLOWUP)
        source = record.get("source_geometry") or {}
        selected = record.get("selected_diagnostic") or {}
        metrics = selected.get("metrics") or {}
        interpretation = record.get("diagnostic_interpretation") or {}
        required = (
            record.get("schema_version") == 1,
            record.get("artifact_type") == "source_geometry_resolved_followup_candidate",
            record.get("status") == "candidate_protocol_input_not_validation",
            record.get("evidence_role") == "post_outcome_model_development_diagnostic",
            interpretation.get("source_geometry_confirmed_after_original_outcome") is True,
            interpretation.get("runtime_parameter_updated") is False,
            interpretation.get("validation_gate_effect") == "none",
            selected.get("nozzle_diameter_mm") == 5.0,
            selected.get("joint_primary_screen_pass") is True,
            isinstance(record.get("claim_boundary"), str),
        )
        if not all(required):
            return None
        return {
            "status": "followup_candidate_only",
            "evidence_role": str(record["evidence_role"]),
            "source_reference": {
                "doi": "10.1016/J.JPOWSOUR.2006.11.077",
                "public_record_url": "https://conference.ing.unipi.it/ichs2009/images/stories/papers/238.pdf",
            },
            "source_confirmed_geometry": {
                key: float(source[key])
                for key in (
                    "inlet_pipe_internal_diameter_m",
                    "inlet_pipe_extension_m",
                    "tank_internal_diameter_m",
                    "tank_internal_length_source_m",
                    "tank_internal_length_archived_case_m",
                )
            },
            "selected_diagnostic": {
                "nozzle_diameter_mm": 5.0,
                "metrics": {
                    key: float(metrics[key])
                    for key in (
                        "pressure_rmse_mpa",
                        "pressure_nrmse_percent_measured_span",
                        "gas_temperature_rmse_k",
                        "gas_temperature_peak_absolute_error_k",
                    )
                },
                "all_four_frozen_screens_pass": True,
            },
            "unresolved_requirements": [
                "tank length interpretation",
                "time-resolved inlet hydrogen temperature",
                "prospectively frozen inlet geometry before outcome access",
            ],
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "validation_gate_effect": "none",
            "claim_limit": str(record["claim_boundary"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


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
        schema_contract = _role_aware_full_loop_schema_summary()
        if schema_contract is not None:
            result["full_loop_schema_contract"] = schema_contract
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
            "full_loop_schema_contract": {
                "status": "unavailable",
                "full_loop_external_validation_supported": False,
            },
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
            or not isinstance(triage.get("scope_exclusions", []), list)
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
        scope_exclusions = []
        for item in triage.get("scope_exclusions", []):
            if not isinstance(item, dict) or not item.get("id"):
                continue
            scope_exclusions.append({
                "id": str(item["id"]),
                "legacy_status": str(item.get("legacy_status") or "UNKNOWN"),
                "reason": str(item.get("reason") or ""),
                "paper_limitation": str(item.get("paper_limitation") or ""),
                "reentry_condition": str(item.get("reentry_condition") or ""),
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
            "scope_exclusions": scope_exclusions,
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
            "scope_exclusions": [],
            "minimum_next_input": {},
            "evidence_inventory": public_evidence_inventory_summary(),
            "claim_boundary": "Evidence artifacts are unavailable; no validation claim is permitted.",
        }


@lru_cache(maxsize=1)
def public_evidence_inventory_summary() -> dict[str, Any]:
    """Return counts and claim-bounded roles for public evidence sources.

    The UI needs to show which evidence families were used, but it must not
    expose local source identity or imply that an accident inventory is a
    probability estimate.  Missing artifacts fail closed individually.
    """

    result: dict[str, Any] = {
        "public_incident_traceability": {
            "status": "unavailable",
            "evidence_role": "public incident traceability for grounded decision support",
            "source_count": 0,
            "source_hashes_verified": False,
            "hiad": {},
            "khk": {},
            "response_grounding": {},
            "runtime_parameter_application": False,
            "full_loop_holdout_eligible": False,
            "claim_limit": "Incident traceability evidence is unavailable; no incident-grounding claim is permitted.",
        },
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
            "independent_event_count": 0,
            "analysis_unit": None,
            "shared_clock_group_count": 0,
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
        "public_nrel_access_boundary": {
            "status": "unavailable",
            "evidence_role": "official_public_access_boundary",
            "source_count": 0,
            "raw_public_full_loop_holdout": False,
            "partial_station_to_tank_boundary": False,
            "saga_effectiveness_evaluation": False,
            "runtime_parameter_application": False,
            "gate_impact": "full_loop_external_validation_remains_open",
            "next_required_input": None,
            "claim_supported": False,
            "claim_limit": None,
            "sources": [],
        },
        "local_scientific_container_discovery": {
            "status": "unavailable",
            "scientific_headers_screened_total": 0,
            "full_loop_candidate_count": 0,
            "partial_loop_candidate_count": 0,
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
        },
        "public_closed_loop_calibrated_diagnostic": {
            "status": "unavailable",
            "case_count": 0,
            "screening_pass_count": 0,
            "screening_pass_fraction": 0.0,
            "mean_metrics": {},
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
        },
        "public_mc_geometry_transfer_diagnostic": {
            "status": "unavailable",
            "runs": [],
            "runtime_geometry_changed": False,
            "geometry_rule_selection_prohibited": True,
            "full_loop_external_validation_ready": False,
        },
        "public_mc_tank_boundary_diagnostic": {
            "status": "unavailable",
            "case_count": 0,
            "joint_screening_pass_count": 0,
            "joint_screening_pass_fraction": 0.0,
            "aggregate": {},
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
        },
        "public_mc_cumulative_mass_sensitivity": {
            "status": "unavailable",
            "case_count": 0,
            "joint_screening_pass_count": 0,
            "joint_screening_pass_fraction": 0.0,
            "aggregate": {},
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
        },
        "public_mc_soc_boundary_diagnostic": {
            "status": "unavailable",
            "case_count": 0,
            "aggregate": {},
            "soc_definition_screen_pass_count": 0,
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
        },
        "public_mc_source_pressure_boundary_diagnostic": {
            "status": "unavailable",
            "case_count": 0,
            "runs": [],
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
        },
        "public_h2safe_spatial_diagnostic": {
            "status": "unavailable",
            "experiment_count": 0,
            "joint_spatial_screen_pass": False,
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
        },
        "public_h2safe_hvac_input_readiness": {
            "status": "unavailable",
            "evidence_role": "public HVAC/spatial input readiness boundary",
            "source_doi": None,
            "test_gas": None,
            "release_test_count": 0,
            "lab_1_vent_count": 0,
            "lab_2_duct_count": 0,
            "lab_2_recirculation_fan_count": 0,
            "missing_inputs": [],
            "runtime_parameter_application": False,
            "promotion_prohibited": True,
            "claim_limit": "H2SAFE HVAC input-readiness evidence is unavailable; no spatial-candidate claim is permitted.",
        },
        "public_h2safe_geometry_containment": {
            "status": "unavailable",
            "evidence_role": "public H2SAFE geometry/sensor containment diagnostic",
            "source_doi": None,
            "sensor_count": 0,
            "sensor_containment_fraction": 0.0,
            "all_sensor_points_inside_mesh_bounds": False,
            "all_release_points_inside_mesh_bounds": False,
            "runtime_parameter_application": False,
            "preaccess_spatial_validation_ready": False,
            "promotion_prohibited": True,
            "claim_limit": "H2SAFE geometry containment evidence is unavailable; no spatial-registration claim is permitted.",
        },
        "public_station_vehicle_search_recheck": {
            "status": "unavailable",
            "recorded_at": None,
            "evidence_role": "public station-to-vehicle data availability boundary",
            "source_count": 0,
            "sources": [],
            "full_loop_external_validation_supported": False,
            "prospective_holdout_eligible": False,
            "runtime_parameter_application": False,
            "claim_supported": False,
            "reentry_condition": "No public station-to-vehicle search recheck is available.",
            "claim_boundary": "Availability evidence is unavailable; no public full-loop claim is permitted.",
        },
        "public_actual_h2_channel_dataset": {
            "status": "unavailable",
            "evidence_role": "independent public actual-hydrogen component dataset candidate",
            "source_doi": None,
            "article_doi": None,
            "license": None,
            "experiment_count": 0,
            "sensor_count": 0,
            "channel_families": [],
            "geometry_context": "",
            "schema_screen_pass": False,
            "independent_actual_hydrogen_component_candidate": False,
            "station_to_vehicle_full_loop": False,
            "runtime_parameter_application": False,
            "validation_gate_promoted": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
            "claim_limit": "Public actual-H2 channel evidence is unavailable; no component-validation claim is permitted.",
        },
        "public_elvhys_dataset": {
            "status": "unavailable",
            "evidence_role": "independent public actual-cryogenic-hydrogen component dataset candidate",
            "source_doi": None,
            "license": None,
            "experimental_campaign": "",
            "transfer_connection_space_volume_m3": 0.0,
            "data_file_count": 0,
            "case_id_count_with_public_data": 0,
            "published_test_plan_count": 0,
            "test_plan_type_counts": {},
            "measured_channel_families": [],
            "schema_screen_pass": False,
            "independent_actual_cryogenic_hydrogen_component_candidate": False,
            "dispersion_candidate": False,
            "pressure_peaking_candidate": False,
            "ignition_consequence_candidate": False,
            "station_to_vehicle_full_loop": False,
            "runtime_parameter_application": False,
            "validation_gate_promoted": False,
            "full_loop_external_validation_ready": False,
            "promotion_prohibited": True,
            "claim_limit": "Public ELVHYS evidence is unavailable; no component-validation claim is permitted.",
        },
        "public_dickens_geometry_followup_candidate": {
            "status": "unavailable",
            "runtime_parameter_application": False,
            "full_loop_external_validation_ready": False,
            "validation_gate_effect": "none",
        },
        "public_mhc_component_screen": {
            "status": "unavailable",
            "evidence_role": "independent_public_component_schema_boundary",
            "source_doi": None,
            "experiment_id": None,
            "record_count": 0,
            "duration_s": None,
            "channel_families": [],
            "schema_screen_pass": False,
            "direct_runtime_model_compatibility": False,
            "runtime_parameter_application": False,
            "full_loop_external_holdout_eligible": False,
            "claim_limit": None,
        },
    }
    incident_traceability = _public_incident_traceability_summary()
    if incident_traceability is not None:
        result["public_incident_traceability"] = incident_traceability
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
        record = _read_json(_NREL_NFCTEC_ACCESS_BOUNDARY)
        sources = record.get("sources") or []
        eligibility = record.get("eligibility") or {}
        source_rows = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            source_rows.append({
                key: source.get(key)
                for key in (
                    "id", "title", "url", "doi", "decision",
                    "raw_synchronized_public_archive",
                    "machine_readable_public_raw_rows",
                    "full_loop_external_holdout_eligible",
                )
                if source.get(key) is not None
            })
        if (
            record.get("artifact_type") == "nrel_nfctec_public_access_boundary"
            and record.get("status") == "PUBLIC_COMPOSITE_ONLY_RAW_CUSTODIAN_REQUEST_REQUIRED"
            and eligibility.get("raw_public_full_loop_holdout") is False
            and eligibility.get("partial_station_to_tank_boundary") is True
            and record.get("runtime_parameter_application") is False
            and source_rows
        ):
            result["public_nrel_access_boundary"] = {
                "status": "available",
                "evidence_role": "official_public_access_boundary",
                "source_count": len(source_rows),
                "raw_public_full_loop_holdout": False,
                "partial_station_to_tank_boundary": True,
                "saga_effectiveness_evaluation": (
                    eligibility.get("saga_effectiveness_evaluation") is True
                ),
                "runtime_parameter_application": False,
                "gate_impact": str(record.get("gate_impact") or ""),
                "next_required_input": str(eligibility.get("next_required_input") or ""),
                "claim_supported": False,
                "claim_limit": str(record.get("claim_boundary") or ""),
                "sources": source_rows,
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
                "independent_event_count": 1,
                "analysis_unit": "one common-clock multi-tank fill",
                "shared_clock_group_count": 1,
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
    scientific = _scientific_container_discovery_summary()
    if scientific is not None:
        result["local_scientific_container_discovery"] = {
            "status": "available",
            **scientific,
        }
    calibrated = _closed_loop_calibrated_diagnostic_summary()
    if calibrated is not None:
        result["public_closed_loop_calibrated_diagnostic"] = calibrated
    geometry = _mc_geometry_transfer_diagnostic_summary()
    if geometry is not None:
        result["public_mc_geometry_transfer_diagnostic"] = geometry
    tank_boundary = _mc_tank_boundary_diagnostic_summary()
    if tank_boundary is not None:
        result["public_mc_tank_boundary_diagnostic"] = tank_boundary
    cumulative_mass = _mc_cumulative_mass_sensitivity_summary()
    if cumulative_mass is not None:
        result["public_mc_cumulative_mass_sensitivity"] = cumulative_mass
    soc_boundary = _mc_soc_boundary_diagnostic_summary()
    if soc_boundary is not None:
        result["public_mc_soc_boundary_diagnostic"] = soc_boundary
    source_pressure_boundary = _mc_source_pressure_boundary_diagnostic_summary()
    if source_pressure_boundary is not None:
        result["public_mc_source_pressure_boundary_diagnostic"] = source_pressure_boundary
    h2safe_spatial = _h2safe_spatial_diagnostic_summary()
    if h2safe_spatial is not None:
        result["public_h2safe_spatial_diagnostic"] = h2safe_spatial
    h2safe_hvac = _h2safe_hvac_input_readiness_summary()
    if h2safe_hvac is not None:
        result["public_h2safe_hvac_input_readiness"] = h2safe_hvac
    h2safe_geometry = _h2safe_geometry_containment_summary()
    if h2safe_geometry is not None:
        result["public_h2safe_geometry_containment"] = h2safe_geometry
    station_vehicle_search = _public_station_vehicle_search_recheck_summary()
    if station_vehicle_search is not None:
        result["public_station_vehicle_search_recheck"] = station_vehicle_search
    actual_h2_channel = _public_actual_h2_channel_dataset_summary()
    if actual_h2_channel is not None:
        result["public_actual_h2_channel_dataset"] = actual_h2_channel
    elvhys = _public_elvhys_dataset_summary()
    if elvhys is not None:
        result["public_elvhys_dataset"] = elvhys
    dickens = _dickens_geometry_followup_summary()
    if dickens is not None:
        result["public_dickens_geometry_followup_candidate"] = dickens
    try:
        record = _read_json(_MHC_COMPONENT_SCREEN)
        source = record.get("source") or {}
        protocol = record.get("protocol") or {}
        workbook = record.get("workbook") or {}
        schema_screen = record.get("schema_screen") or {}
        decision = record.get("decision") or {}
        if (
            record.get("artifact_type") == "public_mhc_component_holdout_screen"
            and record.get("status") == "screened_component_only_not_runtime_admitted"
            and source.get("doi") == "10.5281/zenodo.18213166"
            and source.get("accessed_after_protocol_freeze") is True
            and protocol.get("raw_file_persisted_in_repository") is False
            and schema_screen.get("required_families_present") is True
            and decision.get("schema_screen_pass") is True
            and decision.get("direct_runtime_model_compatibility") is False
            and decision.get("runtime_parameter_application") is False
            and decision.get("full_loop_external_holdout_eligible") is False
        ):
            result["public_mhc_component_screen"] = {
                "status": "available",
                "evidence_role": "independent_public_component_schema_boundary",
                "source_doi": str(source.get("doi")),
                "experiment_id": "Experiment 16",
                "record_count": int(workbook.get("cycle_data_numeric_records") or 0),
                "duration_s": float(workbook.get("elapsed_time_span_s") or 0.0),
                "channel_families": [
                    "elapsed_time", "pressure", "volumetric_flow", "temperature",
                ],
                "schema_screen_pass": True,
                "direct_runtime_model_compatibility": False,
                "runtime_parameter_application": False,
                "full_loop_external_holdout_eligible": False,
                "claim_limit": str(record.get("claim_boundary") or ""),
            }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass
    return result
