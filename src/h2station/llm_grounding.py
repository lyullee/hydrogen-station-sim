"""Machine-readable evidence envelopes for LLM decision support.

The envelope is deliberately small and deterministic.  It records what the
assistant was allowed to see; it does not turn a simulation into a field
measurement or make a consequence result more authoritative than its source.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from .calibration_profiles import load_measured_boundary_calibration
from .lifecycle_evidence import load_lifecycle_evidence


def _runtime_calibration_profile(frame: dict[str, Any]) -> dict[str, Any]:
    """Describe the measured-boundary profile used by this simulator frame.

    The profile is opt-in and only changes the station-boundary recharge
    hysteresis.  Keeping the status in the evidence envelope prevents a
    response from presenting a calibrated run and a reference-default run as
    if they were the same experiment.  Only the sanitized artifact metadata
    is exposed; raw rows and private identifiers never enter the prompt.
    """

    operations = frame.get("process_operations") or {}
    settings = operations.get("settings") or {}
    requested = settings.get("measured_boundary_calibration") is True
    profile = load_measured_boundary_calibration() if requested else None
    current_boundary_pressure = operations.get("trailer_pressure_mpa")
    if profile is not None:
        return {
            "status": "active",
            "requested": True,
            **profile.runtime_metadata(
                current_boundary_pressure_mpa=(
                    float(current_boundary_pressure)
                    if isinstance(current_boundary_pressure, (int, float))
                    and math.isfinite(float(current_boundary_pressure))
                    else None
                )
            ),
            "profile_id": profile.profile_id,
            "claim_limit": profile.claim_boundary,
        }
    if requested:
        return {
            "status": "requested_unavailable",
            "requested": True,
            "profile_id": "reference_defaults",
            "evidence_artifact": None,
            "claim_limit": "실측 경계 보정 artifact를 읽지 못해 기준값으로 실행됨",
        }
    return {
        "status": "reference_defaults",
        "requested": False,
        "profile_id": "reference_defaults",
        "evidence_artifact": None,
        "claim_limit": "실측 경계 보정은 선택 적용되지 않음",
    }


def _runtime_geometry_profile(frame: dict[str, Any]) -> dict[str, Any]:
    """Identify the vehicle geometry basis used by the current snapshot."""

    basis = str(frame.get("vehicle_geometry_basis") or "reference")
    if basis not in {"reference", "capacity_eos"}:
        basis = "reference"
    return {
        "basis": basis,
        "vehicle_capacity_kg": frame.get("vehicle_capacity_kg"),
        "vehicle_2_capacity_kg": frame.get("vehicle_2_capacity_kg"),
        "public_sensitivity_available": True,
        "default_basis": "reference",
        "capacity_eos_opt_in": basis == "capacity_eos",
        "claim_limit": (
            "capacity/EOS 형상은 공개 탱크 민감도 진단에 근거한 선택 옵션이며 "
            "독립적인 station-to-vehicle 검증이나 기본값 변경을 의미하지 않음"
        ),
    }


def _public_incident_traceability() -> dict[str, Any] | None:
    """Return the committed HIAD-to-playbook coverage summary when available.

    The artifact is provenance metadata only.  It is intentionally loaded
    once per request path and never exposes the incident workbook's raw prose.
    A source checkout without the research artifact simply omits the optional
    section rather than making runtime decision support unavailable.
    """
    path = Path(__file__).resolve().parents[2] / "research/hiad_action_playbook_coverage.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    aggregate = record.get("aggregate") or {}
    if record.get("status") != "completed_public_action_to_playbook_traceability_audit":
        return None
    result: dict[str, Any] = {
        "artifact": "research/hiad_action_playbook_coverage.json",
        "evidence_role": str(record.get("evidence_role") or ""),
        "category_count": aggregate.get("category_count"),
        "covered_category_count": aggregate.get("covered_category_count"),
        "case_count": aggregate.get("case_count"),
        "covered_case_count": aggregate.get("covered_case_count"),
        "contract_pass": aggregate.get("contract_pass") is True,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }
    # Pass only the compact, derived action taxonomy to the model.  The raw
    # HIAD narrative remains outside the prompt; the digest links the
    # category counts back to the public workbook without implying that the
    # observed actions were safe, effective or statistically representative.
    action_path = path.parent / "hiad_action_evidence.json"
    try:
        action_record = json.loads(action_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        action_record = None
    action_source = (action_record or {}).get("source") or {}
    action_taxonomy = (action_record or {}).get("taxonomy") or {}
    action_status = (action_record or {}).get("status")
    expected_digest = (record.get("source") or {}).get("action_evidence_sha256")
    if (
        isinstance(action_record, dict)
        and action_status == "derived_non_evaluative_action_taxonomy"
        and sha256(action_path.read_bytes()).hexdigest() == expected_digest
        and action_record.get("case_count") == aggregate.get("case_count")
        and action_record.get("source", {}).get("raw_text_retained") is False
        and action_record.get("source", {}).get("holdout_use") is False
    ):
        result["action_taxonomy"] = {
            "artifact": "research/hiad_action_evidence.json",
            "artifact_sha256": expected_digest,
            "source_sha256": action_source.get("sha256"),
            "category_patterns_version": action_taxonomy.get("category_patterns_version"),
            "category_counts": dict(sorted((action_taxonomy.get("category_counts") or {}).items())),
            "raw_text_retained": False,
            "holdout_use": False,
            "claim_limit": str(action_record.get("claim_boundary") or ""),
        }
    return result


def _khk_public_accident_inventory() -> dict[str, Any] | None:
    """Expose KHK's public accident-report inventory as response provenance.

    The inventory contains citation links and scenario classifications, not
    copied report text or process traces.  Keeping it in the evidence envelope
    lets a response show which public accident source family grounds the
    playbook while preserving the separate numerical-validation boundary.
    """
    path = Path(__file__).resolve().parents[2] / (
        "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    coverage = record.get("coverage") or {}
    source_page = record.get("source_page") or {}
    rights = record.get("rights_and_mirroring") or {}
    eligibility = record.get("eligibility") or {}
    if record.get("status") != "public_khk_accident_report_inventory_captured":
        return None
    if rights.get("raw_pdf_mirrored") is not False:
        return None
    result: dict[str, Any] = {
        "artifact": "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json",
        "source_page": source_page.get("url"),
        "institution": source_page.get("institution"),
        "public_report_count": coverage.get("pdf_report_count"),
        "incident_code_count": coverage.get("incident_code_count"),
        "precaution_report_count": coverage.get("precaution_report_count"),
        "raw_pdf_mirrored": False,
        "qualitative_scenario_grounding": eligibility.get(
            "qualitative_scenario_grounding_eligible"
        ) is True,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }
    # The compact map is derived only from the inventory's public equipment
    # classes and titles.  Include it when its source digest matches so the
    # assistant can distinguish relevant accident precedent without receiving
    # copied report text or treating counts as frequencies.
    map_path = Path(__file__).resolve().parents[2] / (
        "research/khk_scenario_precedent_map_2026_10_04.json"
    )
    try:
        scenario_map = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        scenario_map = None
    map_source = (scenario_map or {}).get("source_inventory") or {}
    inventory_digest = sha256(path.read_bytes()).hexdigest()
    if (
        isinstance(scenario_map, dict)
        and scenario_map.get("status") == "citation_only_khk_scenario_precedent_map"
        and map_source.get("sha256") == inventory_digest
        and map_source.get("incident_report_count") == result["public_report_count"]
        and map_source.get("incident_code_count") == result["incident_code_count"]
    ):
        mapping = scenario_map.get("mapping") or {}
        # Keep the runtime manifest intentionally small.  The full map is
        # preserved as a research artifact, while prompt context receives
        # provenance and coverage only.  Internal playbook IDs and long
        # representative citation lists would crowd out live sensor and
        # HAZOP facts and are not user-facing evidence.
        result["scenario_precedent_map"] = {
            "artifact": "research/khk_scenario_precedent_map_2026_10_04.json",
            "mapped_report_count": mapping.get("mapped_report_count"),
            "unmapped_report_count": mapping.get("unmapped_report_count"),
            "citation_only": True,
            "claim_limit": str(scenario_map.get("claim_boundary") or ""),
        }
    return result


def _confidential_local_accident_response_coverage() -> dict[str, Any] | None:
    """Expose only aggregate response-plan traceability for restricted incidents.

    The local owner-controlled casebook is never read by the runtime.  A
    sanitized aggregate can still tell the assistant that the response
    catalogue was checked against actual-incident metadata, while preventing
    operator, site, date, equipment and narrative leakage.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_local_accident_response_coverage_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    aggregate = record.get("aggregate") or {}
    local_contract_run = record.get("local_contract_run") or {}
    if (
        record.get("artifact_type") != "confidential_local_accident_response_coverage"
        or record.get("status") != "local_restricted_metadata_stage_contract"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("raw_descriptions_persisted") is not False
        or aggregate.get("contract_pass") is not True
    ):
        return None
    return {
        "artifact": (
            "research/confidential_local_accident_response_coverage_2026_10_06.json"
        ),
        "evidence_role": str(record.get("evidence_role") or ""),
        "case_count": aggregate.get("case_count"),
        "mapped_case_count": aggregate.get("mapped_case_count"),
        "unmapped_case_count": aggregate.get("unmapped_case_count"),
        "unknown_plan_reference_count": aggregate.get("unknown_plan_reference_count"),
        "case_with_missing_stage_count": aggregate.get("case_with_missing_stage_count"),
        "required_stage_count": aggregate.get("required_stage_count"),
        "scenario_family_candidate_counts": {
            str(key): int(value)
            for key, value in (aggregate.get("scenario_family_candidate_counts") or {}).items()
            if isinstance(value, int) and value >= 0
        },
        "multi_family_case_count": aggregate.get("multi_family_case_count"),
        "contract_pass": True,
        "local_contract_run": {
            "casebook_generated_with_descriptions": local_contract_run.get(
                "casebook_generated_with_descriptions"
            ),
            "casebook_sha256": local_contract_run.get("casebook_sha256"),
            "response_catalog_sha256": local_contract_run.get(
                "response_catalog_sha256"
            ),
            "casebook_and_source_not_committed": local_contract_run.get(
                "casebook_and_source_not_committed"
            ),
            "pipeline": local_contract_run.get("pipeline"),
        },
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_accidental_release_evidence() -> dict[str, Any] | None:
    """Expose the licensed accidental-release archive without overclaiming it.

    The archive contains pressure and paired ignition/no-ignition temperature
    traces from a controlled cylinder breach.  It is useful provenance for
    release/ignition scenario wording, but it is not a station fueling trace
    and must never be presented as an ignition probability or a numerical
    validation of the digital-twin release model.
    """
    root = Path(__file__).resolve().parents[2]
    path = root / "research/accidental_self_ignition_public_evidence_2026_10_04.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    source = record.get("source") or {}
    archive = record.get("archive") or {}
    eligibility = record.get("eligibility") or {}
    if record.get("status") != "public_accidental_release_ignition_evidence_captured":
        return None
    if source.get("license") != "CC BY 4.0" or not eligibility.get(
        "public_accident_or_experiment_evidence"
    ):
        return None

    files: list[dict[str, Any]] = []
    raw_dir = root / "data/public_validation/raw/zenodo_17913628_accidental_self_ignition"
    for item in record.get("files") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        local_path = raw_dir / name
        # The runtime envelope exposes only compact metadata.  A local digest
        # check prevents a stale or edited workbook from silently being used
        # as provenance, while no raw trace values enter the prompt.
        local_match = False
        try:
            local_match = sha256(local_path.read_bytes()).hexdigest() == item.get("sha256")
        except OSError:
            local_match = False
        files.append({
            "name": name,
            "numeric_rows": item.get("numeric_rows"),
            "time_range_s": item.get("time_range_s"),
            "channels": list(item.get("channels") or []),
            "local_sha256_match": local_match,
        })
        if "max_temperature_c" in item:
            files[-1]["max_temperature_c"] = item["max_temperature_c"]
        if "min_temperature_c" in item:
            files[-1]["min_temperature_c"] = item["min_temperature_c"]
    return {
        "artifact": "research/accidental_self_ignition_public_evidence_2026_10_04.json",
        "article_doi": source.get("article_doi"),
        "article_url": source.get("article_url"),
        "zenodo_doi": source.get("zenodo_doi"),
        "dataset_url": source.get("zenodo_record_url"),
        "license": source.get("license"),
        "evidence_role": record.get("evidence_role"),
        "reported_apparatus": source.get("reported_apparatus"),
        "reported_instrumentation": source.get("reported_instrumentation"),
        "archive_sha256": archive.get("sha256"),
        "files": files,
        "consequence_and_ignition_grounding_eligible": eligibility.get(
            "consequence_and_ignition_grounding_eligible"
        ) is True,
        "full_loop_station_vehicle_holdout_eligible": eligibility.get(
            "full_loop_station_vehicle_holdout_eligible"
        ) is True,
        "numerical_release_model_validation_claimed": eligibility.get(
            "numerical_release_model_validation_claimed"
        ) is True,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_detector_logic_evidence() -> dict[str, Any] | None:
    """Expose the public concentration-detector replay as bounded evidence.

    The replay checks the declared alarm/trip persistence rule against measured
    concentration channels from an open-ended channel experiment.  It is
    relevant to detector wording and response sequencing, but it is not a
    station-dispersion or ESD-effectiveness validation.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/dispersion_detector_logic_validation.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    source = record.get("source") or {}
    rule = record.get("rule") or {}
    aggregate = record.get("aggregate") or {}
    if (
        record.get("status") != "completed_bounded_instrumented_detector_logic_evidence"
        or source.get("license") != "CC BY 4.0"
        or not aggregate.get("case_count")
    ):
        return None
    numeric_aggregate = {
        str(key): value
        for key, value in aggregate.items()
        if isinstance(value, (str, int, float, bool))
        and not (isinstance(value, float) and not math.isfinite(value))
    }
    return {
        "artifact": "research/dispersion_detector_logic_validation.json",
        "doi": str(source.get("doi") or ""),
        "license": str(source.get("license") or ""),
        "evidence_role": str(record.get("evidence_role") or ""),
        "rule": {
            "alarm_threshold_percent": rule.get("alarm_threshold_percent"),
            "trip_threshold_percent": rule.get("trip_threshold_percent"),
            "persistence_s": rule.get("persistence_s"),
            "sampling_gap_reset": str(rule.get("sampling_gap_reset") or ""),
        },
        "aggregate": numeric_aggregate,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_dispersion_proxy_evidence() -> dict[str, Any] | None:
    """Expose the concentration scale used by the virtual detector proxy."""

    path = Path(__file__).resolve().parents[2] / (
        "research/dispersion_concentration_proxy_calibration_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    method = record.get("method") or {}
    runtime = record.get("runtime_application") or {}
    coefficient = method.get("coefficient_volpct_per_g_s")
    if (
        record.get("status") != "derived_bounded_dispersion_concentration_proxy"
        or source.get("license") != "CC BY 4.0"
        or source.get("doi") != "10.23642/usn.26117989.v2"
        or not isinstance(coefficient, (int, float))
        or not math.isfinite(float(coefficient))
    ):
        return None
    return {
        "artifact": "research/dispersion_concentration_proxy_calibration_2026_10_06.json",
        "doi": str(source.get("doi") or ""),
        "license": str(source.get("license") or ""),
        "evidence_role": "public measured concentration scale for advisory virtual detector proxy",
        "method": {
            "statistic": method.get("statistic"),
            "case_count": method.get("case_count"),
            "coefficient_volpct_per_g_s": coefficient,
            "coefficient_p25_volpct_per_g_s": method.get("coefficient_p25_volpct_per_g_s"),
            "coefficient_p75_volpct_per_g_s": method.get("coefficient_p75_volpct_per_g_s"),
        },
        "runtime_application": runtime,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_grune_ventilation_evidence() -> dict[str, Any] | None:
    """Expose the measured ventilation envelope used by the virtual proxy.

    Only aggregate ratios enter the evidence envelope.  The raw workbooks stay
    outside Git and the result remains explicitly limited to confined-space
    ventilation/detector-proxy behavior.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/grune_ventilation_empirical_envelope_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    definition = record.get("definition") or {}
    factors = [item for item in record.get("factors") or [] if isinstance(item, dict)]
    if (
        record.get("status") != "derived_empirical_ventilation_envelope"
        or source.get("license") != "CC BY 4.0"
        or source.get("raw_rows_committed") is not False
        or not factors
    ):
        return None
    by_mode: dict[str, list[float]] = {}
    upper_by_mode: dict[str, list[float]] = {}
    for item in factors:
        mode = str(item.get("wind_mode") or "")
        value = item.get("relative_factor")
        upper_value = item.get("relative_factor_upper")
        if mode and isinstance(value, (int, float)) and math.isfinite(float(value)):
            by_mode.setdefault(mode, []).append(float(value))
        if mode and isinstance(upper_value, (int, float)) and math.isfinite(float(upper_value)):
            upper_by_mode.setdefault(mode, []).append(float(upper_value))
    mode_summary = {
        mode: {
            "case_count": len(values),
            "factor_min": min(values),
            "factor_median": float(median(values)),
            "factor_max": max(values),
        }
        for mode, values in sorted(by_mode.items())
        if values
    }
    upper_summary = {
        mode: {
            "case_count": len(values),
            "factor_min": min(values),
            "factor_median": float(median(values)),
            "factor_max": max(values),
        }
        for mode, values in sorted(upper_by_mode.items())
        if values
    }
    return {
        "artifact": "research/grune_ventilation_empirical_envelope_2026_10_06.json",
        "doi": str(source.get("doi") or ""),
        "license": str(source.get("license") or ""),
        "evidence_role": "public measured confined-space ventilation envelope",
        "profiles_used": record.get("profiles_used"),
        "factor_count": record.get("factor_count"),
        "wind_mode_summary": mode_summary,
        "wind_mode_upper_envelope_summary": upper_summary,
        "runtime_parameter_application": "virtual_detector_proxy_only; active releases default to the measured upper spatial envelope",
        "runtime_statistic_default": "upper",
        "definition": {
            "reference": definition.get("reference"),
            "quantity": definition.get("quantity"),
            "fallback": definition.get("fallback"),
        },
        "claim_limit": str(definition.get("not_a_claim") or ""),
    }


def _confidential_measured_boundary_evidence() -> dict[str, Any] | None:
    """Expose only the claim-bounded status of the private-data replay.

    The raw station archive and its mappings never enter the LLM prompt.  This
    compact status lets the assistant distinguish a measured-boundary
    integration check from an independent station-to-vehicle validation claim.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_measured_boundary_replay_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (
        record.get("artifact_type") != "confidential_measured_boundary_replay"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
    ):
        return None
    eligibility = record.get("eligibility") or {}
    replay = record.get("controlled_replay") or {}
    result = {
        "artifact": "research/confidential_measured_boundary_replay_2026_10_06.json",
        "evidence_role": "confidential measured-boundary integration only",
        "trajectory_completed": replay.get("trajectory_completed") is True,
        "station_boundary_calibration_supported": eligibility.get(
            "station_boundary_calibration_supported"
        ) is True,
        "independent_full_loop_validation_supported": eligibility.get(
            "independent_full_loop_validation_supported"
        ) is True,
        "raw_rows_persisted": False,
        "source_identifiers_published": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }
    holdout_path = Path(__file__).resolve().parents[2] / (
        "research/confidential_measured_boundary_holdout_2026_10_06.json"
    )
    try:
        holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        holdout = None
    if (
        isinstance(holdout, dict)
        and holdout.get("artifact_type") == "confidential_measured_boundary_holdout_replay"
        and holdout.get("source_identifiers_published") is False
        and holdout.get("raw_rows_persisted") is False
    ):
        split = holdout.get("split") or {}
        holdout_replay = holdout.get("controlled_replay") or {}
        holdout_eligibility = holdout.get("eligibility") or {}
        result["temporal_holdout"] = {
            "artifact": "research/confidential_measured_boundary_holdout_2026_10_06.json",
            "trajectory_completed": holdout_replay.get("holdout_trajectory_completed") is True,
            "fit_used_holdout": split.get("fit_used_holdout") is True,
            "outcome_used_for_fit": split.get("outcome_used_for_fit") is True,
            "time_ordered_holdout_supported": holdout_eligibility.get(
                "time_ordered_measured_boundary_holdout_supported"
            ) is True,
            "independent_full_loop_validation_supported": holdout_eligibility.get(
                "independent_full_loop_validation_supported"
            ) is True,
            "claim_limit": str(holdout.get("claim_boundary") or ""),
        }
    operational_holdout_path = Path(__file__).resolve().parents[2] / (
        "research/confidential_operational_envelope_holdout_replay_2026_10_06.json"
    )
    try:
        operational_holdout = json.loads(
            operational_holdout_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        operational_holdout = None
    if (
        isinstance(operational_holdout, dict)
        and operational_holdout.get("artifact_type")
        == "confidential_operational_envelope_holdout_replay"
        and operational_holdout.get("source_identifiers_published") is False
        and operational_holdout.get("raw_rows_persisted") is False
    ):
        split = operational_holdout.get("split") or {}
        calibration = operational_holdout.get("calibration") or {}
        replay = operational_holdout.get("replay") or {}
        eligibility = operational_holdout.get("eligibility") or {}
        result["operational_envelope_holdout"] = {
            "artifact": (
                "research/confidential_operational_envelope_holdout_replay_2026_10_06.json"
            ),
            "calibration_points": split.get("calibration_points"),
            "holdout_points": split.get("holdout_points"),
            "fit_used_holdout": split.get("fit_used_holdout") is True,
            "outcome_used_for_fit": split.get("outcome_used_for_fit") is True,
            "calibration_restart_margin_pa": calibration.get(
                "recharge_restart_margin_pa"
            ),
            "trajectory_completed": replay.get("trajectory_completed") is True,
            "esd_triggered": replay.get("esd_triggered") is True,
            "time_ordered_holdout_supported": eligibility.get(
                "time_ordered_measured_boundary_holdout_supported"
            ) is True,
            "independent_full_loop_validation_supported": eligibility.get(
                "independent_full_loop_validation_supported"
            ) is True,
            "claim_limit": str(operational_holdout.get("claim_boundary") or ""),
        }
    cross_station_path = Path(__file__).resolve().parents[2] / (
        "research/confidential_cross_station_pressure_envelope_2026_10_06.json"
    )
    try:
        cross_station = json.loads(cross_station_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cross_station = None
    if (
        isinstance(cross_station, dict)
        and cross_station.get("artifact_type")
        == "confidential_cross_station_pressure_envelope"
        and cross_station.get("source_identifiers_published") is False
        and cross_station.get("raw_rows_persisted") is False
        and cross_station.get("eligibility", {}).get(
            "cross_station_pressure_plausibility_supported"
        ) is True
        and cross_station.get("eligibility", {}).get(
            "station_to_vehicle_validation_supported"
        ) is False
    ):
        comparison = cross_station.get("comparison") or {}
        result["cross_station_pressure_envelope"] = {
            "artifact": (
                "research/confidential_cross_station_pressure_envelope_2026_10_06.json"
            ),
            "profile_count": len(
                [item for item in cross_station.get("profiles") or []
                 if isinstance(item, dict)]
            ),
            "observed_pressure_overlap_mpa": comparison.get(
                "observed_pressure_overlap_mpa"
            ),
            "pressure_semantics_attested_profiles": comparison.get(
                "profiles_with_pressure_semantics_attestation"
            ),
            "temperature_boundary_attested_profiles": comparison.get(
                "profiles_with_temperature_boundary_attestation"
            ),
            "mass_flow_units_attested_profiles": comparison.get(
                "profiles_with_mass_flow_units_attestation"
            ),
            "cross_station_pressure_plausibility_supported": True,
            "station_to_vehicle_validation_supported": False,
            "claim_limit": str(cross_station.get("claim_boundary") or ""),
        }
    return result


def _public_experimental_benchmarks() -> dict[str, Any] | None:
    """Expose aggregate public fueling benchmarks with an explicit claim boundary.

    The benchmarks are useful for answering whether a simulated fill rate,
    pressure ramp or duration is within a published experimental envelope.
    They are deliberately kept separate from live sensor values and from the
    numerical validation gate: the public fast-flow report has no row-level
    logger archive, while the NREL tank/hose trace does not contain station
    controller, ESD, receptacle or vehicle-protocol states.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/public_experimental_benchmarks_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (
        record.get("artifact_type") != "public_experimental_operating_benchmarks"
        or record.get("status") != "citation_bounded_aggregate_benchmarks"
    ):
        return None
    sources: list[dict[str, Any]] = []
    for source in record.get("sources") or []:
        if not isinstance(source, dict) or not source.get("id"):
            continue
        aggregate = source.get("aggregate")
        if not isinstance(aggregate, dict):
            continue
        sources.append({
            "id": str(source["id"]),
            "title": str(source.get("title") or ""),
            "url": str(source.get("url") or ""),
            "raw_rows_public": source.get("raw_rows_public") is True,
            "aggregate": {
                str(key): value
                for key, value in aggregate.items()
                if isinstance(value, (str, int, float, bool))
                and not (isinstance(value, float) and not math.isfinite(value))
            },
            "eligible_for": [str(value) for value in source.get("eligible_for") or []],
            "not_eligible_for": [
                str(value) for value in source.get("not_eligible_for") or []
            ],
        })
    if not sources:
        return None
    return {
        "artifact": "research/public_experimental_benchmarks_2026_10_06.json",
        "evidence_role": str(record.get("evidence_role") or ""),
        "sources": sources,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_tank_validation_evidence() -> dict[str, Any] | None:
    """Expose the frozen public NREL tank screen without exposing raw rows.

    The NREL workbook is a useful measured tank boundary, but it has no
    station-controller or receptacle trace.  Keeping its failed pressure
    screen and geometry diagnostic in the evidence envelope prevents a
    decision assistant from silently turning a partial-boundary result into a
    full HRS validation claim.  This function reads only the aggregate result
    artifact; the workbook remains local and ignored.
    """

    path = Path(__file__).resolve().parents[2] / (
        "data/public_validation/results/nrel_h2fills_hdvs_typeiv/validation.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    aggregate = record.get("aggregate") or {}
    source = record.get("source") or {}
    frozen_model = record.get("frozen_model") or {}
    geometry = record.get("geometry_diagnostic") or {}
    if (
        record.get("evidence_role") != "independent_tank_thermal_external_validation"
        or frozen_model.get("post_access_parameter_tuning") is not False
        or not isinstance(record.get("claim_boundary"), str)
        or aggregate.get("screening_pass_count") is None
    ):
        return None
    return {
        "artifact": "data/public_validation/results/nrel_h2fills_hdvs_typeiv/validation.json",
        "evidence_role": record.get("evidence_role"),
        "source": {
            "publisher": source.get("publisher"),
            "official_download_page": source.get("official_download_page"),
            "dataset_summary": {
                key: source.get("dataset_summary", {}).get(key)
                for key in (
                    "tank_count", "sample_count", "sample_period_median_s",
                    "duration_s", "capacity_per_tank_kg", "mass_added_kg",
                    "reported_mass_added_kg", "initial_pressure_mean_mpa",
                    "final_pressure_mean_mpa", "peak_temperature_mean_c",
                    "ambient_temperature_c",
                )
                if source.get("dataset_summary", {}).get(key) is not None
            },
        },
        "frozen_model": {
            "boundary_conditions": frozen_model.get("boundary_conditions"),
            "post_access_parameter_tuning": False,
            "ambient_temperature_c": frozen_model.get("ambient_temperature_c"),
        },
        "screening_limits": {
            str(key): value
            for key, value in (record.get("screening_limits") or {}).items()
            if isinstance(value, (int, float, str, bool))
        },
        "aggregate": {
            str(key): value
            for key, value in aggregate.items()
            if isinstance(value, (int, float, str, bool))
            and not (isinstance(value, float) and not math.isfinite(value))
        },
        "geometry_diagnostic": {
            "status": geometry.get("status"),
            "method": geometry.get("method"),
            "frozen_effective_volume_m3": geometry.get("frozen_effective_volume_m3"),
            "implied_volume_m3_median_across_tanks": geometry.get(
                "implied_volume_m3_median_across_tanks"
            ),
            "ratio_to_frozen_effective_volume_median": geometry.get(
                "ratio_to_frozen_effective_volume_median"
            ),
            "claim_prohibited": True,
        },
        "claim_supported": False,
        "claim_limit": record.get("claim_boundary"),
    }


def _public_geometry_sensitivity_evidence() -> dict[str, Any] | None:
    """Expose the public capacity/EOS geometry sensitivity as diagnostic evidence.

    The sensitivity report was produced after the public workbook had already
    been accessed.  It is therefore useful for explaining the opt-in geometry
    path and its direction of effect, but it must never be presented as a new
    holdout or silently promote a production default.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/nrel_h2fills_geometry_sensitivity.json"
    )
    rule_path = Path(__file__).resolve().parents[2] / (
        "research/capacity_eos_geometry_rule_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        rule = json.loads(rule_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    variants = record.get("variants") or {}
    claim = record.get("interpretation") or {}
    runtime_rule = rule.get("rule") or {}
    claim_boundary = rule.get("claim_boundary") or {}
    required_variants = (
        "legacy_frozen", "capacity_eos_with_frozen_fit", "capacity_eos_no_volume_fit"
    )
    if (
        record.get("status") != "exploratory_geometry_sensitivity_only"
        or rule.get("status") != "opt_in_runtime_geometry_rule"
        or not all(isinstance(variants.get(name), dict) for name in required_variants)
        or runtime_rule.get("default_changed") is not False
        or claim_boundary.get("independent_confirmatory_validation") is not False
    ):
        return None

    def scalar_values(values: dict[str, Any]) -> dict[str, Any]:
        return {
            str(key): value
            for key, value in values.items()
            if isinstance(value, (int, float, str, bool))
            and not (isinstance(value, float) and not math.isfinite(value))
        }

    return {
        "artifact": "research/nrel_h2fills_geometry_sensitivity.json",
        "evidence_role": "post_access_public_geometry_sensitivity_diagnostic",
        "source": {
            "tank_count": source.get("tank_count"),
            "capacity_per_tank_kg": source.get("capacity_per_tank_kg"),
            "reference_pressure_mpa": source.get("reference_pressure_mpa"),
            "reference_temperature_c": source.get("reference_temperature_c"),
            "capacity_eos_volume_m3": source.get("capacity_eos_volume_m3"),
        },
        "runtime_rule": {
            key: runtime_rule.get(key)
            for key in (
                "basis", "fluid", "reference_pressure_mpa",
                "reference_temperature_c", "runtime_table", "default_basis",
                "default_changed",
            )
            if runtime_rule.get(key) is not None
        },
        "variants": {
            name: scalar_values(variants[name]) for name in required_variants
        },
        "finding": str(claim.get("finding") or ""),
        "required_next_step": str(claim.get("required_next_step") or ""),
        "claim_supported": False,
        "claim_limit": str(claim.get("claim_limit") or "") + " " + str(
            claim_boundary.get("reason") or ""
        ),
    }


def _public_tank_trace_boundary_evidence() -> dict[str, Any] | None:
    """Expose a second public tank trace as a bounded boundary candidate.

    HyTF provides a real 70 MPa tank pressure/thermocouple trace, but it has no
    transferred-mass, dispenser, controller or ESD channels.  The raw file is
    referenced by hash and is never copied into the prompt.  This evidence is
    therefore useful for provenance and future frozen component screening only.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/hytf_open_tank_trace_boundary_2026_10_05.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    experiment = record.get("experiment") or {}
    channels = experiment.get("channels") or {}
    eligibility = record.get("eligibility") or {}
    access = record.get("access_observation") or {}
    if (
        record.get("status") != "PUBLIC_RAW_TANK_TRACE_BOUNDARY_RECHECKED"
        or source.get("repository_commit") is None
        or source.get("dataset_sha256") is None
        or experiment.get("sample_count") is None
        or eligibility.get("component_tank_screen_eligible_after_protocol_freeze")
        is not True
        or eligibility.get("full_loop_external_holdout_eligible") is not False
        or access.get("vehicle_or_receptacle_pressure_temperature_trace") is not False
    ):
        return None
    geometry = experiment.get("geometry") or {}
    observed = experiment.get("observed_ranges") or {}
    return {
        "artifact": "research/hytf_open_tank_trace_boundary_2026_10_05.json",
        "evidence_role": "public_tank_thermal_boundary_candidate",
        "source": {
            "title": source.get("title"),
            "repository_url": source.get("repository_url"),
            "repository_commit": source.get("repository_commit"),
            "repository_license": source.get("repository_license"),
            "dataset_specific_license_identified": (
                source.get("dataset_specific_license_identified") is True
            ),
            "dataset_sha256": source.get("dataset_sha256"),
        },
        "experiment": {
            key: experiment.get(key)
            for key in ("dataset_id", "sample_count", "sample_period_s", "duration_s")
            if experiment.get(key) is not None
        },
        "geometry": {
            key: geometry.get(key)
            for key in ("internal_volume_m3", "internal_diameter_m", "inlet_area_m2")
            if geometry.get(key) is not None
        },
        "channel_scope": {
            "pressure_channel_count": len(channels.get("pressure_channels") or []),
            "tank_thermocouple_count": len(channels.get("tank_thermocouples") or []),
            "mass_flow_channel_present": (
                channels.get("mass_flow_channel_present") is True
            ),
            "vehicle_receptacle_channel_present": (
                channels.get("vehicle_receptacle_channel_present") is True
            ),
            "station_controller_or_esd_channel_present": (
                channels.get("station_controller_or_esd_channel_present") is True
            ),
        },
        "observed_ranges": {
            key: observed.get(key)
            for key in ("p_1_bar", "p_2_bar", "tank_thermocouple_min_degC",
                        "tank_thermocouple_max_degC")
            if observed.get(key) is not None
        },
        "component_tank_screen_eligible": True,
        "full_loop_external_holdout_eligible": False,
        "claim_supported": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_measurement_instrumentation_evidence() -> dict[str, Any] | None:
    """Expose public sampling-workbook scope without inventing channel meaning.

    The MetHyTrucks workbooks are real, openly licensed measurements, but the
    public record does not identify vehicle/receptacle channels or a complete
    refuelling protocol.  Supplying only their provenance and timing context
    keeps the assistant from silently treating tag names as HRS variables.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/metHyTrucks_public_measurement_recheck_2026_10_04.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    classification = record.get("classification") or {}
    inspection = record.get("file_level_inspection") or {}
    if (
        record.get("decision") != "PUBLIC_RAW_HRS_SAMPLING_TIME_SERIES_AUXILIARY_ONLY"
        or classification.get("station_measurement_auxiliary_eligible") is not True
        or classification.get("full_loop_holdout_eligible") is not False
    ):
        return None
    sources = []
    for source in record.get("sources") or []:
        if not isinstance(source, dict) or not source.get("record_id"):
            continue
        sources.append({
            "record_id": str(source.get("record_id")),
            "doi": str(source.get("doi") or ""),
            "title": str(source.get("title") or ""),
            "license": str(source.get("license") or ""),
            "observed_file_count": source.get("observed_file_count"),
        })
    intervals = sorted({
        float(item.get("sampling_interval_observed_s"))
        for item in inspection.get("files") or []
        if isinstance(item, dict)
        and isinstance(item.get("sampling_interval_observed_s"), (int, float))
    })
    return {
        "artifact": "research/metHyTrucks_public_measurement_recheck_2026_10_04.json",
        "evidence_role": "public HRS sampling-system instrumentation context",
        "source_count": len(sources),
        "sources": sources,
        "file_count": inspection.get("file_count"),
        "observed_sampling_intervals_s": intervals,
        "station_measurement_auxiliary_eligible": True,
        "full_loop_holdout_eligible": False,
        "channel_dictionary_present": False,
        "vehicle_or_receptacle_channels_identified": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _preslhy_validation_boundary() -> dict[str, Any] | None:
    """Expose development versus independent PRESLHY outcomes separately.

    The E3.1 development score is useful context, while the E5.1 result is the
    independent holdout that controls the claim.  Neither result is used to
    tune the runtime release model here.
    """

    root = Path(__file__).resolve().parents[2]
    holdout_path = root / "data/public_validation/results/preslhy_e5_1_holdout.json"
    development_path = root / "research/preslhy_nonadiabatic_development_result.json"
    protocol_path = root / "research/preslhy_e5_1_holdout_protocol.json"
    try:
        holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
        development = json.loads(development_path.read_text(encoding="utf-8"))
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    primary = holdout.get("primary_ambient") or {}
    holdout_aggregate = primary.get("aggregate") or {}
    development_aggregate = development.get("aggregate") or {}
    locked_model = protocol.get("locked_model") or {}
    if (
        development.get("evidence_role") != "consumed_development_data_not_external_validation"
        or development.get("claim_prohibited") is not True
        or holdout_aggregate.get("claim_supported") is not False
        or holdout_aggregate.get("minimum_requirements_met") is not False
        or not isinstance(holdout.get("claim_boundary"), str)
        or not isinstance(locked_model.get("module"), str)
    ):
        return None
    return {
        "artifact": "data/public_validation/results/preslhy_e5_1_holdout.json",
        "development_artifact": "research/preslhy_nonadiabatic_development_result.json",
        "evidence_role": "public source-depletion development and independent holdout boundary",
        "locked_model_module": locked_model.get("module"),
        "locked_discharge_coefficient": locked_model.get("discharge_coefficient"),
        "development": {
            "cases": development_aggregate.get("cases"),
            "joint_primary_passes": development_aggregate.get("joint_primary_passes"),
            "joint_primary_pass_fraction": development_aggregate.get(
                "joint_primary_pass_fraction"
            ),
            "claim_prohibited": True,
        },
        "independent_holdout": {
            "cases": holdout_aggregate.get("cases"),
            "joint_primary_passes": holdout_aggregate.get("joint_primary_passes"),
            "joint_primary_pass_fraction": holdout_aggregate.get(
                "joint_primary_pass_fraction"
            ),
            "minimum_requirements_met": False,
            "claim_supported": False,
            "claim_threshold": holdout_aggregate.get("claim_threshold"),
        },
        "runtime_model_parameter_changed": False,
        "claim_limit": str(holdout.get("claim_boundary") or ""),
    }


def _closed_loop_validation_boundary() -> dict[str, Any] | None:
    """Expose the frozen station-to-vehicle holdout boundary.

    The MC-default result is an intentionally consumed external holdout.  It
    failed its predeclared pressure, temperature and final-SOC screens, so it
    must remain visible to decision support as a limitation.  A later
    parameter sweep is carried only as a post-freeze diagnostic and cannot be
    presented as validation or used to support a release claim.
    """

    root = Path(__file__).resolve().parents[2]
    holdout_path = root / (
        "data/public_validation/results/closed_loop_external_holdout/validation.json"
    )
    diagnostic_path = root / "research/closed_loop_mc_default_postfreeze_diagnostic.json"
    try:
        holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
        diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    aggregate = holdout.get("aggregate") or {}
    limits = holdout.get("screening_limits") or {}
    metrics = aggregate.get("metrics") or {}
    diagnostic_aggregate = diagnostic.get("diagnostic_aggregate") or {}
    required = (
        holdout.get("protocol_frozen_before_data_access") is True,
        holdout.get("post_freeze_parameter_tuning") is False,
        aggregate.get("case_count") == 8,
        aggregate.get("screening_pass_count") == 0,
        diagnostic.get("status") == "post_freeze_diagnostic_only",
        diagnostic.get("prohibited_use") and isinstance(
            diagnostic.get("purpose"), str
        ),
    )
    if not all(required):
        return None

    def metric(name: str, field: str) -> Any:
        value = (metrics.get(name) or {}).get(field)
        return _finite_number(value)

    return {
        "artifact": "data/public_validation/results/closed_loop_external_holdout/validation.json",
        "diagnostic_artifact": "research/closed_loop_mc_default_postfreeze_diagnostic.json",
        "evidence_role": "frozen station-to-vehicle external holdout boundary",
        "protocol": holdout.get("protocol"),
        "frozen_model_commit": holdout.get("frozen_model_commit"),
        "protocol_frozen_before_data_access": True,
        "post_freeze_parameter_tuning": False,
        "screening_limits": {
            key: _finite_number(value) for key, value in limits.items()
        },
        "aggregate": {
            "case_count": aggregate.get("case_count"),
            "screening_pass_count": aggregate.get("screening_pass_count"),
            "screening_pass_fraction": _finite_number(
                aggregate.get("screening_pass_fraction")
            ),
            "final_stop_reason_counts": {
                str(key): value
                for key, value in (aggregate.get("final_stop_reason_counts") or {}).items()
                if isinstance(value, int)
            },
            "pressure_rmse_mean_mpa": metric("pressure_rmse_mpa", "mean"),
            "temperature_rmse_mean_c": metric("temperature_rmse_c", "mean"),
            "soc_rmse_mean_percentage_points": metric(
                "soc_rmse_percentage_points", "mean"
            ),
        },
        "post_freeze_diagnostic": {
            "status": diagnostic.get("status"),
            "screening_pass_count": diagnostic_aggregate.get(
                "screening_pass_count"
            ),
            "case_count": diagnostic_aggregate.get("case_count"),
            "pressure_rmse_mean_mpa": _finite_number(
                diagnostic_aggregate.get("pressure_rmse_mean_mpa")
            ),
            "temperature_rmse_mean_c": _finite_number(
                diagnostic_aggregate.get("temperature_rmse_mean_c")
            ),
            "soc_rmse_mean_percentage_points": _finite_number(
                diagnostic_aggregate.get("soc_rmse_mean_percentage_points")
            ),
            "final_stop_reason_counts": {
                str(key): value
                for key, value in (
                    diagnostic_aggregate.get("final_stop_reason_counts") or {}
                ).items()
                if isinstance(value, int)
            },
            "claim_prohibited": True,
        },
        "runtime_model_parameter_changed": False,
        "claim_supported": False,
        "claim_limit": (
            "8개 외부 차량 충전 holdout은 사전 고정된 압력·온도·최종 SOC 기준을 "
            "0/8로 통과하지 못했습니다. 사후 보정 결과는 진단용이며 검증·인증·"
            "현장 일반화 또는 안전성 주장을 뒷받침하지 않습니다."
        ),
    }


def _release_model_validation_boundary() -> dict[str, Any] | None:
    """Expose the locked component-release limitation to decision support.

    The Proust result is a post-outcome diagnostic, not a calibration target.
    Carrying that distinction into the evidence envelope prevents an assistant
    from presenting a release-distance result as if the underlying aperture
    law had passed an independent campaign.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/proust_discharge_coefficient_sensitivity_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.get("artifact_type")
        != "proust_discharge_coefficient_sensitivity_diagnostic"
        or record.get("evidence_role") != "post_outcome_diagnostic_only"
        or record.get("parameter_fitting") is not False
        or record.get("production_model_parameter_changed") is not False
        or not isinstance(record.get("claim_boundary"), str)
    ):
        return None
    rows: list[dict[str, Any]] = []
    for item in record.get("effective_coefficient_by_diameter") or []:
        if not isinstance(item, dict):
            continue
        diameter = item.get("nozzle_diameter_mm")
        median = item.get("effective_cd_median")
        if not isinstance(diameter, (int, float)) or not isinstance(median, (int, float)):
            continue
        if not math.isfinite(float(diameter)) or not math.isfinite(float(median)):
            continue
        rows.append({
            "nozzle_diameter_mm": float(diameter),
            "effective_cd_median": float(median),
        })
    baseline = record.get("baseline_discharge_coefficient")
    if (
        not isinstance(baseline, (int, float))
        or not math.isfinite(float(baseline))
        or len(rows) != 3
    ):
        return None
    baseline_series = next(
        (
            item for item in record.get("sensitivity_grid") or []
            if isinstance(item, dict)
            and item.get("discharge_coefficient") == baseline
        ),
        None,
    )
    return {
        "artifact": "research/proust_discharge_coefficient_sensitivity_2026_10_06.json",
        "evidence_role": "post_outcome_diagnostic_only",
        "baseline_discharge_coefficient": float(baseline),
        "baseline_joint_primary_pass_count": (
            baseline_series.get("joint_primary_pass_count")
            if isinstance(baseline_series, dict) else None
        ),
        "effective_coefficient_by_diameter": sorted(
            rows, key=lambda item: item["nozzle_diameter_mm"]
        ),
        "parameter_fitting": False,
        "production_model_parameter_changed": False,
        "claim_limit": str(record.get("claim_boundary")),
    }


def _public_hitrf_operational_reference() -> dict[str, Any] | None:
    """Expose a public facility envelope without treating it as raw validation.

    The HITRF page describes real storage, compression and thermal equipment,
    but it does not publish synchronized logger rows.  Keeping this reference
    separate from experimental benchmarks lets the assistant explain scale and
    operating-envelope differences while preserving the full-loop validation
    boundary.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/nlr_hitrf_public_operational_reference_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    runtime = record.get("runtime_use") or {}
    if (
        record.get("artifact_type") != "public_facility_operational_reference"
        or record.get("status") != "public_facility_operational_reference"
        or source.get("raw_synchronized_logger_public") is not False
        or not source.get("url")
        or not runtime.get("claim_boundary")
    ):
        return None

    def compact_equipment(value: Any) -> dict[str, Any]:
        return {
            str(key): item
            for key, item in (value or {}).items()
            if isinstance(item, (str, int, float, bool))
            and not (isinstance(item, float) and not math.isfinite(item))
        }

    storage = record.get("storage") or {}
    storage_rows = {
        str(tier): compact_equipment(values)
        for tier, values in storage.items()
        if isinstance(values, dict)
    }
    compression_rows = [
        compact_equipment(values)
        for values in record.get("compression", {}).get("stages") or []
        if isinstance(values, dict)
    ]
    thermal = record.get("dispensing_and_thermal") or {}
    return {
        "artifact": "research/nlr_hitrf_public_operational_reference_2026_10_06.json",
        "evidence_role": str(record.get("evidence_role") or ""),
        "source": {
            "title": str(source.get("title") or ""),
            "institution": str(source.get("institution") or ""),
            "url": str(source.get("url") or ""),
            "public_page_describes_automated_logging": (
                source.get("public_page_describes_automated_logging") is True
            ),
            "raw_synchronized_logger_public": False,
        },
        "storage": storage_rows,
        "compression_stages": compression_rows,
        "dispensing_and_thermal": {
            key: thermal.get(key)
            for key in (
                "dispensing_pressures", "chiller_target_temperature_c",
                "chiller_idle_energy_kwh_per_day", "chiller_recovery_energy_kwh_per_fill",
                "research_dispenser_adjustable_fields",
            )
            if thermal.get(key) is not None
        },
        "eligible_for": [str(value) for value in runtime.get("eligible_for") or []],
        "not_eligible_for": [str(value) for value in runtime.get("not_eligible_for") or []],
        "claim_limit": str(runtime.get("claim_boundary") or ""),
    }


def _public_real_station_context() -> dict[str, Any] | None:
    """Load a public real-station report without treating it as raw holdout data."""

    path = Path(__file__).resolve().parents[2] / (
        "research/calstate_la_back_to_back_article_data_boundary_2026_10_05.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    observed = record.get("observed_evidence") or {}
    decision = record.get("eligibility_decision") or {}
    if (
        not isinstance(source, dict)
        or not source.get("doi")
        or not str(source.get("url") or "").startswith(("https://", "http://"))
        or observed.get("field_integration") is not True
        or observed.get("public_raw_synchronized_rows") is not False
        or decision.get("full_loop_external_holdout_eligible") is not False
    ):
        return None
    return {
        "artifact": "research/calstate_la_back_to_back_article_data_boundary_2026_10_05.json",
        "evidence_role": "public real-station operational context",
        "source": {
            "title": str(source.get("title") or ""),
            "doi": str(source.get("doi") or ""),
            "url": str(source.get("url") or ""),
            "publisher": str(source.get("publisher") or ""),
            "article_open_access": source.get("article_open_access") is True,
            "public_raw_synchronized_rows": False,
        },
        "reported_campaign": str(observed.get("reported_campaign") or ""),
        "reported_scenarios": [
            str(value) for value in observed.get("reported_scenarios") or []
        ],
        "reported_channels_or_outputs": [
            str(value) for value in observed.get("reported_channels_or_outputs") or []
        ],
        "full_loop_external_holdout_eligible": False,
        "allowed_use": [str(value) for value in decision.get("allowed_use") or []],
        "prohibited_use": [
            str(value) for value in decision.get("prohibited_use") or []
        ],
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_source_links(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a tiny, inspectable index of public sources used for grounding.

    The live prompt needs enough provenance for an operator to follow a claim
    back to its public source, but it must not receive raw private rows or
    internal file paths.  Only URLs/DOIs already admitted by the bounded
    evidence readers are copied here; private evidence is intentionally
    excluded.
    """

    links: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(source_id: str, title: str, url: str, role: str) -> None:
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            return
        key = (source_id, url)
        if key in seen:
            return
        seen.add(key)
        links.append({
            "id": source_id,
            "title": title,
            "url": url,
            "role": role,
        })

    benchmarks = evidence.get("public_experimental_benchmarks") or {}
    for source in benchmarks.get("sources") or []:
        if not isinstance(source, dict):
            continue
        add(
            str(source.get("id") or "public_experiment"),
            str(source.get("title") or "Public hydrogen experiment"),
            str(source.get("url") or ""),
            "실제 충전 실험 운전범위·부분 경계 근거",
        )

    hitrf = evidence.get("public_hitrf_operational_reference") or {}
    hitrf_source = hitrf.get("source") or {}
    add(
        "PUBLIC_HITRF_OPERATIONAL_REFERENCE",
        str(hitrf_source.get("title") or "Public HRS facility reference"),
        str(hitrf_source.get("url") or ""),
        "실설비 규모·압력 tier·압축/예냉 운전범위 참고",
    )

    station_context = evidence.get("public_real_station_context") or {}
    station_source = station_context.get("source") or {}
    add(
        "PUBLIC_REAL_STATION_B2B_CONTEXT",
        str(station_source.get("title") or "Real-station back-to-back fueling context"),
        str(station_source.get("url") or ""),
        "실충전소 back-to-back 운전·저장압력·냉각·차량 SOC 맥락",
    )

    tank_trace = evidence.get("public_tank_trace_boundary") or {}
    tank_source = tank_trace.get("source") or {}
    add(
        "PUBLIC_HYTF_TANK_TRACE",
        str(tank_source.get("title") or "Public high-pressure tank trace"),
        str(tank_source.get("repository_url") or ""),
        "실측 70 MPa 탱크 압력·열경계 후보(충전소 full-loop 검증 아님)",
    )

    khk = evidence.get("public_accident_report_inventory") or {}
    add(
        "KHK_PUBLIC_ACCIDENT_REPORTS",
        str(khk.get("institution") or "Public hydrogen accident reports"),
        str(khk.get("source_page") or ""),
        "공개 사고사례 분류·대응절차 근거",
    )

    accidental = evidence.get("public_accidental_release_evidence") or {}
    add(
        "PUBLIC_ACCIDENTAL_RELEASE_ARTICLE",
        "Accidental self-ignition of hydrogen released from pressurized cylinder",
        str(accidental.get("article_url") or ""),
        "방출·점화 현상 참고자료(충전소 full-loop 검증 아님)",
    )
    add(
        "PUBLIC_ACCIDENTAL_RELEASE_DATASET",
        "Accidental release temperature/pressure dataset",
        str(accidental.get("dataset_url") or ""),
        "공개 실험 원자료 출처(방출모델 검증 주장 아님)",
    )

    detector = evidence.get("public_detector_logic_evidence") or {}
    detector_doi = str(detector.get("doi") or "")
    if detector_doi:
        add(
            "PUBLIC_DETECTOR_LOGIC_DATASET",
            "Experimental hydrogen dispersion detector dataset",
            f"https://doi.org/{detector_doi}",
            "검지기 alarm/trip persistence 재현 근거",
        )
    proxy = evidence.get("public_dispersion_proxy_evidence") or {}
    proxy_doi = str(proxy.get("doi") or "")
    if proxy_doi:
        add(
            "PUBLIC_DISPERSION_PROXY_CALIBRATION",
            "Experimental hydrogen dispersion concentration scale",
            f"https://doi.org/{proxy_doi}",
            "공개 농도·방출량 통계 기반 가상 검지기 농도 스케일",
        )
    ventilation = evidence.get("public_grune_ventilation_evidence") or {}
    ventilation_doi = str(ventilation.get("doi") or "")
    if ventilation_doi:
        add(
            "PUBLIC_GRUNE_VENTILATION_DATASET",
            "Efficiency of mechanical ventilation on H2 dispersion",
            f"https://doi.org/{ventilation_doi}",
            "공개 환기·확산 측정 기반 검지기 proxy 보정",
        )
    return links


def _public_operating_envelope_screen(
    frame: dict[str, Any],
    benchmarks: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Compare live simulated flow with public aggregate experiment context.

    This is deliberately a descriptive screen, not a validation score.  The
    public heavy-duty reports do not provide an untouched station-to-vehicle
    row-level holdout, so the result may only say whether the current simulated
    flow is below, within, or above the published operating context.
    """

    if not isinstance(benchmarks, dict):
        return None
    sources = [item for item in benchmarks.get("sources") or [] if isinstance(item, dict)]
    fast_flow = next(
        (item for item in sources if item.get("id") == "NREL_HD_FAST_FLOW_2024_REPORT"),
        None,
    )
    if not isinstance(fast_flow, dict):
        return None
    aggregate = fast_flow.get("aggregate") or {}
    current = _finite_number(frame.get("nozzle_flow_g_s"))
    pressure = _finite_number(frame.get("vehicle_pressure_mpa"))
    if current is None:
        return None
    peak = _finite_number(aggregate.get("peak_mass_flow_g_s"))
    average = _finite_number(aggregate.get("average_mass_flow_g_s"))
    if current <= 1.0e-9:
        flow_context = "idle"
    elif peak is not None and current > peak:
        flow_context = "above_public_fast_flow_peak_context"
    elif average is not None and current >= average:
        flow_context = "within_public_fast_flow_context"
    else:
        flow_context = "below_public_heavy_duty_average_context"
    endpoint_pressure = {
        "reported_start_mpa": _finite_number(aggregate.get("starting_pressure_mpa")),
        "reported_end_mpa": _finite_number(aggregate.get("ending_pressure_mpa")),
    }
    return {
        "status": "screened",
        "source_id": str(fast_flow.get("id") or ""),
        "source_url": str(fast_flow.get("url") or ""),
        "current_simulated_nozzle_flow_g_s": current,
        "public_average_flow_g_s": average,
        "public_peak_flow_g_s": peak,
        "flow_context": flow_context,
        "current_simulated_vehicle_pressure_mpa": pressure,
        "public_reported_pressure_context_mpa": endpoint_pressure,
        "raw_rows_public": fast_flow.get("raw_rows_public") is True,
        "validation_claim": False,
        "claim_limit": (
            "공개 고유량 실험의 집계 운전범위와 비교한 설명용 screen이다. "
            "충전소-차량 full-loop 정확도·프로토콜 적합성·안전 인증을 검증하지 않는다."
        ),
    }


def _confidential_lifecycle_evidence() -> dict[str, Any] | None:
    """Expose only de-identified lifecycle-counter calibration context."""

    profile = load_lifecycle_evidence()
    if profile is None:
        return None
    metadata = profile.runtime_metadata()
    return {
        "artifact": metadata["artifact"],
        "evidence_role": "confidential de-identified lifecycle history",
        "counter_semantics": metadata["counter_semantics"],
        "sampled_rows": metadata["sampled_rows"],
        "counters": metadata["counters"],
        "full_recharge_threshold_bar": metadata["full_recharge_threshold_bar"],
        "counter_semantics_attested": metadata["counter_semantics_attested"],
        "threshold_units_attested": metadata["threshold_units_attested"],
        "cycle_aware_degradation_fit": metadata[
            "degradation_relationship_attested"
        ],
        "claim_limit": metadata["claim_boundary"],
    }


def _confidential_station_calibration_evidence() -> dict[str, Any] | None:
    """Expose bounded pressure-log calibration context to the assistant."""

    profile = load_measured_boundary_calibration()
    if profile is None:
        return None
    path = Path(__file__).resolve().parents[2] / profile.evidence_artifact
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.get("artifact_type") not in {
            "confidential_station_boundary_calibration_summary",
            "confidential_operational_envelope_calibration_summary",
        }
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
    ):
        return None
    pressure = record.get("boundary_pressure_mpa") or {}
    return {
        "artifact": profile.evidence_artifact,
        "evidence_role": "confidential measured station-boundary calibration",
        "profile_id": profile.profile_id,
        "source_scope": profile.source_scope,
        "files_read": record.get("files_read"),
        "sampled_rows": record.get("sampled_rows"),
        "duration_s": record.get("duration_s"),
        "median_sample_period_s": record.get("median_sample_period_s"),
        "maximum_gap_s": record.get("maximum_gap_s"),
        "boundary_pressure_mpa": {
            key: pressure.get(key)
            for key in ("min", "median", "max")
            if pressure.get(key) is not None
        },
        "positive_pressure_ramp_p95_pa_s": record.get(
            "positive_pressure_ramp_p95_pa_s"
        ),
        "pressure_noise_sigma_pa": record.get("pressure_noise_sigma_pa"),
        "recommended_recharge_restart_margin_pa": record.get(
            "recommended_recharge_restart_margin_pa"
        ),
        "state_transition_count": record.get("state_transition_count"),
        "channel_roles": list(record.get("channel_roles") or []),
        "channel_attestation": {
            key: bool(value)
            for key, value in (record.get("channel_attestation") or {}).items()
            if key in {
                "pressure_boundary_semantics_attested",
                "lifecycle_counter_semantics_attested",
                "temperature_boundary_role_attested",
                "mass_flow_units_attested",
            }
        },
        "station_boundary_calibration_supported": (
            record.get("eligibility", {}).get("station_boundary_calibration_supported")
            is True
        ),
        "full_station_vehicle_validation": (
            record.get("eligibility", {}).get("full_station_vehicle_validation") is True
        ),
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_pressure_channel_evidence() -> dict[str, Any] | None:
    """Expose channel-specific measured envelopes without bank identity."""

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_station_boundary_channel_envelopes_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.get("artifact_type")
        != "confidential_station_boundary_channel_envelopes"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("exact_source_dates_published") is not False
    ):
        return None
    channels: dict[str, dict[str, Any]] = {}
    for channel_id, value in (record.get("channels") or {}).items():
        if not str(channel_id).startswith("boundary_channel_") or not isinstance(value, dict):
            continue
        pressure = value.get("pressure_mpa") or {}
        channels[str(channel_id)] = {
            "sampled_rows": value.get("sampled_rows"),
            "pressure_mpa": {
                key: pressure.get(key)
                for key in ("min", "p05", "median", "p95", "max")
                if pressure.get(key) is not None
            },
            "positive_pressure_ramp_p95_pa_s": value.get(
                "positive_pressure_ramp_p95_pa_s"
            ),
            "recommended_restart_margin_pa": value.get(
                "recommended_restart_margin_pa"
            ),
            "pressure_semantics_attested": value.get(
                "pressure_semantics_attested"
            ) is True,
        }
    if not channels:
        return None
    return {
        "artifact": "research/confidential_station_boundary_channel_envelopes_2026_10_06.json",
        "evidence_role": "confidential measured channel-indexed pressure envelope",
        "sampled_rows": sum(
            int(value.get("sampled_rows") or 0) for value in channels.values()
        ),
        "channels": channels,
        "bank_role_mapping_attested": (
            record.get("eligibility", {}).get("bank_role_mapping_attested") is True
        ),
        "runtime_parameter_application": (
            record.get("eligibility", {}).get("runtime_parameter_application") is True
        ),
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_station_equipment_evidence() -> dict[str, Any] | None:
    """Expose a de-identified equipment envelope without fitting new physics."""

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_station_equipment_operational_envelope_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.get("artifact_type")
        != "confidential_station_equipment_operational_envelope"
        or record.get("evidence_role")
        != "privacy_bounded_station_equipment_diagnostic"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("exact_source_dates_published") is not False
        or record.get("manufacturer_or_model_published") is not False
        or record.get("tag_names_published") is not False
    ):
        return None
    observed = record.get("observed_envelope") or {}
    pressure = observed.get("storage_pressure_mpa") or {}
    temperature = observed.get("station_temperature_degC") or {}
    sampling = record.get("sampling") or {}
    eligibility = record.get("eligibility") or {}
    attestation = record.get("channel_attestation") or {}
    return {
        "artifact": "research/confidential_station_equipment_operational_envelope_2026_10_06.json",
        "evidence_role": str(record.get("evidence_role")),
        "source_scope": str(record.get("source_scope") or ""),
        "sampled_rows": sampling.get("sampled_rows"),
        "duration_s": sampling.get("duration_s"),
        "median_sample_period_s": sampling.get("median_sample_period_s"),
        "maximum_gap_s": sampling.get("maximum_gap_s"),
        "storage_pressure_mpa": {
            key: pressure.get(key) for key in ("min", "median", "max")
            if pressure.get(key) is not None
        },
        "station_temperature_degC": {
            key: temperature.get(key) for key in ("min", "median", "max")
            if temperature.get(key) is not None
        },
        "state_transition_count": observed.get("state_transition_count"),
        "channel_roles": list(record.get("channel_roles") or []),
        "channel_attestation": {
            key: bool(attestation.get(key))
            for key in (
                "pressure_boundary_semantics_attested",
                "temperature_boundary_role_attested",
                "state_semantics_attested",
            )
        },
        "station_equipment_envelope_supported": (
            eligibility.get("station_equipment_envelope_supported") is True
        ),
        "station_boundary_temperature_calibration_supported": (
            eligibility.get("station_boundary_temperature_calibration_supported") is True
        ),
        "vehicle_side_channels_present": (
            eligibility.get("vehicle_side_channels_present") is True
        ),
        "full_station_vehicle_validation": (
            eligibility.get("full_station_vehicle_validation") is True
        ),
        "default_model_parameters_changed": (
            eligibility.get("default_model_parameters_changed") is True
        ),
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_pressure_recheck_decision() -> dict[str, Any] | None:
    """Expose the privacy-safe decision on a rejected pressure recheck.

    The candidate margin is kept separate from the active calibration profile.
    Including that distinction in the evidence envelope prevents an LLM from
    presenting a sparse or sentinel-contaminated recheck as an applied model
    parameter.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_pressure_recheck_decision_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    decision = record.get("decision") or {}
    recheck = record.get("recheck") or {}
    provenance = record.get("provenance_boundary") or {}
    if (
        record.get("artifact_type") != "confidential_pressure_recheck_decision"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or provenance.get("operator_published") is not False
        or provenance.get("site_published") is not False
        or provenance.get("exact_source_dates_published") is not False
        or decision.get("candidate_applied_to_runtime") is not False
        or not decision.get("production_profile_retained")
    ):
        return None
    return {
        "artifact": "research/confidential_pressure_recheck_decision_2026_10_06.json",
        "evidence_role": "confidential calibration quality decision",
        "candidate_applied_to_runtime": False,
        "production_profile_retained": decision.get("production_profile_retained"),
        "retained_restart_margin_mpa": decision.get("retained_restart_margin_mpa"),
        "candidate_restart_margin_mpa": recheck.get("candidate_restart_margin_mpa"),
        "quality_warnings": list(recheck.get("quality_warnings") or []),
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_station_schema_evidence() -> dict[str, Any] | None:
    """Expose only the de-identified private-channel intake boundary."""

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_station_schema_audit_2026_10.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.get("artifact_type") != "confidential_station_schema_audit"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("exact_source_dates_published") is not False
    ):
        return None
    inventory = record.get("signal_inventory") or {}
    units = record.get("unit_attestation") or {}
    eligibility = record.get("eligibility") or {}
    family_counts = dict(inventory.get("privacy_bounded_channel_families") or {})
    station_side_families = list(
        eligibility.get("station_side_component_families_present") or []
    )
    return {
        "artifact": "research/confidential_station_schema_audit_2026_10.json",
        "evidence_role": "confidential de-identified station schema intake",
        "source_bundle_count": record.get("source_bundle_count"),
        "file_count": record.get("file_count"),
        "tagged_channel_counts": dict(inventory.get("tagged_channel_counts") or {}),
        # Keep the private intake useful to the assistant without exposing raw
        # tag names, filenames, dates, or site/manufacturer identifiers.
        "privacy_bounded_channel_families": family_counts,
        "vehicle_side_channel_family_count": eligibility.get(
            "vehicle_side_channel_family_count"
        ),
        "station_side_component_families_present": station_side_families,
        "unit_attestation": {
            key: units.get(key)
            for key in (
                "machine_readable_unit_dictionary_found",
                "pressure_units_attested",
                "temperature_units_attested",
                "flow_units_attested",
                "state_semantics_attested",
            )
        },
        "station_side_schema_intake_supported": (
            eligibility.get("station_side_schema_intake_supported") is True
        ),
        "full_loop_holdout_eligible": (
            eligibility.get("full_loop_holdout_eligible") is True
        ),
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _finite_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(float(value)):
        return None
    return value


def _signal_rows(signals: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tag, raw in sorted((signals or {}).items()):
        if not isinstance(raw, dict):
            continue
        value = _finite_number(raw.get("value"))
        if value is None:
            continue
        rows.append({
            "tag": str(tag),
            "value": value,
            "unit": str(raw.get("unit") or ""),
            "quality": str(raw.get("quality") or "UNKNOWN"),
        })
    return rows


def _impact_rows(results: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Keep only values needed to audit an answer, not implementation fields."""
    fields = (
        "node_id", "node_name", "calculation_status", "calculation_basis",
        "sensor_basis", "pressure_sensor", "temperature_sensor",
        "current_pressure_mpa", "current_temperature_c", "orifice_diameter_mm",
        "maximum_heat_flux_w_m2", "maximum_overpressure_pa",
        "sampled_effect_radius_m", "sampled_next_distance_m",
        "flammable_plume_streamline_distance_m", "effect_range_status",
        "modeled_consequence_mass_flow_kg_s", "mass_flow_override_requested",
        "mass_flow_override_status", "mass_flow_override_ratio",
        "mass_flow_override_claim_limit",
    )
    rows: list[dict[str, Any]] = []
    for result in results or []:
        if not isinstance(result, dict):
            continue
        row: dict[str, Any] = {}
        for field in fields:
            value = result.get(field)
            if isinstance(value, (str, int, float, bool)):
                if isinstance(value, float) and not math.isfinite(value):
                    continue
                row[field] = value
        if row:
            rows.append(row)
    return rows


def build_evidence_manifest(
    frame: dict[str, Any],
    sensor_values: dict[str, Any] | None,
    impact_results: Iterable[dict[str, Any]] | None,
    impact_calculation_attempted: bool,
    *,
    active_conditions: Iterable[dict[str, Any]] | None = None,
    selected_sensor: str | None = None,
    question: str = "",
) -> dict[str, Any]:
    """Build a provenance envelope shared by the main and sensor assistants.

    ``calculation_status`` is intentionally explicit: ``not_requested`` is
    different from ``attempted_no_result`` and both differ from ``calculated``.
    The digest covers every field except itself, allowing a saved LLM response
    to be tied back to the exact simulator snapshot used for that response.
    """
    all_signals = _signal_rows(sensor_values)
    # The LLM prompt has a bounded context.  The selected/related signals are
    # already supplied separately; retain a deterministic prefix here so that
    # provenance cannot crowd out the impact result and response guidance.
    signals = all_signals[:48]
    impacts = _impact_rows(impact_results)
    if not impact_calculation_attempted:
        impact_status = "not_requested"
    elif impacts and any(row.get("calculation_status") == "calculated" for row in impacts):
        impact_status = "calculated"
    else:
        impact_status = "attempted_no_result"

    conditions = []
    response_source_ids: set[str] = set()
    for condition in active_conditions or []:
        if not isinstance(condition, dict):
            continue
        label = condition.get("scenario") or condition.get("시나리오명") or condition.get("condition_status")
        if label:
            raw_source_ids = condition.get("response_source_ids") or condition.get("source_ids") or condition.get("sources") or []
            if isinstance(raw_source_ids, str):
                raw_source_ids = [raw_source_ids]
            source_ids = sorted({str(value) for value in raw_source_ids if value})
            response_source_ids.update(source_ids)
            conditions.append({
                "label": str(label),
                "sensor": str(condition.get("sensor_id") or ""),
                "severity": str(condition.get("severity") or condition.get("등급") or ""),
                "state": str(condition.get("state") or ""),
                "response_source_ids": source_ids,
            })

    envelope: dict[str, Any] = {
        "schema": "h2station.llm-evidence.v1",
        "source": {
            "kind": "DIGITAL_TWIN_SIMULATION",
            "simulation_time_s": _finite_number(frame.get("time_s")),
            "field_measurement": False,
            "claim_limit": "모의 계측과 모델 계산이며 현장 안전거리·실측 사고를 확정하지 않음",
        },
        "runtime_calibration": _runtime_calibration_profile(frame),
        "runtime_geometry": _runtime_geometry_profile(frame),
        "virtual_detector_proxy": frame.get("virtual_detector_proxy") or {},
        "detector_policy": {
            key: frame.get("detector_policy", {}).get(key)
            for key in (
                "source_artifact", "source_doi", "source_license", "status",
                "alarm_threshold_volpct_h2", "trip_threshold_volpct_h2",
                "persistence_s", "claim_limit",
            )
            if isinstance(frame.get("detector_policy"), dict)
            and frame.get("detector_policy", {}).get(key) is not None
        },
        "selected_sensor": selected_sensor,
        "question": question[:1200],
        "signals": {
            "count": len(all_signals),
            "exposed_count": len(signals),
            "omitted_count": max(0, len(all_signals) - len(signals)),
            "rows": signals,
            "good_quality_count": sum(row["quality"] == "GOOD" for row in all_signals),
        },
        "conditions": conditions,
        "response_evidence": {
            "source_ids": sorted(response_source_ids),
            "claim_limit": "대응 절차의 공개 근거 식별자이며, 현장 절차 승인·효과·법적 적합성을 자동으로 보증하지 않음",
        },
        "impact": {
            "calculation_attempted": bool(impact_calculation_attempted),
            "calculation_status": impact_status,
            "result_count": len(impacts),
            "results": impacts,
            "claim_limit": "표본 초과 거리이며 현장 대피거리 또는 확정 사고범위가 아님",
        },
        "uncertainty": {
            "sensor_quality_is_simulated": True,
            "assumptions_must_be_named": True,
            "uncalculated_values_must_not_be_invented": True,
        },
    }
    traceability = _public_incident_traceability()
    if traceability is not None:
        envelope["response_evidence"]["public_incident_traceability"] = traceability
    khk_inventory = _khk_public_accident_inventory()
    if khk_inventory is not None:
        envelope["response_evidence"]["public_accident_report_inventory"] = khk_inventory
    local_accident_coverage = _confidential_local_accident_response_coverage()
    if local_accident_coverage is not None:
        envelope["response_evidence"][
            "confidential_local_accident_response_coverage"
        ] = local_accident_coverage
    accidental_release = _public_accidental_release_evidence()
    if accidental_release is not None:
        envelope["response_evidence"]["public_accidental_release_evidence"] = accidental_release
    detector_logic = _public_detector_logic_evidence()
    if detector_logic is not None:
        envelope["response_evidence"]["public_detector_logic_evidence"] = detector_logic
    dispersion_proxy = _public_dispersion_proxy_evidence()
    if dispersion_proxy is not None:
        envelope["response_evidence"]["public_dispersion_proxy_evidence"] = dispersion_proxy
    grune_ventilation = _public_grune_ventilation_evidence()
    if grune_ventilation is not None:
        envelope["response_evidence"][
            "public_grune_ventilation_evidence"
        ] = grune_ventilation
    confidential_boundary = _confidential_measured_boundary_evidence()
    if confidential_boundary is not None:
        envelope["response_evidence"]["confidential_measured_boundary_replay"] = confidential_boundary
    public_benchmarks = _public_experimental_benchmarks()
    if public_benchmarks is not None:
        envelope["response_evidence"]["public_experimental_benchmarks"] = public_benchmarks
        envelope_screen = _public_operating_envelope_screen(frame, public_benchmarks)
        if envelope_screen is not None:
            envelope["response_evidence"]["public_operating_envelope_screen"] = envelope_screen
    public_tank_validation = _public_tank_validation_evidence()
    if public_tank_validation is not None:
        envelope["response_evidence"][
            "public_tank_validation_boundary"
        ] = public_tank_validation
    public_geometry_sensitivity = _public_geometry_sensitivity_evidence()
    if public_geometry_sensitivity is not None:
        envelope["response_evidence"][
            "public_geometry_sensitivity"
        ] = public_geometry_sensitivity
    public_tank_trace = _public_tank_trace_boundary_evidence()
    if public_tank_trace is not None:
        envelope["response_evidence"][
            "public_tank_trace_boundary"
        ] = public_tank_trace
    public_measurement = _public_measurement_instrumentation_evidence()
    if public_measurement is not None:
        envelope["response_evidence"][
            "public_measurement_instrumentation"
        ] = public_measurement
    preslhy = _preslhy_validation_boundary()
    if preslhy is not None:
        envelope["response_evidence"]["preslhy_validation_boundary"] = preslhy
    closed_loop = _closed_loop_validation_boundary()
    if closed_loop is not None:
        envelope["response_evidence"][
            "closed_loop_validation_boundary"
        ] = closed_loop
    release_boundary = _release_model_validation_boundary()
    if release_boundary is not None:
        envelope["response_evidence"][
            "proust_release_model_validation_boundary"
        ] = release_boundary
    hitrf_reference = _public_hitrf_operational_reference()
    if hitrf_reference is not None:
        envelope["response_evidence"][
            "public_hitrf_operational_reference"
        ] = hitrf_reference
    real_station_context = _public_real_station_context()
    if real_station_context is not None:
        envelope["response_evidence"][
            "public_real_station_context"
        ] = real_station_context
    lifecycle = _confidential_lifecycle_evidence()
    if lifecycle is not None:
        envelope["response_evidence"]["confidential_lifecycle_counter_summary"] = lifecycle
    station_calibration = _confidential_station_calibration_evidence()
    if station_calibration is not None:
        envelope["response_evidence"][
            "confidential_station_boundary_calibration"
        ] = station_calibration
    channel_envelopes = _confidential_pressure_channel_evidence()
    if channel_envelopes is not None:
        envelope["response_evidence"][
            "confidential_pressure_channel_envelopes"
        ] = channel_envelopes
    station_equipment = _confidential_station_equipment_evidence()
    if station_equipment is not None:
        envelope["response_evidence"][
            "confidential_station_equipment_operational_envelope"
        ] = station_equipment
    pressure_recheck = _confidential_pressure_recheck_decision()
    if pressure_recheck is not None:
        envelope["response_evidence"][
            "confidential_pressure_recheck_decision"
        ] = pressure_recheck
    station_schema = _confidential_station_schema_evidence()
    if station_schema is not None:
        envelope["response_evidence"][
            "confidential_station_schema_intake"
        ] = station_schema
    canonical = json.dumps(envelope, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), default=str).encode("utf-8")
    envelope["evidence_digest"] = "sha256:" + sha256(canonical).hexdigest()
    return envelope


def prompt_evidence_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a bounded evidence slice that is safe to place early in prompts.

    Live telemetry and registered response rules can be large enough to push
    provenance to the end of a provider's context cap.  This compact view keeps
    the public experiment, detector replay and confidential measured-boundary
    claim limits visible without copying raw rows or the full signal set.
    """

    evidence = manifest.get("response_evidence") or {}
    def short(value: Any, limit: int = 240) -> str:
        text = str(value or "")
        return text if len(text) <= limit else text[: limit - 1] + "…"

    summary: dict[str, Any] = {
        "claim_limit": short(evidence.get("claim_limit")),
        "runtime_calibration": manifest.get("runtime_calibration") or {},
        "runtime_geometry": manifest.get("runtime_geometry") or {},
        "virtual_detector_proxy": manifest.get("virtual_detector_proxy") or {},
        "detector_policy": manifest.get("detector_policy") or {},
    }
    benchmarks = evidence.get("public_experimental_benchmarks")
    if isinstance(benchmarks, dict):
        rows = []
        for source in benchmarks.get("sources") or []:
            if not isinstance(source, dict):
                continue
            aggregate = source.get("aggregate") or {}
            # Keep only values used for a live operating-envelope comparison.
            keys = (
                "sample_count", "duration_s", "tank_count", "reported_transfer_kg",
                "reported_start_pressure_mpa", "reported_end_pressure_mpa",
                "mass_transfer_kg", "total_fill_time_s", "fueling_time_s",
                "average_mass_flow_g_s", "peak_mass_flow_g_s", "aprr_mpa_min",
                "starting_pressure_mpa", "ending_pressure_mpa",
            )
            rows.append({
                "id": source.get("id"),
                "aggregate": {key: aggregate[key] for key in keys if key in aggregate},
                "raw_rows_public": source.get("raw_rows_public") is True,
            })
        if rows:
            summary["public_experimental_benchmarks"] = {
                "sources": rows,
                "claim_limit": short(benchmarks.get("claim_limit")),
            }
    public_tank_validation = evidence.get("public_tank_validation_boundary")
    if isinstance(public_tank_validation, dict):
        summary["public_tank_validation_boundary"] = {
            key: public_tank_validation.get(key)
            for key in (
                "evidence_role", "source", "frozen_model", "screening_limits",
                "aggregate", "geometry_diagnostic", "claim_supported",
                "claim_limit",
            )
            if public_tank_validation.get(key) is not None
        }
    public_geometry_sensitivity = evidence.get("public_geometry_sensitivity")
    if isinstance(public_geometry_sensitivity, dict):
        summary["public_geometry_sensitivity"] = {
            key: public_geometry_sensitivity.get(key)
            for key in (
                "evidence_role", "source", "runtime_rule", "variants",
                "finding", "required_next_step", "claim_supported",
                "claim_limit",
            )
            if public_geometry_sensitivity.get(key) is not None
        }
    public_tank_trace = evidence.get("public_tank_trace_boundary")
    if isinstance(public_tank_trace, dict):
        summary["public_tank_trace_boundary"] = {
            key: public_tank_trace.get(key)
            for key in (
                "evidence_role", "source", "experiment", "geometry",
                "channel_scope", "observed_ranges",
                "component_tank_screen_eligible",
                "full_loop_external_holdout_eligible", "claim_supported",
                "claim_limit",
            )
            if public_tank_trace.get(key) is not None
        }
    public_measurement = evidence.get("public_measurement_instrumentation")
    if isinstance(public_measurement, dict):
        summary["public_measurement_instrumentation"] = {
            key: public_measurement.get(key)
            for key in (
                "evidence_role", "source_count", "file_count",
                "observed_sampling_intervals_s",
                "station_measurement_auxiliary_eligible",
                "full_loop_holdout_eligible",
                "channel_dictionary_present",
                "vehicle_or_receptacle_channels_identified", "claim_limit",
            )
            if public_measurement.get(key) is not None
        }
    preslhy = evidence.get("preslhy_validation_boundary")
    if isinstance(preslhy, dict):
        summary["preslhy_validation_boundary"] = {
            "evidence_role": preslhy.get("evidence_role"),
            "locked_model_module": preslhy.get("locked_model_module"),
            "locked_discharge_coefficient": preslhy.get(
                "locked_discharge_coefficient"
            ),
            "development": preslhy.get("development") or {},
            "independent_holdout": preslhy.get("independent_holdout") or {},
            "runtime_model_parameter_changed": preslhy.get(
                "runtime_model_parameter_changed"
            ),
            "claim_limit": short(preslhy.get("claim_limit")),
        }
    closed_loop = evidence.get("closed_loop_validation_boundary")
    if isinstance(closed_loop, dict):
        summary["closed_loop_validation_boundary"] = {
            "evidence_role": closed_loop.get("evidence_role"),
            "protocol_frozen_before_data_access": closed_loop.get(
                "protocol_frozen_before_data_access"
            ),
            "post_freeze_parameter_tuning": closed_loop.get(
                "post_freeze_parameter_tuning"
            ),
            "screening_limits": closed_loop.get("screening_limits") or {},
            "aggregate": closed_loop.get("aggregate") or {},
            "post_freeze_diagnostic": closed_loop.get(
                "post_freeze_diagnostic"
            ) or {},
            "runtime_model_parameter_changed": closed_loop.get(
                "runtime_model_parameter_changed"
            ),
            "claim_supported": closed_loop.get("claim_supported"),
            "claim_limit": short(closed_loop.get("claim_limit")),
        }
    envelope_screen = evidence.get("public_operating_envelope_screen")
    if isinstance(envelope_screen, dict):
        summary["public_operating_envelope_screen"] = {
            key: envelope_screen.get(key)
            for key in (
                "status", "source_id", "current_simulated_nozzle_flow_g_s",
                "public_average_flow_g_s", "public_peak_flow_g_s", "flow_context",
                "current_simulated_vehicle_pressure_mpa",
                "public_reported_pressure_context_mpa", "raw_rows_public",
                "validation_claim", "claim_limit",
            )
            if envelope_screen.get(key) is not None
        }
    release_boundary = evidence.get("proust_release_model_validation_boundary")
    if isinstance(release_boundary, dict):
        summary["proust_release_model_validation_boundary"] = {
            key: release_boundary.get(key)
            for key in (
                "evidence_role", "baseline_discharge_coefficient",
                "baseline_joint_primary_pass_count",
                "effective_coefficient_by_diameter", "parameter_fitting",
                "production_model_parameter_changed", "claim_limit",
            )
            if release_boundary.get(key) is not None
        }
    hitrf_reference = evidence.get("public_hitrf_operational_reference")
    if isinstance(hitrf_reference, dict):
        summary["public_hitrf_operational_reference"] = {
            "source": hitrf_reference.get("source") or {},
            "storage": hitrf_reference.get("storage") or {},
            "compression_stages": hitrf_reference.get("compression_stages") or [],
            "dispensing_and_thermal": hitrf_reference.get(
                "dispensing_and_thermal"
            ) or {},
            "eligible_for": hitrf_reference.get("eligible_for") or [],
            "not_eligible_for": hitrf_reference.get("not_eligible_for") or [],
            "claim_limit": short(hitrf_reference.get("claim_limit")),
        }
    real_station_context = evidence.get("public_real_station_context")
    if isinstance(real_station_context, dict):
        summary["public_real_station_context"] = {
            key: real_station_context.get(key)
            for key in (
                "evidence_role", "source", "reported_campaign",
                "reported_scenarios", "reported_channels_or_outputs",
                "full_loop_external_holdout_eligible", "allowed_use",
                "prohibited_use", "claim_limit",
            )
            if real_station_context.get(key) is not None
        }
    detector = evidence.get("public_detector_logic_evidence")
    if isinstance(detector, dict):
        aggregate = detector.get("aggregate") or {}
        summary["public_detector_logic_evidence"] = {
            "doi": detector.get("doi"),
            "rule": detector.get("rule"),
            "aggregate": {
                key: aggregate[key] for key in (
                    "case_count", "cases_with_alarm_detection",
                    "cases_with_trip_detection", "mean_alarm_sensor_coverage_fraction",
                    "mean_trip_sensor_coverage_fraction",
                ) if key in aggregate
            },
            "claim_limit": short(detector.get("claim_limit")),
        }
    dispersion_proxy = evidence.get("public_dispersion_proxy_evidence")
    if isinstance(dispersion_proxy, dict):
        summary["public_dispersion_proxy_evidence"] = {
            key: dispersion_proxy.get(key)
            for key in ("doi", "evidence_role", "method", "runtime_application", "claim_limit")
            if dispersion_proxy.get(key) is not None
        }
    grune_ventilation = evidence.get("public_grune_ventilation_evidence")
    if isinstance(grune_ventilation, dict):
        summary["public_grune_ventilation_evidence"] = {
            key: grune_ventilation.get(key)
            for key in (
                "doi", "evidence_role", "profiles_used", "factor_count",
                "wind_mode_summary", "runtime_parameter_application",
                "definition", "claim_limit",
            )
            if grune_ventilation.get(key) is not None
        }
    local_accident_coverage = evidence.get(
        "confidential_local_accident_response_coverage"
    )
    if isinstance(local_accident_coverage, dict):
        summary["confidential_local_accident_response_coverage"] = {
            key: local_accident_coverage.get(key)
            for key in (
                "evidence_role", "case_count", "mapped_case_count",
                "unmapped_case_count", "case_with_missing_stage_count",
                "required_stage_count", "scenario_family_candidate_counts",
                "multi_family_case_count", "contract_pass", "claim_limit",
            )
            if local_accident_coverage.get(key) is not None
        }
    accidental = evidence.get("public_accidental_release_evidence")
    if isinstance(accidental, dict):
        summary["public_accidental_release_evidence"] = {
            key: accidental.get(key) for key in (
                "article_doi", "zenodo_doi", "license", "evidence_role",
                "consequence_and_ignition_grounding_eligible",
                "full_loop_station_vehicle_holdout_eligible",
            ) if accidental.get(key) is not None
        }
        summary["public_accidental_release_evidence"]["claim_limit"] = short(
            accidental.get("claim_limit")
        )
    confidential = evidence.get("confidential_measured_boundary_replay")
    if isinstance(confidential, dict):
        summary["confidential_measured_boundary_replay"] = {
            key: confidential.get(key) for key in (
                "evidence_role", "trajectory_completed",
                "station_boundary_calibration_supported",
                "independent_full_loop_validation_supported",
            ) if confidential.get(key) is not None
        }
        holdout = confidential.get("temporal_holdout")
        if isinstance(holdout, dict):
            summary["confidential_measured_boundary_replay"]["temporal_holdout"] = {
                key: holdout.get(key) for key in (
                    "trajectory_completed", "fit_used_holdout",
                    "outcome_used_for_fit", "time_ordered_holdout_supported",
                    "independent_full_loop_validation_supported",
                ) if holdout.get(key) is not None
            }
        operational_holdout = confidential.get("operational_envelope_holdout")
        if isinstance(operational_holdout, dict):
            summary["confidential_measured_boundary_replay"][
                "operational_envelope_holdout"
            ] = {
                key: operational_holdout.get(key)
                for key in (
                    "calibration_points", "holdout_points", "fit_used_holdout",
                    "outcome_used_for_fit", "calibration_restart_margin_pa",
                    "trajectory_completed", "esd_triggered",
                    "time_ordered_holdout_supported",
                    "independent_full_loop_validation_supported",
                )
                if operational_holdout.get(key) is not None
            }
        cross_station = confidential.get("cross_station_pressure_envelope")
        if isinstance(cross_station, dict):
            summary["confidential_measured_boundary_replay"][
                "cross_station_pressure_envelope"
            ] = {
                key: cross_station.get(key)
                for key in (
                    "profile_count", "observed_pressure_overlap_mpa",
                    "pressure_semantics_attested_profiles",
                    "temperature_boundary_attested_profiles",
                    "mass_flow_units_attested_profiles",
                    "cross_station_pressure_plausibility_supported",
                    "station_to_vehicle_validation_supported",
                )
                if cross_station.get(key) is not None
            }
    lifecycle = evidence.get("confidential_lifecycle_counter_summary")
    if isinstance(lifecycle, dict):
        summary["confidential_lifecycle_counter_summary"] = {
            "evidence_role": lifecycle.get("evidence_role"),
            "counter_semantics": lifecycle.get("counter_semantics"),
            "sampled_rows": lifecycle.get("sampled_rows"),
            "counters": lifecycle.get("counters"),
            "cycle_aware_degradation_fit": lifecycle.get(
                "cycle_aware_degradation_fit"
            ),
            "claim_limit": short(lifecycle.get("claim_limit")),
        }
    station_calibration = evidence.get("confidential_station_boundary_calibration")
    if isinstance(station_calibration, dict):
        summary["confidential_station_boundary_calibration"] = {
            key: station_calibration.get(key)
            for key in (
                "evidence_role", "profile_id", "source_scope", "files_read",
                "sampled_rows", "duration_s",
                "boundary_pressure_mpa", "positive_pressure_ramp_p95_pa_s",
                "median_sample_period_s", "maximum_gap_s", "pressure_noise_sigma_pa",
                "recommended_recharge_restart_margin_pa",
                "state_transition_count", "channel_roles",
                "channel_attestation",
                "station_boundary_calibration_supported",
                "full_station_vehicle_validation", "claim_limit",
            )
            if station_calibration.get(key) is not None
        }
    channel_envelopes = evidence.get("confidential_pressure_channel_envelopes")
    if isinstance(channel_envelopes, dict):
        summary["confidential_pressure_channel_envelopes"] = {
            key: channel_envelopes.get(key)
            for key in (
                "evidence_role", "artifact", "sampled_rows", "channels",
                "bank_role_mapping_attested", "runtime_parameter_application",
                "claim_limit",
            )
            if channel_envelopes.get(key) is not None
        }
    station_equipment = evidence.get(
        "confidential_station_equipment_operational_envelope"
    )
    if isinstance(station_equipment, dict):
        summary["confidential_station_equipment_operational_envelope"] = {
            key: station_equipment.get(key)
            for key in (
                "evidence_role", "source_scope", "sampled_rows", "duration_s",
                "storage_pressure_mpa", "station_temperature_degC",
                "state_transition_count", "channel_roles", "channel_attestation",
                "station_equipment_envelope_supported",
                "station_boundary_temperature_calibration_supported",
                "vehicle_side_channels_present", "full_station_vehicle_validation",
                "default_model_parameters_changed", "claim_limit",
            )
            if station_equipment.get(key) is not None
        }
    pressure_recheck = evidence.get("confidential_pressure_recheck_decision")
    if isinstance(pressure_recheck, dict):
        summary["confidential_pressure_recheck_decision"] = {
            key: pressure_recheck.get(key)
            for key in (
                "evidence_role", "candidate_applied_to_runtime",
                "production_profile_retained", "retained_restart_margin_mpa",
                "candidate_restart_margin_mpa", "quality_warnings", "claim_limit",
            )
            if pressure_recheck.get(key) is not None
        }
    station_schema = evidence.get("confidential_station_schema_intake")
    if isinstance(station_schema, dict):
        summary["confidential_station_schema_intake"] = {
            key: station_schema.get(key)
            for key in (
                "evidence_role", "source_bundle_count", "file_count",
                "tagged_channel_counts", "unit_attestation",
                "privacy_bounded_channel_families",
                "vehicle_side_channel_family_count",
                "station_side_component_families_present",
                "station_side_schema_intake_supported",
                "full_loop_holdout_eligible", "claim_limit",
            )
            if station_schema.get(key) is not None
        }
    public_source_links = _public_source_links(evidence)
    if public_source_links:
        summary["public_source_links"] = public_source_links
    impact = manifest.get("impact") or {}
    summary["impact_status"] = impact.get("calculation_status")
    summary["impact_result_count"] = impact.get("result_count", 0)
    summary["evidence_digest"] = manifest.get("evidence_digest")
    return summary


def prompt_evidence_header(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a very small provenance header that survives prompt caps."""

    evidence = manifest.get("response_evidence") or {}
    benchmarks = evidence.get("public_experimental_benchmarks") or {}
    hitrf_reference = evidence.get("public_hitrf_operational_reference") or {}
    real_station_context = evidence.get("public_real_station_context") or {}
    benchmark_ids = [
        str(source.get("id"))
        for source in benchmarks.get("sources") or []
        if isinstance(source, dict) and source.get("id")
    ]
    detector = evidence.get("public_detector_logic_evidence") or {}
    detector_aggregate = detector.get("aggregate") or {}
    dispersion_proxy = evidence.get("public_dispersion_proxy_evidence") or {}
    grune_ventilation = evidence.get("public_grune_ventilation_evidence") or {}
    confidential = evidence.get("confidential_measured_boundary_replay") or {}
    holdout = confidential.get("temporal_holdout") or {}
    operational_holdout = confidential.get("operational_envelope_holdout") or {}
    cross_station = confidential.get("cross_station_pressure_envelope") or {}
    lifecycle = evidence.get("confidential_lifecycle_counter_summary") or {}
    station_calibration = evidence.get("confidential_station_boundary_calibration") or {}
    channel_envelopes = evidence.get(
        "confidential_pressure_channel_envelopes"
    ) or {}
    station_equipment = evidence.get(
        "confidential_station_equipment_operational_envelope"
    ) or {}
    pressure_recheck = evidence.get("confidential_pressure_recheck_decision") or {}
    station_schema = evidence.get("confidential_station_schema_intake") or {}
    incident = evidence.get("public_incident_traceability") or {}
    action_taxonomy = incident.get("action_taxonomy") or {}
    accident_inventory = evidence.get("public_accident_report_inventory") or {}
    accidental_release = evidence.get("public_accidental_release_evidence") or {}
    local_accident_coverage = evidence.get(
        "confidential_local_accident_response_coverage"
    ) or {}
    hitrf_storage = hitrf_reference.get("storage") or {}
    hitrf_thermal = hitrf_reference.get("dispensing_and_thermal") or {}
    envelope_screen = evidence.get("public_operating_envelope_screen") or {}
    public_measurement = evidence.get("public_measurement_instrumentation") or {}
    preslhy = evidence.get("preslhy_validation_boundary") or {}
    closed_loop = evidence.get("closed_loop_validation_boundary") or {}
    release_boundary = evidence.get("proust_release_model_validation_boundary") or {}
    return {
        "runtime_calibration": manifest.get("runtime_calibration") or {},
        "runtime_geometry": manifest.get("runtime_geometry") or {},
        "virtual_detector_proxy": manifest.get("virtual_detector_proxy") or {},
        "detector_policy": manifest.get("detector_policy") or {},
        "public_dispersion_proxy_evidence": {
            "doi": dispersion_proxy.get("doi"),
            "method": dispersion_proxy.get("method") or {},
            "runtime_application": dispersion_proxy.get("runtime_application") or {},
            "claim_limit": dispersion_proxy.get("claim_limit"),
        },
        "public_source_links": _public_source_links(evidence),
        "public_experiment_sources": benchmark_ids,
        "public_real_station_context": {
            "doi": (real_station_context.get("source") or {}).get("doi"),
            "reported_scenarios": real_station_context.get(
                "reported_scenarios"
            ) or [],
            "reported_channels_or_outputs": real_station_context.get(
                "reported_channels_or_outputs"
            ) or [],
            "full_loop_external_holdout_eligible": real_station_context.get(
                "full_loop_external_holdout_eligible"
            ) is True,
            "claim_limit": real_station_context.get("claim_limit"),
        },
        "public_measurement_instrumentation": {
            "source_count": public_measurement.get("source_count"),
            "file_count": public_measurement.get("file_count"),
            "observed_sampling_intervals_s": public_measurement.get(
                "observed_sampling_intervals_s"
            ),
            "station_measurement_auxiliary_eligible": public_measurement.get(
                "station_measurement_auxiliary_eligible"
            ) is True,
            "full_loop_holdout_eligible": public_measurement.get(
                "full_loop_holdout_eligible"
            ) is True,
            "channel_dictionary_present": public_measurement.get(
                "channel_dictionary_present"
            ) is True,
            "vehicle_or_receptacle_channels_identified": public_measurement.get(
                "vehicle_or_receptacle_channels_identified"
            ) is True,
            "claim_limit": public_measurement.get("claim_limit"),
        },
        "public_tank_validation_boundary": {
            "evidence_role": (
                evidence.get("public_tank_validation_boundary") or {}
            ).get("evidence_role"),
            "source": (
                evidence.get("public_tank_validation_boundary") or {}
            ).get("source") or {},
            "frozen_model": (
                evidence.get("public_tank_validation_boundary") or {}
            ).get("frozen_model") or {},
            "screening_limits": (
                evidence.get("public_tank_validation_boundary") or {}
            ).get("screening_limits") or {},
            "aggregate": (
                evidence.get("public_tank_validation_boundary") or {}
            ).get("aggregate") or {},
            "geometry_diagnostic": (
                evidence.get("public_tank_validation_boundary") or {}
            ).get("geometry_diagnostic") or {},
            "claim_supported": (
                evidence.get("public_tank_validation_boundary") or {}
            ).get("claim_supported"),
            "claim_limit": (
                evidence.get("public_tank_validation_boundary") or {}
            ).get("claim_limit"),
        },
        "public_geometry_sensitivity": {
            "evidence_role": (
                evidence.get("public_geometry_sensitivity") or {}
            ).get("evidence_role"),
            "source": (
                evidence.get("public_geometry_sensitivity") or {}
            ).get("source") or {},
            "runtime_rule": (
                evidence.get("public_geometry_sensitivity") or {}
            ).get("runtime_rule") or {},
            "variants": (
                evidence.get("public_geometry_sensitivity") or {}
            ).get("variants") or {},
            "finding": (
                evidence.get("public_geometry_sensitivity") or {}
            ).get("finding"),
            "required_next_step": (
                evidence.get("public_geometry_sensitivity") or {}
            ).get("required_next_step"),
            "claim_supported": (
                evidence.get("public_geometry_sensitivity") or {}
            ).get("claim_supported"),
            "claim_limit": (
                evidence.get("public_geometry_sensitivity") or {}
            ).get("claim_limit"),
        },
        "public_tank_trace_boundary": {
            "evidence_role": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("evidence_role"),
            "source": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("source") or {},
            "experiment": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("experiment") or {},
            "geometry": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("geometry") or {},
            "channel_scope": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("channel_scope") or {},
            "observed_ranges": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("observed_ranges") or {},
            "component_tank_screen_eligible": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("component_tank_screen_eligible"),
            "full_loop_external_holdout_eligible": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("full_loop_external_holdout_eligible"),
            "claim_supported": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("claim_supported"),
            "claim_limit": (
                evidence.get("public_tank_trace_boundary") or {}
            ).get("claim_limit"),
        },
        "preslhy_validation_boundary": {
            "locked_model_module": preslhy.get("locked_model_module"),
            "locked_discharge_coefficient": preslhy.get(
                "locked_discharge_coefficient"
            ),
            "development_joint_primary_pass_fraction": (
                preslhy.get("development") or {}
            ).get("joint_primary_pass_fraction"),
            "independent_holdout_joint_primary_pass_fraction": (
                preslhy.get("independent_holdout") or {}
            ).get("joint_primary_pass_fraction"),
            "independent_holdout_claim_supported": (
                preslhy.get("independent_holdout") or {}
            ).get("claim_supported") is True,
            "runtime_model_parameter_changed": preslhy.get(
                "runtime_model_parameter_changed"
            ) is True,
            "claim_limit": preslhy.get("claim_limit"),
        },
        "closed_loop_validation_boundary": {
            "evidence_role": closed_loop.get("evidence_role"),
            "protocol_frozen_before_data_access": closed_loop.get(
                "protocol_frozen_before_data_access"
            ) is True,
            "post_freeze_parameter_tuning": closed_loop.get(
                "post_freeze_parameter_tuning"
            ) is True,
            "screening_limits": closed_loop.get("screening_limits") or {},
            "aggregate": closed_loop.get("aggregate") or {},
            "post_freeze_diagnostic": closed_loop.get(
                "post_freeze_diagnostic"
            ) or {},
            "runtime_model_parameter_changed": closed_loop.get(
                "runtime_model_parameter_changed"
            ) is True,
            "claim_supported": closed_loop.get("claim_supported") is True,
            "claim_limit": closed_loop.get("claim_limit"),
        },
        "public_operating_envelope_screen": {
            "status": envelope_screen.get("status"),
            "source_id": envelope_screen.get("source_id"),
            "source_url": envelope_screen.get("source_url"),
            "current_simulated_nozzle_flow_g_s": envelope_screen.get(
                "current_simulated_nozzle_flow_g_s"
            ),
            "public_average_flow_g_s": envelope_screen.get("public_average_flow_g_s"),
            "public_peak_flow_g_s": envelope_screen.get("public_peak_flow_g_s"),
            "flow_context": envelope_screen.get("flow_context"),
            "raw_rows_public": envelope_screen.get("raw_rows_public"),
            "validation_claim": envelope_screen.get("validation_claim"),
            "claim_limit": envelope_screen.get("claim_limit"),
        },
        "proust_release_model_validation_boundary": {
            "evidence_role": release_boundary.get("evidence_role"),
            "baseline_discharge_coefficient": release_boundary.get(
                "baseline_discharge_coefficient"
            ),
            "baseline_joint_primary_pass_count": release_boundary.get(
                "baseline_joint_primary_pass_count"
            ),
            "parameter_fitting": release_boundary.get("parameter_fitting") is True,
            "production_model_parameter_changed": release_boundary.get(
                "production_model_parameter_changed"
            ) is True,
            "claim_limit": release_boundary.get("claim_limit"),
        },
        "public_hitrf_operational_reference": {
            "source_url": (hitrf_reference.get("source") or {}).get("url"),
            "available": bool(hitrf_reference),
            "raw_synchronized_logger_public": (
                (hitrf_reference.get("source") or {}).get(
                    "raw_synchronized_logger_public"
                ) is True
            ),
            "storage_tiers": sorted((hitrf_reference.get("storage") or {}).keys()),
            "storage_pressure_mpa": {
                str(tier): values.get("maximum_pressure_mpa")
                for tier, values in hitrf_storage.items()
                if isinstance(values, dict)
                and values.get("maximum_pressure_mpa") is not None
            },
            "storage_capacity_kg": {
                str(tier): values.get("reported_capacity_kg")
                for tier, values in hitrf_storage.items()
                if isinstance(values, dict)
                and values.get("reported_capacity_kg") is not None
            },
            "compression_stage_count": len(
                hitrf_reference.get("compression_stages") or []
            ),
            "compression_stages": [
                {
                    "inlet_pressure_bar": stage.get("inlet_pressure_bar"),
                    "outlet_pressure_bar": stage.get("outlet_pressure_bar"),
                    "capacity_kg_per_day": stage.get("capacity_kg_per_day"),
                    "capacity_kg_per_hour": stage.get("capacity_kg_per_hour"),
                }
                for stage in hitrf_reference.get("compression_stages") or []
                if isinstance(stage, dict)
            ],
            "chiller_target_temperature_c": hitrf_thermal.get(
                "chiller_target_temperature_c"
            ),
            "claim_limit": hitrf_reference.get("claim_limit"),
        },
        "public_detector_replay_cases": detector_aggregate.get("case_count"),
        "public_detector_trip_coverage": detector_aggregate.get(
            "mean_trip_sensor_coverage_fraction"
        ),
        "public_grune_ventilation_envelope": {
            "doi": grune_ventilation.get("doi"),
            "profiles_used": grune_ventilation.get("profiles_used"),
            "factor_count": grune_ventilation.get("factor_count"),
            "wind_mode_summary": grune_ventilation.get("wind_mode_summary") or {},
            "runtime_parameter_application": grune_ventilation.get(
                "runtime_parameter_application"
            ),
            "claim_limit": grune_ventilation.get("claim_limit"),
        },
        "public_accident_evidence": {
            "hiad_case_count": incident.get("case_count"),
            "hiad_action_taxonomy": incident.get("action_taxonomy", {}).get(
                "category_patterns_version"
            ) if isinstance(incident.get("action_taxonomy"), dict) else None,
            "public_report_count": accident_inventory.get("public_report_count"),
            "incident_code_count": accident_inventory.get("incident_code_count"),
            "accidental_release_zenodo_doi": accidental_release.get("zenodo_doi"),
            "accidental_release_full_loop": accidental_release.get(
                "full_loop_station_vehicle_holdout_eligible"
            ),
            "action_category_counts": {
                str(key): value
                for key, value in (action_taxonomy.get("category_counts") or {}).items()
                if isinstance(value, int)
            },
        },
        "confidential_local_accident_response_coverage": {
            "case_count": local_accident_coverage.get("case_count"),
            "mapped_case_count": local_accident_coverage.get("mapped_case_count"),
            "required_stage_count": local_accident_coverage.get(
                "required_stage_count"
            ),
            "scenario_family_candidate_counts": local_accident_coverage.get(
                "scenario_family_candidate_counts"
            ) or {},
            "multi_family_case_count": local_accident_coverage.get(
                "multi_family_case_count"
            ),
            "contract_pass": local_accident_coverage.get("contract_pass") is True,
        },
        "confidential_boundary_holdout": holdout.get(
            "time_ordered_holdout_supported"
        ) is True,
        "confidential_operational_envelope_holdout": {
            "calibration_points": operational_holdout.get("calibration_points"),
            "holdout_points": operational_holdout.get("holdout_points"),
            "trajectory_completed": operational_holdout.get(
                "trajectory_completed"
            ) is True,
            "fit_used_holdout": operational_holdout.get("fit_used_holdout") is True,
            "outcome_used_for_fit": operational_holdout.get(
                "outcome_used_for_fit"
            ) is True,
            "independent_full_loop_validation_supported": operational_holdout.get(
                "independent_full_loop_validation_supported"
            ) is True,
        },
        "confidential_cross_station_pressure_envelope": {
            "profile_count": cross_station.get("profile_count"),
            "observed_pressure_overlap_mpa": cross_station.get(
                "observed_pressure_overlap_mpa"
            ),
            "pressure_semantics_attested_profiles": cross_station.get(
                "pressure_semantics_attested_profiles"
            ),
            "cross_station_pressure_plausibility_supported": cross_station.get(
                "cross_station_pressure_plausibility_supported"
            ) is True,
            "station_to_vehicle_validation_supported": cross_station.get(
                "station_to_vehicle_validation_supported"
            ) is True,
        },
        "full_loop_validation_supported": confidential.get(
            "independent_full_loop_validation_supported"
        ) is True,
        "confidential_lifecycle_evidence": {
            "sampled_rows": lifecycle.get("sampled_rows"),
            "counter_roles": sorted((lifecycle.get("counters") or {}).keys()),
            "cycle_aware_degradation_fit": lifecycle.get(
                "cycle_aware_degradation_fit"
            ) is True,
        },
        "confidential_station_boundary_calibration": {
            "profile_id": station_calibration.get("profile_id"),
            "evidence_artifact": station_calibration.get("artifact"),
            "files_read": station_calibration.get("files_read"),
            "sampled_rows": station_calibration.get("sampled_rows"),
            "pressure_range_mpa": station_calibration.get("boundary_pressure_mpa"),
            "channel_attestation": station_calibration.get("channel_attestation") or {},
            "recharge_restart_margin_pa": station_calibration.get(
                "recommended_recharge_restart_margin_pa"
            ),
            "state_transition_count": station_calibration.get("state_transition_count"),
            "full_station_vehicle_validation": station_calibration.get(
                "full_station_vehicle_validation"
            ) is True,
        },
        "confidential_pressure_channel_envelopes": {
            "artifact": channel_envelopes.get("artifact"),
            "sampled_rows": channel_envelopes.get("sampled_rows"),
            "channels": channel_envelopes.get("channels") or {},
            "bank_role_mapping_attested": channel_envelopes.get(
                "bank_role_mapping_attested"
            ) is True,
            "runtime_parameter_application": channel_envelopes.get(
                "runtime_parameter_application"
            ) is True,
            "claim_limit": channel_envelopes.get("claim_limit"),
        },
        "confidential_station_equipment_operational_envelope": {
            "sampled_rows": station_equipment.get("sampled_rows"),
            "storage_pressure_mpa": station_equipment.get("storage_pressure_mpa"),
            "station_temperature_degC": station_equipment.get(
                "station_temperature_degC"
            ),
            "state_transition_count": station_equipment.get("state_transition_count"),
            "channel_attestation": station_equipment.get("channel_attestation") or {},
            "station_equipment_envelope_supported": station_equipment.get(
                "station_equipment_envelope_supported"
            ) is True,
            "station_boundary_temperature_calibration_supported": station_equipment.get(
                "station_boundary_temperature_calibration_supported"
            ) is True,
            "vehicle_side_channels_present": station_equipment.get(
                "vehicle_side_channels_present"
            ) is True,
            "full_station_vehicle_validation": station_equipment.get(
                "full_station_vehicle_validation"
            ) is True,
            "default_model_parameters_changed": station_equipment.get(
                "default_model_parameters_changed"
            ) is True,
        },
        "confidential_pressure_recheck_decision": {
            "candidate_applied_to_runtime": pressure_recheck.get(
                "candidate_applied_to_runtime"
            ) is True,
            "production_profile_retained": pressure_recheck.get(
                "production_profile_retained"
            ),
            "retained_restart_margin_mpa": pressure_recheck.get(
                "retained_restart_margin_mpa"
            ),
            "candidate_restart_margin_mpa": pressure_recheck.get(
                "candidate_restart_margin_mpa"
            ),
            "quality_warnings": pressure_recheck.get("quality_warnings") or [],
        },
        "confidential_station_schema_intake": {
            "source_bundle_count": station_schema.get("source_bundle_count"),
            "file_count": station_schema.get("file_count"),
            "tagged_channel_counts": station_schema.get("tagged_channel_counts"),
            "privacy_bounded_channel_families": station_schema.get(
                "privacy_bounded_channel_families"
            ),
            "vehicle_side_channel_family_count": station_schema.get(
                "vehicle_side_channel_family_count"
            ),
            "station_side_component_families_present": station_schema.get(
                "station_side_component_families_present"
            ),
            "pressure_units_attested": (
                station_schema.get("unit_attestation", {}).get("pressure_units_attested")
                is True
            ),
            "station_side_schema_intake_supported": (
                station_schema.get("station_side_schema_intake_supported") is True
            ),
            "full_loop_holdout_eligible": (
                station_schema.get("full_loop_holdout_eligible") is True
            ),
        },
        "impact_status": (manifest.get("impact") or {}).get("calculation_status"),
        "evidence_digest": manifest.get("evidence_digest"),
    }
