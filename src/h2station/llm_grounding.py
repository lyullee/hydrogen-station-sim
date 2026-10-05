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
from typing import Any, Iterable

from .calibration_profiles import load_measured_boundary_calibration


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
    if profile is not None:
        return {
            "status": "active",
            "requested": True,
            **profile.runtime_metadata(),
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
        "contract_pass": True,
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


def _confidential_lifecycle_evidence() -> dict[str, Any] | None:
    """Expose only de-identified lifecycle-counter calibration context."""

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_lifecycle_counter_summary_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (
        record.get("artifact_type") != "confidential_lifecycle_counter_summary"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
    ):
        return None
    counters: dict[str, dict[str, Any]] = {}
    for role, values in (record.get("counters") or {}).items():
        if not isinstance(values, dict):
            continue
        counters[str(role)] = {
            key: values.get(key)
            for key in (
                "sample_count", "observed_min", "observed_max",
                "positive_increment_count", "total_positive_increment",
                "maximum_single_increment",
            )
            if values.get(key) is not None
        }
    return {
        "artifact": "research/confidential_lifecycle_counter_summary_2026_10_06.json",
        "evidence_role": "confidential de-identified lifecycle history",
        "counter_semantics": str(record.get("counter_semantics") or ""),
        "files_read": record.get("files_read"),
        "sampled_rows": record.get("sampled_rows"),
        "counters": counters,
        "cycle_aware_degradation_fit": (
            record.get("eligibility", {}).get("cycle_aware_degradation_fit") is True
        ),
        "claim_limit": str(record.get("claim_boundary") or ""),
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
    confidential_boundary = _confidential_measured_boundary_evidence()
    if confidential_boundary is not None:
        envelope["response_evidence"]["confidential_measured_boundary_replay"] = confidential_boundary
    public_benchmarks = _public_experimental_benchmarks()
    if public_benchmarks is not None:
        envelope["response_evidence"]["public_experimental_benchmarks"] = public_benchmarks
    hitrf_reference = _public_hitrf_operational_reference()
    if hitrf_reference is not None:
        envelope["response_evidence"][
            "public_hitrf_operational_reference"
        ] = hitrf_reference
    lifecycle = _confidential_lifecycle_evidence()
    if lifecycle is not None:
        envelope["response_evidence"]["confidential_lifecycle_counter_summary"] = lifecycle
    station_calibration = _confidential_station_calibration_evidence()
    if station_calibration is not None:
        envelope["response_evidence"][
            "confidential_station_boundary_calibration"
        ] = station_calibration
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
    local_accident_coverage = evidence.get(
        "confidential_local_accident_response_coverage"
    )
    if isinstance(local_accident_coverage, dict):
        summary["confidential_local_accident_response_coverage"] = {
            key: local_accident_coverage.get(key)
            for key in (
                "evidence_role", "case_count", "mapped_case_count",
                "unmapped_case_count", "case_with_missing_stage_count",
                "required_stage_count", "contract_pass", "claim_limit",
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
    benchmark_ids = [
        str(source.get("id"))
        for source in benchmarks.get("sources") or []
        if isinstance(source, dict) and source.get("id")
    ]
    detector = evidence.get("public_detector_logic_evidence") or {}
    detector_aggregate = detector.get("aggregate") or {}
    confidential = evidence.get("confidential_measured_boundary_replay") or {}
    holdout = confidential.get("temporal_holdout") or {}
    operational_holdout = confidential.get("operational_envelope_holdout") or {}
    cross_station = confidential.get("cross_station_pressure_envelope") or {}
    lifecycle = evidence.get("confidential_lifecycle_counter_summary") or {}
    station_calibration = evidence.get("confidential_station_boundary_calibration") or {}
    incident = evidence.get("public_incident_traceability") or {}
    action_taxonomy = incident.get("action_taxonomy") or {}
    accident_inventory = evidence.get("public_accident_report_inventory") or {}
    accidental_release = evidence.get("public_accidental_release_evidence") or {}
    local_accident_coverage = evidence.get(
        "confidential_local_accident_response_coverage"
    ) or {}
    hitrf_storage = hitrf_reference.get("storage") or {}
    hitrf_thermal = hitrf_reference.get("dispensing_and_thermal") or {}
    return {
        "runtime_calibration": manifest.get("runtime_calibration") or {},
        "public_experiment_sources": benchmark_ids,
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
        "impact_status": (manifest.get("impact") or {}).get("calculation_status"),
        "evidence_digest": manifest.get("evidence_digest"),
    }
