"""Machine-readable evidence envelopes for LLM decision support.

The envelope is deliberately small and deterministic.  It records what the
assistant was allowed to see; it does not turn a simulation into a field
measurement or make a consequence result more authoritative than its source.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
import re
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from .calibration_profiles import (
    load_measured_boundary_calibration,
    load_station_recharge_dynamics_calibration,
)
from .public_tank_calibration import load_public_type_iv_tank_calibration
from .lifecycle_evidence import load_lifecycle_evidence
from .hazop.response import public_accident_precedents
from .local_evidence import local_station_evidence_summary


def _ijhe_readiness_ledger() -> dict[str, Any]:
    """Return a privacy-bounded view of the submission-readiness ledger.

    The ledger is a repository-level audit of validation gates.  It is useful
    context for an LLM because it prevents a response from turning a passing
    component test into a claim of full-loop or journal-ready validation.  The
    prompt receives only aggregate counts and a few claim-boundary booleans;
    paths, gate evidence payloads, raw rows and private identifiers are never
    included.  Missing or malformed ledgers fail closed.
    """

    unavailable: dict[str, Any] = {
        "evidence_role": "aggregate validation-readiness ledger",
        "status": "unavailable",
        "ledger_integrity": False,
        "gate_counts": {},
        "bounded_ijhe_submission_ready": False,
        "full_user_objective_ready": False,
        "goal_completion_permitted": False,
        "full_loop_external_validation_supported": False,
        "expert_effectiveness_evaluation_supported": False,
        "independent_expert_review_complete": False,
        "claim_boundary": (
            "Validation-readiness metadata is unavailable; do not claim full-loop "
            "external validation, journal readiness, or objective completion."
        ),
    }
    ledger_path = Path(__file__).resolve().parents[2] / "manuscript" / (
        "ijhe_readiness_audit.json"
    )
    try:
        payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return unavailable
    if not isinstance(payload, dict):
        return unavailable

    raw_counts = payload.get("gate_counts")
    if not isinstance(raw_counts, dict):
        return unavailable
    counts: dict[str, int] = {}
    for key in ("PASS", "FAIL", "PENDING"):
        value = raw_counts.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return unavailable
        counts[key] = value

    statuses: dict[str, str] = {}
    gates = payload.get("gates")
    if not isinstance(gates, list):
        return unavailable
    for gate in gates:
        if not isinstance(gate, dict):
            continue
        gate_id = gate.get("id")
        status = gate.get("status")
        if gate_id and isinstance(status, str):
            statuses[str(gate_id)] = status.upper()
    computed_counts = {
        key: sum(1 for status in statuses.values() if status == key)
        for key in ("PASS", "FAIL", "PENDING")
    }
    # A stale or partially written audit must not be used to relax claim
    # boundaries.  The count check is deliberately strict and deterministic.
    if computed_counts != counts:
        return unavailable

    return {
        "evidence_role": "aggregate validation-readiness ledger",
        "status": "available",
        "ledger_integrity": True,
        "generated_at": payload.get("generated_at"),
        "gate_counts": counts,
        "bounded_ijhe_submission_ready": (
            payload.get("bounded_ijhe_submission_ready") is True
        ),
        "full_user_objective_ready": (
            payload.get("full_user_objective_ready") is True
        ),
        "goal_completion_permitted": (
            payload.get("goal_completion_permitted") is True
        ),
        "full_loop_external_validation_supported": (
            statuses.get("full_loop_external_validation") == "PASS"
        ),
        "expert_effectiveness_evaluation_supported": (
            statuses.get("saga_effectiveness_and_safety_supported") == "PASS"
        ),
        "independent_expert_review_complete": (
            statuses.get("independent_expert_review_complete") == "PASS"
        ),
        "claim_boundary": (
            "Aggregate audit status only; this does not predict peer review or "
            "journal acceptance. Full-loop and objective-completion claims remain "
            "disabled unless their gates are PASS."
        ),
    }


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
    dynamics_requested = (
        settings.get("measured_station_dynamics_calibration") is True
    )
    profile = load_measured_boundary_calibration() if requested else None
    dynamics_profile = (
        load_station_recharge_dynamics_calibration()
        if dynamics_requested else None
    )

    def dynamics_metadata() -> dict[str, Any]:
        """Describe the independent opt-in restart-dwell setting.

        This is intentionally a nested field: a station-boundary pressure
        envelope and a compressor restart dwell come from different restricted
        evidence artifacts and affect different simulator controls.
        """

        if dynamics_profile is not None:
            return {
                "status": "active",
                "requested": True,
                **dynamics_profile.runtime_metadata(),
            }
        if dynamics_requested:
            return {
                "status": "requested_unavailable",
                "requested": True,
                "id": "reference_defaults",
                "evidence_artifact": None,
                "claim_boundary": (
                    "실측 재충전 동특성 artifact를 읽지 못해 기준 재시작 대기시간으로 실행됨"
                ),
            }
        return {
            "status": "disabled",
            "requested": False,
            "id": "reference_defaults",
            "evidence_artifact": None,
            "claim_boundary": "실측 재충전 동특성 보정은 선택 적용되지 않음",
        }
    current_boundary_pressure = operations.get("trailer_pressure_mpa")
    if profile is not None:
        result = {
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
        result["station_recharge_dynamics"] = dynamics_metadata()
        return result
    if requested:
        result = {
            "status": "requested_unavailable",
            "requested": True,
            "profile_id": "reference_defaults",
            "evidence_artifact": None,
            "claim_limit": "실측 경계 보정 artifact를 읽지 못해 기준값으로 실행됨",
        }
        result["station_recharge_dynamics"] = dynamics_metadata()
        return result
    result = {
        "status": "reference_defaults",
        "requested": False,
        "profile_id": "reference_defaults",
        "evidence_artifact": None,
        "claim_limit": "실측 경계 보정은 선택 적용되지 않음",
    }
    result["station_recharge_dynamics"] = dynamics_metadata()
    return result


def _runtime_geometry_profile(frame: dict[str, Any]) -> dict[str, Any]:
    """Identify the vehicle geometry basis used by the current snapshot."""

    basis = str(frame.get("vehicle_geometry_basis") or "reference")
    if basis not in {"reference", "capacity_eos"}:
        basis = "reference"
    thermal_model = str(
        frame.get("vehicle_tank_thermal_model") or "constant_ua"
    )
    if thermal_model not in {"constant_ua", "mixed_convection"}:
        thermal_model = "constant_ua"
    thermal_geometry = {
        key: frame.get(key)
        for key in (
            "vehicle_internal_diameter_m",
            "vehicle_internal_length_m",
            "vehicle_inlet_nozzle_diameter_m",
            "vehicle_2_internal_diameter_m",
            "vehicle_2_internal_length_m",
            "vehicle_2_inlet_nozzle_diameter_m",
        )
    }
    return {
        "basis": basis,
        "vehicle_capacity_kg": frame.get("vehicle_capacity_kg"),
        "vehicle_2_capacity_kg": frame.get("vehicle_2_capacity_kg"),
        "effective_volume_multiplier": frame.get(
            "vehicle_effective_volume_multiplier"
        ),
        "effective_volume_policy": (
            "single_pass_capacity_eos"
            if basis == "capacity_eos" else "public_fit_or_explicit_override"
        ),
        "public_sensitivity_available": True,
        "default_basis": "reference",
        "capacity_eos_opt_in": basis == "capacity_eos",
        "tank_thermal_model": thermal_model,
        "mixed_convection_opt_in": thermal_model == "mixed_convection",
        "thermal_geometry": thermal_geometry,
        "thermal_geometry_complete": all(
            value is not None for value in thermal_geometry.values()
        ),
        "claim_limit": (
            "capacity/EOS 형상은 선언 용량으로 기체 체적을 한 번만 산정하는 "
            "공개 탱크 민감도 진단 기반 선택 옵션이며 "
            "독립적인 station-to-vehicle 검증이나 기본값 변경을 의미하지 않음. "
            "mixed_convection은 명시 치수를 사용하는 연구 경로이며 미검증 기본값이 아님"
        ),
    }


def _runtime_vehicle_tank_calibration_profile(frame: dict[str, Any]) -> dict[str, Any]:
    """Expose the bounded public tank fit used by the simulated vehicle."""

    mode = str(frame.get("vehicle_tank_calibration") or "public_type_iv")
    if mode == "reference":
        return {
            "status": "reference",
            "mode": mode,
            "claim_limit": (
                "기준 Type-IV 탱크 물성값으로 실행됨. 공개 실험 기반 탱크 보정은 "
                "이번 실행에 적용되지 않음"
            ),
        }
    profile = load_public_type_iv_tank_calibration()
    if profile is None:
        return {
            "status": "unavailable",
            "mode": mode,
            "claim_limit": (
                "공개 Type-IV 탱크 보정 artifact를 읽지 못해 탱크 보정 적용 여부를 "
                "확인할 수 없음"
            ),
        }
    return {"mode": mode, **profile.runtime_metadata()}


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
    # Keep the current public HIAD 2.2 provenance next to the derived
    # traceability counts.  The workbook is never copied into the prompt;
    # this only tells the assistant which public release and coverage window
    # the scenario inventory came from.
    provenance_path = path.parent / "hiad_2_2_access_recheck_2026_10_05.json"
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        provenance = None
    provenance_source = (provenance or {}).get("source") or {}
    provenance_observation = (provenance or {}).get("workbook_observation") or {}
    if (
        isinstance(provenance, dict)
        and provenance.get("status") == "completed_public_accident_dataset_provenance_recheck"
        and provenance_source.get("version") == "HIAD 2.2"
        and str(provenance_source.get("official_page") or "").startswith("https://")
        and str(provenance_source.get("download_url") or "").startswith("https://")
        and provenance_observation.get("hydrogen_refuelling_station_records") == aggregate.get("case_count")
    ):
        result["public_source"] = {
            "title": str(provenance_source.get("title") or ""),
            "publisher": str(provenance_source.get("publisher") or ""),
            "version": str(provenance_source.get("version") or ""),
            "coverage_end": str(provenance_source.get("coverage_end") or ""),
            "official_page": str(provenance_source.get("official_page") or ""),
            "download_url": str(provenance_source.get("download_url") or ""),
            "station_record_count": provenance_observation.get(
                "hydrogen_refuelling_station_records"
            ),
            "raw_rows_in_prompt": False,
            "claim_limit": (
                "HIAD 2.2 public incident metadata provide qualitative scenario and "
                "response grounding only; they do not provide synchronized process traces "
                "or numerical station-to-vehicle validation."
            ),
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
    replay_path = path.parent / "hiad_digital_twin_replay_coverage_2026_10_08.json"
    try:
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        replay = None
    replay_source = (replay or {}).get("source") or {}
    replay_runtime = (replay or {}).get("runtime") or {}
    replay_aggregate = (replay or {}).get("aggregate") or {}
    replay_counts = replay_aggregate.get("representation_case_counts") or {}
    replay_cases = (replay or {}).get("cases") or []
    replay_model_hashes = replay_source.get("model_input_sha256") or {}
    root = path.parents[1]
    if (
        isinstance(replay, dict)
        and replay.get("status") == "completed_family_level_integration_audit"
        and replay_source.get("hiad_inventory_sha256")
        == sha256((path.parent / "hiad_hrs_public_evidence.json").read_bytes()).hexdigest()
        and replay_source.get("playbook_catalog_sha256")
        == sha256((root / "src/h2station/data/emergency_playbooks.json").read_bytes()).hexdigest()
        and replay_source.get("public_response_text_used") is False
        and replay_source.get("case_narrative_used_for_physical_parameters") is False
        and bool(replay_model_hashes)
        and all(
            (root / relative).is_file()
            and sha256((root / relative).read_bytes()).hexdigest() == digest
            for relative, digest in replay_model_hashes.items()
        )
        and replay_runtime.get("family_recipe_pass_count") == 9
        and replay_runtime.get("unique_family_recipes_run") == 9
        and replay_runtime.get("all_executable_recipes_passed") is True
        and replay_aggregate.get("case_count") == 34
        and replay_aggregate.get("integration_trace_pass_count") == 34
        and len(replay_cases) == 34
        and all(case.get("integration_trace_pass") is True for case in replay_cases)
    ):
        result["digital_twin_replay"] = {
            "artifact": "research/hiad_digital_twin_replay_coverage_2026_10_08.json",
            "artifact_sha256": sha256(replay_path.read_bytes()).hexdigest(),
            "backend": replay_runtime.get("backend"),
            "case_count": replay_aggregate.get("case_count"),
            "integration_trace_pass_count": replay_aggregate.get(
                "integration_trace_pass_count"
            ),
            "direct_physical_case_count": replay_counts.get(
                "direct_physical_replay"
            ),
            "partial_proxy_case_count": replay_counts.get(
                "proxy_partial_replay"
            ),
            "response_only_case_count": replay_counts.get(
                "response_only_no_physical_model"
            ),
            "canonical_recipe_pass_count": replay_runtime.get(
                "family_recipe_pass_count"
            ),
            "canonical_recipe_count": replay_runtime.get(
                "unique_family_recipes_run"
            ),
            "case_narrative_used_for_physical_parameters": False,
            "claim_limit": " ".join(str(item) for item in replay.get("claim_boundary") or []),
        }
    return result


def _khk_public_accident_inventory() -> dict[str, Any] | None:
    """Expose KHK's public accident-report inventory as response provenance.

    The inventory contains citation links and scenario classifications, not
    copied report text or process traces.  Keeping it in the evidence envelope
    lets a response show which public accident source family grounds the
    playbook while preserving the separate numerical-validation boundary.
    """
    root = Path(__file__).resolve().parents[2]
    path = root / (
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
    map_path = root / (
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
    replay_path = root / "research/khk_digital_twin_replay_coverage_2026_10_08.json"
    try:
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        replay = None
    replay_source = (replay or {}).get("source") or {}
    replay_runtime = (replay or {}).get("runtime") or {}
    replay_aggregate = (replay or {}).get("aggregate") or {}
    replay_claims = (replay or {}).get("claims") or {}
    source_records = [
        replay_source.get(key) or {}
        for key in ("inventory", "access_verification", "precedent_map", "playbook_catalog")
    ]
    model_hashes = replay_source.get("model_input_sha256") or {}
    if (
        isinstance(replay, dict)
        and replay.get("status") == "completed_independent_public_accident_integration_audit"
        and len(source_records) == 4
        and all(
            isinstance(item.get("path"), str)
            and (root / item["path"]).is_file()
            and sha256((root / item["path"]).read_bytes()).hexdigest() == item.get("sha256")
            for item in source_records
        )
        and bool(model_hashes)
        and all(
            (root / relative).is_file()
            and sha256((root / relative).read_bytes()).hexdigest() == digest
            for relative, digest in model_hashes.items()
        )
        and replay_source.get("public_report_text_used") is False
        and replay_source.get("report_narrative_used_for_physical_parameters") is False
        and replay_runtime.get("family_recipe_count") == 8
        and replay_runtime.get("family_recipe_pass_count") == 8
        and replay_runtime.get("all_family_recipes_passed") is True
        and replay_aggregate.get("public_report_count") == result["public_report_count"]
        and replay_aggregate.get("incident_code_count") == result["incident_code_count"]
        and replay_aggregate.get("integration_trace_pass_report_count") == 22
        and replay_aggregate.get("integration_trace_pass_incident_code_count") == 25
        and replay_aggregate.get("out_of_scope_report_count") == 1
        and replay_claims
        and all(value is False for value in replay_claims.values())
    ):
        result["digital_twin_replay"] = {
            "artifact": "research/khk_digital_twin_replay_coverage_2026_10_08.json",
            "backend": replay_runtime.get("backend"),
            "public_report_count": replay_aggregate.get("public_report_count"),
            "incident_code_count": replay_aggregate.get("incident_code_count"),
            "integration_trace_pass_report_count": replay_aggregate.get(
                "integration_trace_pass_report_count"
            ),
            "integration_trace_pass_incident_code_count": replay_aggregate.get(
                "integration_trace_pass_incident_code_count"
            ),
            "out_of_scope_report_count": replay_aggregate.get(
                "out_of_scope_report_count"
            ),
            "canonical_recipe_pass_count": replay_runtime.get(
                "family_recipe_pass_count"
            ),
            "canonical_recipe_count": replay_runtime.get("family_recipe_count"),
            "report_narrative_used_for_physical_parameters": False,
            "claim_limit": " ".join(
                str(item) for item in replay.get("claim_boundary") or []
            ),
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

    reported_findings = record.get("reported_findings") or {}
    # Keep the article-reported observations separate from model-derived
    # quantities.  These values are useful for response wording (for example,
    # checking remote/delayed ignition), but they must never become an
    # ignition-probability prior or an automatic release-model calibration.
    reported_findings_payload = {
        key: reported_findings.get(key)
        for key in (
            "experiment_count",
            "ignition_observed_case_count",
            "no_ignition_case_count",
            "remote_or_obstructed_ignition_reported",
            "delayed_ignition_delay_s_reported",
            "fire_jet_length_m_greater_than_reported",
            "pressure_sampling_period_s",
            "thermocouple_sampling_period_s",
            "thermocouple_vertical_heights_m",
            "thermocouple_horizontal_distances_m",
            "ignition_probability_estimated",
            "ignition_mechanism_confirmed",
            "qualifier",
        )
        if reported_findings.get(key) is not None
    }

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
        "reported_findings": reported_findings_payload,
        "full_loop_station_vehicle_holdout_eligible": eligibility.get(
            "full_loop_station_vehicle_holdout_eligible"
        ) is True,
        "numerical_release_model_validation_claimed": eligibility.get(
            "numerical_release_model_validation_claimed"
        ) is True,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_controlled_flare_evidence() -> dict[str, Any] | None:
    """Expose HyDelta's report-level flare safeguards with strict boundaries."""

    artifact = "research/hydelta_controlled_flare_evidence_2026_10_08.json"
    path = Path(__file__).resolve().parents[2] / artifact
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    findings = record.get("reported_findings") or {}
    runtime = record.get("runtime_use") or {}
    checks = record.get("claim_checks") or {}
    identity = source.get("publisher_file_identity") or {}
    if (
        record.get("status") != "verified_report_level_controlled_flare_evidence"
        or source.get("doi") != "10.5281/zenodo.20817291"
        or source.get("license") != "CC BY 4.0"
        or identity.get("identity_match") is not True
        or not checks
        or not all(value is True for value in checks.values())
        or runtime.get("emergency_response_grounding") is not True
        or runtime.get("station_release_model_validation") is not False
        or runtime.get("ad_hoc_ignition_of_vent_stream_authorized") is not False
    ):
        return None
    return {
        "artifact": artifact,
        "doi": source.get("doi"),
        "record_url": source.get("record_url"),
        "license": source.get("license"),
        "evidence_role": "engineered controlled-flare emergency-response grounding",
        "reported_findings": {
            key: findings.get(key)
            for key in (
                "controlled_flare_combustion_efficiency_lower_bound_percent",
                "nox_reduction_factor_approximate",
                "maximum_reported_nitrogen_fraction_for_continued_operation_volpct",
                "above_reported_nitrogen_boundary",
                "tested_safeguards",
            )
        },
        "runtime_use": runtime,
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


def _public_reference_leak_detector_evidence() -> dict[str, Any] | None:
    """Expose prospective physical-H2 detector ordering evidence.

    The protocol was committed before the workbook outcomes were opened. Only
    compact aggregate results enter the prompt; the raw workbook stays outside
    Git. Strict checks prevent this evidence from silently becoming a runtime
    calibration, alarm-setpoint, or spatial-detector claim.
    """

    artifact = "research/hydrogen_reference_leak_detector_result_2026_10_08.json"
    path = Path(__file__).resolve().parents[2] / artifact
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    protocol = record.get("protocol") or {}
    results = record.get("results") or {}
    decision = record.get("decision") or {}
    series = [item for item in results.get("series") or [] if isinstance(item, dict)]
    if (
        record.get("artifact_type")
        != "prospective_physical_hydrogen_reference_leak_detector_result"
        or record.get("status") != "COMPLETED_FROZEN_PROTOCOL_PASS"
        or source.get("doi") != "10.5281/zenodo.12180368"
        or source.get("license") != "CC BY 4.0"
        or source.get("test_gas") != "hydrogen"
        or source.get("physical_reference_leaks") is not True
        or source.get("identity_match") is not True
        or protocol.get("status") != "FROZEN_BEFORE_RAW_EXCEL_OUTCOME_ACCESS"
        or protocol.get("raw_outcomes_accessed_before_freeze") is not False
        or protocol.get("parameters_fitted") is not False
        or protocol.get("runtime_parameter_changed") is not False
        or results.get("eligible_detector_class_count") != 2
        or results.get("evaluated_series_count") != 3
        or results.get("total_observation_count") != 45
        or len(series) != 3
        or results.get("joint_pass") is not True
        or not all(item.get("joint_pass") is True for item in series)
        or decision.get("bounded_actual_hydrogen_response_ordering_supported") is not True
        or decision.get("runtime_application") is not False
        or decision.get("spatial_detector_transfer_gate_changed") is not False
        or decision.get("full_loop_validation_supported") is not False
    ):
        return None

    compact_series: list[dict[str, Any]] = []
    for item in series:
        reference_summaries = [
            row for row in item.get("reference_summaries") or [] if isinstance(row, dict)
        ]
        ratios = [
            float(row["median_response_to_reference_ratio"])
            for row in reference_summaries
            if isinstance(row.get("median_response_to_reference_ratio"), (int, float))
            and math.isfinite(float(row["median_response_to_reference_ratio"]))
        ]
        compact_series.append(
            {
                "series_id": item.get("series_id"),
                "detector_class": item.get("detector_class"),
                "mode": item.get("mode"),
                "observation_count": item.get("observation_count"),
                "distinct_reference_level_count": item.get(
                    "distinct_reference_level_count"
                ),
                "spearman_rho": item.get("spearman_rho"),
                "pairwise_order_concordance": item.get(
                    "pairwise_order_concordance"
                ),
                "finite_mapped_observation_fraction": item.get(
                    "finite_mapped_observation_fraction"
                ),
                "median_response_to_reference_ratio_range": (
                    [min(ratios), max(ratios)] if ratios else []
                ),
                "joint_pass": True,
            }
        )
    return {
        "artifact": artifact,
        "doi": source.get("doi"),
        "related_article_doi": source.get("supplement_to"),
        "license": source.get("license"),
        "evidence_role": (
            "prospective physical-hydrogen reference-leak detector-response ordering"
        ),
        "observation_count": results.get("total_observation_count"),
        "detector_class_count": results.get("eligible_detector_class_count"),
        "evaluated_series_count": results.get("evaluated_series_count"),
        "series": compact_series,
        "joint_pass": True,
        "runtime_application": False,
        "spatial_detector_transfer_gate_changed": False,
        "full_loop_validation_supported": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_actual_hydrogen_spatial_stratification_evidence() -> dict[str, Any] | None:
    """Expose bounded physical-H2 detector-height evidence.

    This analysis was designed after outcome access.  Strict checks keep it as
    descriptive placement guidance and prevent promotion to runtime routing or
    independent spatial-transfer validation.
    """

    artifact = (
        "research/usn_channel_spatial_stratification_evidence_2026_10_08.json"
    )
    path = Path(__file__).resolve().parents[2] / artifact
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    design = record.get("analysis_design") or {}
    aggregate = record.get("aggregate") or {}
    placements = aggregate.get("placements") or {}
    near_source_bottom = (
        aggregate.get("jet_path_subsets") or {}
    ).get("near_source_bottom") or {}
    decision = record.get("decision") or {}
    if (
        record.get("artifact_type")
        != "post_access_actual_hydrogen_spatial_stratification_evidence"
        or record.get("status")
        != "COMPLETED_DESCRIPTIVE_EVIDENCE_NOT_INDEPENDENT_VALIDATION"
        or source.get("dataset_doi") != "10.23642/usn.26117989.v2"
        or source.get("article_doi") != "10.1016/j.jlp.2025.105669"
        or source.get("test_gas") != "hydrogen"
        or source.get("license") != "CC BY 4.0"
        or design.get("outcomes_accessed_before_analysis_design") is not True
        or design.get("parameter_fitting_performed") is not False
        or aggregate.get("experiment_count") != 22
        or aggregate.get("sensor_count_per_experiment") != 29
        or aggregate.get("sensor_case_observation_count") != 638
        or len(placements) != 4
        or near_source_bottom.get("sensor_case_observation_count") != 66
        or (near_source_bottom.get("alarm") or {}).get(
            "coverage_fraction"
        ) != 1.0
        or decision.get(
            "layered_confined_detector_placement_rationale_supported"
        ) is not True
        or decision.get("independent_spatial_validation_supported") is not False
        or decision.get("runtime_application") is not False
        or decision.get("h2safe_gate_changed") is not False
        or decision.get("full_loop_validation_supported") is not False
    ):
        return None

    placement_summary: dict[str, Any] = {}
    for name in ("top", "mid-high", "mid-low", "bottom"):
        item = placements.get(name) or {}
        alarm = item.get("alarm") or {}
        trip = item.get("trip") or {}
        concentration = item.get("steady_concentration_percent") or {}
        placement_summary[name] = {
            "sensor_case_observation_count": item.get(
                "sensor_case_observation_count"
            ),
            "median_steady_concentration_percent": concentration.get("median"),
            "alarm_coverage_fraction": alarm.get("coverage_fraction"),
            "median_alarm_latency_after_fill_start_s": alarm.get(
                "median_latency_after_fill_start_s"
            ),
            "trip_coverage_fraction": trip.get("coverage_fraction"),
        }
    return {
        "artifact": artifact,
        "dataset_doi": source.get("dataset_doi"),
        "article_doi": source.get("article_doi"),
        "license": source.get("license"),
        "evidence_role": (
            "post-access descriptive physical-hydrogen spatial stratification"
        ),
        "experiment_count": aggregate.get("experiment_count"),
        "sensor_count_per_experiment": aggregate.get(
            "sensor_count_per_experiment"
        ),
        "sensor_case_observation_count": aggregate.get(
            "sensor_case_observation_count"
        ),
        "top_placement_highest_case_mean_count": aggregate.get(
            "top_placement_highest_case_mean_count"
        ),
        "placements": placement_summary,
        "near_source_bottom": {
            "sensor_case_observation_count": near_source_bottom.get(
                "sensor_case_observation_count"
            ),
            "median_alarm_latency_after_fill_start_s": (
                near_source_bottom.get("alarm") or {}
            ).get("median_latency_after_fill_start_s"),
            "alarm_coverage_fraction": (
                near_source_bottom.get("alarm") or {}
            ).get("coverage_fraction"),
            "trip_coverage_fraction": (
                near_source_bottom.get("trip") or {}
            ).get("coverage_fraction"),
        },
        "bounded_guidance": (
            "In this confined downward-jet geometry, combine ceiling coverage "
            "for the sustained buoyant layer with near-source jet-path coverage."
        ),
        "post_access_descriptive_evidence": True,
        "runtime_application": False,
        "h2safe_gate_changed": False,
        "independent_spatial_validation_supported": False,
        "full_loop_validation_supported": False,
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


def _public_h2safe_indoor_surrogate_evidence() -> dict[str, Any] | None:
    """Expose bounded full-scale indoor surrogate data to the assistant.

    H2SAFE provides useful full-scale sensor/geometry/HVAC provenance, but the
    published package does not state a concentration unit in its CSV headers or
    an unambiguous release-start alignment for the traces. It must therefore be
    visible as qualitative context, never as a fitted H2 detector threshold or
    as a site-dispersion result.
    """

    artifact = "research/h2safe_indoor_release_intake_2026_10_07.json"
    path = Path(__file__).resolve().parents[2] / artifact
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    intake = record.get("intake") or {}
    eligibility = record.get("eligibility") or {}
    cases = [item for item in intake.get("cases") or [] if isinstance(item, dict)]
    if (
        record.get("status") != "completed_bounded_full_scale_indoor_surrogate_intake"
        or source.get("doi") != "10.7799/17118570"
        or source.get("raw_rows_committed") is not False
        or intake.get("case_count") != 5
        or len(cases) != 5
        or not all(not item.get("unmapped_sensor_columns") for item in cases)
        or eligibility.get("numerical_hydrogen_alarm_or_trip_threshold_calibration") is not False
    ):
        return None
    return {
        "artifact": artifact,
        "doi": str(source.get("doi") or ""),
        "catalog_url": str(source.get("catalog_url") or ""),
        "license_summary": str(source.get("license_summary") or ""),
        "evidence_role": "public full-scale indoor helium-surrogate sensor/geometry/HVAC context",
        "medium": str(source.get("medium") or ""),
        "case_count": intake.get("case_count"),
        "lab_sensor_coordinate_counts": intake.get("lab_sensor_coordinate_counts") or {},
        "timestamped_signal_schema_available": eligibility.get(
            "timestamped_signal_schema_available"
        ) is True,
        "qualitative_geometry_hvac_context_available": eligibility.get(
            "full_scale_indoor_geometry_and_sensor_coordinate_context"
        ) is True and eligibility.get("release_and_hvac_metadata_available") is True,
        "numerical_hydrogen_alarm_or_trip_threshold_calibration": False,
        "full_loop_station_vehicle_validation": False,
        "runtime_parameter_updated": record.get("runtime_parameter_updated") is True,
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


def _public_tank_validation_evidence() -> dict[str, Any] | None:
    """Expose the frozen public NREL tank/hose screen without raw rows.

    The NREL workbook is a useful measured tank/hose boundary, but it has no
    station-controller, ESD, cascade, protocol or receptacle trace. Keeping
    its failed pressure screen, hose channels and geometry diagnostic in the
    evidence envelope prevents a decision assistant from silently turning a
    partial-boundary result into a full HRS validation claim. This function
    reads only the aggregate result artifact; the workbook remains local and
    ignored.
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
        "common_time_base": (record.get("boundary_channel_screen") or {}).get(
            "common_time_base"
        ),
        "hose_pressure_temperature_present": (
            record.get("boundary_channel_screen") or {}
        ).get("hose_pressure_temperature_present"),
        "per_tank_pressure_temperature_mass_present": (
            record.get("boundary_channel_screen") or {}
        ).get("per_tank_pressure_temperature_mass_present"),
        "station_controller_or_cascade_state_present": (
            record.get("boundary_channel_screen") or {}
        ).get("station_controller_or_cascade_state_present"),
        "esd_or_safety_interlock_trace_present": (
            record.get("boundary_channel_screen") or {}
        ).get("esd_or_safety_interlock_trace_present"),
        "breakaway_hose_nozzle_receptacle_trace_present": (
            record.get("boundary_channel_screen") or {}
        ).get("breakaway_hose_nozzle_receptacle_trace_present"),
        "vehicle_side_protocol_trace_present": (
            record.get("boundary_channel_screen") or {}
        ).get("vehicle_side_protocol_trace_present"),
        "partial_station_to_tank_boundary_eligible": (
            record.get("boundary_channel_screen") or {}
        ).get("partial_station_to_tank_boundary_eligible"),
        "full_loop_external_holdout_eligible": (
            record.get("boundary_channel_screen") or {}
        ).get("full_loop_external_holdout_eligible"),
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
                    "hose_pressure_initial_mpa", "hose_pressure_final_mpa",
                    "hose_pressure_peak_mpa", "hose_temperature_min_c",
                    "hose_temperature_max_c", "ambient_temperature_c",
                )
                if source.get("dataset_summary", {}).get(key) is not None
            },
        },
        "frozen_model": {
            "boundary_conditions": frozen_model.get("boundary_conditions"),
            "post_access_parameter_tuning": False,
            "ambient_temperature_c": frozen_model.get("ambient_temperature_c"),
        },
        "boundary_channel_screen": {
            str(key): value
            for key, value in (record.get("boundary_channel_screen") or {}).items()
            if isinstance(value, (int, float, str, bool))
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
        "research/methytrucks_2026_public_measurement_intake.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    integrity = record.get("integrity") or {}
    aggregate = record.get("aggregate") or {}
    eligibility = record.get("eligibility") or {}
    mapping = record.get("mapping_boundary") or {}
    official_test_context = mapping.get("official_test_context") or {}
    group_a = official_test_context.get("group_a_npl") or {}
    group_c = official_test_context.get("group_c_engie") or {}
    if (
        record.get("status") != "PASS"
        or integrity.get("all_zenodo_md5_and_sizes_match") is not True
        or aggregate.get("workbook_count") != 15
        or eligibility.get("public_real_experimental_measurements") is not True
        or eligibility.get("full_loop_station_vehicle_validation_eligible") is not False
        or mapping.get("publisher_channel_dictionary_present") is not False
    ):
        return None
    sources = []
    source_block = record.get("sources") or {}
    for source in source_block.get("measurement_records") or []:
        if not isinstance(source, dict) or not source.get("record_id"):
            continue
        sources.append({
            "record_id": str(source.get("record_id")),
            "doi": str(source.get("doi") or ""),
            "title": str(source.get("title") or ""),
            "license": str(source.get("license") or ""),
            "observed_file_count": source.get("workbook_count"),
        })
    return {
        "artifact": "research/methytrucks_2026_public_measurement_intake.json",
        "evidence_role": (
            "post-access public HRS sampling-system instrumentation and "
            "flow-mass component diagnostic"
        ),
        "source_count": len(sources),
        "sources": sources,
        "file_count": aggregate.get("workbook_count"),
        "sample_count": aggregate.get("sample_count"),
        "observed_sampling_intervals_s": aggregate.get("sampling_intervals_s"),
        "workbooks_with_mass": aggregate.get("workbooks_with_mass"),
        "mass_closure_session_count": aggregate.get("mass_closure_session_count"),
        "mass_closure_comparable_session_count": aggregate.get(
            "mass_closure_comparable_session_count"
        ),
        "mass_closure_non_comparable_session_count": aggregate.get(
            "mass_closure_non_comparable_session_count"
        ),
        "mass_closure_screen_pass_count": aggregate.get(
            "mass_closure_screen_pass_count"
        ),
        "mass_closure_comparable_pass_fraction": aggregate.get(
            "mass_closure_comparable_pass_fraction"
        ),
        "mass_closure_pass_ratio_median": aggregate.get(
            "mass_closure_pass_ratio_median"
        ),
        "mass_closure_comparable_ratio_median": aggregate.get(
            "mass_closure_comparable_ratio_median"
        ),
        "mass_closure_comparable_absolute_relative_difference_pct_median": aggregate.get(
            "mass_closure_comparable_absolute_relative_difference_pct_median"
        ),
        "station_measurement_auxiliary_eligible": True,
        "full_loop_holdout_eligible": False,
        "channel_dictionary_present": False,
        "vehicle_or_receptacle_channels_identified": False,
        "official_test_context": official_test_context,
        "group_a_c_vehicle_fill_eligible": bool(
            group_a.get("vehicle_receiving_tank") is True
            and group_c.get("vehicle_receiving_tank") is True
        ),
        "test_class_interpretation": (
            "Groups A and C are documented 35 MPa direct/serial sampling-system "
            "tests with sampling-hardware sinks; do not describe them as vehicle "
            "fills or station-to-vehicle full-loop validation."
        ),
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _methytrucks_tank_diagnostic_evidence() -> dict[str, Any] | None:
    """Expose the bounded HySaM tank replay without promoting it to validation.

    The public workbooks support a useful no-fit component diagnostic, but the
    released package still lacks a channel dictionary and a workbook-to-sink
    crosswalk.  The compact aggregate below lets every assistant route use the
    measured error evidence while preserving those two blocking limitations.
    Raw rows, workbook names and inferred tag mappings are deliberately omitted.
    """

    root = Path(__file__).resolve().parents[2]
    diagnostic_path = root / (
        "research/methytrucks_hysam_postaccess_diagnostic_2026_10_08.json"
    )
    supplement_path = root / (
        "research/methytrucks_supplementary_mapping_recheck_2026_10_08.json"
    )
    try:
        diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
        supplement = json.loads(supplement_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None

    source = diagnostic.get("source") or {}
    aggregate = diagnostic.get("candidate_session_aggregate") or {}
    alternative = (
        (diagnostic.get("candidate_volume_sensitivity") or {}).get("aggregate")
        or {}
    )
    eligibility = diagnostic.get("eligibility") or {}
    observed = supplement.get("observed_contents") or {}
    geometry = supplement.get("article_geometry_boundary") or {}
    candidate_screen = aggregate.get("project_screen") or {}
    alternative_screen = alternative.get("project_screen") or {}

    if not all((
        diagnostic.get("status") == "completed_post_access_external_diagnostic",
        supplement.get("status")
        == "supplement_downloaded_and_mapping_gap_confirmed",
        source.get("dataset_doi") == "10.5281/zenodo.20590842",
        aggregate.get("case_count") == 5,
        aggregate.get("unique_workbook_count") == 2,
        aggregate.get("independent_event_count_claimed") is False,
        eligibility.get("component_diagnostic_eligible") is True,
        eligibility.get("prospective_holdout_eligible") is False,
        eligibility.get("quantitative_full_loop_validation_eligible") is False,
        observed.get("channel_dictionary_present") is False,
        observed.get("workbook_test_to_setup_crosswalk_present") is False,
        geometry.get("public_workbook_to_set_up_mapping_confirmed") is False,
    )):
        return None

    def metric(container: dict[str, Any], name: str) -> Any:
        return _finite_number((container.get(name) or {}).get("case_mean"))

    return {
        "artifact": (
            "research/methytrucks_hysam_postaccess_diagnostic_2026_10_08.json"
        ),
        "supplementary_artifact": (
            "research/methytrucks_supplementary_mapping_recheck_2026_10_08.json"
        ),
        "evidence_role": "post_access_no_fit_public_tank_diagnostic",
        "source": {
            "dataset_doi": source.get("dataset_doi"),
            "dataset_license": source.get("dataset_license"),
            "article_doi": source.get("article_doi"),
            "article_license": source.get("article_license"),
        },
        "scope": {
            "case_count": aggregate.get("case_count"),
            "unique_workbook_count": aggregate.get("unique_workbook_count"),
            "independent_event_count_claimed": False,
            "within_workbook_sessions_may_be_correlated": (
                aggregate.get("within_workbook_sessions_may_be_correlated") is True
            ),
            "selection_is_independent_of_model_prediction": (
                aggregate.get("selection_is_independent_of_model_prediction") is True
            ),
            "case_specific_fitting": False,
        },
        "candidate_244_l_diagnostic": {
            "pressure_rmse_case_mean_mpa": metric(aggregate, "pressure_rmse_mpa"),
            "temperature_rmse_case_mean_c": metric(aggregate, "temperature_rmse_c"),
            "descriptive_joint_pass_count": candidate_screen.get(
                "joint_pass_count"
            ),
            "descriptive_joint_pass_fraction": _finite_number(
                candidate_screen.get("joint_pass_fraction")
            ),
        },
        "alternate_77_l_sensitivity": {
            "pressure_rmse_case_mean_mpa": metric(
                alternative, "pressure_rmse_mpa"
            ),
            "temperature_rmse_case_mean_c": metric(
                alternative, "temperature_rmse_c"
            ),
            "descriptive_joint_pass_count": alternative_screen.get(
                "joint_pass_count"
            ),
            "descriptive_joint_pass_fraction": _finite_number(
                alternative_screen.get("joint_pass_fraction")
            ),
        },
        "mapping_boundary": {
            "channel_dictionary_present": False,
            "workbook_to_sink_crosswalk_present": False,
            "candidate_sink_volumes_l": [
                geometry.get("set_up_1_sink_l"),
                geometry.get("set_up_2_sink_l"),
            ],
        },
        "component_diagnostic_eligible": True,
        "prospective_holdout_eligible": False,
        "full_loop_validation_eligible": False,
        "claim_supported": False,
        "required_next_step": str(diagnostic.get("highest_value_next_action") or ""),
        "claim_limit": str(diagnostic.get("claim_boundary") or ""),
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
    mixed_path = root / (
        "research/mc_station_mixed_convection_diagnostic_2026_10_08.json"
    )
    try:
        holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
        diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
        mixed = json.loads(mixed_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    aggregate = holdout.get("aggregate") or {}
    limits = holdout.get("screening_limits") or {}
    metrics = aggregate.get("metrics") or {}
    diagnostic_aggregate = diagnostic.get("diagnostic_aggregate") or {}
    mixed_interpretation = mixed.get("interpretation") or {}
    mixed_runs = mixed.get("runs") or []
    required = (
        holdout.get("protocol_frozen_before_data_access") is True,
        holdout.get("post_freeze_parameter_tuning") is False,
        aggregate.get("case_count") == 8,
        aggregate.get("screening_pass_count") == 0,
        diagnostic.get("status") == "post_freeze_diagnostic_only",
        diagnostic.get("prohibited_use") and isinstance(
            diagnostic.get("purpose"), str
        ),
        mixed.get("diagnostic_type")
        == "MC Default full-station mixed-convection sensitivity",
        mixed.get("evidence_role") == "post_outcome_development_diagnostic_only",
        mixed.get("post_outcome") is True,
        mixed.get("parameter_fitting") is False,
        mixed.get("geometry_selection_prohibited") is True,
        mixed.get("historical_frozen_validation_unchanged") is True,
        mixed.get("case_count") == 8,
        len(mixed_runs) == 4,
        all(
            (row.get("aggregate") or {}).get("joint_screening_pass_count") == 0
            for row in mixed_runs
            if isinstance(row, dict)
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
        "mixed_convection_diagnostic": {
            "artifact": (
                "research/mc_station_mixed_convection_diagnostic_2026_10_08.json"
            ),
            "evidence_role": "post_outcome_development_diagnostic_only",
            "case_count": mixed.get("case_count"),
            "nozzle_diameter_grid_mm": (
                mixed.get("configuration") or {}
            ).get("nozzle_diameter_grid_mm") or [],
            "constant_ua_temperature_stop_count": mixed_interpretation.get(
                "constant_ua_temperature_stop_count"
            ),
            "mixed_convection_temperature_stop_count_range": (
                mixed_interpretation.get(
                    "mixed_convection_temperature_stop_count_range"
                ) or []
            ),
            "mixed_convection_pressure_rmse_mpa_mean_range": (
                mixed_interpretation.get(
                    "mixed_convection_pressure_rmse_mpa_mean_range"
                ) or []
            ),
            "mixed_convection_temperature_rmse_c_mean_range": (
                mixed_interpretation.get(
                    "mixed_convection_temperature_rmse_c_mean_range"
                ) or []
            ),
            "joint_screening_pass_count_range": mixed_interpretation.get(
                "joint_screening_pass_count_range"
            ) or [],
            "runtime_default_changed": False,
            "geometry_selection_prohibited": True,
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


def _temperature_observation_semantic_boundary() -> dict[str, Any] | None:
    """Expose a bounded warning about cross-dataset tank-temperature meaning.

    A public Type-IV fit may use a channel whose physical observation model is
    declared differently from another public fill experiment. This evidence
    makes that distinction visible to the decision assistant without selecting
    a more favourable post-outcome observation operator or changing runtime
    temperature logic.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/mc_temperature_observation_diagnostic_2026_10_07.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    expected_operators = {
        "gas_temperature",
        "liner_temperature",
        "shell_temperature",
        "liner_shell_mean",
    }
    aggregate = record.get("aggregate") or {}
    if (
        record.get("diagnostic_type")
        != "MC Default temperature-observation semantic replay"
        or record.get("evidence_role") != "post_outcome_semantic_diagnostic_only"
        or record.get("post_outcome") is not True
        or record.get("parameter_fitting") is not False
        or record.get("runtime_thermal_observation_changed") is not False
        or record.get("observation_mapping_selection_prohibited") is not True
        or record.get("promotion_to_validation_prohibited") is not True
        or record.get("raw_experimental_rows_persisted") is not False
        or record.get("source_workbook_names_persisted") is not False
        or set(aggregate) != expected_operators
        or len(record.get("cases") or []) != 8
    ):
        return None
    # Do not relay outcome-derived error ranks to the provider. It only needs
    # to know that multiple physical observation operators diverged and that
    # no post-outcome selection has been made.
    return {
        "artifact": "research/mc_temperature_observation_diagnostic_2026_10_07.json",
        "evidence_role": "post_outcome_semantic_diagnostic_only",
        "runtime_temperature_state": "gas_temperature",
        "candidate_observation_operators": sorted(expected_operators),
        "candidate_operator_count": len(expected_operators),
        "cross_dataset_semantic_mismatch_detected": True,
        "runtime_thermal_observation_changed": False,
        "operator_selection_prohibited": True,
        "validation_claim_supported": False,
        "claim_limit": (
            "공개 충전시험의 탱크 평균온도는 가스·라이너·쉘·센서 평균 중 무엇을 "
            "뜻하는지 별도 확인이 필요합니다. 사후 오차가 낮은 관측 연산자를 선택하지 "
            "않았으며, 현재 가상 운전의 가스온도를 현장 탱크 센서값과 동등하다고 단정하지 않습니다."
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


def _cross_campaign_release_validation_evidence() -> dict[str, Any] | None:
    """Expose mixed public release-validation outcomes without averaging them away.

    A single passing transient cannot erase failures from other apparatus and
    endpoints. This projection preserves each campaign's pass, fail and
    eligibility state and keeps the apparatus-resolved protocol unexecuted.
    """

    root = Path(__file__).resolve().parents[2]
    filenames = {
        "ekoto_2012": "research/ekoto_2012_holdout_result.json",
        "schefer_2006": "research/schefer_2006_holdout_result.json",
        "schefer_2007": "research/schefer_2007_holdout_result.json",
        "grune_2014": "research/grune_2014_holdout_result.json",
    }
    try:
        records = {
            key: json.loads((root / filename).read_text(encoding="utf-8"))
            for key, filename in filenames.items()
        }
        diagnosis = json.loads(
            (root / "research/release_validation_failure_diagnosis_2026_10_04.json")
            .read_text(encoding="utf-8")
        )
        prospective = json.loads(
            (root / "research/release_network_prospective_protocol.json")
            .read_text(encoding="utf-8")
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return None

    ekoto = records["ekoto_2012"]
    schefer_2006 = records["schefer_2006"]
    schefer_2007 = records["schefer_2007"]
    grune = records["grune_2014"]
    grune_eligibility = grune.get("eligibility") or {}
    diagnosis_boundary = diagnosis.get("validation_boundary") or {}
    diagnosis_review = diagnosis.get("implementation_review") or {}
    prospective_result = prospective.get("current_result") or {}
    if (
        ekoto.get("claim_supported") is not True
        or (ekoto.get("result") or {}).get("joint_primary_screen_pass") is not True
        or schefer_2006.get("claim_supported") is not False
        or (schefer_2006.get("result") or {}).get("joint_primary_screen_pass") is not False
        or schefer_2007.get("claim_supported") is not False
        or (schefer_2007.get("result") or {}).get("joint_primary_screen_pass") is not False
        or grune.get("claim_supported") is not False
        or grune_eligibility.get("minimum_requirements_met") is not False
        or diagnosis.get("status") != "DEVELOPMENT_DIAGNOSTIC_ONLY"
        or diagnosis_boundary.get("frozen_holdouts_modified") is not False
        or diagnosis_boundary.get("post_outcome_parameter_fitting") is not False
        or diagnosis_review.get("clear_unit_or_initial_condition_bug_found") is not False
        or prospective.get("status") != "prospective_model_only_no_holdout_received"
        or prospective_result.get("raw_campaign_received") is not False
        or prospective_result.get("numerical_holdout_run") is not False
    ):
        return None

    def campaign(
        key: str,
        *,
        endpoint: str,
        eligible: bool,
        metric_names: tuple[str, ...],
        ineligibility_reason: str | None = None,
    ) -> dict[str, Any]:
        source = records[key]
        result = source.get("result") or {}
        metrics = {
            name: result.get(name)
            for name in metric_names
            if isinstance(result.get(name), (int, float))
            and math.isfinite(float(result[name]))
        }
        row: dict[str, Any] = {
            "artifact": filenames[key],
            "endpoint": endpoint,
            "minimum_requirements_met": eligible,
            "joint_primary_screen_pass": (
                result.get("joint_primary_screen_pass") is True
            ),
            "claim_supported": source.get("claim_supported") is True,
            "metrics": metrics,
        }
        if ineligibility_reason:
            row["ineligibility_reason"] = ineligibility_reason
        return row

    campaigns = {
        "ekoto_2012": campaign(
            "ekoto_2012",
            endpoint="transient_mass_flow",
            eligible=True,
            metric_names=(
                "mass_flow_nrmse_percent_peak_measured",
                "median_absolute_percentage_error_percent",
                "half_peak_time_relative_error_percent",
            ),
        ),
        "schefer_2006": campaign(
            "schefer_2006",
            endpoint="transient_mass_flow",
            eligible=True,
            metric_names=(
                "mass_flow_nrmse_percent_peak_measured",
                "median_absolute_percentage_error_percent",
                "half_peak_time_relative_error_percent",
            ),
        ),
        "schefer_2007": campaign(
            "schefer_2007",
            endpoint="pressure_decay",
            eligible=True,
            metric_names=(
                "pressure_nrmse_percent_initial_measured",
                "median_absolute_percentage_error_percent",
                "half_pressure_time_relative_error_percent",
            ),
        ),
        "grune_2014": campaign(
            "grune_2014",
            endpoint="pressure_decay",
            eligible=False,
            metric_names=(
                "pressure_nrmse_percent_initial_measured",
                "median_absolute_percentage_error_percent",
            ),
            ineligibility_reason=str(grune_eligibility.get("reason") or ""),
        ),
    }
    return {
        "evidence_role": "mixed_external_release_component_validation",
        "campaigns": campaigns,
        "eligible_campaign_count": 3,
        "supported_campaign_count": 1,
        "failed_campaign_count": 2,
        "ineligible_campaign_count": 1,
        "universal_release_validation_supported": False,
        "apparatus_resolved_holdout_received": False,
        "apparatus_resolved_holdout_run": False,
        "runtime_model_changed_after_outcomes": False,
        "claim_limit": (
            "공개 방출 캠페인별 결과는 서로 다른 장치와 종점을 포함하며 1건 통과, "
            "2건 실패, 1건 검증요건 미충족입니다. 장치 형상·밸브·라인팩이 확인된 "
            "신규 전향적 홀드아웃 전에는 범용 방출, 충전소 전체, 피해거리 또는 현장 "
            "안전 검증으로 확대할 수 없습니다."
        ),
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


def _public_station_operation_practice_reference() -> dict[str, Any] | None:
    """Expose qualitative public-facility operating practice with hard limits.

    The source describes one public research facility's sequence and operating
    cues.  It is useful for explaining pauses, cascade-to-compressor transfer
    and pre-cooling, but it must never be promoted to a universal station
    protocol or a site-specific safety limit.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/calstate_la_operation_practice_reference_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    practices = record.get("reported_practices") or {}
    if (
        record.get("artifact_type") != "public_station_operation_practice_reference"
        or record.get("status") != "public_qualitative_operating_context"
        or source.get("public_access") is not True
        or not str(source.get("url") or "").startswith("https://")
        or practices.get("cascade_then_compressor_topoff") is not True
        or practices.get("periodic_leak_check_pause_s") != 5
        or not isinstance(practices.get("delivered_gas_temperature_band_c"), list)
        or len(practices.get("delivered_gas_temperature_band_c")) != 2
        or not record.get("allowed_use")
        or not record.get("not_allowed")
    ):
        return None
    return {
        "artifact": "research/calstate_la_operation_practice_reference_2026_10_09.json",
        "evidence_role": "public facility qualitative operating-practice reference",
        "source": {
            "title": str(source.get("title") or ""),
            "institution": str(source.get("institution") or ""),
            "url": str(source.get("url") or ""),
            "source_type": str(source.get("source_type") or ""),
        },
        "reported_practices": {
            key: practices.get(key)
            for key in (
                "cascade_then_compressor_topoff",
                "approximate_storage_to_vehicle_equilibrium_psi",
                "target_pressure_can_exceed_nominal_psi",
                "pre_cooler_setpoint_c",
                "delivered_gas_temperature_band_c",
                "periodic_leak_check_pressure_increment_psi",
                "periodic_leak_check_pause_s",
                "leak_and_flame_detection_described",
                "post_fill_cooldown_soc_percent_range",
            )
            if practices.get(key) is not None
        },
        "allowed_use": [str(value) for value in record.get("allowed_use") or []],
        "not_allowed": [str(value) for value in record.get("not_allowed") or []],
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_station_aggregate_benchmark_reference() -> dict[str, Any] | None:
    """Expose aggregate public-station operating context with hard limits.

    The article reports multi-year counts and energy aggregates, not a
    synchronized station-to-vehicle logger.  Keep this source available for
    sanity checks and explanations while preventing calibration or holdout
    claims from entering the runtime evidence envelope.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/calstate_la_multi_year_aggregate_reference_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    aggregate = record.get("reported_aggregate") or {}
    event_count = aggregate.get("refueling_event_count_approx")
    hydrogen_kg = aggregate.get("dispensed_hydrogen_kg_approx")
    energy_range = aggregate.get("reported_2020_q1_energy_kwh_per_kg_range")
    if (
        record.get("artifact_type") != "public_station_aggregate_benchmark_reference"
        or record.get("status") != "public_aggregate_operating_context"
        or source.get("public_access") is not True
        or source.get("public_raw_synchronized_rows") is not False
        or not str(source.get("doi") or "").strip()
        or not str(source.get("url") or "").startswith("https://")
        or not isinstance(event_count, (int, float))
        or event_count <= 0
        or not isinstance(hydrogen_kg, (int, float))
        or hydrogen_kg <= 0
        or not isinstance(energy_range, list)
        or len(energy_range) != 2
        or not all(isinstance(value, (int, float)) for value in energy_range)
        or not record.get("allowed_use")
        or not record.get("not_allowed")
    ):
        return None
    return {
        "artifact": "research/calstate_la_multi_year_aggregate_reference_2026_10_09.json",
        "evidence_role": "public aggregate station operating benchmark",
        "source": {
            "title": str(source.get("title") or ""),
            "institution": str(source.get("institution") or ""),
            "doi": str(source.get("doi") or ""),
            "url": str(source.get("url") or ""),
            "source_type": str(source.get("source_type") or ""),
            "public_raw_synchronized_rows": False,
        },
        "reported_aggregate": {
            "observation_period": str(aggregate.get("observation_period") or ""),
            "refueling_event_count_approx": event_count,
            "dispensed_hydrogen_kg_approx": hydrogen_kg,
            "reported_domains": [
                str(value) for value in aggregate.get("reported_domains") or []
            ],
            "reported_2020_q1_energy_kwh_per_kg_range": list(energy_range),
            "reported_2020_q1_site_efficiency_percent_max": aggregate.get(
                "reported_2020_q1_site_efficiency_percent_max"
            ),
        },
        "allowed_use": [str(value) for value in record.get("allowed_use") or []],
        "not_allowed": [str(value) for value in record.get("not_allowed") or []],
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_threeemotion_operating_aggregate_reference() -> dict[str, Any] | None:
    """Expose the 3Emotion bus-station aggregates without raw-log claims."""

    path = Path(__file__).resolve().parents[2] / (
        "research/threeemotion_station_operating_aggregate_reference_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    aggregate = record.get("reported_aggregate") or {}
    required_numeric = (
        "average_daily_mass_per_bus_kg",
        "most_frequent_daily_mass_per_bus_kg",
        "daily_mass_standard_deviation_kg",
        "overnight_dispensed_fraction_approx",
        "typical_refueling_interval_h",
        "station_utilization_below_percent",
    )
    if (
        record.get("artifact_type") != "public_station_operating_aggregate_reference"
        or record.get("status") != "public_aggregate_operating_context"
        or source.get("public_access") is not True
        or source.get("public_raw_synchronized_rows") is not False
        or not str(source.get("doi") or "").strip()
        or not str(source.get("url") or "").startswith("https://")
        or aggregate.get("vehicle_class") != "350 bar fuel-cell buses"
        or any(
            not isinstance(aggregate.get(key), (int, float))
            for key in required_numeric
        )
        or not aggregate.get("reported_outputs")
        or not record.get("allowed_use")
        or not record.get("not_allowed")
    ):
        return None
    return {
        "artifact": (
            "research/threeemotion_station_operating_aggregate_reference_2026_10_09.json"
        ),
        "evidence_role": "public aggregate heavy-duty station operating benchmark",
        "source": {
            "title": str(source.get("title") or ""),
            "authors": [str(value) for value in source.get("authors") or []],
            "doi": str(source.get("doi") or ""),
            "url": str(source.get("url") or ""),
            "source_type": str(source.get("source_type") or ""),
            "public_raw_synchronized_rows": False,
        },
        "reported_aggregate": {
            key: aggregate.get(key)
            for key in (
                "vehicle_class",
                "source_scope_note",
                "average_daily_mass_per_bus_kg",
                "most_frequent_daily_mass_per_bus_kg",
                "daily_mass_standard_deviation_kg",
                "overnight_dispensed_fraction_approx",
                "typical_refueling_interval_h",
                "station_utilization_below_percent",
                "reported_outputs",
            )
            if aggregate.get(key) is not None
        },
        "allowed_use": [str(value) for value in record.get("allowed_use") or []],
        "not_allowed": [str(value) for value in record.get("not_allowed") or []],
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_hrs_measurement_leads() -> dict[str, Any] | None:
    """Expose public HRS measurement leads with an explicit data boundary.

    These records are useful for operating-range context and for preparing a
    data request, but the cited papers/facilities do not release a
    de-identified synchronized station-to-vehicle trace.  The assistant must
    therefore never treat this index as an external holdout, a parameter-fit
    source, or evidence of SAGA effectiveness.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/public_hrs_measurement_leads_recheck_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    leads = record.get("leads") or []
    if (
        record.get("artifact_type") != "public_hrs_measurement_leads_recheck"
        or record.get("status") != "HIGH_VALUE_HRS_MEASUREMENT_LEADS_RAW_TRACE_NOT_PUBLIC"
        or not all(
            privacy.get(key) is False
            for key in (
                "private_station_paths_included",
                "raw_rows_included",
                "private_site_identifiers_included",
                "unpublished_personal_data_included",
            )
        )
        or not leads
    ):
        return None

    compact_leads: list[dict[str, Any]] = []
    for lead in leads:
        if not isinstance(lead, dict):
            continue
        url = str(lead.get("url") or "")
        lead_id = str(lead.get("id") or "")
        if not lead_id or not url.startswith(("https://", "http://")):
            return None
        reported_scope = lead.get("reported_scope") or {}
        compact_leads.append({
            "id": lead_id,
            "title": str(lead.get("title") or ""),
            "url": url,
            "reported_scope": reported_scope,
            "raw_trace_public": lead.get("raw_trace_public") is True,
            "abnormal_data_provenance": str(
                lead.get("abnormal_data_provenance")
                or lead.get("data_availability_boundary")
                or ""
            ),
            "decision": str(lead.get("decision") or ""),
            "eligible_use": [str(value) for value in lead.get("eligible_use") or []],
            "ineligible_use": [
                str(value) for value in lead.get("ineligible_use") or []
            ],
        })
    if len(compact_leads) != len(leads):
        return None
    return {
        "artifact": "research/public_hrs_measurement_leads_recheck_2026_10_09.json",
        "evidence_role": "public HRS measurement lead index and raw-trace availability boundary",
        "status": str(record.get("status") or ""),
        "leads": compact_leads,
        "request_package_requirements": [
            str(value) for value in record.get("request_package_requirements") or []
        ],
        "full_loop_external_validation_supported": False,
        "parameter_fitting_supported": False,
        "saga_effectiveness_supported": False,
        "claim_limit": str(record.get("gate_impact", {}).get("full_loop_external_validation") or "")
        + "; "
        + "공개 문헌·시설 페이지의 측정 주장만 전달하며 동기화된 원시 trace가 없어 외부 full-loop 검증·보정·SAGA 효과평가에 사용할 수 없습니다.",
    }


def _public_vehicle_side_h2_measurement_leads() -> dict[str, Any] | None:
    """Expose public vehicle-side measurement leads without overstating access.

    The lead is useful when a user asks how to close the vehicle-side mass or
    pressure boundary.  It is deliberately kept separate from the HRS lead
    index because a vehicle-side comparison paper is not a synchronized
    station-controller holdout.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/public_vehicle_side_h2_measurement_leads_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    leads = record.get("leads") or []
    if (
        record.get("artifact_type") != "public_vehicle_side_h2_measurement_leads"
        or privacy.get("local_raw_rows_persisted") is not False
        or privacy.get("private_station_identifiers_published") is not False
        or not leads
    ):
        return None
    compact: list[dict[str, Any]] = []
    for lead in leads:
        if not isinstance(lead, dict):
            return None
        url = str(lead.get("article_url") or "")
        repository = str(lead.get("repository_page") or "")
        if not url.startswith("https://") or not repository.startswith("https://"):
            return None
        compact.append({
            "id": str(lead.get("id") or ""),
            "title": str(lead.get("title") or ""),
            "article_doi": str(lead.get("article_doi") or ""),
            "article_url": url,
            "repository_page": repository,
            "reported_measurements": [
                str(value) for value in lead.get("reported_measurements") or []
            ],
            "reported_scope": str(lead.get("reported_scope") or ""),
            "raw_trace_status": str(lead.get("raw_trace_status") or ""),
            "full_loop_eligibility": lead.get("full_loop_eligibility") is True,
            "eligible_use": [str(value) for value in lead.get("eligible_use") or []],
            "ineligible_use": [
                str(value) for value in lead.get("ineligible_use") or []
            ],
            "next_access_request": [
                str(value) for value in lead.get("next_access_request") or []
            ],
            "claim_limit": str(lead.get("claim_limit") or ""),
        })
    return {
        "artifact": "research/public_vehicle_side_h2_measurement_leads_2026_10_09.json",
        "evidence_role": "public vehicle-side H2 measurement lead and access boundary",
        "leads": compact,
        "full_loop_external_validation_supported": False,
        "parameter_fitting_supported": False,
        "saga_effectiveness_supported": False,
        "claim_limit": (
            "Vehicle-side mass-accounting context only; synchronized raw station-"
            "controller traces and full-loop validation remain unavailable."
        ),
    }


def _public_carb_hrs_inuse_field_benchmark() -> dict[str, Any] | None:
    """Load CARB's aggregate 22-station field benchmark with claim limits."""

    path = Path(__file__).resolve().parents[2] / (
        "research/carb_2024_hrs_inuse_field_benchmark_2026_10_08.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    population = record.get("population") or {}
    eligibility = record.get("eligibility") or {}
    tables = record.get("tables") or {}
    if (
        record.get("artifact_type") != "public_real_station_field_benchmark"
        or population.get("stations_tested") != 22
        or not str(source.get("url") or "").startswith(("https://", "http://"))
        or eligibility.get("field_relevance_benchmark") is not True
        or eligibility.get("dynamic_model_parameter_calibration") is not False
        or eligibility.get("full_loop_external_holdout") is not False
        or not all(name in tables for name in (
            "protocol_fault", "general_fault", "communications",
            "fueling_performance",
        ))
    ):
        return None
    return {
        "artifact": "research/carb_2024_hrs_inuse_field_benchmark_2026_10_08.json",
        "evidence_role": "public real-station HGV 4.3 field benchmark and functional-gap audit",
        "source": {
            key: source.get(key)
            for key in (
                "title", "institution", "url", "publication_date", "test_basis",
            )
        },
        "population": {
            key: population.get(key)
            for key in (
                "stations_tested", "estimated_operational_station_population",
                "sample_fraction", "stations_passing_all_hgv_4_3_tests",
                "stations_passing_all_fault_and_communications_tests",
                "stations_passing_all_nine_fueling_performance_metrics",
                "in_use_protocol_counts",
            )
        },
        "category_station_pass_rates": record.get("category_station_pass_rates") or {},
        "communication_results": (
            (tables.get("communications") or {}).get("results") or {}
        ),
        "general_fault_results": (
            (tables.get("general_fault") or {}).get("results") or {}
        ),
        "digital_twin_functional_coverage": (
            record.get("digital_twin_functional_coverage") or {}
        ),
        "full_loop_external_holdout_eligible": False,
        "dynamic_model_parameter_calibration_eligible": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _public_hytunnel_failure_diagnostic_evidence() -> dict[str, Any] | None:
    """Expose the bounded post-outcome HyTunnel diagnostic to the LLM.

    The public actual-hydrogen archive is useful evidence, but its frozen
    dispersion and local mass-flow claims did not pass the declared joint
    endpoints.  This reader intentionally exposes that negative result and
    the regime/support diagnostics so the assistant cannot turn a partial
    enclosure screen into an HRS consequence-distance validation claim.
    No raw MAT rows or private local-station identifiers are admitted here.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/hytunnel_carpark_failure_regime_diagnostic_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    source = record.get("source") or {}
    regimes = record.get("regimes") or {}
    dispersion = (record.get("holdout_result") or {}).get("dispersion") or {}
    mass_flow = (record.get("holdout_result") or {}).get("mass_flow") or {}
    # The diagnostic stores the frozen result by reference.  Read the result
    # artifact separately so this reader remains robust if a future diagnostic
    # omits the convenience summary fields.
    result_path = Path(__file__).resolve().parents[2] / (
        "research/hytunnel_carpark_holdout_result_2026_10_08.json"
    )
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        result = {}
    evaluation = result.get("evaluation") or {}
    dispersion = evaluation.get("dispersion") or dispersion
    mass_flow = evaluation.get("mass_flow") or mass_flow
    claims = result.get("claims") or {}
    if (
        record.get("artifact_type")
        != "hytunnel_carpark_post_outcome_failure_regime_diagnostic"
        or record.get("post_outcome_diagnostic") is not True
        or record.get("runtime_parameter_application") is not False
        or record.get("default_model_parameters_changed") is not False
        or source.get("dataset_doi") != "10.23642/USN.14405903"
        or not isinstance(regimes.get("short_release_cases"), dict)
        or not isinstance(regimes.get("long_blowdown_cases"), dict)
        or claims.get("well_mixed_sensor_mean_transfer_supported") is True
        or claims.get("local_real_gas_mass_flow_transfer_supported") is True
    ):
        return None
    safe_regime_fields = (
        "case_count", "experiments", "median_sensor_span_s",
        "median_mass_flow_span_s", "median_common_support_duration_s",
        "median_source_to_sensor_end_gap_s", "median_ventilation_m3_h",
        "median_flow_peak_g_s", "common_support_shorter_than_sensor_in_all_cases",
    )
    safe_regimes = {
        name: {
            key: value
            for key, value in group.items()
            if key in safe_regime_fields
        }
        for name, group in regimes.items()
        if isinstance(group, dict)
    }
    return {
        "artifact": "research/hytunnel_carpark_failure_regime_diagnostic_2026_10_09.json",
        "evidence_role": "public actual-hydrogen holdout failure and regime diagnostic",
        "source": {
            key: source.get(key)
            for key in ("dataset_doi", "article_doi", "license")
            if source.get(key) is not None
        },
        "holdout": {
            "dispersion_declared_cases": dispersion.get("eligible_case_count"),
            "dispersion_pass_count": dispersion.get("pass_count"),
            "dispersion_pass_fraction": dispersion.get(
                "pass_fraction_of_declared_cases"
            ),
            "dispersion_joint_screen_pass": dispersion.get("joint_screen_pass") is True,
            "mass_flow_declared_cases": mass_flow.get("eligible_case_count"),
            "mass_flow_pass_count": mass_flow.get("pass_count"),
            "mass_flow_pass_fraction": mass_flow.get(
                "pass_fraction_of_declared_cases"
            ),
            "mass_flow_joint_screen_pass": mass_flow.get("joint_screen_pass") is True,
        },
        "regimes": safe_regimes,
        "findings": [
            {
                "id": str(item.get("id")),
                "finding": str(item.get("finding")),
                "implication": str(item.get("implication")),
            }
            for item in record.get("findings") or []
            if isinstance(item, dict) and item.get("id")
        ],
        "runtime_parameter_application": False,
        "default_model_parameters_changed": False,
        "claim_supported": False,
        "claim_limit": str(record.get("claim_boundary") or result.get("claim_boundary") or ""),
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

    hytunnel = evidence.get("public_hytunnel_failure_diagnostic") or {}
    hytunnel_source = hytunnel.get("source") or {}
    hytunnel_doi = str(hytunnel_source.get("dataset_doi") or "").strip()
    if hytunnel_doi:
        add(
            "PUBLIC_HYTUNNEL_CARPARK_RAW_TIMESERIES",
            "HyTunnel-CS actual-hydrogen mechanically ventilated enclosure dataset",
            f"https://doi.org/{hytunnel_doi}",
            "공개 실제 수소 시계열 holdout 및 모델 한계 진단",
        )

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

    # MetHyTrucks publishes open sampling-system workbooks with a common
    # 0.5-s time base.  The record is useful for instrumentation provenance,
    # but its public metadata do not identify a vehicle/receptacle loop or
    # protocol state.  Keep the DOI discoverable to the assistant while
    # preserving that explicit auxiliary-only boundary.
    public_measurement = evidence.get("public_measurement_instrumentation") or {}
    methytrucks_tank = evidence.get("methytrucks_tank_diagnostic_boundary") or {}
    for source in public_measurement.get("sources") or []:
        if not isinstance(source, dict):
            continue
        doi = str(source.get("doi") or "").strip()
        record_id = str(source.get("record_id") or "").strip()
        if not doi or not record_id:
            continue
        add(
            f"PUBLIC_METHYTRUCKS_{record_id}",
            str(source.get("title") or "MetHyTrucks public measurement dataset"),
            f"https://doi.org/{doi}",
            "공개 HRS 계측·시간축 근거(차량 full-loop 검증 아님)",
        )

    methytrucks_source = methytrucks_tank.get("source") or {}
    dataset_doi = str(methytrucks_source.get("dataset_doi") or "").strip()
    article_doi = str(methytrucks_source.get("article_doi") or "").strip()
    if dataset_doi:
        add(
            "PUBLIC_METHYTRUCKS_HYSAM_TANK_DATA",
            "MetHyTrucks HySaM public measurement data",
            f"https://doi.org/{dataset_doi}",
            "post-access tank diagnostic source; not a prospective holdout",
        )
    if article_doi:
        add(
            "PUBLIC_METHYTRUCKS_HYSAM_ARTICLE",
            "Representative hydrogen sampling at hydrogen refuelling stations",
            f"https://doi.org/{article_doi}",
            "test context and sink geometry source; logger crosswalk unresolved",
        )

    qra = evidence.get("qra_multimethod_comparison") or {}
    qra_source = qra.get("source") or {}
    qra_doi = str(qra_source.get("doi") or "").strip()
    if qra_doi:
        add(
            "PUBLIC_QRA_MULTIMETHOD_DATA3632",
            "Multi-method hydrogen refuelling station QRA benchmark",
            f"https://doi.org/{qra_doi}",
            "simulation-method spread and source-boundary diagnostic; not experimental validation",
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

    operation_practice = evidence.get(
        "public_station_operation_practice_reference"
    ) or {}
    operation_source = operation_practice.get("source") or {}
    add(
        "PUBLIC_STATION_OPERATION_PRACTICE",
        str(
            operation_source.get("title")
            or "Public station operating-practice reference"
        ),
        str(operation_source.get("url") or ""),
        "공개 시설의 정성적 충전 시퀀스·리크체크·예냉 맥락(보편 프로토콜/검증 아님)",
    )

    aggregate_benchmark = evidence.get(
        "public_station_aggregate_benchmark_reference"
    ) or {}
    aggregate_source = aggregate_benchmark.get("source") or {}
    add(
        "PUBLIC_STATION_AGGREGATE_BENCHMARK",
        str(
            aggregate_source.get("title")
            or "Public station aggregate operating benchmark"
        ),
        str(aggregate_source.get("url") or ""),
        "공개 실제 충전소 집계 처리량·에너지 운전 맥락(원시 full-loop 검증 아님)",
    )

    threeemotion_aggregate = evidence.get(
        "public_threeemotion_operating_aggregate_reference"
    ) or {}
    threeemotion_source = threeemotion_aggregate.get("source") or {}
    add(
        "PUBLIC_3EMOTION_STATION_OPERATING_AGGREGATE",
        str(
            threeemotion_source.get("title")
            or "3Emotion station operating aggregate"
        ),
        str(threeemotion_source.get("url") or ""),
        "공개 350 bar 버스 충전소 집계 운전 맥락(원시 full-loop 검증 아님)",
    )

    measurement_leads = evidence.get("public_hrs_measurement_leads") or {}
    for lead in measurement_leads.get("leads") or []:
        if not isinstance(lead, dict):
            continue
        add(
            f"PUBLIC_HRS_MEASUREMENT_LEAD_{lead.get('id')}",
            str(lead.get("title") or "Public HRS measurement lead"),
            str(lead.get("url") or ""),
            "공개 HRS 계측 연구·시설의 측정범위 맥락(원시 trace·full-loop 검증 아님)",
        )

    carb = evidence.get("public_carb_hrs_inuse_field_benchmark") or {}
    carb_source = carb.get("source") or {}
    add(
        "PUBLIC_CARB_2024_HRS_INUSE",
        str(carb_source.get("title") or "CARB 2024 in-use HRS study"),
        str(carb_source.get("url") or ""),
        "22개 실제 충전소 HGV 4.3 고장·통신·충전성능 현장 벤치마크",
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

    incident = evidence.get("public_incident_traceability") or {}
    hiad_source = incident.get("public_source") or {}
    add(
        "PUBLIC_HIAD_2_2",
        str(hiad_source.get("title") or "European Hydrogen Incidents and Accidents Database HIAD 2.2"),
        str(hiad_source.get("official_page") or ""),
        "공개 HIAD 2.2 사고·근접사고 시나리오 근거(정성적·비수치 검증)",
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
    controlled_flare = evidence.get("public_controlled_flare_evidence") or {}
    flare_doi = str(controlled_flare.get("doi") or "").strip()
    if flare_doi:
        add(
            "HYDELTA_FLARE_2026",
            "HyDelta controlled hydrogen flaring experiment",
            f"https://doi.org/{flare_doi}",
            "승인된 제어식 플레어 보호기능·운전경계 근거(일반 벤트 점화 지침 아님)",
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
    reference_detector = evidence.get("public_reference_leak_detector_evidence") or {}
    reference_detector_doi = str(reference_detector.get("doi") or "")
    if reference_detector_doi:
        add(
            "PUBLIC_REFERENCE_LEAK_DETECTOR_DATASET",
            "Physical hydrogen reference-leak detector dataset",
            f"https://doi.org/{reference_detector_doi}",
            "실제 수소 기준누출에 대한 검지기 응답 순서 근거(경보값·공간배치 보정 아님)",
        )
    spatial_stratification = evidence.get(
        "public_actual_hydrogen_spatial_stratification_evidence"
    ) or {}
    spatial_article_doi = str(spatial_stratification.get("article_doi") or "")
    if spatial_article_doi:
        add(
            "PUBLIC_ACTUAL_H2_SPATIAL_STRATIFICATION_ARTICLE",
            "Physical-H2 spatial stratification in an open-ended channel",
            f"https://doi.org/{spatial_article_doi}",
            "밀폐 유사 채널의 천장층·하향 제트 경로 검지기 배치 근거(충전소 배치 검증 아님)",
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
    h2safe_indoor = evidence.get("public_h2safe_indoor_surrogate_evidence") or {}
    add(
        "PUBLIC_H2SAFE_INDOOR_SURROGATE",
        "H2SAFE controlled indoor surrogate-release sensor dataset",
        str(h2safe_indoor.get("catalog_url") or ""),
        "공개 full-scale 실내 대체가스 검지기·좌표·환기 맥락(수소 임계값 보정 아님)",
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


def _confidential_station_recharge_dynamics_evidence() -> dict[str, Any] | None:
    """Expose the multi-trace result even when runtime use is rejected.

    Evidence availability and parameter eligibility are deliberately separate.
    A failed holdout is useful negative evidence for the LLM, but it must never
    be converted into a simulator setting.
    """

    artifact = "research/confidential_station_recharge_dynamics_multitrace_2026_10_08.json"
    path = Path(__file__).resolve().parents[2] / artifact
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        calibration = record["calibration"]
        holdout = record["temporal_holdout"]
        eligibility = record["eligibility"]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    privacy_flags = (
        record.get("source_identifiers_published") is False,
        record.get("raw_rows_persisted") is False,
        record.get("absolute_timestamps_published") is False,
        record.get("source_paths_published") is False,
        record.get("tag_names_published") is False,
        record.get("manufacturer_or_model_published") is False,
    )
    if (
        record.get("artifact_type")
        != "confidential_station_recharge_dynamics_calibration"
        or not all(privacy_flags)
        or not isinstance(calibration.get("files_read"), int)
        or calibration.get("files_read", 0) < 2
        or not isinstance(calibration.get("sampled_rows"), int)
        or calibration.get("sampled_rows", 0) < 1
        or holdout.get("method") != "chronological_within_trace_holdout"
        or eligibility.get("default_model_parameters_changed") is not False
        or eligibility.get("full_station_vehicle_validation") is not False
    ):
        return None
    pressure_path = Path(__file__).resolve().parents[2] / (
        "research/confidential_station_recharge_pressure_drop_diagnostic_2026_10_08.json"
    )
    pressure_band: dict[str, Any] | None = None
    try:
        pressure_record = json.loads(pressure_path.read_text(encoding="utf-8"))
        pressure_observations = pressure_record["observations"]
        pressure_drop = pressure_observations["stop_to_restart_pressure_drop_mpa"]
        pressure_decision = pressure_record["software_decision"]
        pressure_boundary = pressure_record["validation_boundary"]
        if (
            pressure_record.get("artifact_type")
            == "confidential_station_recharge_pressure_drop_diagnostic"
            and pressure_record.get("source_identifiers_published") is False
            and pressure_record.get("raw_rows_persisted") is False
            and pressure_record.get("tag_names_published") is False
            and pressure_observations.get("completed_high_stage_restarts") == 124
            and pressure_drop.get("median") == 4.555
            and pressure_decision.get("high_bank_restart_margin_default_mpa") == 4.5
            and pressure_decision.get("minimum_time_dwell_applied") is False
            and pressure_boundary.get("independent_holdout") is False
            and pressure_boundary.get("full_station_vehicle_validation") is False
        ):
            pressure_band = {
                "artifact": pressure_path.relative_to(
                    Path(__file__).resolve().parents[2]
                ).as_posix(),
                "completed_restarts": pressure_observations.get(
                    "completed_high_stage_restarts"
                ),
                "stop_to_restart_drop_mpa": {
                    "p10": pressure_drop.get("p10"),
                    "median": pressure_drop.get("median"),
                },
                "development_default_mpa": pressure_decision.get(
                    "high_bank_restart_margin_default_mpa"
                ),
                "post_outcome_diagnostic": True,
                "independent_holdout": False,
                "minimum_time_dwell_applied": False,
                "full_station_vehicle_validation": False,
            }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        pass
    return {
        "artifact": artifact,
        "evidence_role": "confidential multi-trace station recharge-dynamics holdout",
        "profile_id": str(
            record.get("profile_id") or "owner_station_recharge_dynamics_multitrace_v1"
        ),
        "files_read": calibration["files_read"],
        "sampled_rows": calibration["sampled_rows"],
        "state_transition_count": calibration.get("state_transition_count"),
        "observed_off_to_on_intervals": calibration.get(
            "observed_off_to_on_intervals"
        ),
        "candidate_minimum_recharge_off_time_s": calibration.get(
            "recommended_minimum_recharge_off_time_s"
        ),
        "temporal_holdout": {
            "method": "chronological_within_trace_holdout",
            "calibration_fraction": holdout.get("calibration_fraction"),
            "files": holdout.get("holdout_files"),
            "sampled_rows": holdout.get("holdout_sampled_rows"),
            "completed_off_to_on_intervals": holdout.get(
                "holdout_completed_off_to_on_intervals"
            ),
            "minimum_off_to_on_s": holdout.get("holdout_minimum_off_to_on_s"),
            "dwell_consistent": holdout.get("dwell_consistent") is True,
        },
        "opt_in_runtime_parameter_available": (
            eligibility.get("runtime_parameter_application") is True
        ),
        "runtime_application_block_reason": eligibility.get(
            "runtime_application_block_reason"
        ),
        "prior_single_trace_profile_superseded": (
            (record.get("validation_decision") or {}).get(
                "prior_single_trace_profile_superseded"
            )
            is True
        ),
        "default_model_parameters_changed": (
            eligibility.get("default_model_parameters_changed") is True
        ),
        "full_station_vehicle_validation": (
            eligibility.get("full_station_vehicle_validation") is True
        ),
        "observed_high_bank_restart_pressure_band": pressure_band,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_cascade_sequence_evidence() -> dict[str, Any] | None:
    """Expose only the privacy-bounded medium/high sequence holdout."""

    root = Path(__file__).resolve().parents[2]
    artifact = "research/confidential_station_cascade_sequence_holdout_2026_10_08.json"
    result_path = root / artifact
    protocol_path = root / (
        "research/confidential_station_cascade_sequence_protocol_2026_10_08.json"
    )
    try:
        record = json.loads(result_path.read_text(encoding="utf-8"))
        calibration = record["calibration"]
        holdout = record["holdout"]
        decision = record["decision"]
        protocol = record["protocol"]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    privacy_keys = (
        "source_identifiers_published",
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "calendar_dates_published",
    )
    try:
        protocol_hash = sha256(protocol_path.read_bytes()).hexdigest()
    except OSError:
        return None
    if (
        record.get("artifact_type")
        != "confidential_station_cascade_sequence_holdout"
        or not all(record.get(key) is False for key in privacy_keys)
        or protocol.get("protocol_sha256") != protocol_hash
        or record.get("files_read") != 12
        or calibration.get("paired_episode_count") != 8_106
        or holdout.get("paired_episode_count") != 3_664
        or decision.get("cascade_controller_structure_supported") is not True
        or decision.get("runtime_parameter_application") is not False
        or decision.get("vehicle_fill_validation") is not False
        or decision.get("full_loop_holdout_eligible") is not False
        or decision.get("independent_external_validation") is not False
    ):
        return None
    return {
        "artifact": artifact,
        "evidence_role": "confidential same-site medium/high pressure sequence holdout",
        "files_read": record.get("files_read"),
        "calibration": {
            key: calibration.get(key)
            for key in (
                "high_cycle_count", "paired_episode_count",
                "pair_coverage_fraction", "sequential_fraction", "handoff_gap_s",
            )
        },
        "holdout": {
            key: holdout.get(key)
            for key in (
                "high_cycle_count", "paired_episode_count",
                "pair_coverage_fraction", "sequential_fraction", "handoff_gap_s",
            )
        },
        "cascade_controller_structure_supported": True,
        "runtime_parameter_application": False,
        "vehicle_fill_validation": False,
        "full_loop_holdout_eligible": False,
        "independent_external_validation": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_recharge_pressure_forecast_evidence() -> dict[str, Any] | None:
    """Expose the frozen same-site short-horizon forecast without case rows."""

    root = Path(__file__).resolve().parents[2]
    artifact = (
        "research/confidential_station_recharge_pressure_forecast_holdout_"
        "2026_10_08.json"
    )
    result_path = root / artifact
    protocol_path = root / (
        "research/confidential_station_recharge_pressure_forecast_protocol_"
        "2026_10_08.json"
    )
    try:
        record = json.loads(result_path.read_text(encoding="utf-8"))
        calibration = record["calibration"]
        holdout = record["holdout"]
        decision = record["decision"]
        protocol = record["protocol"]
        protocol_hash = sha256(protocol_path.read_bytes()).hexdigest()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    privacy_keys = (
        "source_identifiers_published",
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "calendar_dates_published",
        "tag_names_published",
        "manufacturer_or_model_published",
    )
    if (
        record.get("artifact_type")
        != "confidential_station_recharge_pressure_forecast_holdout"
        or not all(record.get(key) is False for key in privacy_keys)
        or protocol.get("protocol_sha256") != protocol_hash
        or record.get("files_read") != 8
        or calibration.get("case_count") != 1_024
        or holdout.get("case_count") != 394
        or not all((record.get("eligibility") or {}).values())
        or not all((record.get("screens") or {}).values())
        or decision.get("short_horizon_station_pressure_forecast_supported")
        is not True
        or decision.get("runtime_parameter_application") is not False
        or decision.get("default_model_parameters_changed") is not False
        or decision.get("vehicle_fill_validation") is not False
        or decision.get("full_loop_holdout_eligible") is not False
        or decision.get("independent_external_validation") is not False
    ):
        return None
    combined = holdout.get("combined") or {}
    return {
        "artifact": artifact,
        "evidence_role": (
            "confidential same-site short-horizon storage-pressure forecast holdout"
        ),
        "files_read": record.get("files_read"),
        "sampled_rows": record.get("sampled_rows"),
        "calibration_case_count": calibration.get("case_count"),
        "holdout_case_count": holdout.get("case_count"),
        "fitted_continuation_gain_by_bank": calibration.get(
            "fitted_continuation_gain_by_bank"
        ) or {},
        "holdout_metrics": {
            key: combined.get(key)
            for key in (
                "mae_mpa", "median_absolute_error_mpa",
                "p90_absolute_error_mpa", "persistence_mae_mpa",
                "mae_improvement_over_persistence_fraction",
                "mae_improvement_over_uncalibrated_prefix_fraction",
                "positive_direction_fraction",
            )
        },
        "short_horizon_station_pressure_forecast_supported": True,
        "runtime_parameter_application": False,
        "default_model_parameters_changed": False,
        "vehicle_fill_validation": False,
        "full_loop_holdout_eligible": False,
        "independent_external_validation": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_lifecycle_pressure_alignment_evidence() -> dict[str, Any] | None:
    """Expose the retained negative lifecycle/pressure alignment holdout."""

    root = Path(__file__).resolve().parents[2]
    artifact = (
        "research/confidential_station_lifecycle_pressure_alignment_holdout_"
        "2026_10_09.json"
    )
    result_path = root / artifact
    protocol_path = root / (
        "research/confidential_station_lifecycle_pressure_alignment_protocol_"
        "2026_10_08.json"
    )
    try:
        record = json.loads(result_path.read_text(encoding="utf-8"))
        calibration = record["calibration"]
        holdout = record["holdout"]
        eligibility = record["eligibility"]
        screens = record["screens"]
        decision = record["decision"]
        protocol = record["protocol"]
        protocol_hash = sha256(protocol_path.read_bytes()).hexdigest()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    privacy_keys = (
        "source_identifiers_published",
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "per_file_hashes_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "calendar_dates_published",
        "site_company_location_manufacturer_published",
    )
    files = record.get("files") or {}
    rows = record.get("rows") or {}
    calibration_combined = calibration.get("combined") or {}
    holdout_combined = holdout.get("combined") or {}
    if (
        record.get("artifact_type")
        != "confidential_station_lifecycle_pressure_alignment_holdout"
        or not all(privacy.get(key) is False for key in privacy_keys)
        or protocol.get("protocol_sha256") != protocol_hash
        or files.get("pressure_files_read") != 12
        or files.get("counter_files_read") != 12
        or files.get("exact_duplicate_files_excluded") != 1
        or rows.get("pressure_rows_read") != 29_361_281
        or rows.get("counter_rows_read") != 26_839_420
        or calibration_combined.get("counter_event_recall") != 0.170591
        or holdout_combined.get("counter_event_recall") != 0.196032
        or holdout_combined.get("pressure_event_precision") != 0.902716
        or eligibility.get("counter_monotonicity_met") is not False
        or screens.get("holdout_counter_recall_met") is not False
        or screens.get("recall_stability_met") is not False
        or decision.get("pressure_completion_counter_alignment_supported")
        is not False
        or decision.get("recharge_event_detector_corroborated") is not False
        or any(
            decision.get(key) is not False
            for key in (
                "runtime_parameter_application",
                "default_model_parameters_changed",
                "vehicle_fill_validation",
                "full_loop_holdout_eligible",
                "independent_external_validation",
            )
        )
    ):
        return None
    return {
        "artifact": artifact,
        "evidence_role": (
            "retained negative same-site lifecycle-counter and storage-pressure "
            "alignment holdout"
        ),
        "files": files,
        "rows": rows,
        "counter_quality": record.get("counter_quality") or {},
        "calibration": {
            "combined": calibration_combined,
            "by_bank": calibration.get("by_bank") or {},
        },
        "holdout": {
            "combined": holdout_combined,
            "by_bank": holdout.get("by_bank") or {},
        },
        "recall_shift_by_bank": (
            (record.get("metrics") or {}).get("recall_shift_by_bank") or {}
        ),
        "eligibility": eligibility,
        "screens": screens,
        "pressure_completion_counter_alignment_supported": False,
        "recharge_event_detector_corroborated": False,
        "runtime_parameter_application": False,
        "default_model_parameters_changed": False,
        "vehicle_fill_validation": False,
        "full_loop_holdout_eligible": False,
        "independent_external_validation": False,
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


def _confidential_station_thermal_evidence() -> dict[str, Any] | None:
    """Expose attestation status and, when available, thermal diagnostics.

    The pending review is useful decision context: it prevents an assistant
    from presenting mapped compressor/cooler temperatures as validated
    boundaries.  A future completed result is accepted only when its privacy
    controls and attestation-gated artifact type are intact.
    """

    root = Path(__file__).resolve().parents[2]
    request_path = root / (
        "research/confidential_station_equipment_attestation_request_2026_10_08.json"
    )
    protocol_path = root / (
        "research/confidential_station_thermal_dynamics_protocol_2026_10_08.json"
    )
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy_flags = (
        "source_identifiers_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "tag_names_published",
        "source_paths_published",
    )
    privacy = protocol.get("privacy_controls") or {}
    if (
        request.get("artifact_type")
        != "confidential_station_attestation_request_status"
        or any(request.get(key) is not False for key in privacy_flags)
        or protocol.get("protocol_id")
        != "CONFIDENTIAL-STATION-THERMAL-DYNAMICS-001"
        or any(privacy.get(key) is not False for key in privacy_flags)
        or privacy.get("company_location_date_manufacturer_published") is not False
    ):
        return None
    base: dict[str, Any] = {
        "artifact": str(request_path.relative_to(root)).replace("\\", "/"),
        "protocol": str(protocol_path.relative_to(root)).replace("\\", "/"),
        "evidence_role": str(protocol.get("evidence_role") or ""),
        "status": str(request.get("review_status") or "UNCONFIRMED"),
        "mapped_channel_family_counts": dict(
            request.get("mapped_channel_family_counts") or {}
        ),
        "proposed_engineering_units": dict(
            request.get("proposed_engineering_units") or {}
        ),
        "proposals_attested": (
            (protocol.get("generic_component_mapping") or {}).get(
                "proposals_are_attested"
            ) is True
        ),
        "confirmation_required": dict(request.get("confirmation_required") or {}),
        "result_available": False,
        "station_component_thermal_envelope_supported": False,
        "runtime_parameter_application": False,
        "vehicle_fill_thermal_validation": False,
        "full_station_vehicle_validation": False,
        "full_loop_holdout_eligible": False,
        "default_model_parameters_changed": False,
        "claim_limit": str(request.get("claim_boundary") or ""),
    }
    result_path = root / (
        "research/confidential_station_thermal_dynamics_diagnostic_2026_10_08.json"
    )
    if not result_path.is_file():
        return base
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return base
    attestation = result.get("channel_attestation") or {}
    required_attestations = (
        "timebase_semantics_attested",
        "temperature_role_and_unit_semantics_attested",
        "state_semantics_attested",
        "calibration_metadata_attested",
    )
    if (
        result.get("artifact_type")
        != "confidential_station_thermal_dynamics_diagnostic"
        or result.get("status") != "completed_attested_within_trace_diagnostic"
        or any(result.get(key) is not False for key in privacy_flags)
        or result.get("manufacturer_or_model_published") is not False
        or any(attestation.get(key) is not True for key in required_attestations)
        or any(attestation.get(key) is not False for key in privacy_flags)
    ):
        return base
    eligibility = result.get("eligibility") or {}
    stability = result.get("temporal_stability") or {}
    base.update({
        "artifact": str(result_path.relative_to(root)).replace("\\", "/"),
        "status": str(result.get("status") or ""),
        "result_available": True,
        "channel_attestation": {
            key: attestation.get(key) is True
            for key in (
                "timebase_semantics_attested",
                "temperature_role_and_unit_semantics_attested",
                "state_semantics_attested",
                "calibration_metadata_attested",
            )
        },
        "temporal_stability": {
            key: stability.get(key)
            for key in (
                "method", "calibration_fraction",
                "component_medians_inside_calibration_p05_p95",
                "cooler_active_drop_median_inside_calibration_p05_p95",
                "minimum_holdout_rows_met", "stability_supported",
            )
            if stability.get(key) is not None
        },
        "station_component_thermal_envelope_supported": (
            eligibility.get("station_component_thermal_envelope_supported") is True
        ),
        "runtime_parameter_application": (
            eligibility.get("runtime_parameter_application") is True
        ),
        "vehicle_fill_thermal_validation": (
            eligibility.get("vehicle_fill_thermal_validation") is True
        ),
        "full_station_vehicle_validation": (
            eligibility.get("full_station_vehicle_validation") is True
        ),
        "full_loop_holdout_eligible": (
            eligibility.get("full_loop_holdout_eligible") is True
        ),
        "default_model_parameters_changed": (
            eligibility.get("default_model_parameters_changed") is True
        ),
        "claim_limit": str(result.get("claim_boundary") or ""),
    })
    return base


def _confidential_bank_pressure_evidence() -> dict[str, Any] | None:
    """Expose anonymized medium/high-bank pressure envelopes to the LLM.

    The artifact is derived from owner-controlled logs, but contains no raw
    rows, tags, dates, site names or equipment identifiers.  It is deliberately
    diagnostic-only: the LLM may use it to explain plausibility and observed
    ranges, while the simulator keeps its reference controller parameters.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_bank_role_pressure_envelopes_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.get("artifact_type") != "confidential_bank_role_pressure_envelopes"
        or record.get("evidence_role")
        != "privacy_bounded_bank_role_pressure_diagnostic"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("exact_source_dates_published") is not False
        or record.get("tag_names_published") is not False
        or record.get("manufacturer_or_model_published") is not False
    ):
        return None
    attestation = record.get("attestation") or {}
    eligibility = record.get("eligibility") or {}
    profiles: list[dict[str, Any]] = []
    for profile in record.get("profiles") or []:
        if not isinstance(profile, dict):
            continue
        banks: dict[str, Any] = {}
        for role in ("medium_storage_pressure", "high_storage_pressure"):
            value = (profile.get("bank_roles") or {}).get(role)
            if not isinstance(value, dict):
                continue
            pressure = value.get("pressure_mpa") or {}
            banks[role] = {
                "sampled_rows": value.get("sampled_rows"),
                "pressure_mpa": {
                    key: pressure.get(key)
                    for key in ("p05", "median", "p95")
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
        if banks:
            profiles.append({
                "profile_id": str(profile.get("profile_id") or ""),
                "sampled_rows": profile.get("sampled_rows"),
                "bank_roles": banks,
            })
    if not profiles:
        return None
    return {
        "artifact": "research/confidential_bank_role_pressure_envelopes_2026_10_06.json",
        "evidence_role": str(record.get("evidence_role") or ""),
        "profiles": profiles,
        "bank_role_mapping_attested": attestation.get(
            "bank_role_mapping_attested"
        ) is True,
        "pressure_scale_mapping_attested": attestation.get(
            "pressure_scale_mapping_attested"
        ) is True,
        "machine_readable_unit_dictionary_present": attestation.get(
            "machine_readable_unit_dictionary_present"
        ) is True,
        "temperature_or_flow_roles_attested": attestation.get(
            "temperature_or_flow_roles_attested"
        ) is True,
        "bank_role_pressure_diagnostic_supported": eligibility.get(
            "bank_role_pressure_diagnostic_supported"
        ) is True,
        "runtime_parameter_application": eligibility.get(
            "runtime_parameter_application"
        ) is True,
        "full_station_vehicle_validation": eligibility.get(
            "full_station_vehicle_validation"
        ) is True,
        "full_loop_holdout_eligible": eligibility.get(
            "full_loop_holdout_eligible"
        ) is True,
        "default_model_parameters_changed": eligibility.get(
            "default_model_parameters_changed"
        ) is True,
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


def _confidential_operational_profile_recheck() -> dict[str, Any] | None:
    """Expose the fresh aggregate/profile consistency check to the LLM.

    This is provenance evidence only.  A match confirms that the owner-side
    recheck reproduces the committed station-boundary profile; it does not
    add vehicle channels or turn the profile into a full-loop validation.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_operational_profile_recheck_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    comparison = record.get("committed_profile_comparison") or {}
    runtime = record.get("runtime_decision") or {}
    fresh = record.get("fresh_calibration") or {}
    if (
        record.get("artifact_type") != "confidential_operational_envelope_recheck"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("exact_source_dates_published") is not False
        or record.get("source_paths_published") is not False
        or comparison.get("matches") is not True
        or runtime.get("committed_profile_replaced") is not False
        or runtime.get("default_model_parameters_changed") is not False
        or runtime.get("measured_boundary_calibration_remains_opt_in") is not True
    ):
        return None
    return {
        "artifact": "research/confidential_operational_profile_recheck_2026_10_06.json",
        "evidence_role": "confidential operational-profile consistency recheck",
        "profile_match": True,
        "fields_compared": list(comparison.get("fields_compared") or []),
        "fields_omitted_without_attestation": list(
            comparison.get("fields_omitted_without_attestation") or []
        ),
        "sampled_rows": fresh.get("sampled_rows"),
        "channel_roles": list(fresh.get("channel_roles") or []),
        "committed_profile_replaced": False,
        "measured_boundary_calibration_remains_opt_in": True,
        "full_station_vehicle_validation": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_station_channel_quality_recheck() -> dict[str, Any] | None:
    """Expose station-channel quality aggregates without implying calibration.

    Temperature, flow and state channels are useful for intake planning, but
    their units and semantics remain unconfirmed.  Keeping this evidence
    separate from runtime calibration prevents the LLM from presenting a
    quality screen as a full-loop measurement result.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_station_channel_quality_recheck_2026_10_06.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    eligibility = record.get("eligibility") or {}
    if (
        record.get("artifact_type") != "confidential_station_channel_quality_recheck"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("exact_source_dates_published") is not False
        or record.get("source_paths_published") is not False
        or eligibility.get("station_channel_quality_recheck_supported") is not True
        or eligibility.get("temperature_or_flow_parameter_fit_supported") is not False
        or eligibility.get("full_station_vehicle_validation") is not False
        or eligibility.get("full_loop_holdout_eligible") is not False
    ):
        return None
    return {
        "artifact": "research/confidential_station_channel_quality_recheck_2026_10_06.json",
        "evidence_role": "confidential station-channel quality recheck",
        "files_read": record.get("files_read"),
        "sampled_rows": record.get("sampled_rows"),
        "parseable_timestamp_fraction": record.get("parseable_timestamp_fraction"),
        "timebase": record.get("timebase") or {},
        "roles": record.get("roles") or {},
        "discrete_state_transition_count": record.get(
            "discrete_state_transition_count"
        ),
        "temperature_or_flow_parameter_fit_supported": False,
        "full_station_vehicle_validation": False,
        "full_loop_holdout_eligible": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_station_signal_consistency_evidence() -> dict[str, Any] | None:
    """Expose the bounded flow/totalizer consistency screen.

    The archive contains recurring station-side signal relationships, but the
    custodian has not yet attested channel roles, engineering units, reset
    semantics or calibration.  Keeping this as a *candidate* evidence class
    lets the assistant explain why a flow-related question has useful local
    support without turning correlation into an absolute mass-flow model.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_station_signal_consistency_screen_2026_10_08.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    screen = record.get("screen") or {}
    aggregate = screen.get("candidate_pair_aggregate") or {}
    strong = screen.get("strong_pair_aggregate") or {}
    attestation = record.get("attestation") or {}
    eligibility = record.get("eligibility") or {}
    required_privacy = (
        "source_identifiers_published", "source_paths_published",
        "filenames_published", "tag_names_published", "raw_rows_persisted",
        "exact_timestamps_published", "manufacturer_or_model_published",
    )
    if (
        record.get("schema_version") != 1
        or record.get("artifact_type")
        != "confidential_station_signal_consistency_screen"
        or record.get("analysis_status")
        != "pre_attestation_internal_consistency_screen"
        or not all(privacy.get(key) is False for key in required_privacy)
        or screen.get("candidate_pairs_evaluated") != 54
        or screen.get("strong_consistency_pairs") != 27
        or screen.get("files_with_strong_consistency_pair") != 17
        or eligibility.get("flow_channel_pair_attestation_candidate") is not True
        or eligibility.get("absolute_mass_flow_supported") is not False
        or eligibility.get("conditional_bank_inventory_estimation_supported") is not False
        or eligibility.get("full_station_vehicle_validation") is not False
        or eligibility.get("independent_holdout") is not False
        or any(attestation.get(key) is not False for key in (
            "channel_roles_attested", "flow_units_attested",
            "totalizer_reset_semantics_attested", "calibration_status_attested",
        ))
    ):
        return None
    return {
        "artifact": "research/confidential_station_signal_consistency_screen_2026_10_08.json",
        "evidence_role": "confidential station-side flow/totalizer consistency candidate",
        "analysis_status": record.get("analysis_status"),
        "candidate_pairs_evaluated": screen.get("candidate_pairs_evaluated"),
        "strong_consistency_pairs": screen.get("strong_consistency_pairs"),
        "files_with_strong_consistency_pair": screen.get(
            "files_with_strong_consistency_pair"
        ),
        "candidate_pair_aggregate": {
            key: aggregate.get(key)
            for key in (
                "correlation_median", "correlation_max",
                "normalized_rmse_percent_median", "active_samples_median",
            )
            if aggregate.get(key) is not None
        },
        "strong_pair_aggregate": {
            key: strong.get(key)
            for key in (
                "correlation_median", "correlation_p10", "correlation_p90",
                "normalized_rmse_percent_median",
                "normalized_rmse_percent_p90",
                "derivative_to_signal_scale_median",
                "aggregation_window_seconds_median",
            )
            if strong.get(key) is not None
        },
        "channel_roles_attested": False,
        "flow_units_attested": False,
        "totalizer_reset_semantics_attested": False,
        "calibration_status_attested": False,
        "flow_parameter_fit_supported": False,
        "absolute_mass_flow_supported": False,
        "full_station_vehicle_validation": False,
        "independent_holdout": False,
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


def _confidential_local_station_utilization_evidence() -> dict[str, Any] | None:
    """Expose aggregate local-station utilization without raw provenance.

    The inventory is intentionally separate from channel-schema intake.  It
    tells the assistant how much station-side evidence actually contributed to
    the reviewed analyses, while preserving the boundary that vehicle-side
    full-loop validation is not available.  No path, filename, header, date or
    row is allowed through this function.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/local_confidential_station_data_utilization_2026_10_08.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    inventory = record.get("inventory") or {}
    utilization = record.get("utilization") or {}
    semantic_attestation = utilization.get("semantic_attestation") or {}
    assessment = record.get("assessment") or {}
    required_privacy = (
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "per_file_hashes_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "site_company_manufacturer_published",
    )
    if (
        record.get("artifact_type") != "local_confidential_station_data_utilization_audit"
        or not all(privacy.get(key) is False for key in required_privacy)
        or inventory.get("csv_files") != 33
        or inventory.get("unique_csv_payloads") != 32
        or inventory.get("deduplicated_data_rows") != 56_854_143
        or utilization.get("station_side_evidence_is_substantial") is not True
        or utilization.get("independent_full_loop_vehicle_validation_complete") is not False
        or assessment.get("local_station_data_is_sparse") is not False
        or assessment.get("station_side_dynamic_validation_ready") is not True
        or assessment.get("vehicle_side_full_loop_validation_ready") is not False
    ):
        return None
    return {
        "artifact": "research/local_confidential_station_data_utilization_2026_10_08.json",
        "evidence_role": "privacy-bounded aggregate local station-data utilization",
        "inventory": {
            key: inventory.get(key)
            for key in (
                "csv_files", "total_csv_gib", "physical_data_rows_after_one_header_per_file",
                "unique_csv_payloads", "redundant_csv_files", "duplicate_rows",
                "deduplicated_data_rows", "narrow_schema_files", "wide_schema_files",
                "schema_width_file_counts", "header_family_screen",
            )
        },
        "utilization": {
            key: utilization.get(key)
            for key in (
                "ordered_high_bank_pressure_cycles",
                "paired_medium_high_pressure_episodes",
                "sequential_medium_high_pressure_episodes",
                "short_horizon_pressure_forecast_cases",
                "conditional_recharge_flow_episodes",
                "strong_instantaneous_totalizer_consistency_pairs",
                "station_side_evidence_is_substantial",
                "independent_full_loop_vehicle_validation_complete",
            )
        },
        "semantic_attestation": {
            key: semantic_attestation.get(key)
            for key in (
                "storage_pressure_role_count",
                "lifecycle_counter_role_count",
                "storage_pressure_units_attested",
                "lifecycle_counter_event_definition_attested",
                "flow_units_attested",
                "totalizer_reset_semantics_attested",
                "vehicle_side_channels_attested",
            )
            if semantic_attestation.get(key) is not None
        },
        "assessment": {
            key: assessment.get(key)
            for key in (
                "local_station_data_is_sparse",
                "station_side_dynamic_validation_ready",
                "station_side_longitudinal_analysis_ready",
                "vehicle_side_full_loop_validation_ready",
                "primary_limit",
            )
        },
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_cross_station_bundle_recheck_evidence() -> dict[str, Any] | None:
    """Expose the cross-station station-side data-quality recheck.

    Only aggregate counts and qualitative family presence are made available
    to the assistant. This is a transfer candidate, not vehicle-side
    validation, and it must not retune runtime parameters.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/local_cross_station_bundle_recheck_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    bundles = record.get("bundles") or []
    if (
        record.get("schema_version") != 1
        or record.get("artifact_type") != "confidential_cross_station_bundle_recheck"
        or record.get("bundle_count") != 2
        or len(bundles) != 2
        or record.get("station_side_transfer_candidate") is not True
        or record.get("full_loop_external_validation_supported") is not False
        or record.get("quantitative_consequence_validation_supported") is not False
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("exact_source_dates_published") is not False
        or record.get("manufacturer_or_model_published") is not False
        or record.get("tag_names_published") is not False
        or not all(
            item.get("timestamp_parse_rate_min") == 1.0
            and item.get("ordered_timestamp_file_count") == item.get("file_count")
            and (item.get("family_presence_file_counts") or {}).get("pressure", 0) > 0
            and (item.get("family_presence_file_counts") or {}).get("control_state", 0) > 0
            for item in bundles
        )
    ):
        return None
    return {
        "artifact": "research/local_cross_station_bundle_recheck_2026_10_09.json",
        "evidence_role": "privacy-bounded cross-station station-side transfer candidate",
        "bundle_count": 2,
        "bundles": [
            {
                "id": item.get("id"),
                "file_count": item.get("file_count"),
                "data_rows": item.get("data_rows"),
                "timestamp_parse_rate_min": item.get("timestamp_parse_rate_min"),
                "ordered_timestamp_file_count": item.get("ordered_timestamp_file_count"),
                "timestamp_directions": list(item.get("timestamp_directions") or []),
                "family_presence_file_counts": dict(
                    item.get("family_presence_file_counts") or {}
                ),
            }
            for item in bundles
        ],
        "station_side_transfer_candidate": True,
        "full_loop_external_validation_supported": False,
        "quantitative_consequence_validation_supported": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _local_station_cross_bundle_transfer_evidence() -> dict[str, Any] | None:
    """Expose the privacy-bounded numerical station-side transfer diagnostic.

    The result is intentionally routed as corroboration for a fixed pressure
    cycle candidate only.  It is never promoted to a vehicle/full-loop or
    safety-limit claim, and raw local files remain outside the repository.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/local_station_cross_bundle_transfer_result_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy_keys = (
        "source_identifiers_published",
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "calendar_dates_published",
    )
    decision = record.get("decision") or {}
    if (
        record.get("schema_version") != 1
        or record.get("artifact_type")
        != "local_station_cross_bundle_pressure_transfer_diagnostic"
        or any(record.get(key) is not False for key in privacy_keys)
        or record.get("normalization", {}).get("pressure_unit") != "MPa"
        or record.get("method", {}).get("outcome_used_for_fit") is not False
        or decision.get("independent_external_validation") is not False
        or decision.get("full_loop_vehicle_validation") is not False
        or decision.get("safety_limit_or_field_certification") is not False
        or decision.get("runtime_parameter_application") is not False
        or not isinstance(record.get("transfer_bundle"), dict)
        or not isinstance(record.get("metrics"), dict)
    ):
        return None
    calibration = record.get("calibration_bundle") or {}
    transfer = record.get("transfer_bundle") or {}
    calibration_cycles = calibration.get("cycles") or {}
    transfer_cycles = transfer.get("cycles") or {}
    return {
        "artifact": "research/local_station_cross_bundle_transfer_result_2026_10_09.json",
        "evidence_role": "privacy-bounded station-side cross-bundle transfer diagnostic",
        "candidate_margin_mpa": record.get("method", {}).get("candidate_margin_mpa"),
        "calibration_bundle": {
            "file_count": calibration.get("files_read"),
            "cycle_count": calibration_cycles.get("count"),
            "median_pressure_drop_mpa": calibration_cycles.get("median"),
        },
        "transfer_bundle": {
            "file_count": transfer.get("files_read"),
            "files_with_cycles": transfer.get("files_with_cycles"),
            "cycle_count": transfer_cycles.get("count"),
            "p05_pressure_drop_mpa": transfer_cycles.get("p05"),
            "median_pressure_drop_mpa": transfer_cycles.get("median"),
            "p95_pressure_drop_mpa": transfer_cycles.get("p95"),
        },
        "candidate_relative_transfer_median_error_percent": (
            record.get("metrics", {}).get(
                "candidate_relative_transfer_median_error_percent"
            )
        ),
        "candidate_inside_transfer_p05_p95": (
            record.get("screens", {}).get("candidate_inside_transfer_p05_p95")
            is True
        ),
        "fixed_candidate_corroborated_on_transfer_bundle": (
            decision.get("fixed_candidate_corroborated_on_transfer_bundle")
            is True
        ),
        "full_loop_external_validation_supported": False,
        "runtime_parameter_application": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _local_station_asset_screen_evidence() -> dict[str, Any] | None:
    """Expose the de-identified local scenario/asset screen to the assistant.

    The source record is an aggregate inventory of local operational tables,
    trend workbooks and engineering references.  It deliberately contains no
    source path, tag, filename, date, site or raw row.  The assistant may use
    it to choose qualitative HAZOP/action families, but it must not turn the
    scenario counts into incident frequencies, safety limits or full-loop
    validation claims.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/local_station_asset_screen_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    coverage = record.get("coverage_assessment") or {}
    bundles = record.get("station_specific_bundles") or []
    matrix = next(
        (item for item in bundles
         if item.get("id") == "local_liquid_hydrogen_operational_scenario_matrix"),
        None,
    )
    if (
        record.get("artifact_type") != "local_station_asset_screen"
        or not all(
            privacy.get(key) is False
            for key in (
                "source_paths_published",
                "source_filenames_published",
                "source_headers_published",
                "site_company_manufacturer_published",
                "raw_rows_persisted",
                "per_file_hashes_published",
            )
        )
        or not isinstance(matrix, dict)
        or matrix.get("scenario_step_rows") != 52
        or coverage.get("local_station_data_is_sparse") is not False
        or coverage.get("local_hazop_scenario_coverage_is_substantial") is not True
        or coverage.get("vehicle_side_full_loop_validation_ready") is not False
        or coverage.get("quantitative_consequence_validation_ready") is not False
    ):
        return None
    return {
        "artifact": "research/local_station_asset_screen_2026_10_09.json",
        "evidence_role": "privacy-bounded local operational scenario and asset coverage",
        "scenario_matrix": {
            "scenario_step_rows": matrix.get("scenario_step_rows"),
            "column_count": matrix.get("column_count"),
            "nonempty_consequence_fields": matrix.get("nonempty_consequence_fields") or {},
            "referenced_standard_families": matrix.get("referenced_standard_families") or {},
            "eligible_use": matrix.get("eligible_use") or [],
            "ineligible_use": matrix.get("ineligible_use") or [],
        },
        "asset_bundles": {
            item.get("id"): {
                key: item.get(key)
                for key in (
                    "workbook_count", "sheet_count", "nonempty_rows",
                    "repeated_operation_cycles", "file_count", "document_count",
                    "pdf_count", "image_count", "video_count",
                )
                if item.get(key) is not None
            }
            for item in bundles
            if item.get("id") != "local_liquid_hydrogen_operational_scenario_matrix"
        },
        "coverage": {
            key: coverage.get(key)
            for key in (
                "local_station_data_is_sparse",
                "station_side_dynamic_evidence_is_substantial",
                "local_hazop_scenario_coverage_is_substantial",
                "vehicle_side_full_loop_validation_ready",
                "quantitative_consequence_validation_ready",
                "main_limit",
            )
        },
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _local_hydrogen_station_discovery_evidence() -> dict[str, Any] | None:
    """Expose the bounded local-data discovery result to the LLM.

    This is deliberately a discovery/coverage record rather than a second
    telemetry source.  It lets the assistant answer whether local station
    data are sparse and how they may be used, while keeping source paths,
    filenames, headers, dates, site identity and raw rows out of prompts.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/local_hydrogen_station_data_discovery_recheck_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    groups = {
        item.get("id"): item
        for item in record.get("candidate_groups") or []
        if isinstance(item, dict) and item.get("id")
    }
    measured = groups.get("confidential_station_measurement_bundle") or {}
    coverage = record.get("coverage_assessment") or {}
    header_recheck = record.get("independent_header_recheck") or {}
    header_counts = header_recheck.get("candidate_file_counts") or {}
    required_privacy = (
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "site_company_manufacturer_published",
        "calendar_dates_published",
        "raw_rows_persisted",
        "per_file_hashes_published",
    )
    if (
        record.get("artifact_type") != "local_hydrogen_station_data_discovery_recheck"
        or not all(privacy.get(key) is False for key in required_privacy)
        or measured.get("file_count") != 33
        or measured.get("deduplicated_rows") != 56_854_143
        or coverage.get("local_station_data_is_sparse") is not False
        or coverage.get("station_side_dynamic_evidence_is_substantial") is not True
        or coverage.get("vehicle_side_full_loop_validation_ready") is not False
        or coverage.get("quantitative_consequence_validation_ready") is not False
        or header_recheck.get("files_screened") != 33
        or header_recheck.get("schema_widths") != {"9": 25, "64": 8}
        or header_counts.get("vehicle_or_dispenser_expanded") != 0
        or header_counts.get("vehicle_pressure_temperature_expanded") != 0
    ):
        return None

    safe_group_fields = (
        "evidence_class",
        "file_count",
        "csv_gib",
        "physical_rows",
        "deduplicated_rows",
        "scenario_step_rows",
        "operation_workbook_rows",
        "minute_trend_rows",
        "timestamp_differential_rows",
        "recovered_storage_rows",
        "document_count",
        "image_count",
        "video_count",
        "raw_machine_readable_trace_available",
        "independence",
        "eligible_use",
        "ineligible_use",
        "claim_boundary",
    )
    safe_groups: dict[str, dict[str, Any]] = {}
    for group_id, group in groups.items():
        safe_groups[group_id] = {
            key: group.get(key)
            for key in safe_group_fields
            if group.get(key) is not None
        }

    # Keep the newly identified adjacent operational telemetry in the same
    # privacy-bounded discovery envelope.  It is useful for upstream/site-
    # utility context, but the explicit boundary prevents the assistant from
    # presenting it as a station-to-vehicle refueling trace.
    adjacent_path = Path(__file__).resolve().parents[2] / (
        "research/local_adjacent_h2_operational_data_recheck_2026_10_09.json"
    )
    try:
        adjacent_record = json.loads(
            adjacent_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, json.JSONDecodeError):
        adjacent_record = None
    adjacent_privacy = (adjacent_record or {}).get("privacy") or {}
    adjacent_inventory = (adjacent_record or {}).get("inventory") or {}
    adjacent_coverage = (adjacent_record or {}).get("coverage_assessment") or {}
    adjacent_required_privacy = (
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "site_company_manufacturer_published",
        "calendar_dates_published",
        "raw_rows_persisted",
        "per_file_hashes_published",
    )
    if (
        (adjacent_record or {}).get("artifact_type")
        == "local_adjacent_h2_operational_data_recheck"
        and all(adjacent_privacy.get(key) is False for key in adjacent_required_privacy)
        and adjacent_inventory.get("telemetry_rows") == 2_410_985
        and adjacent_inventory.get("telemetry_signal_key_count") == 273
        and adjacent_coverage.get("local_hydrogen_operational_data_is_abundant") is True
        and adjacent_coverage.get("station_to_vehicle_full_loop_ready") is False
    ):
        safe_groups["adjacent_h2_operational_telemetry"] = {
            "evidence_class": (adjacent_record or {}).get("evidence_class"),
            "telemetry_file_count": adjacent_inventory.get("telemetry_file_count"),
            "telemetry_rows": adjacent_inventory.get("telemetry_rows"),
            "telemetry_signal_key_count": adjacent_inventory.get(
                "telemetry_signal_key_count"
            ),
            "telemetry_time_span_hours": adjacent_inventory.get(
                "telemetry_time_span_hours"
            ),
            "signal_families": adjacent_inventory.get("signal_families") or [],
            "static_engineering_workbook_count": adjacent_inventory.get(
                "static_engineering_workbook_count"
            ),
            "eligible_use": (adjacent_record or {}).get("eligible_use") or [],
            "ineligible_use": (adjacent_record or {}).get("ineligible_use") or [],
            "claim_boundary": (adjacent_record or {}).get("claim_boundary"),
        }

    # Keep the wide station-equipment logger as a distinct evidence class.
    # It is useful for pressure/temperature/state continuity, but its flow
    # units and vehicle-side coverage are not attested.  Never pass tags,
    # paths, dates or raw rows to the model.
    wide_path = Path(__file__).resolve().parents[2] / (
        "research/local_wide_equipment_recheck_2026_10_09.json"
    )
    try:
        wide_record = json.loads(wide_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        wide_record = None
    wide_privacy = (wide_record or {}).get("privacy") or {}
    wide_inventory = (wide_record or {}).get("inventory") or {}
    wide_quality = (wide_record or {}).get("quality_screen") or {}
    wide_coverage = (wide_record or {}).get("coverage_assessment") or {}
    wide_required_privacy = (
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "site_company_manufacturer_published",
        "calendar_dates_published",
        "raw_rows_persisted",
        "per_file_hashes_published",
    )
    if (
        (wide_record or {}).get("artifact_type") == "local_wide_equipment_recheck"
        and all(wide_privacy.get(key) is False for key in wide_required_privacy)
        and wide_inventory.get("file_count") == 8
        and wide_inventory.get("row_count") == 653442
        and wide_inventory.get("schema_width") == 64
        and wide_coverage.get("local_equipment_boundary_data_is_substantial") is True
        and wide_coverage.get("vehicle_side_full_loop_validation_ready") is False
    ):
        safe_groups["wide_equipment_boundary_recheck"] = {
            "evidence_class": "privacy-bounded local wide station-equipment logger screen",
            "file_count": wide_inventory.get("file_count"),
            "row_count": wide_inventory.get("row_count"),
            "schema_width": wide_inventory.get("schema_width"),
            "median_sample_period_s": wide_inventory.get("median_sample_period_s"),
            "maximum_gap_s": wide_inventory.get("maximum_gap_s"),
            "pressure_role_count": wide_inventory.get("pressure_role_count"),
            "temperature_role_count": wide_inventory.get("temperature_role_count"),
            "equipment_state_role_count": wide_inventory.get("equipment_state_role_count"),
            "flow_like_candidate_count": wide_inventory.get("flow_like_candidate_count"),
            "totalizer_like_candidate_count": wide_inventory.get("totalizer_like_candidate_count"),
            "vehicle_or_dispenser_candidate_count": wide_inventory.get(
                "vehicle_or_dispenser_candidate_count"
            ),
            "pressure_roles_fully_finite": wide_quality.get(
                "pressure_roles_fully_finite"
            ),
            "temperature_roles_fully_finite": wide_quality.get(
                "temperature_roles_fully_finite"
            ),
            "compressor_load_transition_count": wide_quality.get(
                "compressor_load_transition_count"
            ),
            "cooling_run_transition_count": wide_quality.get(
                "cooling_run_transition_count"
            ),
            "flow_units_attested": wide_quality.get("flow_units_attested"),
            "state_semantics_attested": wide_quality.get("state_semantics_attested"),
            "eligible_use": (wide_record or {}).get("eligible_use") or [],
            "ineligible_use": (wide_record or {}).get("ineligible_use") or [],
            "claim_boundary": (wide_record or {}).get("claim_boundary"),
        }

    # The continuity screen is kept separate from the older header-only wide
    # logger screen.  It proves timestamp/numeric continuity only; it does not
    # attest units or state semantics and must not be promoted to calibration.
    continuity_path = Path(__file__).resolve().parents[2] / (
        "research/local_wide_equipment_continuity_recheck_2026_10_09.json"
    )
    try:
        continuity_record = json.loads(
            continuity_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, json.JSONDecodeError):
        continuity_record = None
    continuity_privacy = (continuity_record or {}).get("privacy") or {}
    continuity_inventory = (continuity_record or {}).get("inventory") or {}
    continuity_eligibility = (continuity_record or {}).get("eligibility") or {}
    continuity_required_privacy = (
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "source_identifiers_published",
        "calendar_dates_published",
        "raw_rows_persisted",
        "per_file_metrics_published",
    )
    if (
        (continuity_record or {}).get("artifact_type")
        == "local_wide_equipment_continuity_screen"
        and all(
            continuity_privacy.get(key) is False
            for key in continuity_required_privacy
        )
        and continuity_inventory.get("wide_file_count") == 8
        and continuity_inventory.get("wide_row_count") == 653442
        and continuity_inventory.get("timestamp_parse_failures") == 0
        and continuity_inventory.get("negative_interval_count") == 0
        and continuity_eligibility.get(
            "station_equipment_continuity_screen_ready"
        ) is True
        and continuity_eligibility.get("measured_boundary_replay_ready") is False
        and continuity_eligibility.get("full_loop_vehicle_validation") is False
    ):
        safe_groups["wide_equipment_continuity_screen"] = {
            "evidence_class": "privacy-bounded local wide equipment time-continuity screen",
            "wide_file_count": continuity_inventory.get("wide_file_count"),
            "wide_row_count": continuity_inventory.get("wide_row_count"),
            "timestamp_parse_failures": continuity_inventory.get(
                "timestamp_parse_failures"
            ),
            "duplicate_timestamp_count": continuity_inventory.get(
                "duplicate_timestamp_count"
            ),
            "negative_interval_count": continuity_inventory.get(
                "negative_interval_count"
            ),
            "files_with_monotonic_time": continuity_inventory.get(
                "files_with_monotonic_time"
            ),
            "median_positive_interval_s": continuity_inventory.get(
                "median_positive_interval_s"
            ),
            "maximum_positive_interval_s": continuity_inventory.get(
                "maximum_positive_interval_s"
            ),
            "numeric_column_count_min": continuity_inventory.get(
                "numeric_column_count_min"
            ),
            "numeric_columns_fully_finite_total": continuity_inventory.get(
                "numeric_columns_fully_finite_total"
            ),
            "state_candidate_column_count": continuity_inventory.get(
                "state_candidate_column_count"
            ),
            "state_transition_count": continuity_inventory.get(
                "state_transition_count"
            ),
            "eligible_use": [
                "time continuity and missingness checks",
                "station-equipment replay after custodian attestation",
            ],
            "ineligible_use": [
                "unit or pressure-reference calibration",
                "vehicle-side full-loop validation",
                "quantitative consequence-distance validation",
            ],
            "claim_boundary": (continuity_record or {}).get("claim_boundary"),
        }
    return {
        "artifact": "research/local_hydrogen_station_data_discovery_recheck_2026_10_09.json",
        "evidence_role": "privacy-bounded local hydrogen-station data discovery and claim boundary",
        "candidate_groups": safe_groups,
        "coverage_assessment": {
            key: coverage.get(key)
            for key in (
                "local_station_data_is_sparse",
                "station_side_dynamic_evidence_is_substantial",
                "vehicle_side_full_loop_validation_ready",
                "quantitative_consequence_validation_ready",
                "derived_exports_must_be_excluded_from_external_validation",
                "main_limit",
            )
        },
        "independent_header_recheck": {
            "method": header_recheck.get("method"),
            "files_screened": header_recheck.get("files_screened"),
            "schema_widths": header_recheck.get("schema_widths") or {},
            "candidate_file_counts": {
                "vehicle_or_dispenser_expanded": header_counts.get(
                    "vehicle_or_dispenser_expanded"
                ),
                "vehicle_pressure_temperature_expanded": header_counts.get(
                    "vehicle_pressure_temperature_expanded"
                ),
                "flow_or_mass_expanded": header_counts.get(
                    "flow_or_mass_expanded"
                ),
                "pressure_expanded": header_counts.get("pressure_expanded"),
                "temperature_expanded": header_counts.get(
                    "temperature_expanded"
                ),
                "protocol_state_expanded": header_counts.get(
                    "protocol_state_expanded"
                ),
            },
            "interpretation": header_recheck.get("interpretation"),
        },
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _local_station_custodian_attestation_request_evidence() -> dict[str, Any] | None:
    """Expose the privacy-bounded checklist needed to close local-data gates.

    This is a request contract, not a measurement source.  Keeping it in the
    evidence envelope lets the LLM state precisely which local semantics are
    still missing without exposing raw paths, tags, timestamps or rows.
    """

    root = Path(__file__).resolve().parents[2]
    path = root / (
        "research/local_station_custodian_attestation_request_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    required_privacy = (
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "source_tags_published",
        "site_company_manufacturer_published",
        "calendar_dates_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "per_file_hashes_published",
    )
    inventory = record.get("observed_local_archive") or {}
    if (
        record.get("artifact_type") != "local_station_custodian_attestation_request"
        or record.get("status") != "awaiting_custodian_confirmation"
        or any(privacy.get(key) is not False for key in required_privacy)
        or inventory.get("csv_file_count") != 33
        or inventory.get("unique_csv_payload_count") != 32
        or inventory.get("deduplicated_data_row_count") != 56854143
        or inventory.get("station_side_dynamic_evidence_ready") is not True
        or inventory.get("vehicle_side_full_loop_ready") is not False
    ):
        return None

    requests: list[dict[str, Any]] = []
    for item in record.get("requested_attestations") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        requests.append({
            "id": str(item.get("id")),
            "request": str(item.get("request") or ""),
            "acceptance": str(item.get("acceptance") or ""),
            "enables": [str(value) for value in item.get("enables") or []],
        })
    if len(requests) < 8:
        return None
    return {
        "artifact": str(path.relative_to(root)).replace("\\", "/"),
        "evidence_role": "privacy-bounded local-station custodian attestation request",
        "status": str(record.get("status")),
        "observed_local_archive": {
            "csv_file_count": inventory.get("csv_file_count"),
            "unique_csv_payload_count": inventory.get("unique_csv_payload_count"),
            "deduplicated_data_row_count": inventory.get(
                "deduplicated_data_row_count"
            ),
            "schema_width_file_counts": inventory.get("schema_width_file_counts") or {},
            "station_side_dynamic_evidence_ready": True,
            "vehicle_side_full_loop_ready": False,
        },
        "requested_attestations": requests,
        "current_gate_effect": record.get("current_gate_effect") or {},
        "custodian_submission_contract": [
            str(value) for value in record.get("custodian_submission_contract") or []
        ],
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _local_data_deep_scan_evidence() -> dict[str, Any] | None:
    """Expose the broader local-corpus scan without private provenance.

    The deep scan is a coverage and false-positive classification record.  It
    must not make keyword matches look like synchronized station-to-vehicle
    measurements, and it deliberately omits paths, filenames, identifiers,
    dates and raw values before the record enters an LLM prompt.
    """

    root = Path(__file__).resolve().parents[2]
    path = root / "research/local_data_deep_scan_2026_10_09.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    required_privacy = (
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "source_identifiers_published",
        "site_company_manufacturer_published",
        "calendar_dates_published",
        "raw_rows_persisted",
        "candidate_values_persisted",
    )
    station = record.get("measured_station_bundle") or {}
    inventory = record.get("broad_candidate_inventory") or {}
    decision = record.get("full_loop_decision") or {}
    classes = record.get("broad_candidate_inventory", {}).get(
        "candidate_classes"
    ) or []
    if (
        record.get("artifact_type") != "local_data_deep_scan"
        or record.get("status")
        != "privacy_bounded_inventory_with_full_loop_negative_result"
        or not all(privacy.get(key) is False for key in required_privacy)
        or station.get("csv_files") != 33
        or station.get("deduplicated_rows") != 56_854_143
        or inventory.get("inventory_files") != 2
        or inventory.get("listed_entries") != 394
        or inventory.get("unique_candidate_assets") != 206
        or inventory.get("duplicate_listings_across_inventories") != 188
        or inventory.get("coarse_candidate_groups") != 8
        or len(classes) != 4
        or decision.get("new_eligible_synchronized_station_vehicle_cohort_found")
        is not False
        or decision.get("decision") != "NO_NEW_FULL_LOOP_HOLDOUT"
    ):
        return None

    safe_classes: list[dict[str, Any]] = []
    for item in classes:
        if not isinstance(item, dict) or not item.get("class"):
            return None
        safe_classes.append({
            key: item.get(key)
            for key in (
                "class", "unique_assets", "description", "full_loop_eligibility"
            )
            if item.get(key) is not None
        })
    return {
        "artifact": str(path.relative_to(root)).replace("\\", "/"),
        "evidence_role": "privacy-bounded local data deep-scan coverage and claim boundary",
        "scan_scope": [str(value) for value in record.get("scan_scope") or []],
        "measured_station_bundle": {
            key: station.get(key)
            for key in (
                "csv_files", "deduplicated_rows", "raw_storage_gib_rounded",
                "station_side_evidence",
            )
            if station.get(key) is not None
        },
        "broad_candidate_inventory": {
            key: inventory.get(key)
            for key in (
                "inventory_files", "listed_entries", "unique_candidate_assets",
                "duplicate_listings_across_inventories", "coarse_candidate_groups",
                "keyword_scanner_warning",
            )
            if inventory.get(key) is not None
        },
        "candidate_classes": safe_classes,
        "full_loop_decision": {
            "new_eligible_synchronized_station_vehicle_cohort_found": False,
            "decision": str(decision.get("decision")),
            "reason": str(decision.get("reason") or ""),
            "required_before_full_loop_validation": [
                str(value)
                for value in decision.get("required_before_full_loop_validation") or []
            ],
        },
        "claim_limit": str(record.get("next_action") or ""),
    }


def _local_adjacent_process_evidence() -> dict[str, Any] | None:
    """Expose adjacent hydrogen-process inventory without raw provenance.

    These logs can help explain process-context and sequence plausibility, but
    they must never be presented as HRS station-to-vehicle validation or used
    to retune runtime parameters automatically.
    """

    root = Path(__file__).resolve().parents[2]
    path = root / "research/local_adjacent_hydrogen_data_discovery_2026_10_09.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    collections = record.get("collections") or {}
    process = collections.get("high_pressure_hydrogen_process") or {}
    liquid = collections.get("liquid_hydrogen_centre_context") or {}
    eligibility = record.get("eligibility") or {}
    if (
        record.get("artifact_type")
        != "local_adjacent_hydrogen_process_data_discovery"
        or not all(value is False for value in privacy.values())
        or process.get("csv_event_log_count") != 18
        or process.get("csv_event_row_count") != 2_411_774
        or process.get("domain_classification")
        != "hydrogen_city_or_pipeline_process_context_not_HRS"
        or eligibility.get("station_side_runtime_parameter_application") is not False
        or eligibility.get("synchronized_station_dispenser_vehicle_validation") is not False
        or eligibility.get("quantitative_consequence_validation") is not False
    ):
        return None
    return {
        "artifact": str(path.relative_to(root)).replace("\\", "/"),
        "evidence_role": "privacy-bounded adjacent hydrogen-process inventory",
        "domain_classification": process.get("domain_classification"),
        "high_pressure_process": {
            key: process.get(key)
            for key in (
                "csv_event_log_count", "csv_event_row_count", "largest_event_log_row_count",
                "entity_key_count", "logical_key_count", "value_family_row_counts",
                "workbook_count", "workbook_sheet_count", "nontrivial_workbook_table_count",
                "time_semantics_documented_in_local_index",
                "time_order_interpretation",
            )
            if process.get(key) is not None
        },
        "liquid_hydrogen_centre_context": {
            key: liquid.get(key)
            for key in (
                "csv_file_count", "scenario_row_count", "workbook_count",
                "workbook_sheet_count", "nontrivial_workbook_table_count",
                "semantic_role",
            )
            if liquid.get(key) is not None
        },
        "runtime_parameter_application": False,
        "station_to_vehicle_full_loop_validation": False,
        "quantitative_consequence_validation": False,
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _local_docudata_discovery_evidence() -> dict[str, Any] | None:
    """Expose the broad local header scan as a discovery boundary only."""

    root = Path(__file__).resolve().parents[2]
    path = root / "research/local_docudata_full_discovery_2026_10_09.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
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
        "artifact": str(path.relative_to(root)).replace("\\", "/"),
        "evidence_role": "privacy-bounded local document discovery",
        "broad_scan": {
            key: broad.get(key)
            for key in (
                "machine_readable_files_screened", "csv_tsv_headers_screened",
                "path_keyword_candidates", "vehicle_or_dispenser_keyword_candidates",
                "release_rig_or_jet_candidates",
            )
            if broad.get(key) is not None
        },
        "refined_header_screen": {
            key: refined.get(key)
            for key in (
                "csv_files_screened", "vehicle_keyword_hits",
                "vehicle_pressure_temperature_flow_time_candidates",
            )
            if refined.get(key) is not None
        },
        "eligibility": {
            key: eligibility.get(key)
            for key in (
                "eligible_synchronized_station_dispenser_vehicle_cohort",
                "full_loop_external_validation_ready",
                "quantitative_consequence_validation_ready",
                "runtime_parameter_application",
            )
            if eligibility.get(key) is not None
        },
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _local_public_validation_catalog_evidence() -> dict[str, Any] | None:
    """Expose the local public-cache inventory without exposing its files.

    The catalog is intentionally only a coverage signal.  Dataset-specific
    evidence functions remain the authority for units, synchronization,
    provenance and holdout eligibility.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/local_public_validation_catalog_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    scope = record.get("scope") or {}
    coverage = record.get("coverage_assessment") or {}
    if (
        record.get("artifact_type") != "local_public_validation_catalog"
        or record.get("status") != "privacy_bounded_catalog_only"
        or not all(value is False for value in privacy.values())
        or scope.get("collection_count", 0) < 10
        or scope.get("file_count", 0) < 100
        or coverage.get("public_component_evidence_is_substantial") is not True
        or coverage.get("new_full_loop_cohort_identified_by_catalog") is not False
        or coverage.get("full_loop_holdout_eligible") is not False
    ):
        return None
    family_counts: dict[str, int] = {}
    family_files: dict[str, int] = {}
    for item in record.get("collections") or []:
        if not isinstance(item, dict):
            continue
        family = str(item.get("family_hint") or "other_public_validation_material")
        family_counts[family] = family_counts.get(family, 0) + 1
        family_files[family] = family_files.get(family, 0) + int(item.get("file_count") or 0)
    return {
        "artifact": "research/local_public_validation_catalog_2026_10_09.json",
        "evidence_role": "privacy-bounded local public validation corpus availability",
        "scope": {
            "collection_count": scope.get("collection_count"),
            "file_count": scope.get("file_count"),
            "size_gb_decimal": scope.get("size_gb_decimal"),
            "family_collection_counts": dict(sorted(family_counts.items())),
            "family_file_counts": dict(sorted(family_files.items())),
        },
        "coverage_assessment": {
            "public_component_evidence_is_substantial": True,
            "new_full_loop_cohort_identified_by_catalog": False,
            "full_loop_holdout_eligible": False,
            "next_action": coverage.get("next_action"),
        },
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _local_public_candidate_scan_evidence() -> dict[str, Any] | None:
    """Expose the semantic second-pass screen for the public cache.

    This is deliberately separate from the broad file catalog.  It tells the
    assistants why a keyword match was retained as a release experiment or a
    static consequence table instead of being promoted to a synchronized
    station-to-vehicle holdout.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/local_public_candidate_scan_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy = record.get("privacy") or {}
    scan = record.get("scan") or {}
    eligibility = record.get("eligibility") or {}
    classes = scan.get("coarse_candidate_classes") or {}
    if (
        record.get("artifact_type")
        != "privacy_bounded_local_workspace_candidate_scan"
        or record.get("status") != "discovery_only"
        or not privacy
        or not all(value is False for value in privacy.values())
        or int(scan.get("machine_readable_files") or 0) < 1
        or int(scan.get("csv_tsv_headers_screened") or 0) < 1
        or eligibility.get("decision") != "DISCOVERY_ONLY_UNTIL_ATTESTED"
        or int(eligibility.get("full_loop_candidate_count", -1)) != 0
        or int(classes.get("vehicle_pressure_temperature_candidate") or 0) != 0
    ):
        return None
    return {
        "artifact": "research/local_public_candidate_scan_2026_10_09.json",
        "evidence_role": "privacy-bounded semantic screening of local public candidates",
        "scan": {
            "machine_readable_files": int(scan.get("machine_readable_files") or 0),
            "csv_tsv_headers_screened": int(scan.get("csv_tsv_headers_screened") or 0),
            "header_parse_errors": int(scan.get("header_parse_errors") or 0),
            "coarse_candidate_classes": {
                str(key): int(value) for key, value in classes.items()
            },
        },
        "eligibility": {
            "full_loop_candidate_count": 0,
            "decision": str(eligibility.get("decision")),
            "required_attestation": [
                str(value) for value in eligibility.get("required_attestation") or []
            ],
        },
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _local_candidate_full_loop_screen_evidence() -> dict[str, Any] | None:
    """Expose the bounded local/public candidate classification to the LLM.

    The record distinguishes private station-side telemetry, the measured
    NREL tank boundary, and the DTU Modelica simulator. This prevents a
    component trace or simulator output from being presented as an
    independent station-to-vehicle holdout.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/local_candidate_full_loop_screen_2026_10_09.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    coverage = record.get("coverage_assessment") or {}
    candidates = record.get("candidates") or []
    if (
        record.get("artifact_type") != "local_candidate_full_loop_screen"
        or record.get("decision") != "NO_NEW_FULL_LOOP_MEASURED_COHORT"
        or coverage.get("local_station_data_is_sparse") is not False
        or coverage.get("full_loop_holdout_eligible") is not False
        or len(candidates) != 3
    ):
        return None

    safe_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            return None
        safe_candidates.append({
            key: candidate.get(key)
            for key in (
                "id", "evidence_class", "availability", "quantity_summary",
                "package_summary", "observed_channels",
                "measured_time_series_present",
                "vehicle_or_dispenser_boundary_attested",
                "station_controller_or_cascade_state_attested",
                "esd_or_safety_interlock_trace_attested",
                "vehicle_protocol_trace_attested", "decision", "eligible_use",
                "ineligible_use", "claim_limit",
            )
            if candidate.get(key) is not None
        })
    return {
        "artifact": "research/local_candidate_full_loop_screen_2026_10_09.json",
        "evidence_role": "privacy-bounded local/public candidate classification",
        "candidates": safe_candidates,
        "coverage_assessment": {
            key: coverage.get(key)
            for key in (
                "local_station_data_is_sparse",
                "station_side_dynamic_evidence_is_substantial",
                "public_component_boundary_evidence_available",
                "new_full_loop_measured_cohort_found",
                "full_loop_holdout_eligible",
                "quantitative_consequence_validation_ready",
                "main_limit",
            )
        },
        "decision": record.get("decision"),
        "next_action": record.get("next_action"),
    }


def _confidential_multisource_mapping_feasibility() -> dict[str, Any] | None:
    """Expose the controlled multi-sheet mapping boundary without identifiers.

    The private review record itself stays outside the repository because it
    contains source paths and original labels.  The committed result is only a
    header-and-structure feasibility screen, so it can keep an LLM from
    treating documentation-shaped tables as synchronized measurement evidence
    or inventing unmapped channels.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_multisource_mapping_feasibility_2026_10_07.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    review = record.get("controlled_review") or {}
    screen = record.get("canonical_mapping_screen") or {}
    if (
        record.get("artifact_type") != "controlled_multisource_mapping_feasibility"
        or record.get("source_identifiers_published") is not False
        or record.get("original_headers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("absolute_timestamps_published") is not False
        or review.get("sample_data_rows_structurally_inspected_in_memory") is not True
        or review.get("measurement_values_persisted") is not False
        or screen.get("all_required_full_loop_channels_have_unambiguous_header_candidates")
        is not False
        or screen.get("decision")
        != "no_measurement_grade_multisource_candidate_found_in_controlled_intake"
    ):
        return None
    return {
        "artifact": "research/confidential_multisource_mapping_feasibility_2026_10_07.json",
        "evidence_role": "controlled multi-source full-loop mapping feasibility",
        "co_located_workbook_candidates": review.get("co_located_workbook_candidates"),
        "candidate_worksheet_count": review.get("candidate_worksheet_count"),
        "sample_data_rows_structurally_inspected_in_memory": True,
        "measurement_values_persisted": False,
        "unambiguous_full_loop_mapping_available": False,
        "header_level_candidates_present": list(
            screen.get("header_level_candidates_present") or []
        ),
        "header_level_candidates_not_identified": list(
            screen.get("header_level_candidates_not_identified") or []
        ),
        "full_loop_holdout_eligible": False,
        "decision": screen.get("decision"),
        "claim_limit": str(record.get("claim_boundary") or ""),
    }


def _confidential_private_media_evidence() -> dict[str, Any] | None:
    """Expose the private-media intake boundary without exposing media.

    Screen recordings and photographs can establish provenance and suggest
    channel/equipment families, but they must not be presented to an assistant
    as calibrated logger rows.  Keeping this status in the evidence envelope
    prevents the LLM from silently treating a video-derived observation as a
    numerical field validation.
    """

    path = Path(__file__).resolve().parents[2] / (
        "research/confidential_private_media_intake_assessment_2026_10.json"
    )
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        record.get("artifact_type") != "confidential_private_media_intake_assessment"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_media_persisted") is not False
        or record.get("exact_source_dates_published") is not False
    ):
        return None
    inventory = record.get("media_inventory") or {}
    assessment = record.get("content_assessment") or {}
    eligibility = record.get("eligibility") or {}
    return {
        "artifact": (
            "research/confidential_private_media_intake_assessment_2026_10.json"
        ),
        "evidence_role": "confidential private-media provenance and intake boundary",
        "image_count": inventory.get("image_count"),
        "video_count": inventory.get("video_count"),
        "video_decoded_count": inventory.get("video_decoded_count"),
        "video_probe_undecodable_count": inventory.get("video_undecodable_count"),
        "screen_recorded_logger_candidate": assessment.get(
            "screen_recorded_logger_candidate"
        ) is True,
        "machine_readable_trace_present": assessment.get(
            "machine_readable_trace_present"
        ) is True,
        "ocr_or_frame_values_used_for_calibration": assessment.get(
            "ocr_or_frame_values_used_for_calibration"
        ) is True,
        "channel_inventory_candidate": eligibility.get(
            "channel_inventory_candidate"
        ) is True,
        "parameter_fit_permitted": eligibility.get(
            "pressure_or_temperature_parameter_fit"
        ) is True,
        "full_loop_holdout_eligible": eligibility.get(
            "full_loop_holdout_eligible"
        ) is True,
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
        "indoor_status", "maximum_indoor_overpressure_pa",
        "ignited_enclosure_status", "ignited_enclosure_model",
        "maximum_ignited_enclosure_overpressure_pa",
        "ignited_enclosure_peak_time_s",
        "ignited_enclosure_average_mass_flow_kg_s",
        "ignited_enclosure_volume_m3", "ignited_enclosure_vent_area_m2",
        "ignited_enclosure_external_holdout_supported",
        "ignited_enclosure_validation_artifact",
        "ignited_enclosure_claim_limit",
        "sampled_effect_radius_m", "sampled_thermal_radius_m",
        "sampled_overpressure_radius_m", "sampled_next_distance_m",
        "thermal_range_status", "overpressure_range_status",
        "flammable_plume_streamline_distance_m", "effect_range_status",
        "modeled_consequence_mass_flow_kg_s", "mass_flow_override_requested",
        "mass_flow_override_status", "mass_flow_override_ratio",
        "mass_flow_override_claim_limit",
        "release_source_boundary", "process_flow_limit_kg_s",
        "physical_orifice_diameter_m", "consequence_equivalent_orifice_diameter_m",
        "flow_limited_equivalent_orifice_applied", "flow_limited_consequence_status",
        "flow_limited_consequence_claim_limit",
        "literature_delayed_ignition_status",
        "literature_delayed_ignition_in_validation_domain",
        "literature_delayed_ignition_5kpa_radial_distance_m",
        "literature_delayed_ignition_no_harm_radial_distance_m",
        "literature_delayed_ignition_injury_radial_distance_m",
        "literature_delayed_ignition_fatality_radial_distance_m",
        "literature_delayed_ignition_distance_origin",
        "literature_delayed_ignition_site_safety_distance",
        "literature_delayed_ignition_doi", "literature_delayed_ignition_claim_limit",
        "literature_jet_flame_status",
        "literature_jet_flame_in_validation_domain",
        "literature_jet_flame_length_m",
        "literature_jet_flame_mass_flow_basis",
        "literature_jet_flame_is_harm_distance",
        "literature_jet_flame_doi", "literature_jet_flame_claim_limit",
        "consequence_validation_scope", "geometry_display_mapping_verified",
        "source_depletion_external_holdout_supported",
        "full_station_vehicle_validation_supported",
        "site_specific_safety_distance_supported",
        "consequence_validation_artifacts", "consequence_validation_claim_limit",
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


def _qra_multimethod_comparison_evidence() -> dict[str, Any] | None:
    """Expose a compact, non-validating consequence-method comparison.

    DATA3632 is a seven-method simulation benchmark.  It is valuable for
    identifying source-boundary and method spread, but it is not experimental
    truth and must never be used to silently tune the runtime consequence
    model.  Only committed aggregate diagnostics are exposed to the LLM.
    """

    root = Path(__file__).resolve().parents[2]
    comparison_path = root / "research/qra_multimethod_comparison_2026_10_08.json"
    runtime_path = root / "research/runtime_qra_envelope_comparison_2026_10_08.json"
    try:
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if (
        comparison.get("source", {}).get("doi") != "10.34810/DATA3632"
        or runtime.get("source", {}).get("doi") != "10.34810/DATA3632"
        or comparison.get("selection", {}).get("method_count") != 7
        or not str(runtime.get("model_action") or "").startswith(
            "No automatic calibration"
        )
    ):
        return None
    aggregate = runtime.get("aggregate") or {}
    cases = []
    for case in runtime.get("cases") or []:
        if not isinstance(case, dict):
            continue
        benchmark = case.get("benchmark") or {}
        mass = benchmark.get("jet_fire_mass_rate_kg_s") or {}
        current = case.get("runtime") or {}
        comparison_row = case.get("comparison") or {}
        cases.append({
            "equipment": case.get("equipment"),
            "runtime_mass_flow_kg_s": current.get("modeled_mass_flow_kg_s"),
            "benchmark_mass_flow_range_kg_s": [mass.get("minimum"), mass.get("maximum")],
            "mass_flow_ratio_to_method_median": (
                comparison_row.get("mass_rate") or {}
            ).get("ratio_to_method_median"),
            "thermal_within_method_envelope": (
                comparison_row.get("thermal") or {}
            ).get("within_method_envelope") is True,
            "overpressure_within_method_envelope": (
                comparison_row.get("overpressure") or {}
            ).get("within_method_envelope") is True,
        })
    return {
        "artifact": "research/runtime_qra_envelope_comparison_2026_10_08.json",
        "source": {
            "doi": "10.34810/DATA3632",
            "version": comparison.get("source", {}).get("version"),
            "license": comparison.get("source", {}).get("license"),
        },
        "evidence_role": "post-access simulation-to-simulation QRA method comparison",
        "method_count": comparison.get("selection", {}).get("method_count"),
        "retained_row_count": comparison.get("aggregate", {}).get(
            "observation_count"
        ),
        "matched_group_count": comparison.get("aggregate", {}).get(
            "matched_input_group_count"
        ),
        "maximum_matched_method_ratio": (
            comparison.get("aggregate", {}).get("matched_input_spread_ratio") or {}
        ).get("maximum"),
        "runtime_case_count": aggregate.get("case_count"),
        "runtime_thermal_within_envelope_count": aggregate.get(
            "thermal_within_method_envelope_count"
        ),
        "runtime_overpressure_within_envelope_count": aggregate.get(
            "overpressure_within_method_envelope_count"
        ),
        "cases": cases,
        "automatic_calibration_performed": False,
        "experimental_validation": False,
        "claim_limit": runtime.get("claim_boundary"),
        "operator_rule": (
            "방출원 유형과 실제/제한 유량을 먼저 확인한다. 이 QRA 방법군만으로 "
            "거리계수나 설비별 유량을 자동 보정하지 않는다."
        ),
    }


_UNSUPPORTED_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "full_loop_field_validation",
        re.compile(
            r"(?:full[\s-]*loop|station[\s-]*to[\s-]*vehicle|충전소[\s·-]*차량|전체\s*(?:충전)?\s*루프|현장)"
            r".{0,24}(?:검증|validation|validated|검증됨|검증완료|통과)",
            re.IGNORECASE,
        ),
    ),
    (
        "safety_certification",
        re.compile(
            r"(?:안전\s*(?:인증|승인)|safety\s*certif(?:ied|ication)|certified\s*safe)",
            re.IGNORECASE,
        ),
    ),
    (
        "confirmed_safety_distance",
        re.compile(
            r"(?:현장\s*)?(?:안전|대피|영향|피해)\s*(?:거리|반경).{0,20}"
            r"(?:확정|보장|적용|confirmed|guaranteed|validated)",
            re.IGNORECASE,
        ),
    ),
)


# A command in the virtual safety console is deliberately not a completed
# protective action.  These patterns only recognise retrospective completion
# wording, never an instruction such as "close the valve" or "verify ESD".
# The response may therefore continue to recommend a protective step while
# being prevented from claiming that the simulator has already verified it.
_VIRTUAL_ACTION_COMPLETION_PATTERNS: tuple[tuple[str, tuple[str, ...], re.Pattern[str]], ...] = (
    (
        "esd_trip",
        ("esd.trip",),
        re.compile(
            r"(?:\bESD(?![A-Za-z0-9_])|비상\s*차단|emergency\s*shutdown).{0,30}"
            r"(?:(?:가동|작동|트립|실행)\s*(?:완료|되었습니다|됐습니다|됐다|되었다|했습니다|됨)"
            r"|(?:완료|activated|tripped|completed|confirmed|successfully))",
            re.IGNORECASE,
        ),
    ),
    (
        "operation_stop",
        ("operation.stop", "esd.trip"),
        re.compile(
            r"(?:충전|공급|압축|공정|운전|fueling|supply|compression|operation).{0,28}"
            r"(?:(?:정지|중지|멈춤)\s*(?:완료|되었습니다|됐습니다|됐다|되었다|했습니다|됨)"
            r"|(?:stopped|halted)(?:\s*(?:confirmed|successfully))?)",
            re.IGNORECASE,
        ),
    ),
    (
        "isolation",
        ("valve.close",),
        re.compile(
            r"(?:밸브|상류|하류|유입|유출|차단|valve|isolation).{0,28}"
            r"(?:(?:폐쇄|닫힘|차단)\s*(?:완료|되었습니다|됐습니다|됐다|되었다|했습니다|됨)"
            r"|(?:isolated|closed)(?:\s*(?:confirmed|successfully))?)",
            re.IGNORECASE,
        ),
    ),
    (
        "evacuation",
        ("personnel.evacuate", "vehicle.evacuate"),
        re.compile(
            r"(?:대피|출입\s*통제|evacuat(?:ion|ed)|access\s*restrict(?:ed|ion)).{0,24}"
            r"(?:완료|되었습니다|됐습니다|됐다|되었다|했습니다|됨|confirmed|completed|successfully)",
            re.IGNORECASE,
        ),
    ),
    (
        "ventilation",
        ("ventilation.on",),
        re.compile(
            r"(?:환기(?:팬)?|배기|ventilation|exhaust).{0,24}"
            r"(?:(?:가동|작동)\s*(?:완료|되었습니다|됐습니다|됐다|되었다|했습니다|됨)"
            r"|(?:started|running|activated)(?:\s*(?:confirmed|successfully))?)",
            re.IGNORECASE,
        ),
    ),
)


def _virtual_safety_evidence(frame: dict[str, Any]) -> dict[str, Any]:
    """Return action feedback needed to bound an LLM response.

    This projection deliberately excludes action IDs, operator notes and raw
    before/after metric snapshots.  The LLM needs only command type, target
    and terminal feedback status to distinguish an issued command from a
    confirmed protective state.  Full training replay remains available only
    through the virtual-safety API.
    """

    raw = frame.get("virtual_safety") or {}
    if not isinstance(raw, dict):
        return {
            "actions": [],
            "action_count": 0,
            "claim_limit": "가상 안전조치의 명령과 완료 피드백을 구분하며, 피드백이 없으면 완료로 단정하지 않음",
        }
    actions: list[dict[str, Any]] = []
    for item in (raw.get("actions") or [])[-24:]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        target = str(item.get("target") or "")
        status = str(item.get("status") or "unknown")
        if not kind:
            continue
        row = {"kind": kind, "target": target, "status": status}
        for key in ("issued_s", "completed_s"):
            value = _finite_number(item.get(key))
            if value is not None:
                row[key] = value
        actions.append(row)
    return {
        "actions": actions,
        "action_count": len(actions),
        "confirmed_count": sum(row["status"] == "confirmed" for row in actions),
        "failed_count": sum(row["status"] == "failed" for row in actions),
        "pending_count": sum(row["status"] not in {"confirmed", "failed"} for row in actions),
        "claim_limit": "가상 안전조치의 명령과 완료 피드백을 구분하며, 피드백이 없으면 완료로 단정하지 않음",
    }


def _confirmed_virtual_action_kinds(manifest: dict[str, Any]) -> set[str]:
    safety = manifest.get("virtual_safety") or {}
    if not isinstance(safety, dict):
        return set()
    return {
        str(action.get("kind"))
        for action in safety.get("actions") or []
        if isinstance(action, dict)
        and action.get("status") == "confirmed"
        and action.get("kind")
    }


def _claim_is_explicitly_limited(line: str, match: re.Match[str]) -> bool:
    """Return true when a matched phrase is explicitly negated or bounded.

    The LLM is expected to explain these limits.  The post-generation guard
    must therefore preserve sentences such as ``현장 검증이 아닙니다`` and
    ``not a confirmed safety distance`` instead of treating every occurrence
    of a validation word as an overclaim.
    """

    start = max(0, match.start() - 42)
    end = min(len(line), match.end() + 42)
    window = line[start:end].lower().replace(" ", "")
    return any(token in window for token in (
        "아니", "아닙", "아니다", "않", "못", "불가", "미확인", "미지원", "한계", "가정",
        "not", "no", "cannot", "can't", "unsupported", "unconfirmed",
        "screeningonly", "advisoryonly", "notafield",
    ))


def guard_llm_claims(
    answer: str,
    evidence_manifest: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    """Bound generated claims to the evidence envelope.

    Public experiments and the anonymized station replay currently support
    component/envelope calibration only.  They do not establish station to
    vehicle full-loop validation, field safety certification, or a confirmed
    evacuation distance.  This guard is intentionally narrow: it leaves
    sensor observations, calculated consequence values, response steps, and
    explicit limitation statements intact, while replacing a positive claim
    that exceeds the manifest with a deterministic caveat.

    Returns the guarded answer and a small audit record suitable for API
    responses and saved LLM traces.
    """

    text = str(answer or "")
    manifest = evidence_manifest or {}
    real_station = manifest.get("public_real_station_context") or {}
    closed_loop = manifest.get("closed_loop_validation_boundary") or {}
    readiness = (manifest.get("response_evidence") or {}).get(
        "validation_readiness"
    ) or {}
    full_loop_supported = any(
        value is True
        for value in (
            manifest.get("full_loop_validation_supported"),
            real_station.get("full_loop_external_holdout_eligible"),
            closed_loop.get("claim_supported"),
        )
    )
    # The repository-level readiness ledger is the authoritative upper bound
    # for generated claims.  Even if a stale or synthetic manifest contains a
    # permissive component flag, it cannot re-enable a failed full-loop gate.
    if isinstance(readiness, dict):
        if readiness.get("status") != "available" or readiness.get(
            "ledger_integrity"
        ) is not True:
            full_loop_supported = False
        else:
            full_loop_supported = (
                full_loop_supported
                and readiness.get("full_loop_external_validation_supported") is True
            )
    # These are separate flags so a future component-level certification does
    # not accidentally authorize a full-loop claim.
    blocked_families: set[str] = set()
    if not full_loop_supported:
        blocked_families.add("full_loop_field_validation")
    blocked_families.update({"safety_certification", "confirmed_safety_distance"})

    blocked: list[dict[str, str]] = []
    confirmed_action_kinds = _confirmed_virtual_action_kinds(manifest)
    output: list[str] = []
    caveat = (
        "※ 근거 경계: 현재 자료는 공개 실험·비식별 운전 경계 보정과 모의 계산을 지원하지만 "
        "충전소-차량 full-loop 현장검증, 안전 인증 또는 확정 대피거리를 입증하지 않습니다."
    )
    action_caveat = (
        "※ 가상 조치 상태: 완료 피드백이 확인되지 않아 해당 안전조치가 완료되었다고 단정하지 않습니다. "
        "명령·밸브 피드백·유량 변화를 안전 대응 기록에서 확인하세요."
    )
    for line in text.splitlines():
        line_families: list[tuple[str, str]] = []
        for family, pattern in _UNSUPPORTED_CLAIM_PATTERNS:
            if family not in blocked_families:
                continue
            match = pattern.search(line)
            if match is None or _claim_is_explicitly_limited(line, match):
                continue
            line_families.append((family, match.group(0)[:160]))
        action_families: list[tuple[str, str]] = []
        for family, required_kinds, pattern in _VIRTUAL_ACTION_COMPLETION_PATTERNS:
            match = pattern.search(line)
            if match is None:
                continue
            if any(kind in confirmed_action_kinds for kind in required_kinds):
                continue
            action_families.append((family, match.group(0)[:160]))
        if line_families:
            blocked.extend({"family": family, "text": text} for family, text in line_families)
            # Keep the answer readable and avoid silently dropping the whole
            # response.  The deterministic caveat is the only replacement;
            # verified values and response guidance remain in adjacent lines.
            output.append(caveat)
        if action_families:
            blocked.extend({"family": "unverified_virtual_action_completion",
                            "text": text, "action_family": family}
                           for family, text in action_families)
            output.append(action_caveat)
        if not line_families and not action_families:
            output.append(line)
    guarded = "\n".join(output).strip()
    return guarded, {
        "status": "guarded" if blocked else "clear",
        "blocked_claims": blocked,
        "full_loop_validation_supported": full_loop_supported,
        "source_field_measurement": (manifest.get("source") or {}).get("field_measurement"),
        "virtual_action_feedback": {
            "confirmed_action_kinds": sorted(confirmed_action_kinds),
            "recorded_action_count": len((manifest.get("virtual_safety") or {}).get("actions") or []),
        },
        "claim_limit": "생성 답변의 검증·인증·확정 거리 및 가상 조치 완료 과장을 근거 봉투와 일치시킴",
    }


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
    response_plan_ids: set[str] = set()
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
            response_plan_id = str(condition.get("response_plan_id") or "")
            if response_plan_id:
                response_plan_ids.add(response_plan_id)
            conditions.append({
                "label": str(label),
                "sensor": str(condition.get("sensor_id") or ""),
                "severity": str(condition.get("severity") or condition.get("등급") or ""),
                "state": str(condition.get("state") or ""),
                "response_plan_id": response_plan_id,
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
        "runtime_vehicle_tank_calibration": _runtime_vehicle_tank_calibration_profile(frame),
        "virtual_safety": _virtual_safety_evidence(frame),
        "measured_bank_pressure_envelope": frame.get(
            "measured_bank_pressure_envelope"
        ) or {},
        "virtual_detector_proxy": frame.get("virtual_detector_proxy") or {},
        "virtual_detector_spatial_proxy": frame.get(
            "virtual_detector_spatial_proxy"
        ) or {},
        # A station-side, same-site forecast may inform the answer when it is
        # available, but its claim boundary travels with the frame so the LLM
        # cannot turn it into a safety limit or full-loop validation claim.
        "station_pressure_forecast": frame.get(
            "station_pressure_forecast"
        ) or {},
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
            "claim_limit": (
                "표본 초과 거리이며 현장 대피거리 또는 확정 사고범위가 아님. "
                "결과별 consequence_validation_claim_limit도 함께 적용함"
            ),
        },
        "uncertainty": {
            "sensor_quality_is_simulated": True,
            "assumptions_must_be_named": True,
            "uncalculated_values_must_not_be_invented": True,
        },
    }
    common_header = {
        "pressure_mpa_abs": _finite_number(frame.get("header_pressure_mpa")),
        "temperature_c": _finite_number(frame.get("header_temperature_c")),
        "inventory_kg": _finite_number(frame.get("header_mass_kg")),
        "bank_inflow_g_s": _finite_number(frame.get("header_inflow_g_s")),
    }
    if any(value is not None for value in common_header.values()):
        envelope["common_header"] = {
            **common_header,
            "origin": "DIGITAL_TWIN_PROCESS_STATE",
            "model_status": "PROSPECTIVE_NOT_EXTERNALLY_VALIDATED",
            "claim_limit": (
                "유한 공통 헤더의 모의 상태이며 현장 계측 또는 검증된 배관 치수를 의미하지 않음"
            ),
        }
    traceability = _public_incident_traceability()
    if traceability is not None:
        envelope["response_evidence"]["public_incident_traceability"] = traceability
    khk_inventory = _khk_public_accident_inventory()
    if khk_inventory is not None:
        envelope["response_evidence"]["public_accident_report_inventory"] = khk_inventory
        relevant_precedents = {
            plan_id: public_accident_precedents(plan_id)
            for plan_id in sorted(response_plan_ids)
        }
        relevant_precedents = {
            plan_id: rows for plan_id, rows in relevant_precedents.items() if rows
        }
        if relevant_precedents:
            envelope["response_evidence"]["relevant_public_accident_precedents"] = {
                "by_response_plan": relevant_precedents,
                "citation_only": True,
                "claim_limit": (
                    "현재 response family와 연결된 공개 실제사고의 정성적 선례이며 "
                    "현재 사고의 원인·빈도·결과 또는 조치 효과를 확정하지 않음"
                ),
            }
    local_accident_coverage = _confidential_local_accident_response_coverage()
    if local_accident_coverage is not None:
        envelope["response_evidence"][
            "confidential_local_accident_response_coverage"
        ] = local_accident_coverage
    accidental_release = _public_accidental_release_evidence()
    if accidental_release is not None:
        envelope["response_evidence"]["public_accidental_release_evidence"] = accidental_release
    controlled_flare = _public_controlled_flare_evidence()
    if controlled_flare is not None:
        envelope["response_evidence"]["public_controlled_flare_evidence"] = controlled_flare
    detector_logic = _public_detector_logic_evidence()
    if detector_logic is not None:
        envelope["response_evidence"]["public_detector_logic_evidence"] = detector_logic
    reference_detector = _public_reference_leak_detector_evidence()
    if reference_detector is not None:
        envelope["response_evidence"][
            "public_reference_leak_detector_evidence"
        ] = reference_detector
    spatial_stratification = _public_actual_hydrogen_spatial_stratification_evidence()
    if spatial_stratification is not None:
        envelope["response_evidence"][
            "public_actual_hydrogen_spatial_stratification_evidence"
        ] = spatial_stratification
    dispersion_proxy = _public_dispersion_proxy_evidence()
    if dispersion_proxy is not None:
        envelope["response_evidence"]["public_dispersion_proxy_evidence"] = dispersion_proxy
    grune_ventilation = _public_grune_ventilation_evidence()
    if grune_ventilation is not None:
        envelope["response_evidence"][
            "public_grune_ventilation_evidence"
        ] = grune_ventilation
    h2safe_indoor = _public_h2safe_indoor_surrogate_evidence()
    if h2safe_indoor is not None:
        envelope["response_evidence"][
            "public_h2safe_indoor_surrogate_evidence"
        ] = h2safe_indoor
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
    hytunnel_diagnostic = _public_hytunnel_failure_diagnostic_evidence()
    if hytunnel_diagnostic is not None:
        envelope["response_evidence"][
            "public_hytunnel_failure_diagnostic"
        ] = hytunnel_diagnostic
    methytrucks_tank = _methytrucks_tank_diagnostic_evidence()
    if methytrucks_tank is not None:
        envelope["response_evidence"][
            "methytrucks_tank_diagnostic_boundary"
        ] = methytrucks_tank
    qra_multimethod = _qra_multimethod_comparison_evidence()
    if qra_multimethod is not None:
        envelope["response_evidence"][
            "qra_multimethod_comparison"
        ] = qra_multimethod
    preslhy = _preslhy_validation_boundary()
    if preslhy is not None:
        envelope["response_evidence"]["preslhy_validation_boundary"] = preslhy
    closed_loop = _closed_loop_validation_boundary()
    if closed_loop is not None:
        envelope["response_evidence"][
            "closed_loop_validation_boundary"
        ] = closed_loop
    thermal_observation = _temperature_observation_semantic_boundary()
    if thermal_observation is not None:
        envelope["response_evidence"][
            "temperature_observation_semantic_boundary"
        ] = thermal_observation
    release_boundary = _release_model_validation_boundary()
    if release_boundary is not None:
        envelope["response_evidence"][
            "proust_release_model_validation_boundary"
        ] = release_boundary
    cross_campaign_release = _cross_campaign_release_validation_evidence()
    if cross_campaign_release is not None:
        envelope["response_evidence"][
            "cross_campaign_release_validation_boundary"
        ] = cross_campaign_release
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
    operation_practice = _public_station_operation_practice_reference()
    if operation_practice is not None:
        envelope["response_evidence"][
            "public_station_operation_practice_reference"
        ] = operation_practice
    aggregate_benchmark = _public_station_aggregate_benchmark_reference()
    if aggregate_benchmark is not None:
        envelope["response_evidence"][
            "public_station_aggregate_benchmark_reference"
        ] = aggregate_benchmark
    threeemotion_aggregate = _public_threeemotion_operating_aggregate_reference()
    if threeemotion_aggregate is not None:
        envelope["response_evidence"][
            "public_threeemotion_operating_aggregate_reference"
        ] = threeemotion_aggregate
    public_hrs_leads = _public_hrs_measurement_leads()
    if public_hrs_leads is not None:
        envelope["response_evidence"][
            "public_hrs_measurement_leads"
        ] = public_hrs_leads
    vehicle_side_leads = _public_vehicle_side_h2_measurement_leads()
    if vehicle_side_leads is not None:
        envelope["response_evidence"][
            "public_vehicle_side_h2_measurement_leads"
        ] = vehicle_side_leads
    carb_field_benchmark = _public_carb_hrs_inuse_field_benchmark()
    if carb_field_benchmark is not None:
        envelope["response_evidence"][
            "public_carb_hrs_inuse_field_benchmark"
        ] = carb_field_benchmark
    lifecycle = _confidential_lifecycle_evidence()
    if lifecycle is not None:
        envelope["response_evidence"]["confidential_lifecycle_counter_summary"] = lifecycle
    station_calibration = _confidential_station_calibration_evidence()
    if station_calibration is not None:
        envelope["response_evidence"][
            "confidential_station_boundary_calibration"
        ] = station_calibration
    recharge_dynamics = _confidential_station_recharge_dynamics_evidence()
    if recharge_dynamics is not None:
        envelope["response_evidence"][
            "confidential_station_recharge_dynamics_calibration"
        ] = recharge_dynamics
    cascade_sequence = _confidential_cascade_sequence_evidence()
    if cascade_sequence is not None:
        envelope["response_evidence"][
            "confidential_station_cascade_sequence_holdout"
        ] = cascade_sequence
    recharge_forecast = _confidential_recharge_pressure_forecast_evidence()
    if recharge_forecast is not None:
        envelope["response_evidence"][
            "confidential_station_recharge_pressure_forecast_holdout"
        ] = recharge_forecast
    lifecycle_alignment = _confidential_lifecycle_pressure_alignment_evidence()
    if lifecycle_alignment is not None:
        envelope["response_evidence"][
            "confidential_station_lifecycle_pressure_alignment_holdout"
        ] = lifecycle_alignment
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
    station_thermal = _confidential_station_thermal_evidence()
    if station_thermal is not None:
        envelope["response_evidence"][
            "confidential_station_thermal_dynamics"
        ] = station_thermal
    bank_pressure = _confidential_bank_pressure_evidence()
    if bank_pressure is not None:
        envelope["response_evidence"][
            "confidential_bank_role_pressure_envelopes"
        ] = bank_pressure
    pressure_recheck = _confidential_pressure_recheck_decision()
    if pressure_recheck is not None:
        envelope["response_evidence"][
            "confidential_pressure_recheck_decision"
        ] = pressure_recheck
    operational_profile_recheck = _confidential_operational_profile_recheck()
    if operational_profile_recheck is not None:
        envelope["response_evidence"][
            "confidential_operational_profile_recheck"
        ] = operational_profile_recheck
    channel_quality_recheck = _confidential_station_channel_quality_recheck()
    if channel_quality_recheck is not None:
        envelope["response_evidence"][
            "confidential_station_channel_quality_recheck"
        ] = channel_quality_recheck
    signal_consistency = _confidential_station_signal_consistency_evidence()
    if signal_consistency is not None:
        envelope["response_evidence"][
            "confidential_station_signal_consistency"
        ] = signal_consistency
    station_schema = _confidential_station_schema_evidence()
    if station_schema is not None:
        envelope["response_evidence"][
            "confidential_station_schema_intake"
        ] = station_schema
    local_station_utilization = _confidential_local_station_utilization_evidence()
    if local_station_utilization is not None:
        envelope["response_evidence"][
            "confidential_local_station_data_utilization"
        ] = local_station_utilization
    # Keep the latest local archive revalidation visible to the LLM through
    # the same privacy-bounded API projection used by the UI.  This reads only
    # committed aggregate evidence; raw rows, paths, identifiers and site
    # metadata never enter the prompt.  The projection deliberately preserves
    # the full-loop gate and does not apply parameters at runtime.
    local_evidence = local_station_evidence_summary()
    local_revalidation = local_evidence.get("station_data_revalidation")
    if isinstance(local_revalidation, dict):
        envelope["response_evidence"][
            "local_station_data_revalidation"
        ] = local_revalidation
    # Expose only the aggregate readiness state so the LLM cannot infer that
    # passing station-side checks imply full-loop or journal-ready validation.
    envelope["response_evidence"][
        "validation_readiness"
    ] = _ijhe_readiness_ledger()
    cross_station_bundle = _confidential_cross_station_bundle_recheck_evidence()
    if cross_station_bundle is not None:
        envelope["response_evidence"][
            "confidential_cross_station_bundle_recheck"
        ] = cross_station_bundle
    cross_station_transfer = _local_station_cross_bundle_transfer_evidence()
    if cross_station_transfer is not None:
        envelope["response_evidence"][
            "confidential_local_station_cross_bundle_transfer"
        ] = cross_station_transfer
    local_station_asset_screen = _local_station_asset_screen_evidence()
    if local_station_asset_screen is not None:
        envelope["response_evidence"][
            "confidential_local_station_asset_screen"
        ] = local_station_asset_screen
    local_station_discovery = _local_hydrogen_station_discovery_evidence()
    if local_station_discovery is not None:
        envelope["response_evidence"][
            "confidential_local_station_data_discovery"
        ] = local_station_discovery
    local_attestation_request = _local_station_custodian_attestation_request_evidence()
    if local_attestation_request is not None:
        envelope["response_evidence"][
            "confidential_local_station_attestation_request"
        ] = local_attestation_request
    local_data_deep_scan = _local_data_deep_scan_evidence()
    if local_data_deep_scan is not None:
        envelope["response_evidence"][
            "confidential_local_data_deep_scan"
        ] = local_data_deep_scan
    adjacent_process = _local_adjacent_process_evidence()
    if adjacent_process is not None:
        envelope["response_evidence"][
            "local_adjacent_hydrogen_process_context"
        ] = adjacent_process
    docudata_discovery = _local_docudata_discovery_evidence()
    if docudata_discovery is not None:
        envelope["response_evidence"][
            "local_docudata_full_discovery"
        ] = docudata_discovery
    local_public_catalog = _local_public_validation_catalog_evidence()
    if local_public_catalog is not None:
        envelope["response_evidence"][
            "local_public_validation_catalog"
        ] = local_public_catalog
    local_public_candidate_scan = _local_public_candidate_scan_evidence()
    if local_public_candidate_scan is not None:
        envelope["response_evidence"][
            "local_public_candidate_scan"
        ] = local_public_candidate_scan
    local_candidate_screen = _local_candidate_full_loop_screen_evidence()
    if local_candidate_screen is not None:
        envelope["response_evidence"][
            "local_candidate_full_loop_screen"
        ] = local_candidate_screen
    multisource_feasibility = _confidential_multisource_mapping_feasibility()
    if multisource_feasibility is not None:
        envelope["response_evidence"][
            "confidential_multisource_mapping_feasibility"
        ] = multisource_feasibility
    private_media = _confidential_private_media_evidence()
    if private_media is not None:
        envelope["response_evidence"][
            "confidential_private_media_intake"
        ] = private_media
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
        "runtime_vehicle_tank_calibration": manifest.get(
            "runtime_vehicle_tank_calibration"
        ) or {},
        "measured_bank_pressure_envelope": manifest.get(
            "measured_bank_pressure_envelope"
        ) or {},
        "virtual_detector_proxy": manifest.get("virtual_detector_proxy") or {},
        "virtual_detector_spatial_proxy": manifest.get(
            "virtual_detector_spatial_proxy"
        ) or {},
        "detector_policy": manifest.get("detector_policy") or {},
        "common_header": manifest.get("common_header") or {},
    }
    incident_traceability = evidence.get("public_incident_traceability")
    if isinstance(incident_traceability, dict):
        replay = incident_traceability.get("digital_twin_replay") or {}
        summary["public_incident_traceability"] = {
            "case_count": incident_traceability.get("case_count"),
            "contract_pass": incident_traceability.get("contract_pass") is True,
            "public_source": incident_traceability.get("public_source") or {},
            "digital_twin_replay": {
                key: replay.get(key)
                for key in (
                    "backend", "case_count", "integration_trace_pass_count",
                    "direct_physical_case_count", "partial_proxy_case_count",
                    "response_only_case_count", "canonical_recipe_pass_count",
                    "canonical_recipe_count",
                    "case_narrative_used_for_physical_parameters", "claim_limit",
                )
                if replay.get(key) is not None
            },
        }
    accident_inventory = evidence.get("public_accident_report_inventory")
    if isinstance(accident_inventory, dict):
        khk_replay = accident_inventory.get("digital_twin_replay") or {}
        summary["public_accident_report_inventory"] = {
            "public_report_count": accident_inventory.get("public_report_count"),
            "incident_code_count": accident_inventory.get("incident_code_count"),
            "digital_twin_replay": {
                key: khk_replay.get(key)
                for key in (
                    "backend", "public_report_count", "incident_code_count",
                    "integration_trace_pass_report_count",
                    "integration_trace_pass_incident_code_count",
                    "out_of_scope_report_count", "canonical_recipe_pass_count",
                    "canonical_recipe_count",
                    "report_narrative_used_for_physical_parameters", "claim_limit",
                )
                if khk_replay.get(key) is not None
            },
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
                "boundary_channel_screen", "aggregate", "geometry_diagnostic",
                "claim_supported", "claim_limit",
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
                "evidence_role", "source_count", "file_count", "sample_count",
                "observed_sampling_intervals_s",
                "workbooks_with_mass", "mass_closure_session_count",
                "mass_closure_comparable_session_count",
                "mass_closure_non_comparable_session_count",
                "mass_closure_screen_pass_count",
                "mass_closure_comparable_pass_fraction",
                "mass_closure_pass_ratio_median",
                "mass_closure_comparable_ratio_median",
                "mass_closure_comparable_absolute_relative_difference_pct_median",
                "station_measurement_auxiliary_eligible",
                "full_loop_holdout_eligible",
                "channel_dictionary_present",
                "vehicle_or_receptacle_channels_identified",
                "official_test_context",
                "group_a_c_vehicle_fill_eligible",
                "test_class_interpretation",
                "claim_limit",
            )
            if public_measurement.get(key) is not None
        }
    hytunnel_diagnostic = evidence.get("public_hytunnel_failure_diagnostic")
    if isinstance(hytunnel_diagnostic, dict):
        summary["public_hytunnel_failure_diagnostic"] = {
            "evidence_role": hytunnel_diagnostic.get("evidence_role"),
            "source": hytunnel_diagnostic.get("source") or {},
            "holdout": hytunnel_diagnostic.get("holdout") or {},
            "regimes": hytunnel_diagnostic.get("regimes") or {},
            "findings": hytunnel_diagnostic.get("findings") or [],
            "runtime_parameter_application": hytunnel_diagnostic.get(
                "runtime_parameter_application"
            ) is True,
            "default_model_parameters_changed": hytunnel_diagnostic.get(
                "default_model_parameters_changed"
            ) is True,
            "claim_supported": hytunnel_diagnostic.get("claim_supported") is True,
            "claim_limit": short(hytunnel_diagnostic.get("claim_limit"), 320),
        }
    methytrucks_tank = evidence.get("methytrucks_tank_diagnostic_boundary")
    if isinstance(methytrucks_tank, dict):
        summary["methytrucks_tank_diagnostic_boundary"] = {
            key: methytrucks_tank.get(key)
            for key in (
                "evidence_role", "source", "scope",
                "candidate_244_l_diagnostic", "alternate_77_l_sensitivity",
                "mapping_boundary", "component_diagnostic_eligible",
                "prospective_holdout_eligible", "full_loop_validation_eligible",
                "claim_supported", "required_next_step", "claim_limit",
            )
            if methytrucks_tank.get(key) is not None
        }
    local_public_catalog = evidence.get("local_public_validation_catalog")
    if isinstance(local_public_catalog, dict):
        summary["local_public_validation_catalog"] = {
            "evidence_role": local_public_catalog.get("evidence_role"),
            "scope": local_public_catalog.get("scope") or {},
            "coverage_assessment": local_public_catalog.get(
                "coverage_assessment"
            ) or {},
            "claim_limit": short(local_public_catalog.get("claim_limit"), 320),
        }
    local_public_candidate_scan = evidence.get("local_public_candidate_scan")
    if isinstance(local_public_candidate_scan, dict):
        summary["local_public_candidate_scan"] = {
            "evidence_role": local_public_candidate_scan.get("evidence_role"),
            "scan": local_public_candidate_scan.get("scan") or {},
            "eligibility": local_public_candidate_scan.get("eligibility") or {},
            "claim_limit": short(
                local_public_candidate_scan.get("claim_limit"), 320
            ),
        }
    local_attestation_request = evidence.get(
        "confidential_local_station_attestation_request"
    )
    if isinstance(local_attestation_request, dict):
        summary["confidential_local_station_attestation_request"] = {
            "evidence_role": local_attestation_request.get("evidence_role"),
            "status": local_attestation_request.get("status"),
            "observed_local_archive": local_attestation_request.get(
                "observed_local_archive"
            ) or {},
            "requested_attestations": [
                {
                    "id": item.get("id"),
                    "acceptance": item.get("acceptance"),
                    "enables": item.get("enables") or [],
                }
                for item in local_attestation_request.get("requested_attestations") or []
                if isinstance(item, dict)
            ],
            "current_gate_effect": local_attestation_request.get(
                "current_gate_effect"
            ) or {},
            "claim_limit": short(local_attestation_request.get("claim_limit"), 320),
        }
    qra = evidence.get("qra_multimethod_comparison")
    if isinstance(qra, dict):
        summary["qra_multimethod_comparison"] = {
            key: qra.get(key)
            for key in (
                "evidence_role", "source", "method_count", "retained_row_count",
                "matched_group_count", "maximum_matched_method_ratio",
                "runtime_case_count", "runtime_thermal_within_envelope_count",
                "runtime_overpressure_within_envelope_count", "cases",
                "automatic_calibration_performed", "experimental_validation",
                "operator_rule", "claim_limit",
            )
            if qra.get(key) is not None
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
            "mixed_convection_diagnostic": closed_loop.get(
                "mixed_convection_diagnostic"
            ) or {},
            "runtime_model_parameter_changed": closed_loop.get(
                "runtime_model_parameter_changed"
            ),
            "claim_supported": closed_loop.get("claim_supported"),
            "claim_limit": short(closed_loop.get("claim_limit")),
        }
    multisource = evidence.get("confidential_multisource_mapping_feasibility")
    if isinstance(multisource, dict):
        summary["confidential_multisource_mapping_feasibility"] = {
            key: multisource.get(key)
            for key in (
                "evidence_role", "co_located_workbook_candidates",
                "candidate_worksheet_count", "measurement_rows_read",
                "unambiguous_full_loop_mapping_available",
                "full_loop_holdout_eligible", "decision", "claim_limit",
            )
            if multisource.get(key) is not None
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
    cross_campaign_release = evidence.get(
        "cross_campaign_release_validation_boundary"
    )
    if isinstance(cross_campaign_release, dict):
        summary["cross_campaign_release_validation_boundary"] = {
            key: cross_campaign_release.get(key)
            for key in (
                "evidence_role", "campaigns", "eligible_campaign_count",
                "supported_campaign_count", "failed_campaign_count",
                "ineligible_campaign_count",
                "universal_release_validation_supported",
                "apparatus_resolved_holdout_received",
                "apparatus_resolved_holdout_run",
                "runtime_model_changed_after_outcomes", "claim_limit",
            )
            if cross_campaign_release.get(key) is not None
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
    operation_practice = evidence.get(
        "public_station_operation_practice_reference"
    )
    if isinstance(operation_practice, dict):
        summary["public_station_operation_practice_reference"] = {
            "evidence_role": operation_practice.get("evidence_role"),
            "source": operation_practice.get("source") or {},
            "reported_practices": operation_practice.get(
                "reported_practices"
            ) or {},
            "allowed_use": operation_practice.get("allowed_use") or [],
            "not_allowed": operation_practice.get("not_allowed") or [],
            "claim_limit": short(operation_practice.get("claim_limit"), 320),
        }
    aggregate_benchmark = evidence.get(
        "public_station_aggregate_benchmark_reference"
    )
    if isinstance(aggregate_benchmark, dict):
        aggregate = aggregate_benchmark.get("reported_aggregate") or {}
        summary["public_station_aggregate_benchmark_reference"] = {
            "evidence_role": aggregate_benchmark.get("evidence_role"),
            "source": aggregate_benchmark.get("source") or {},
            "reported_aggregate": {
                key: aggregate.get(key)
                for key in (
                    "observation_period",
                    "refueling_event_count_approx",
                    "dispensed_hydrogen_kg_approx",
                    "reported_domains",
                    "reported_2020_q1_energy_kwh_per_kg_range",
                    "reported_2020_q1_site_efficiency_percent_max",
                )
                if aggregate.get(key) is not None
            },
            "allowed_use": aggregate_benchmark.get("allowed_use") or [],
            "not_allowed": aggregate_benchmark.get("not_allowed") or [],
            "claim_limit": short(aggregate_benchmark.get("claim_limit"), 360),
        }
    threeemotion_aggregate = evidence.get(
        "public_threeemotion_operating_aggregate_reference"
    )
    if isinstance(threeemotion_aggregate, dict):
        summary["public_threeemotion_operating_aggregate_reference"] = {
            "evidence_role": threeemotion_aggregate.get("evidence_role"),
            "source": threeemotion_aggregate.get("source") or {},
            "reported_aggregate": threeemotion_aggregate.get(
                "reported_aggregate"
            ) or {},
            "allowed_use": threeemotion_aggregate.get("allowed_use") or [],
            "not_allowed": threeemotion_aggregate.get("not_allowed") or [],
            "claim_limit": short(threeemotion_aggregate.get("claim_limit"), 360),
        }
    measurement_leads = evidence.get("public_hrs_measurement_leads")
    if isinstance(measurement_leads, dict):
        summary["public_hrs_measurement_leads"] = {
            "evidence_role": measurement_leads.get("evidence_role"),
            "status": measurement_leads.get("status"),
            "leads": [
                {
                    key: lead.get(key)
                    for key in (
                        "id", "title", "url", "reported_scope",
                        "raw_trace_public", "decision", "eligible_use",
                        "ineligible_use", "abnormal_data_provenance",
                    )
                    if lead.get(key) is not None
                }
                for lead in measurement_leads.get("leads") or []
                if isinstance(lead, dict)
            ],
            "request_package_requirements": measurement_leads.get(
                "request_package_requirements"
            ) or [],
            "full_loop_external_validation_supported": False,
            "parameter_fitting_supported": False,
            "saga_effectiveness_supported": False,
            "claim_limit": short(measurement_leads.get("claim_limit"), 280),
        }
    local_candidate_screen = evidence.get("local_candidate_full_loop_screen")
    if isinstance(local_candidate_screen, dict):
        summary["local_candidate_full_loop_screen"] = {
            "evidence_role": local_candidate_screen.get("evidence_role"),
            "decision": local_candidate_screen.get("decision"),
            "candidates": [
                {
                    key: candidate.get(key)
                    for key in (
                        "id", "evidence_class", "decision",
                        "measured_time_series_present",
                        "vehicle_or_dispenser_boundary_attested",
                        "station_controller_or_cascade_state_attested",
                        "esd_or_safety_interlock_trace_attested",
                        "vehicle_protocol_trace_attested", "eligible_use",
                        "ineligible_use", "claim_limit",
                    )
                    if candidate.get(key) is not None
                }
                for candidate in local_candidate_screen.get("candidates") or []
                if isinstance(candidate, dict)
            ],
            "coverage_assessment": local_candidate_screen.get(
                "coverage_assessment"
            ) or {},
            "next_action": local_candidate_screen.get("next_action"),
        }
    vehicle_side_leads = evidence.get("public_vehicle_side_h2_measurement_leads")
    if isinstance(vehicle_side_leads, dict):
        summary["public_vehicle_side_h2_measurement_leads"] = {
            "evidence_role": vehicle_side_leads.get("evidence_role"),
            "leads": [
                {
                    key: lead.get(key)
                    for key in (
                        "id", "title", "article_doi", "reported_measurements",
                        "reported_scope", "raw_trace_status",
                        "full_loop_eligibility", "eligible_use", "ineligible_use",
                        "next_access_request", "claim_limit",
                    )
                    if lead.get(key) is not None
                }
                for lead in vehicle_side_leads.get("leads") or []
                if isinstance(lead, dict)
            ],
            "full_loop_external_validation_supported": False,
            "parameter_fitting_supported": False,
            "saga_effectiveness_supported": False,
            "claim_limit": short(vehicle_side_leads.get("claim_limit"), 280),
        }
    carb = evidence.get("public_carb_hrs_inuse_field_benchmark")
    if isinstance(carb, dict):
        summary["public_carb_hrs_inuse_field_benchmark"] = {
            "evidence_role": carb.get("evidence_role"),
            "source": carb.get("source") or {},
            "population": carb.get("population") or {},
            "category_station_pass_rates": (
                carb.get("category_station_pass_rates") or {}
            ),
            "full_loop_external_holdout_eligible": False,
            "dynamic_model_parameter_calibration_eligible": False,
            "claim_limit": short(carb.get("claim_limit")),
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
    reference_detector = evidence.get("public_reference_leak_detector_evidence")
    if isinstance(reference_detector, dict):
        summary["public_reference_leak_detector_evidence"] = {
            key: reference_detector.get(key)
            for key in (
                "doi", "related_article_doi", "evidence_role", "observation_count",
                "detector_class_count", "evaluated_series_count", "series",
                "joint_pass", "runtime_application",
                "spatial_detector_transfer_gate_changed",
                "full_loop_validation_supported", "claim_limit",
            )
            if reference_detector.get(key) is not None
        }
    spatial_stratification = evidence.get(
        "public_actual_hydrogen_spatial_stratification_evidence"
    )
    if isinstance(spatial_stratification, dict):
        summary["public_actual_hydrogen_spatial_stratification_evidence"] = {
            key: spatial_stratification.get(key)
            for key in (
                "dataset_doi", "article_doi", "evidence_role",
                "experiment_count", "sensor_count_per_experiment",
                "sensor_case_observation_count",
                "top_placement_highest_case_mean_count", "placements",
                "near_source_bottom",
                "bounded_guidance", "post_access_descriptive_evidence",
                "runtime_application", "h2safe_gate_changed",
                "independent_spatial_validation_supported",
                "full_loop_validation_supported", "claim_limit",
            )
            if spatial_stratification.get(key) is not None
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
    h2safe_indoor = evidence.get("public_h2safe_indoor_surrogate_evidence")
    if isinstance(h2safe_indoor, dict):
        summary["public_h2safe_indoor_surrogate_evidence"] = {
            key: h2safe_indoor.get(key)
            for key in (
                "doi", "evidence_role", "medium", "case_count",
                "lab_sensor_coordinate_counts",
                "timestamped_signal_schema_available",
                "qualitative_geometry_hvac_context_available",
                "numerical_hydrogen_alarm_or_trip_threshold_calibration",
                "full_loop_station_vehicle_validation",
                "runtime_parameter_updated", "claim_limit",
            )
            if h2safe_indoor.get(key) is not None
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
    cross_station_bundle = evidence.get(
        "confidential_cross_station_bundle_recheck"
    )
    if isinstance(cross_station_bundle, dict):
        summary["confidential_cross_station_bundle_recheck"] = {
            key: cross_station_bundle.get(key)
            for key in (
                "evidence_role", "bundle_count", "bundles",
                "station_side_transfer_candidate",
                "full_loop_external_validation_supported",
                "quantitative_consequence_validation_supported", "claim_limit",
            )
            if cross_station_bundle.get(key) is not None
        }
    cross_station_transfer = evidence.get(
        "confidential_local_station_cross_bundle_transfer"
    )
    if isinstance(cross_station_transfer, dict):
        summary["confidential_local_station_cross_bundle_transfer"] = {
            key: cross_station_transfer.get(key)
            for key in (
                "evidence_role", "candidate_margin_mpa",
                "calibration_bundle", "transfer_bundle",
                "candidate_relative_transfer_median_error_percent",
                "candidate_inside_transfer_p05_p95",
                "fixed_candidate_corroborated_on_transfer_bundle",
                "full_loop_external_validation_supported",
                "runtime_parameter_application", "claim_limit",
            )
            if cross_station_transfer.get(key) is not None
        }
    accidental = evidence.get("public_accidental_release_evidence")
    if isinstance(accidental, dict):
        reported_findings = accidental.get("reported_findings") or {}
        summary["public_accidental_release_evidence"] = {
            key: accidental.get(key) for key in (
                "article_doi", "zenodo_doi", "license", "evidence_role",
                "consequence_and_ignition_grounding_eligible",
                "full_loop_station_vehicle_holdout_eligible",
            ) if accidental.get(key) is not None
        }
        summary["public_accidental_release_evidence"]["reported_findings"] = {
            key: reported_findings.get(key)
            for key in (
                "experiment_count",
                "ignition_observed_case_count",
                "no_ignition_case_count",
                "remote_or_obstructed_ignition_reported",
                "delayed_ignition_delay_s_reported",
                "fire_jet_length_m_greater_than_reported",
                "ignition_probability_estimated",
                "ignition_mechanism_confirmed",
                "qualifier",
            )
            if reported_findings.get(key) is not None
        }
        summary["public_accidental_release_evidence"]["claim_limit"] = short(
            accidental.get("claim_limit")
        )
    controlled_flare = evidence.get("public_controlled_flare_evidence")
    if isinstance(controlled_flare, dict):
        findings = controlled_flare.get("reported_findings") or {}
        runtime_use = controlled_flare.get("runtime_use") or {}
        summary["public_controlled_flare_evidence"] = {
            "doi": controlled_flare.get("doi"),
            "nitrogen_operating_boundary_volpct": findings.get(
                "maximum_reported_nitrogen_fraction_for_continued_operation_volpct"
            ),
            "tested_safeguards": list(findings.get("tested_safeguards") or []),
            "engineered_flare_only": runtime_use.get(
                "applies_only_to_engineered_approved_controlled_flare"
            ) is True,
            "ad_hoc_vent_ignition_authorized": False,
            "claim_limit": short(controlled_flare.get("claim_limit")),
        }
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
    recharge_dynamics = evidence.get(
        "confidential_station_recharge_dynamics_calibration"
    )
    if isinstance(recharge_dynamics, dict):
        summary["confidential_station_recharge_dynamics_calibration"] = {
            key: recharge_dynamics.get(key)
            for key in (
                "evidence_role", "artifact", "profile_id", "files_read",
                "sampled_rows", "state_transition_count",
                "observed_off_to_on_intervals",
                "candidate_minimum_recharge_off_time_s", "temporal_holdout",
                "opt_in_runtime_parameter_available",
                "runtime_application_block_reason",
                "prior_single_trace_profile_superseded",
                "default_model_parameters_changed",
                "observed_high_bank_restart_pressure_band",
                "full_station_vehicle_validation", "claim_limit",
            )
            if recharge_dynamics.get(key) is not None
        }
    cascade_sequence = evidence.get(
        "confidential_station_cascade_sequence_holdout"
    )
    if isinstance(cascade_sequence, dict):
        summary["confidential_station_cascade_sequence_holdout"] = {
            key: cascade_sequence.get(key)
            for key in (
                "evidence_role", "artifact", "files_read", "calibration",
                "holdout", "cascade_controller_structure_supported",
                "runtime_parameter_application", "vehicle_fill_validation",
                "full_loop_holdout_eligible", "independent_external_validation",
                "claim_limit",
            )
            if cascade_sequence.get(key) is not None
        }
    recharge_forecast = evidence.get(
        "confidential_station_recharge_pressure_forecast_holdout"
    )
    if isinstance(recharge_forecast, dict):
        summary["confidential_station_recharge_pressure_forecast_holdout"] = {
            key: recharge_forecast.get(key)
            for key in (
                "evidence_role", "artifact", "files_read", "sampled_rows",
                "calibration_case_count", "holdout_case_count",
                "fitted_continuation_gain_by_bank", "holdout_metrics",
                "short_horizon_station_pressure_forecast_supported",
                "runtime_parameter_application", "default_model_parameters_changed",
                "vehicle_fill_validation", "full_loop_holdout_eligible",
                "independent_external_validation", "claim_limit",
            )
            if recharge_forecast.get(key) is not None
        }
    lifecycle_alignment = evidence.get(
        "confidential_station_lifecycle_pressure_alignment_holdout"
    )
    if isinstance(lifecycle_alignment, dict):
        summary["confidential_station_lifecycle_pressure_alignment_holdout"] = {
            key: lifecycle_alignment.get(key)
            for key in (
                "evidence_role", "artifact", "files", "rows", "counter_quality",
                "calibration", "holdout", "recall_shift_by_bank", "eligibility",
                "screens", "pressure_completion_counter_alignment_supported",
                "recharge_event_detector_corroborated",
                "runtime_parameter_application", "default_model_parameters_changed",
                "vehicle_fill_validation", "full_loop_holdout_eligible",
                "independent_external_validation", "claim_limit",
            )
            if lifecycle_alignment.get(key) is not None
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
    station_thermal = evidence.get("confidential_station_thermal_dynamics")
    if isinstance(station_thermal, dict):
        summary["confidential_station_thermal_dynamics"] = {
            key: station_thermal.get(key)
            for key in (
                "evidence_role", "artifact", "protocol", "status",
                "mapped_channel_family_counts", "proposed_engineering_units",
                "proposals_attested", "confirmation_required",
                "result_available", "channel_attestation", "temporal_stability",
                "station_component_thermal_envelope_supported",
                "runtime_parameter_application", "vehicle_fill_thermal_validation",
                "full_station_vehicle_validation", "full_loop_holdout_eligible",
                "default_model_parameters_changed", "claim_limit",
            )
            if station_thermal.get(key) is not None
        }
    signal_consistency = evidence.get("confidential_station_signal_consistency")
    if isinstance(signal_consistency, dict):
        summary["confidential_station_signal_consistency"] = {
            key: signal_consistency.get(key)
            for key in (
                "evidence_role", "artifact", "analysis_status",
                "candidate_pairs_evaluated", "strong_consistency_pairs",
                "files_with_strong_consistency_pair", "candidate_pair_aggregate",
                "strong_pair_aggregate", "channel_roles_attested",
                "flow_units_attested", "totalizer_reset_semantics_attested",
                "calibration_status_attested", "flow_parameter_fit_supported",
                "absolute_mass_flow_supported", "full_station_vehicle_validation",
                "independent_holdout", "claim_limit",
            )
            if signal_consistency.get(key) is not None
        }
    bank_pressure = evidence.get("confidential_bank_role_pressure_envelopes")
    if isinstance(bank_pressure, dict):
        summary["confidential_bank_role_pressure_envelopes"] = {
            key: bank_pressure.get(key)
            for key in (
                "evidence_role", "artifact", "profiles",
                "bank_role_mapping_attested", "pressure_scale_mapping_attested",
                "machine_readable_unit_dictionary_present",
                "temperature_or_flow_roles_attested",
                "bank_role_pressure_diagnostic_supported",
                "runtime_parameter_application", "full_station_vehicle_validation",
                "full_loop_holdout_eligible", "default_model_parameters_changed",
                "claim_limit",
            )
            if bank_pressure.get(key) is not None
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
    operational_profile_recheck = evidence.get(
        "confidential_operational_profile_recheck"
    )
    if isinstance(operational_profile_recheck, dict):
        summary["confidential_operational_profile_recheck"] = {
            key: operational_profile_recheck.get(key)
            for key in (
                "evidence_role", "profile_match", "fields_compared",
                "fields_omitted_without_attestation", "sampled_rows",
                "channel_roles", "committed_profile_replaced",
                "measured_boundary_calibration_remains_opt_in",
                "full_station_vehicle_validation", "claim_limit",
            )
            if operational_profile_recheck.get(key) is not None
        }
    channel_quality_recheck = evidence.get(
        "confidential_station_channel_quality_recheck"
    )
    if isinstance(channel_quality_recheck, dict):
        summary["confidential_station_channel_quality_recheck"] = {
            key: channel_quality_recheck.get(key)
            for key in (
                "evidence_role", "files_read", "sampled_rows",
                "parseable_timestamp_fraction", "timebase", "roles",
                "discrete_state_transition_count",
                "temperature_or_flow_parameter_fit_supported",
                "full_station_vehicle_validation", "full_loop_holdout_eligible",
                "claim_limit",
            )
            if channel_quality_recheck.get(key) is not None
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
    local_station_utilization = evidence.get(
        "confidential_local_station_data_utilization"
    )
    if isinstance(local_station_utilization, dict):
        summary["confidential_local_station_data_utilization"] = {
            key: local_station_utilization.get(key)
            for key in (
                "evidence_role", "artifact", "inventory", "utilization",
                "semantic_attestation", "assessment", "claim_limit",
            )
            if local_station_utilization.get(key) is not None
        }
    local_revalidation = evidence.get("local_station_data_revalidation")
    if isinstance(local_revalidation, dict):
        summary["local_station_data_revalidation"] = {
            "evidence_role": local_revalidation.get("evidence_role"),
            "generated_at": local_revalidation.get("generated_at"),
            "inventory": local_revalidation.get("inventory") or {},
            "sampled_candidate_manifest": local_revalidation.get(
                "sampled_candidate_manifest"
            ) or {},
            "broader_local_screen": local_revalidation.get(
                "broader_local_screen"
            ) or {},
            "decision": local_revalidation.get("decision") or {},
            "claim_boundary": short(local_revalidation.get("claim_boundary"), 320),
        }
    readiness = evidence.get("validation_readiness")
    if isinstance(readiness, dict):
        summary["validation_readiness"] = {
            key: readiness.get(key)
            for key in (
                "evidence_role", "status", "ledger_integrity", "generated_at",
                "gate_counts", "bounded_ijhe_submission_ready",
                "full_user_objective_ready", "goal_completion_permitted",
                "full_loop_external_validation_supported",
                "expert_effectiveness_evaluation_supported",
                "independent_expert_review_complete", "claim_boundary",
            )
            if readiness.get(key) is not None
        }
    local_station_asset_screen = evidence.get(
        "confidential_local_station_asset_screen"
    )
    if isinstance(local_station_asset_screen, dict):
        summary["confidential_local_station_asset_screen"] = {
            key: local_station_asset_screen.get(key)
            for key in (
                "evidence_role", "artifact", "scenario_matrix",
                "asset_bundles", "coverage", "claim_limit",
            )
            if local_station_asset_screen.get(key) is not None
        }
    local_station_discovery = evidence.get(
        "confidential_local_station_data_discovery"
    )
    if isinstance(local_station_discovery, dict):
        discovery_groups = local_station_discovery.get("candidate_groups") or {}
        measured_group = discovery_groups.get(
            "confidential_station_measurement_bundle"
        ) or {}
        scenario_group = discovery_groups.get(
            "adjacent_liquid_hydrogen_operations_bundle"
        ) or {}
        adjacent_operational_group = discovery_groups.get(
            "adjacent_h2_operational_telemetry"
        ) or {}
        wide_equipment_group = discovery_groups.get(
            "wide_equipment_boundary_recheck"
        ) or {}
        wide_continuity_group = discovery_groups.get(
            "wide_equipment_continuity_screen"
        ) or {}
        media_group = discovery_groups.get("engineering_and_media_context") or {}
        operational_media_group = discovery_groups.get(
            "local_operational_video_collection"
        ) or {}
        summary["confidential_local_station_data_discovery"] = {
            "evidence_role": local_station_discovery.get("evidence_role"),
            "artifact": local_station_discovery.get("artifact"),
            "inventory": {
                "station_measurement_file_count": measured_group.get("file_count"),
                "station_measurement_physical_rows": measured_group.get(
                    "physical_rows"
                ),
                "station_measurement_deduplicated_rows": measured_group.get(
                    "deduplicated_rows"
                ),
                "scenario_step_rows": scenario_group.get("scenario_step_rows"),
                "adjacent_operational_telemetry_rows": adjacent_operational_group.get(
                    "telemetry_rows"
                ),
                "adjacent_operational_signal_key_count": adjacent_operational_group.get(
                    "telemetry_signal_key_count"
                ),
                "adjacent_operational_time_span_hours": adjacent_operational_group.get(
                    "telemetry_time_span_hours"
                ),
                "wide_equipment_file_count": wide_equipment_group.get(
                    "file_count"
                ),
                "wide_equipment_row_count": wide_equipment_group.get(
                    "row_count"
                ),
                "wide_equipment_schema_width": wide_equipment_group.get(
                    "schema_width"
                ),
                "wide_equipment_median_sample_period_s": wide_equipment_group.get(
                    "median_sample_period_s"
                ),
                "wide_equipment_vehicle_candidate_count": wide_equipment_group.get(
                    "vehicle_or_dispenser_candidate_count"
                ),
                "wide_equipment_continuity_file_count": wide_continuity_group.get(
                    "wide_file_count"
                ),
                "wide_equipment_continuity_row_count": wide_continuity_group.get(
                    "wide_row_count"
                ),
                "wide_equipment_timestamp_parse_failures": wide_continuity_group.get(
                    "timestamp_parse_failures"
                ),
                "wide_equipment_negative_interval_count": wide_continuity_group.get(
                    "negative_interval_count"
                ),
                "wide_equipment_median_positive_interval_s": wide_continuity_group.get(
                    "median_positive_interval_s"
                ),
                "wide_equipment_maximum_positive_interval_s": wide_continuity_group.get(
                    "maximum_positive_interval_s"
                ),
                "wide_equipment_state_transition_count": wide_continuity_group.get(
                    "state_transition_count"
                ),
                "engineering_document_count": media_group.get("document_count"),
                "engineering_image_count": media_group.get("image_count"),
                "engineering_video_count": media_group.get("video_count"),
                "operational_video_file_count": operational_media_group.get(
                    "file_count"
                ),
            },
            "coverage_assessment": local_station_discovery.get(
                "coverage_assessment"
            ) or {},
            "claim_limit": local_station_discovery.get("claim_limit"),
        }
    local_data_deep_scan = evidence.get("confidential_local_data_deep_scan")
    if isinstance(local_data_deep_scan, dict):
        summary["confidential_local_data_deep_scan"] = {
            key: local_data_deep_scan.get(key)
            for key in (
                "evidence_role", "artifact", "measured_station_bundle",
                "broad_candidate_inventory", "candidate_classes",
                "full_loop_decision", "claim_limit",
            )
            if local_data_deep_scan.get(key) is not None
        }
    adjacent_process = evidence.get("local_adjacent_hydrogen_process_context")
    if isinstance(adjacent_process, dict):
        summary["local_adjacent_hydrogen_process_context"] = {
            "evidence_role": adjacent_process.get("evidence_role"),
            "domain_classification": adjacent_process.get("domain_classification"),
            "high_pressure_process": adjacent_process.get(
                "high_pressure_process"
            ) or {},
            "liquid_hydrogen_centre_context": adjacent_process.get(
                "liquid_hydrogen_centre_context"
            ) or {},
            "runtime_parameter_application": adjacent_process.get(
                "runtime_parameter_application"
            ) is True,
            "station_to_vehicle_full_loop_validation": adjacent_process.get(
                "station_to_vehicle_full_loop_validation"
            ) is True,
            "claim_limit": short(adjacent_process.get("claim_limit"), 320),
        }
    docudata_discovery = evidence.get("local_docudata_full_discovery")
    if isinstance(docudata_discovery, dict):
        summary["local_docudata_full_discovery"] = {
            "evidence_role": docudata_discovery.get("evidence_role"),
            "broad_scan": docudata_discovery.get("broad_scan") or {},
            "refined_header_screen": docudata_discovery.get(
                "refined_header_screen"
            ) or {},
            "eligibility": docudata_discovery.get("eligibility") or {},
            "claim_limit": short(docudata_discovery.get("claim_limit"), 320),
        }
    private_media = evidence.get("confidential_private_media_intake")
    if isinstance(private_media, dict):
        summary["confidential_private_media_intake"] = {
            key: private_media.get(key)
            for key in (
                "evidence_role", "artifact", "image_count", "video_count",
                "video_decoded_count", "video_probe_undecodable_count",
                "screen_recorded_logger_candidate", "machine_readable_trace_present",
                "ocr_or_frame_values_used_for_calibration",
                "channel_inventory_candidate", "parameter_fit_permitted",
                "full_loop_holdout_eligible", "claim_limit",
            )
            if private_media.get(key) is not None
        }
    relevant_precedents = evidence.get("relevant_public_accident_precedents")
    if isinstance(relevant_precedents, dict):
        summary["relevant_public_accident_precedents"] = relevant_precedents
    public_source_links = _public_source_links(evidence)
    if public_source_links:
        summary["public_source_links"] = public_source_links
    impact = manifest.get("impact") or {}
    summary["impact_status"] = impact.get("calculation_status")
    summary["impact_result_count"] = impact.get("result_count", 0)
    summary["evidence_digest"] = manifest.get("evidence_digest")
    return summary


def prompt_decision_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the small evidence envelope sent to an interactive LLM.

    ``build_evidence_manifest`` intentionally keeps every auditable artifact,
    so it can exceed a provider context budget by an order of magnitude.  The
    API still returns that complete manifest and its digest to the caller.  An
    LLM only needs the current calculation boundary, calibration state and
    decision-relevant validation limits.  This projection preserves those
    facts without leaking restricted identifiers or displacing live signals,
    active conditions and response steps from the prompt.
    """

    def short(value: Any, limit: int = 150) -> str:
        text = str(value or "")
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def selected(mapping: Any, keys: tuple[str, ...]) -> dict[str, Any]:
        if not isinstance(mapping, dict):
            return {}
        return {key: mapping[key] for key in keys if mapping.get(key) is not None}

    impact = manifest.get("impact") or {}
    compact_impacts: list[dict[str, Any]] = []
    for raw in impact.get("results") or []:
        if not isinstance(raw, dict):
            continue
        row = selected(raw, (
            "node_id", "node_name", "calculation_status", "calculation_basis",
            "pressure_sensor", "temperature_sensor", "current_pressure_mpa",
            "current_temperature_c", "orifice_diameter_mm",
            "maximum_heat_flux_w_m2", "maximum_overpressure_pa",
            "indoor_status", "maximum_indoor_overpressure_pa",
            "ignited_enclosure_status", "ignited_enclosure_model",
            "maximum_ignited_enclosure_overpressure_pa",
            "ignited_enclosure_peak_time_s",
            "ignited_enclosure_average_mass_flow_kg_s",
            "ignited_enclosure_volume_m3", "ignited_enclosure_vent_area_m2",
            "ignited_enclosure_external_holdout_supported",
            "ignited_enclosure_validation_artifact",
            "sampled_effect_radius_m", "sampled_thermal_radius_m",
            "sampled_overpressure_radius_m", "sampled_next_distance_m",
            "thermal_range_status", "overpressure_range_status",
            "flammable_plume_streamline_distance_m", "effect_range_status",
            "consequence_validation_scope", "geometry_display_mapping_verified",
            "source_depletion_external_holdout_supported",
            "release_source_boundary", "process_flow_limit_kg_s",
            "physical_orifice_diameter_m", "consequence_equivalent_orifice_diameter_m",
            "flow_limited_equivalent_orifice_applied", "flow_limited_consequence_status",
            "literature_delayed_ignition_status",
            "literature_delayed_ignition_in_validation_domain",
            "literature_delayed_ignition_5kpa_radial_distance_m",
            "literature_delayed_ignition_no_harm_radial_distance_m",
            "literature_delayed_ignition_injury_radial_distance_m",
            "literature_delayed_ignition_fatality_radial_distance_m",
            "literature_delayed_ignition_distance_origin",
            "literature_delayed_ignition_site_safety_distance",
            "literature_delayed_ignition_doi",
            "literature_jet_flame_status",
            "literature_jet_flame_in_validation_domain",
            "literature_jet_flame_length_m",
            "literature_jet_flame_mass_flow_basis",
            "literature_jet_flame_is_harm_distance",
            "literature_jet_flame_doi",
            "full_station_vehicle_validation_supported",
            "site_specific_safety_distance_supported",
        ))
        if raw.get("consequence_validation_claim_limit"):
            row["consequence_validation_claim_limit"] = short(
                raw["consequence_validation_claim_limit"]
            )
        if raw.get("ignited_enclosure_claim_limit"):
            row["ignited_enclosure_claim_limit"] = short(
                raw["ignited_enclosure_claim_limit"]
            )
        if raw.get("literature_delayed_ignition_claim_limit"):
            row["literature_delayed_ignition_claim_limit"] = short(
                raw["literature_delayed_ignition_claim_limit"]
            )
        if raw.get("literature_jet_flame_claim_limit"):
            row["literature_jet_flame_claim_limit"] = short(
                raw["literature_jet_flame_claim_limit"]
            )
        if row:
            compact_impacts.append(row)

    runtime = manifest.get("runtime_calibration") or {}
    recharge_dynamics = runtime.get("station_recharge_dynamics") or {}
    detector = manifest.get("detector_policy") or {}
    virtual_safety = manifest.get("virtual_safety") or {}
    response = manifest.get("response_evidence") or {}
    closed_loop = response.get("closed_loop_validation_boundary") or {}
    closed_loop_aggregate = closed_loop.get("aggregate") or {}
    release = response.get("proust_release_model_validation_boundary") or {}
    cross_campaign_release = response.get(
        "cross_campaign_release_validation_boundary"
    ) or {}
    preslhy = response.get("preslhy_validation_boundary") or {}
    preslhy_holdout = preslhy.get("independent_holdout") or {}
    operating_screen = response.get("public_operating_envelope_screen") or {}
    operation_practice = response.get(
        "public_station_operation_practice_reference"
    ) or {}
    aggregate_benchmark = response.get(
        "public_station_aggregate_benchmark_reference"
    ) or {}
    threeemotion_aggregate = response.get(
        "public_threeemotion_operating_aggregate_reference"
    ) or {}
    methytrucks_tank = response.get("methytrucks_tank_diagnostic_boundary") or {}
    methytrucks_scope = methytrucks_tank.get("scope") or {}
    methytrucks_244 = methytrucks_tank.get("candidate_244_l_diagnostic") or {}
    methytrucks_mapping = methytrucks_tank.get("mapping_boundary") or {}
    qra_multimethod = response.get("qra_multimethod_comparison") or {}
    incident = response.get("public_incident_traceability") or {}
    accident_inventory = response.get("public_accident_report_inventory") or {}
    khk_replay = accident_inventory.get("digital_twin_replay") or {}
    relevant_precedents = response.get("relevant_public_accident_precedents") or {}
    accidental_release = response.get("public_accidental_release_evidence") or {}
    controlled_flare = response.get("public_controlled_flare_evidence") or {}
    local_incident = response.get("confidential_local_accident_response_coverage") or {}
    cross_station_bundle = response.get(
        "confidential_cross_station_bundle_recheck"
    ) or {}
    cross_station_transfer = response.get(
        "confidential_local_station_cross_bundle_transfer"
    ) or {}
    multisource = response.get("confidential_multisource_mapping_feasibility") or {}
    thermal_observation = response.get("temperature_observation_semantic_boundary") or {}
    station_thermal = response.get("confidential_station_thermal_dynamics") or {}
    signal_consistency = response.get(
        "confidential_station_signal_consistency"
    ) or {}
    cascade_sequence = response.get(
        "confidential_station_cascade_sequence_holdout"
    ) or {}
    recharge_forecast = response.get(
        "confidential_station_recharge_pressure_forecast_holdout"
    ) or {}
    lifecycle_alignment = response.get(
        "confidential_station_lifecycle_pressure_alignment_holdout"
    ) or {}
    local_station_utilization = response.get(
        "confidential_local_station_data_utilization"
    ) or {}
    local_revalidation = response.get("local_station_data_revalidation") or {}
    readiness = response.get("validation_readiness") or {}
    local_station_asset_screen = response.get(
        "confidential_local_station_asset_screen"
    ) or {}
    local_station_discovery = response.get(
        "confidential_local_station_data_discovery"
    ) or {}
    local_attestation_request = response.get(
        "confidential_local_station_attestation_request"
    ) or {}
    local_data_deep_scan = response.get(
        "confidential_local_data_deep_scan"
    ) or {}
    adjacent_process = response.get(
        "local_adjacent_hydrogen_process_context"
    ) or {}
    docudata_discovery = response.get("local_docudata_full_discovery") or {}
    local_public_catalog = response.get("local_public_validation_catalog") or {}
    local_public_candidate_scan = response.get("local_public_candidate_scan") or {}
    hytunnel_diagnostic = response.get(
        "public_hytunnel_failure_diagnostic"
    ) or {}
    public_hrs_leads = response.get("public_hrs_measurement_leads") or {}
    vehicle_side_leads = response.get(
        "public_vehicle_side_h2_measurement_leads"
    ) or {}
    lead_context = " ".join((
        str(manifest.get("question") or ""),
        str(manifest.get("selected_sensor") or ""),
    )).lower()
    public_catalog_relevant = any(token in lead_context for token in (
        "공개", "실측", "실험", "데이터", "검증", "원자료", "자료",
        "public", "measurement", "experiment", "dataset", "validation",
        "data", "raw",
    ))
    public_hrs_leads_relevant = any(token in lead_context for token in (
        "공개", "계측", "실측", "실데이터", "원자료", "검증", "데이터",
        "local", "measurement", "dataset", "raw", "validation", "data",
    ))
    vehicle_side_leads_relevant = any(token in lead_context for token in (
        "차량", "차량탱크", "fcev", "vehicle", "receptacle", "리셉터클",
        "전달 질량", "질량 보정", "mass accounting", "metering",
    ))
    local_discovery_relevant = any(token in lead_context for token in (
        "로컬", "현장 데이터", "충전소 데이터", "운전 데이터", "시계열",
        "private station", "local station", "station data", "operational data",
        "vehicle-side", "vehicle side", "full-loop", "full loop",
    ))
    station_signal_relevant = any(token in lead_context for token in (
        "충전", "압력", "온도", "유량", "질량", "적산", "토털라이저",
        "압축기", "재충전", "flow", "mass", "totalizer", "pressure",
        "temperature", "compressor", "recharge",
    ))
    hytunnel_relevant = any(token in lead_context for token in (
        "공개", "실측", "원자료", "검증", "데이터", "피해영향", "안전거리",
        "public", "measurement", "raw", "validation", "dataset", "dispersion",
        "consequence", "safety distance",
    ))
    spatial_stratification = response.get(
        "public_actual_hydrogen_spatial_stratification_evidence"
    ) or {}
    carb_field = response.get("public_carb_hrs_inuse_field_benchmark") or {}
    detector_context = " ".join((
        str(manifest.get("selected_sensor") or ""),
        str(manifest.get("question") or ""),
    )).lower()
    accidental_release_relevant = bool(
        accidental_release
        and (
            any(token in detector_context for token in (
                "누출", "누설", "화재", "점화", "방출", "가스", "leak",
                "fire", "ignition", "release", "vent", "hydrogen",
            ))
            or any(
                row.get("release_source_boundary")
                or row.get("literature_delayed_ignition_status")
                or row.get("literature_jet_flame_status")
                for row in compact_impacts
            )
        )
    )
    spatial_guidance_relevant = bool(
        spatial_stratification
        and (
            str(manifest.get("selected_sensor") or "").upper().startswith(
                ("GD-", "FD-")
            )
            or any(token in detector_context for token in (
                "검지", "센서 배치", "누출 감지", "detector", "sensor placement"
            ))
        )
    )
    protocol_field_relevant = bool(
        carb_field
        and any(token in detector_context for token in (
            "충전", "프로토콜", "통신", "유량", "압력", "온도", "soc",
            "j2601", "hgv", "abort", "halt", "crc", "fuel", "flow",
            "communication", "pressure", "temperature",
        ))
    )
    operation_practice_relevant = bool(
        operation_practice
        and any(token in detector_context for token in (
            "충전", "충전 중", "재충전", "리크체크", "예냉", "프리쿨",
            "프로토콜", "leak-check", "fueling", "refuel", "recharge",
            "precool", "protocol",
        ))
    )
    aggregate_benchmark_relevant = bool(
        aggregate_benchmark
        and any(token in detector_context for token in (
            "충전소", "운영", "처리량", "에너지", "용량", "실적", "운전",
            "station", "operation", "throughput", "energy", "capacity",
            "performance",
        ))
    )
    threeemotion_aggregate_relevant = bool(
        threeemotion_aggregate
        and any(token in detector_context for token in (
            "버스", "대형차", "350bar", "350 bar", "대중교통", "충전소 처리량",
            "fleet", "bus", "heavy-duty", "350bar", "350 bar", "utilization",
            "daily mass", "station throughput",
        ))
    )
    cascade_sequence_relevant = bool(
        cascade_sequence
        and any(token in detector_context for token in (
            "캐스케이드", "중압", "고압", "뱅크 순서", "재충전",
            "cascade", "bank sequence", "recharge",
        ))
    )
    recharge_forecast_relevant = bool(
        recharge_forecast
        and any(token in detector_context for token in (
            "재충전", "압력 상승", "압력 예측", "압축기", "중압", "고압",
            "recharge", "pressure rise", "pressure forecast", "compressor",
        ))
    )
    lifecycle_alignment_relevant = bool(
        lifecycle_alignment
        and any(token in detector_context for token in (
            "수명", "카운터", "완충", "재충전", "저장", "뱅크",
            "lifecycle", "counter", "full charge", "recharge", "storage", "bank",
        ))
    )

    decision = {
        "evidence_digest": manifest.get("evidence_digest"),
        "source": selected(manifest.get("source"), (
            "kind", "field_measurement", "claim_limit",
        )),
        "runtime_calibration": {
            **selected(runtime, (
                "status", "requested", "profile_id", "claim_limit",
            )),
            "station_recharge_dynamics": selected(recharge_dynamics, (
                "status", "requested", "profile_id",
                "minimum_recharge_off_time_s", "claim_limit",
            )),
        },
        "detector_policy": selected(detector, (
            "status", "alarm_threshold_volpct_h2", "trip_threshold_volpct_h2",
            "persistence_s", "claim_limit",
        )),
        **({
            "virtual_detector_spatial_proxy": {
                **selected(
                    manifest.get("virtual_detector_spatial_proxy"),
                    ("status", "source_doi", "vertical_axis", "runtime_application"),
                ),
                "validation_claim": False,
            }
        } if manifest.get("virtual_detector_spatial_proxy") else {}),
        "common_header": selected(manifest.get("common_header"), (
            "pressure_mpa_abs", "temperature_c", "inventory_kg",
            "bank_inflow_g_s", "origin", "model_status", "claim_limit",
        )),
        "impact": {
            "calculation_attempted": impact.get("calculation_attempted") is True,
            "calculation_status": impact.get("calculation_status"),
            "result_count": impact.get("result_count", 0),
            "claim_limit": short(impact.get("claim_limit")),
            "results": compact_impacts[:3],
        },
        "response_guidance": {
            "source_ids": list(response.get("source_ids") or [])[:12],
            "claim_limit": short(response.get("claim_limit")),
        },
        "public_operating_envelope_screen": selected(operating_screen, (
            "status", "source_id", "flow_context",
            "current_simulated_nozzle_flow_g_s", "public_average_flow_g_s",
            "public_peak_flow_g_s", "raw_rows_public", "validation_claim",
            "claim_limit",
        )),
        "decision_support_evidence": {
            **({
                "public_station_operation_practice_reference": {
                    "source": operation_practice.get("source") or {},
                    "reported_practices": operation_practice.get(
                        "reported_practices"
                    ) or {},
                    "allowed_use": operation_practice.get("allowed_use") or [],
                    "not_allowed": operation_practice.get("not_allowed") or [],
                    "claim_limit": short(operation_practice.get("claim_limit"), 260),
                },
            } if operation_practice and operation_practice_relevant else {}),
            **({
                "public_station_aggregate_benchmark_reference": {
                    "source": aggregate_benchmark.get("source") or {},
                    "reported_aggregate": aggregate_benchmark.get(
                        "reported_aggregate"
                    ) or {},
                    "allowed_use": aggregate_benchmark.get("allowed_use") or [],
                    "not_allowed": aggregate_benchmark.get("not_allowed") or [],
                    "claim_limit": short(
                        aggregate_benchmark.get("claim_limit"), 300
                    ),
                },
            } if aggregate_benchmark and aggregate_benchmark_relevant else {}),
            **({
                "public_threeemotion_operating_aggregate_reference": {
                    "source": threeemotion_aggregate.get("source") or {},
                    "reported_aggregate": threeemotion_aggregate.get(
                        "reported_aggregate"
                    ) or {},
                    "allowed_use": threeemotion_aggregate.get("allowed_use") or [],
                    "not_allowed": threeemotion_aggregate.get("not_allowed") or [],
                    "claim_limit": short(
                        threeemotion_aggregate.get("claim_limit"), 300
                    ),
                },
            } if threeemotion_aggregate and threeemotion_aggregate_relevant else {}),
            **({
                "public_hrs_measurement_leads": {
                    "lead_count": len(public_hrs_leads.get("leads") or []),
                    "raw_trace_public_count": sum(
                        lead.get("raw_trace_public") is True
                        for lead in public_hrs_leads.get("leads") or []
                        if isinstance(lead, dict)
                    ),
                    "full_loop_external_validation_supported": (
                        public_hrs_leads.get(
                            "full_loop_external_validation_supported"
                        ) is True
                    ),
                    "parameter_fitting_supported": (
                        public_hrs_leads.get("parameter_fitting_supported") is True
                    ),
                    "saga_effectiveness_supported": (
                        public_hrs_leads.get("saga_effectiveness_supported") is True
                    ),
                    "claim_limit": short(public_hrs_leads.get("claim_limit"), 220),
                },
            } if public_hrs_leads and public_hrs_leads_relevant else {}),
            **({
                "public_vehicle_side_h2_measurement_leads": {
                    "lead_count": len(vehicle_side_leads.get("leads") or []),
                    "reported_measurements": sorted({
                        measurement
                        for lead in vehicle_side_leads.get("leads") or []
                        if isinstance(lead, dict)
                        for measurement in lead.get("reported_measurements") or []
                    }),
                    "raw_trace_status": sorted({
                        str(lead.get("raw_trace_status"))
                        for lead in vehicle_side_leads.get("leads") or []
                        if isinstance(lead, dict)
                    }),
                    "full_loop_external_validation_supported": False,
                    "parameter_fitting_supported": False,
                    "saga_effectiveness_supported": False,
                    "claim_limit": short(vehicle_side_leads.get("claim_limit"), 220),
                },
            } if vehicle_side_leads and vehicle_side_leads_relevant else {}),
            "public_incident": {
                **selected(incident, (
                    "case_count", "category_count", "covered_case_count",
                    "contract_pass",
                )),
                "digital_twin_replay": {
                    "direct": (incident.get("digital_twin_replay") or {}).get(
                        "direct_physical_case_count"
                    ),
                    "proxy": (incident.get("digital_twin_replay") or {}).get(
                        "partial_proxy_case_count"
                    ),
                    "response_only": (
                        incident.get("digital_twin_replay") or {}
                    ).get("response_only_case_count"),
                    "recipes_passed": (
                        incident.get("digital_twin_replay") or {}
                    ).get("canonical_recipe_pass_count"),
                    "recipes_total": (
                        incident.get("digital_twin_replay") or {}
                    ).get("canonical_recipe_count"),
                    "incident_parameterized": False,
                },
                "claim_limit": short(incident.get("claim_limit")),
            },
            "restricted_incident_metadata": {
                **selected(local_incident, (
                    "case_count", "mapped_case_count", "required_stage_count",
                )),
                "claim_limit": short(local_incident.get("claim_limit")),
            },
            **({
                "confidential_cross_station_bundle_recheck": {
                    "bundle_count": cross_station_bundle.get("bundle_count"),
                    "station_side_transfer_candidate": (
                        cross_station_bundle.get("station_side_transfer_candidate") is True
                    ),
                    "full_loop_external_validation_supported": False,
                    "quantitative_consequence_validation_supported": False,
                    "claim_limit": short(cross_station_bundle.get("claim_limit")),
                },
            } if cross_station_bundle and local_discovery_relevant else {}),
            **({
                "confidential_local_station_cross_bundle_transfer": {
                    "candidate_margin_mpa": cross_station_transfer.get(
                        "candidate_margin_mpa"
                    ),
                    "calibration_cycle_count": (
                        cross_station_transfer.get("calibration_bundle") or {}
                    ).get("cycle_count"),
                    "transfer_cycle_count": (
                        cross_station_transfer.get("transfer_bundle") or {}
                    ).get("cycle_count"),
                    "transfer_median_pressure_drop_mpa": (
                        cross_station_transfer.get("transfer_bundle") or {}
                    ).get("median_pressure_drop_mpa"),
                    "candidate_relative_transfer_median_error_percent": (
                        cross_station_transfer.get(
                            "candidate_relative_transfer_median_error_percent"
                        )
                    ),
                    "fixed_candidate_corroborated_on_transfer_bundle": (
                        cross_station_transfer.get(
                            "fixed_candidate_corroborated_on_transfer_bundle"
                        ) is True
                    ),
                    "full_loop_external_validation_supported": False,
                    "runtime_parameter_application": False,
                    "claim_limit": short(
                        cross_station_transfer.get("claim_limit"), 220
                    ),
                },
            } if cross_station_transfer and local_discovery_relevant else {}),
            **({
                "confidential_station_signal_consistency": {
                    "candidate_pairs_evaluated": signal_consistency.get(
                        "candidate_pairs_evaluated"
                    ),
                    "strong_consistency_pairs": signal_consistency.get(
                        "strong_consistency_pairs"
                    ),
                    "files_with_strong_consistency_pair": signal_consistency.get(
                        "files_with_strong_consistency_pair"
                    ),
                    "strong_pair_aggregate": signal_consistency.get(
                        "strong_pair_aggregate"
                    ) or {},
                    "flow_parameter_fit_supported": False,
                    "absolute_mass_flow_supported": False,
                    "full_station_vehicle_validation": False,
                    "claim_limit": short(
                        signal_consistency.get("claim_limit"), 220
                    ),
                },
            } if signal_consistency and (
                local_discovery_relevant or station_signal_relevant
            ) else {}),
            **({
                "public_accidental_release": {
                    "experiment_count": (
                        accidental_release.get("reported_findings") or {}
                    ).get("experiment_count"),
                    "ignition_observed_case_count": (
                        accidental_release.get("reported_findings") or {}
                    ).get("ignition_observed_case_count"),
                    "no_ignition_case_count": (
                        accidental_release.get("reported_findings") or {}
                    ).get("no_ignition_case_count"),
                    "remote_or_obstructed_ignition_reported": (
                        accidental_release.get("reported_findings") or {}
                    ).get("remote_or_obstructed_ignition_reported") is True,
                    "delayed_ignition_delay_s_reported": (
                        accidental_release.get("reported_findings") or {}
                    ).get("delayed_ignition_delay_s_reported"),
                    "fire_jet_length_m_greater_than_reported": (
                        accidental_release.get("reported_findings") or {}
                    ).get("fire_jet_length_m_greater_than_reported"),
                    "ignition_probability_estimated": False,
                    "ignition_mechanism_confirmed": False,
                    "claim_limit": short(accidental_release.get("claim_limit"), 180),
                }
            } if accidental_release_relevant else {}),
            **({
                "detector_placement": (
                    "22 actual-H2 channel tests, post-access: ceiling + jet-path; "
                    "top alarm/trip 100%; no runtime or station-map validation"
                )
            } if spatial_guidance_relevant else {}),
            **({
                "carb_22_station_field_benchmark": {
                    "stations": (carb_field.get("population") or {}).get(
                        "stations_tested"
                    ),
                    "all_tests_passed": (carb_field.get("population") or {}).get(
                        "stations_passing_all_hgv_4_3_tests"
                    ),
                    "category_pass_rates": (
                        carb_field.get("category_station_pass_rates") or {}
                    ),
                    "communication_fail_counts": {
                        key: values[1]
                        for key, values in (
                            carb_field.get("communication_results") or {}
                        ).items()
                        if isinstance(values, list) and len(values) == 3
                    },
                    "dynamic_model_validation": False,
                    "claim_limit": short(carb_field.get("claim_limit"), 120),
                }
            } if protocol_field_relevant else {}),
        },
        "validation_boundaries": {
            # Keep this projection compact because it is sent on every
            # interactive turn; compact order is PASS/FAIL/PENDING; objective;
            # full-loop, with 0 meaning false.
            "r": (
                f"{(readiness.get('gate_counts') or {}).get('PASS', 0)}/"
                f"{(readiness.get('gate_counts') or {}).get('FAIL', 0)}/"
                f"{(readiness.get('gate_counts') or {}).get('PENDING', 0)};"
                f"{int(readiness.get('full_user_objective_ready') is True)}l"
                f"{int(readiness.get('full_loop_external_validation_supported') is True)}"
            ),
            "public_tank_postaccess": {
                "claim_supported": methytrucks_tank.get("claim_supported") is True,
                "case_count": methytrucks_scope.get("case_count"),
                "pressure_rmse_mpa": methytrucks_244.get(
                    "pressure_rmse_case_mean_mpa"
                ),
                "temperature_rmse_c": methytrucks_244.get(
                    "temperature_rmse_case_mean_c"
                ),
                "geometry_crosswalk": (
                    "resolved"
                    if methytrucks_mapping.get(
                        "workbook_to_sink_crosswalk_present"
                    ) is True
                    else "unresolved"
                ),
                "prospective": (
                    methytrucks_tank.get("prospective_holdout_eligible") is True
                ),
                "full_loop": (
                    methytrucks_tank.get("full_loop_validation_eligible") is True
                ),
            },
            "station_to_vehicle": {
                "claim_supported": closed_loop.get("claim_supported") is True,
                "case_count": closed_loop_aggregate.get("case_count"),
                "screening_pass_count": closed_loop_aggregate.get("screening_pass_count"),
                "thermal": (
                    "unresolved"
                    if thermal_observation.get("cross_dataset_semantic_mismatch_detected") is True
                    else "unavailable"
                ),
                "claim_limit": short(closed_loop.get("claim_limit"), 80),
            },
            "station_component_thermal": {
                "status": station_thermal.get("status"),
                "proposals_attested": station_thermal.get("proposals_attested") is True,
                "component_envelope_supported": station_thermal.get(
                    "station_component_thermal_envelope_supported"
                ) is True,
            },
            **({
                "local_station_cross_bundle_transfer": {
                    "candidate_margin_mpa": cross_station_transfer.get(
                        "candidate_margin_mpa"
                    ),
                    "transfer_cycle_count": (
                        cross_station_transfer.get("transfer_bundle") or {}
                    ).get("cycle_count"),
                    "candidate_corroborated": cross_station_transfer.get(
                        "fixed_candidate_corroborated_on_transfer_bundle"
                    ) is True,
                    "full_loop": False,
                    "runtime_parameter_application": False,
                    "claim_limit": short(
                        cross_station_transfer.get("claim_limit"), 220
                    ),
                },
            } if cross_station_transfer and local_discovery_relevant else {}),
            **({
                "public_hrs_measurement_leads": {
                    "lead_count": len(public_hrs_leads.get("leads") or []),
                    "full_loop_external_validation_ready": (
                        public_hrs_leads.get(
                            "full_loop_external_validation_supported"
                        ) is True
                    ),
                    "parameter_fitting_ready": (
                        public_hrs_leads.get("parameter_fitting_supported") is True
                    ),
                    "saga_effectiveness_ready": (
                        public_hrs_leads.get("saga_effectiveness_supported") is True
                    ),
                    "claim_limit": short(public_hrs_leads.get("claim_limit"), 220),
                },
            } if public_hrs_leads and public_hrs_leads_relevant else {}),
            **({
                "local_station_data_utilization": {
                    "deduplicated_data_rows": (
                        local_station_utilization.get("inventory", {})
                        .get("deduplicated_data_rows")
                    ),
                    "storage_pressure_roles_attested": (
                        local_station_utilization.get("semantic_attestation", {})
                        .get("storage_pressure_role_count") == 2
                    ),
                    "station_side_dynamic_validation_ready": (
                        local_station_utilization.get("assessment", {})
                        .get("station_side_dynamic_validation_ready")
                    ),
                    "vehicle_side_full_loop_validation_ready": (
                        local_station_utilization.get("assessment", {})
                        .get("vehicle_side_full_loop_validation_ready")
                    ),
                },
            } if local_station_utilization and (
                manifest.get("question") or manifest.get("selected_sensor")
            ) else {}),
            **({
                "local_station_data_revalidation": {
                    "csv_file_count": (
                        local_revalidation.get("inventory") or {}
                    ).get("csv_file_count"),
                    "deduplicated_data_rows": (
                        local_revalidation.get("inventory") or {}
                    ).get("deduplicated_row_count"),
                    "sampled_table_count": (
                        local_revalidation.get("sampled_candidate_manifest") or {}
                    ).get("sampled_table_count"),
                    "synchronized_station_dispenser_vehicle_candidates": (
                        local_revalidation.get("broader_local_screen") or {}
                    ).get("synchronized_station_dispenser_vehicle_candidates"),
                    "station_side_replay_supported": (
                        local_revalidation.get("decision") or {}
                    ).get("station_side_replay_and_chronological_holdouts_supported")
                    is True,
                    "full_loop_external_validation_supported": False,
                    "runtime_parameter_application": False,
                    "claim_limit": short(
                        local_revalidation.get("claim_boundary"), 220
                    ),
                },
            } if local_revalidation and (
                local_discovery_relevant or station_signal_relevant
            ) else {}),
            **({
                "station_signal_consistency": {
                    "strong_consistency_pairs": signal_consistency.get(
                        "strong_consistency_pairs"
                    ),
                    "strong_correlation_median": (
                        signal_consistency.get("strong_pair_aggregate") or {}
                    ).get("correlation_median"),
                    "strong_normalized_rmse_percent_median": (
                        signal_consistency.get("strong_pair_aggregate") or {}
                    ).get("normalized_rmse_percent_median"),
                    "aggregation_window_seconds_median": (
                        signal_consistency.get("strong_pair_aggregate") or {}
                    ).get("aggregation_window_seconds_median"),
                    "channel_roles_attested": False,
                    "flow_units_attested": False,
                    "flow_parameter_fit_supported": False,
                    "full_station_vehicle_validation": False,
                    "claim_limit": short(
                        signal_consistency.get("claim_limit"), 220
                    ),
                },
            } if signal_consistency and (
                local_discovery_relevant or station_signal_relevant
            ) else {}),
            **({
                "local_station_asset_screen": {
                    "scenario_step_rows": (
                        local_station_asset_screen.get("scenario_matrix") or {}
                    ).get("scenario_step_rows"),
                    "hazop_scenario_coverage_substantial": (
                        local_station_asset_screen.get("coverage") or {}
                    ).get("local_hazop_scenario_coverage_is_substantial"),
                    "vehicle_side_full_loop_validation_ready": (
                        local_station_asset_screen.get("coverage") or {}
                    ).get("vehicle_side_full_loop_validation_ready"),
                },
            } if local_station_asset_screen and (
                manifest.get("question") or manifest.get("selected_sensor")
            ) else {}),
            **({
                "local_station_data_discovery": {
                    "adjacent_operational_telemetry_rows": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("adjacent_h2_operational_telemetry", {})
                        .get("telemetry_rows")
                    ),
                    "adjacent_operational_signal_key_count": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("adjacent_h2_operational_telemetry", {})
                        .get("telemetry_signal_key_count")
                    ),
                    "adjacent_operational_full_loop_ready": (
                        False
                    ),
                    "wide_equipment_file_count": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_boundary_recheck", {})
                        .get("file_count")
                    ),
                    "wide_equipment_row_count": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_boundary_recheck", {})
                        .get("row_count")
                    ),
                    "wide_equipment_continuity_file_count": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_continuity_screen", {})
                        .get("wide_file_count")
                    ),
                    "wide_equipment_continuity_row_count": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_continuity_screen", {})
                        .get("wide_row_count")
                    ),
                    "wide_equipment_timestamp_parse_failures": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_continuity_screen", {})
                        .get("timestamp_parse_failures")
                    ),
                    "wide_equipment_negative_interval_count": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_continuity_screen", {})
                        .get("negative_interval_count")
                    ),
                    "wide_equipment_median_positive_interval_s": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_continuity_screen", {})
                        .get("median_positive_interval_s")
                    ),
                    "wide_equipment_state_transition_count": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_continuity_screen", {})
                        .get("state_transition_count")
                    ),
                    "wide_equipment_continuity_screen_ready": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_continuity_screen", {})
                        .get("wide_file_count")
                        == 8
                    ),
                    "wide_equipment_replay_ready": False,
                    "wide_equipment_station_side_screen_ready": (
                        (local_station_discovery.get("candidate_groups") or {})
                        .get("wide_equipment_boundary_recheck", {})
                        .get("row_count")
                        == 653442
                    ),
                    "wide_equipment_full_loop_ready": False,
                    "station_data_is_sparse": (
                        (local_station_discovery.get("coverage_assessment") or {})
                        .get("local_station_data_is_sparse")
                    ),
                    "station_side_dynamic_evidence_substantial": (
                        (local_station_discovery.get("coverage_assessment") or {})
                        .get("station_side_dynamic_evidence_is_substantial")
                    ),
                    "vehicle_side_full_loop_validation_ready": (
                        (local_station_discovery.get("coverage_assessment") or {})
                        .get("vehicle_side_full_loop_validation_ready")
                    ),
                    "quantitative_consequence_validation_ready": (
                        (local_station_discovery.get("coverage_assessment") or {})
                        .get("quantitative_consequence_validation_ready")
                    ),
                    "claim_limit": short(local_station_discovery.get("claim_limit"), 220),
                },
            } if local_station_discovery and local_discovery_relevant else {}),
            **({
                "local_data_deep_scan": {
                    "station_csv_files": (
                        (local_data_deep_scan.get("measured_station_bundle") or {})
                        .get("csv_files")
                    ),
                    "station_deduplicated_rows": (
                        (local_data_deep_scan.get("measured_station_bundle") or {})
                        .get("deduplicated_rows")
                    ),
                    "unique_candidate_assets": (
                        (local_data_deep_scan.get("broad_candidate_inventory") or {})
                        .get("unique_candidate_assets")
                    ),
                    "candidate_class_counts": {
                        item.get("class"): item.get("unique_assets")
                        for item in local_data_deep_scan.get("candidate_classes") or []
                        if isinstance(item, dict) and item.get("class")
                    },
                    "new_synchronized_station_vehicle_cohort_found": (
                        (local_data_deep_scan.get("full_loop_decision") or {})
                        .get("new_eligible_synchronized_station_vehicle_cohort_found")
                    ),
                    "full_loop_decision": (
                        (local_data_deep_scan.get("full_loop_decision") or {})
                        .get("decision")
                    ),
                    "claim_limit": short(local_data_deep_scan.get("claim_limit"), 220),
                },
            } if local_data_deep_scan and local_discovery_relevant else {}),
            **({
                "local_adjacent_hydrogen_process_context": {
                    "domain_classification": adjacent_process.get(
                        "domain_classification"
                    ),
                    "csv_event_log_count": (
                        (adjacent_process.get("high_pressure_process") or {})
                        .get("csv_event_log_count")
                    ),
                    "csv_event_row_count": (
                        (adjacent_process.get("high_pressure_process") or {})
                        .get("csv_event_row_count")
                    ),
                    "logical_key_count": (
                        (adjacent_process.get("high_pressure_process") or {})
                        .get("logical_key_count")
                    ),
                    "value_family_row_counts": (
                        (adjacent_process.get("high_pressure_process") or {})
                        .get("value_family_row_counts") or {}
                    ),
                    "runtime_parameter_application": False,
                    "station_to_vehicle_full_loop_validation": False,
                    "claim_limit": short(adjacent_process.get("claim_limit"), 220),
                },
            } if adjacent_process and local_discovery_relevant else {}),
            **({
                "local_docudata_full_discovery": {
                    "machine_readable_files_screened": (
                        (docudata_discovery.get("broad_scan") or {})
                        .get("machine_readable_files_screened")
                    ),
                    "csv_tsv_headers_screened": (
                        (docudata_discovery.get("broad_scan") or {})
                        .get("csv_tsv_headers_screened")
                    ),
                    "vehicle_or_dispenser_keyword_candidates": (
                        (docudata_discovery.get("broad_scan") or {})
                        .get("vehicle_or_dispenser_keyword_candidates")
                    ),
                    "vehicle_pressure_temperature_flow_time_candidates": (
                        (docudata_discovery.get("refined_header_screen") or {})
                        .get("vehicle_pressure_temperature_flow_time_candidates")
                    ),
                    "eligible_synchronized_station_dispenser_vehicle_cohort": (
                        (docudata_discovery.get("eligibility") or {})
                        .get("eligible_synchronized_station_dispenser_vehicle_cohort")
                    ),
                    "runtime_parameter_application": False,
                    "full_loop_external_validation_ready": (
                        (docudata_discovery.get("eligibility") or {})
                        .get("full_loop_external_validation_ready")
                    ),
                    "claim_limit": short(docudata_discovery.get("claim_limit"), 220),
                },
            } if docudata_discovery and local_discovery_relevant else {}),
            **({
                "local_station_attestation_request": {
                    "status": local_attestation_request.get("status"),
                    "observed_archive": local_attestation_request.get(
                        "observed_local_archive"
                    ) or {},
                    "requested_attestation_ids": [
                        item.get("id")
                        for item in local_attestation_request.get(
                            "requested_attestations"
                        ) or []
                        if isinstance(item, dict) and item.get("id")
                    ],
                    "current_gate_effect": local_attestation_request.get(
                        "current_gate_effect"
                    ) or {},
                    "claim_limit": short(
                        local_attestation_request.get("claim_limit"), 220
                    ),
                },
            } if local_attestation_request and local_discovery_relevant else {}),
            **({
                "local_public_validation_catalog": {
                    "collection_count": (
                        (local_public_catalog.get("scope") or {}).get(
                            "collection_count"
                        )
                    ),
                    "file_count": (
                        (local_public_catalog.get("scope") or {}).get(
                            "file_count"
                        )
                    ),
                    "size_gb_decimal": (
                        (local_public_catalog.get("scope") or {}).get(
                            "size_gb_decimal"
                        )
                    ),
                    "public_component_evidence_substantial": (
                        (local_public_catalog.get("coverage_assessment") or {}).get(
                            "public_component_evidence_is_substantial"
                        )
                    ),
                    "full_loop_holdout_eligible": (
                        (local_public_catalog.get("coverage_assessment") or {}).get(
                            "full_loop_holdout_eligible"
                        )
                    ),
                    "claim_limit": short(local_public_catalog.get("claim_limit"), 220),
                },
            } if local_public_catalog and public_catalog_relevant else {}),
            **({
                "local_public_candidate_scan": {
                    "machine_readable_files": (
                        (local_public_candidate_scan.get("scan") or {}).get(
                            "machine_readable_files"
                        )
                    ),
                    "csv_tsv_headers_screened": (
                        (local_public_candidate_scan.get("scan") or {}).get(
                            "csv_tsv_headers_screened"
                        )
                    ),
                    "header_parse_errors": (
                        (local_public_candidate_scan.get("scan") or {}).get(
                            "header_parse_errors"
                        )
                    ),
                    "coarse_candidate_classes": (
                        (local_public_candidate_scan.get("scan") or {}).get(
                            "coarse_candidate_classes"
                        ) or {}
                    ),
                    "full_loop_candidate_count": (
                        (local_public_candidate_scan.get("eligibility") or {}).get(
                            "full_loop_candidate_count"
                        )
                    ),
                    "decision": (
                        (local_public_candidate_scan.get("eligibility") or {}).get(
                            "decision"
                        )
                    ),
                    "claim_limit": short(
                        local_public_candidate_scan.get("claim_limit"), 220
                    ),
                },
            } if local_public_candidate_scan and public_catalog_relevant else {}),
            **({
                "station_cascade_sequence": {
                    "claim_supported": cascade_sequence.get(
                        "cascade_controller_structure_supported"
                    ) is True,
                    "files_read": cascade_sequence.get("files_read"),
                    "calibration_pairs": (
                        cascade_sequence.get("calibration") or {}
                    ).get("paired_episode_count"),
                    "holdout_pairs": (
                        cascade_sequence.get("holdout") or {}
                    ).get("paired_episode_count"),
                    "holdout_pair_coverage": (
                        cascade_sequence.get("holdout") or {}
                    ).get("pair_coverage_fraction"),
                    "holdout_sequential_fraction": (
                        cascade_sequence.get("holdout") or {}
                    ).get("sequential_fraction"),
                    "median_handoff_gap_s": (
                        ((cascade_sequence.get("holdout") or {}).get(
                            "handoff_gap_s"
                        ) or {}).get("median")
                    ),
                    "vehicle_fill_validation": cascade_sequence.get(
                        "vehicle_fill_validation"
                    ) is True,
                    "full_loop": cascade_sequence.get(
                        "full_loop_holdout_eligible"
                    ) is True,
                },
            } if cascade_sequence_relevant else {}),
            **({
            "station_recharge_pressure_forecast": {
                    "claim_supported": recharge_forecast.get(
                        "short_horizon_station_pressure_forecast_supported"
                    ) is True,
                    "files_read": recharge_forecast.get("files_read"),
                    "calibration_cases": recharge_forecast.get(
                        "calibration_case_count"
                    ),
                    "holdout_cases": recharge_forecast.get("holdout_case_count"),
                    "holdout_metrics": recharge_forecast.get(
                        "holdout_metrics"
                    ) or {},
                    "runtime_parameter_application": recharge_forecast.get(
                        "runtime_parameter_application"
                    ) is True,
                    "vehicle_fill_validation": recharge_forecast.get(
                        "vehicle_fill_validation"
                    ) is True,
                    "full_loop": recharge_forecast.get(
                        "full_loop_holdout_eligible"
                    ) is True,
                },
            } if recharge_forecast_relevant else {}),
            **({
                "vehicle_side_measurement_lead": {
                    "claim_supported": False,
                    "lead_count": len(vehicle_side_leads.get("leads") or []),
                    "reported_measurements": sorted({
                        measurement
                        for lead in vehicle_side_leads.get("leads") or []
                        if isinstance(lead, dict)
                        for measurement in lead.get("reported_measurements") or []
                    }),
                    "raw_trace_status": sorted({
                        str(lead.get("raw_trace_status"))
                        for lead in vehicle_side_leads.get("leads") or []
                        if isinstance(lead, dict)
                    }),
                    "full_loop": False,
                    "parameter_fitting": False,
                    "next_access_request": [
                        item
                        for lead in vehicle_side_leads.get("leads") or []
                        if isinstance(lead, dict)
                        for item in lead.get("next_access_request") or []
                    ][:8],
                    "claim_limit": short(vehicle_side_leads.get("claim_limit"), 180),
                },
            } if vehicle_side_leads and vehicle_side_leads_relevant else {}),
            **({
                "station_lifecycle_pressure_alignment": {
                    "claim_supported": lifecycle_alignment.get(
                        "pressure_completion_counter_alignment_supported"
                    ) is True,
                    "recharge_event_detector_corroborated": lifecycle_alignment.get(
                        "recharge_event_detector_corroborated"
                    ) is True,
                    "calibration_counter_recall": (
                        ((lifecycle_alignment.get("calibration") or {}).get(
                            "combined"
                        ) or {}).get("counter_event_recall")
                    ),
                    "holdout_counter_recall": (
                        ((lifecycle_alignment.get("holdout") or {}).get(
                            "combined"
                        ) or {}).get("counter_event_recall")
                    ),
                    "holdout_pressure_precision": (
                        ((lifecycle_alignment.get("holdout") or {}).get(
                            "combined"
                        ) or {}).get("pressure_event_precision")
                    ),
                    "holdout_median_absolute_offset_s": (
                        (((lifecycle_alignment.get("holdout") or {}).get(
                            "combined"
                        ) or {}).get("absolute_time_offset_s") or {}).get("median")
                    ),
                    "counter_monotonicity_met": (
                        (lifecycle_alignment.get("eligibility") or {}).get(
                            "counter_monotonicity_met"
                        ) is True
                    ),
                    "runtime_parameter_application": lifecycle_alignment.get(
                        "runtime_parameter_application"
                    ) is True,
                    "vehicle_fill_validation": lifecycle_alignment.get(
                        "vehicle_fill_validation"
                    ) is True,
                    "full_loop": lifecycle_alignment.get(
                        "full_loop_holdout_eligible"
                    ) is True,
                    "claim_limit": short(lifecycle_alignment.get("claim_limit"), 120),
                },
            } if lifecycle_alignment_relevant else {}),
            "source_depletion": {
                "claim_supported": preslhy_holdout.get("claim_supported") is True,
                "joint_primary_pass_fraction": preslhy_holdout.get(
                    "joint_primary_pass_fraction"
                ),
                "claim_limit": short(preslhy.get("claim_limit"), 80),
            },
            "high_pressure_aperture": {
                "baseline_joint_primary_pass_count": release.get(
                    "baseline_joint_primary_pass_count"
                ),
                "claim_limit": short(release.get("claim_limit"), 80),
            },
            "release_cross_campaign": {
                "supported": cross_campaign_release.get(
                    "supported_campaign_count"
                ),
                "failed": cross_campaign_release.get("failed_campaign_count"),
                "ineligible": cross_campaign_release.get(
                    "ineligible_campaign_count"
                ),
                "universal": cross_campaign_release.get(
                    "universal_release_validation_supported"
                ) is True,
                "apparatus_holdout": cross_campaign_release.get(
                    "apparatus_resolved_holdout_received"
                ) is True,
            },
            **({
                "public_hytunnel_carpark": {
                    "claim_supported": hytunnel_diagnostic.get(
                        "claim_supported"
                    ) is True,
                    "dispersion_joint_screen_pass": (
                        hytunnel_diagnostic.get("holdout") or {}
                    ).get("dispersion_joint_screen_pass") is True,
                    "mass_flow_joint_screen_pass": (
                        hytunnel_diagnostic.get("holdout") or {}
                    ).get("mass_flow_joint_screen_pass") is True,
                    "runtime_parameter_application": hytunnel_diagnostic.get(
                        "runtime_parameter_application"
                    ) is True,
                    "default_model_parameters_changed": hytunnel_diagnostic.get(
                        "default_model_parameters_changed"
                    ) is True,
                    "claim_limit": short(
                        hytunnel_diagnostic.get("claim_limit"), 220
                    ),
                },
            } if hytunnel_diagnostic and hytunnel_relevant
            and not (impact.get("calculation_attempted") is True) else {}),
            # The compact prompt already carries several validation limits.
            # Preserve the controlled-data boundary in one token-cheap status
            # field; the detailed header and audit envelope retain the counts.
            "mapping": (
                "not_found"
                if multisource.get("co_located_workbook_candidates") == 0
                else (
                    "ready"
                    if multisource.get("unambiguous_full_loop_mapping_available") is True
                    and multisource.get("full_loop_holdout_eligible") is True
                    else "partial"
                )
            ),
        },
    }
    if qra_multimethod:
        decision["validation_boundaries"]["qra_method_ensemble"] = (
            "DATA3632 simulation-only: 7 methods; runtime thermal 2/4, "
            "overpressure 0/3; verify release boundary; no automatic tuning"
        )
    if all(
        khk_replay.get(key) is not None
        for key in (
            "integration_trace_pass_incident_code_count", "incident_code_count",
            "canonical_recipe_pass_count", "canonical_recipe_count",
        )
    ):
        decision["decision_support_evidence"]["khk_trace"] = (
            f"{khk_replay['integration_trace_pass_incident_code_count']}/"
            f"{khk_replay['incident_code_count']} codes; "
            f"{khk_replay['canonical_recipe_pass_count']}/"
            f"{khk_replay['canonical_recipe_count']} recipes; "
            "KOH excluded; metadata routing only"
        )
    # Keep the normal interactive prompt compact.  Safety feedback appears
    # only when at least one action exists; an absent history itself is not
    # useful context to the provider and would crowd current alarm evidence.
    if virtual_safety.get("action_count"):
        decision["virtual_safety"] = {
            "actions": [
                selected(action, ("kind", "target", "status", "issued_s", "completed_s"))
                for action in (virtual_safety.get("actions") or [])[-8:]
                if isinstance(action, dict)
            ],
            "confirmed_count": virtual_safety.get("confirmed_count", 0),
            "failed_count": virtual_safety.get("failed_count", 0),
            "pending_count": virtual_safety.get("pending_count", 0),
            "claim_limit": short(virtual_safety.get("claim_limit")),
        }
    # A runtime pressure forecast is useful only as a short-horizon advisory
    # for an active recharge, so expose the current frame value separately
    # from the frozen holdout evidence above.  Keeping the claim boundary in
    # the same compact envelope prevents a provider from treating this value
    # as a safety limit, controller input, or full-loop validation result.
    current_forecast = manifest.get("station_pressure_forecast") or {}
    if isinstance(current_forecast, dict) and current_forecast:
        forecast_view = selected(current_forecast, (
            "status", "reason", "bank", "current_pressure_mpa",
            "forecast_pressure_mpa", "forecast_delta_mpa", "prefix_span_s",
            "horizon_s", "dominant_rise_mpa", "dominance_ratio",
            "gain", "claim_limit",
        ))
        provenance = current_forecast.get("provenance") or current_forecast.get("basis")
        if isinstance(provenance, dict):
            forecast_view["provenance"] = selected(provenance, (
                "artifact", "protocol", "holdout_count", "holdout_metrics",
                "runtime_parameter_application", "vehicle_fill_validation",
                "full_loop_holdout_eligible",
            ))
        if forecast_view:
            decision["current_station_pressure_forecast"] = forecast_view

    # Give the operator a compact, explicit answer to "what data did you use?".
    # This is deliberately derived from the same bounded envelope above rather
    # than from private file names, raw rows, or provider-specific prompt text.
    # It makes the provenance visible in both the main and sensor assistants
    # without allowing restricted identifiers to leak into an interactive turn.
    signal_rows = (manifest.get("signals") or {}).get("rows") or []
    data_used: dict[str, Any] = {
        "signals": [
            row.get("tag")
            for row in signal_rows[:4]
            if isinstance(row, dict) and row.get("tag")
        ],
        "impact": [
            impact.get("calculation_status"),
            impact.get("result_count", 0),
        ],
    }
    if isinstance(current_forecast, dict) and current_forecast:
        data_used["station_pressure_forecast"] = selected(current_forecast, (
            "status", "reason", "bank",
        ))
    # Sensor-analysis and forecast views have a stable UI slot for this
    # provenance line.  Main direct-Q&A keeps its stricter prompt budget and
    # already receives the detailed live signal/impact fields separately.
    if current_forecast or manifest.get("selected_sensor"):
        decision["data_used"] = data_used
    if relevant_precedents.get("by_response_plan"):
        decision["response_guidance"].update({
            "relevant_public_accident_precedents": relevant_precedents[
                "by_response_plan"
            ],
            "precedent_claim_limit": short(relevant_precedents.get("claim_limit")),
        })
    # The flare report is decision-relevant only for registered vent/relief
    # response plans.  Keeping it out of unrelated prompts avoids spending
    # context on a safeguard that cannot be acted on in the current state.
    if (
        "HYDELTA_FLARE_2026" in decision["response_guidance"]["source_ids"]
        and isinstance(controlled_flare, dict)
        and controlled_flare
    ):
        findings = controlled_flare.get("reported_findings") or {}
        runtime_use = controlled_flare.get("runtime_use") or {}
        decision["response_guidance"]["controlled_flare"] = {
            "doi": controlled_flare.get("doi"),
            "engineered_approved_system_only": runtime_use.get(
                "applies_only_to_engineered_approved_controlled_flare"
            ) is True,
            "ad_hoc_vent_ignition_authorized": False,
            "tested_nitrogen_boundary_volpct": findings.get(
                "maximum_reported_nitrogen_fraction_for_continued_operation_volpct"
            ),
            "tested_safeguards": list(findings.get("tested_safeguards") or []),
            "claim_limit": short(controlled_flare.get("claim_limit")),
        }
    return decision


def prompt_evidence_header(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a detailed provenance view for audit and UI consumers.

    Interactive provider prompts use :func:`prompt_decision_evidence` instead
    because this complete traceability view can exceed a chat context budget.
    """

    evidence = manifest.get("response_evidence") or {}
    benchmarks = evidence.get("public_experimental_benchmarks") or {}
    hitrf_reference = evidence.get("public_hitrf_operational_reference") or {}
    real_station_context = evidence.get("public_real_station_context") or {}
    operation_practice = evidence.get(
        "public_station_operation_practice_reference"
    ) or {}
    aggregate_benchmark = evidence.get(
        "public_station_aggregate_benchmark_reference"
    ) or {}
    threeemotion_aggregate = evidence.get(
        "public_threeemotion_operating_aggregate_reference"
    ) or {}
    public_hrs_leads = evidence.get("public_hrs_measurement_leads") or {}
    vehicle_side_leads = evidence.get(
        "public_vehicle_side_h2_measurement_leads"
    ) or {}
    carb_field = evidence.get("public_carb_hrs_inuse_field_benchmark") or {}
    benchmark_ids = [
        str(source.get("id"))
        for source in benchmarks.get("sources") or []
        if isinstance(source, dict) and source.get("id")
    ]
    detector = evidence.get("public_detector_logic_evidence") or {}
    detector_aggregate = detector.get("aggregate") or {}
    reference_detector = evidence.get("public_reference_leak_detector_evidence") or {}
    spatial_stratification = evidence.get(
        "public_actual_hydrogen_spatial_stratification_evidence"
    ) or {}
    dispersion_proxy = evidence.get("public_dispersion_proxy_evidence") or {}
    grune_ventilation = evidence.get("public_grune_ventilation_evidence") or {}
    confidential = evidence.get("confidential_measured_boundary_replay") or {}
    holdout = confidential.get("temporal_holdout") or {}
    operational_holdout = confidential.get("operational_envelope_holdout") or {}
    cross_station = confidential.get("cross_station_pressure_envelope") or {}
    lifecycle = evidence.get("confidential_lifecycle_counter_summary") or {}
    station_calibration = evidence.get("confidential_station_boundary_calibration") or {}
    recharge_dynamics = evidence.get(
        "confidential_station_recharge_dynamics_calibration"
    ) or {}
    cascade_sequence = evidence.get(
        "confidential_station_cascade_sequence_holdout"
    ) or {}
    recharge_forecast = evidence.get(
        "confidential_station_recharge_pressure_forecast_holdout"
    ) or {}
    lifecycle_alignment = evidence.get(
        "confidential_station_lifecycle_pressure_alignment_holdout"
    ) or {}
    channel_envelopes = evidence.get(
        "confidential_pressure_channel_envelopes"
    ) or {}
    station_equipment = evidence.get(
        "confidential_station_equipment_operational_envelope"
    ) or {}
    station_thermal = evidence.get("confidential_station_thermal_dynamics") or {}
    bank_pressure = evidence.get("confidential_bank_role_pressure_envelopes") or {}
    pressure_recheck = evidence.get("confidential_pressure_recheck_decision") or {}
    operational_profile_recheck = evidence.get(
        "confidential_operational_profile_recheck"
    ) or {}
    channel_quality_recheck = evidence.get(
        "confidential_station_channel_quality_recheck"
    ) or {}
    signal_consistency = evidence.get(
        "confidential_station_signal_consistency"
    ) or {}
    station_schema = evidence.get("confidential_station_schema_intake") or {}
    local_station_utilization = evidence.get(
        "confidential_local_station_data_utilization"
    ) or {}
    local_revalidation = evidence.get("local_station_data_revalidation") or {}
    readiness = evidence.get("validation_readiness") or {}
    local_station_asset_screen = evidence.get(
        "confidential_local_station_asset_screen"
    ) or {}
    local_station_discovery = evidence.get(
        "confidential_local_station_data_discovery"
    ) or {}
    local_attestation_request = evidence.get(
        "confidential_local_station_attestation_request"
    ) or {}
    local_data_deep_scan = evidence.get(
        "confidential_local_data_deep_scan"
    ) or {}
    adjacent_process = evidence.get(
        "local_adjacent_hydrogen_process_context"
    ) or {}
    docudata_discovery = evidence.get("local_docudata_full_discovery") or {}
    local_public_catalog = evidence.get("local_public_validation_catalog") or {}
    local_public_candidate_scan = evidence.get("local_public_candidate_scan") or {}
    multisource_feasibility = evidence.get(
        "confidential_multisource_mapping_feasibility"
    ) or {}
    private_media = evidence.get("confidential_private_media_intake") or {}
    incident = evidence.get("public_incident_traceability") or {}
    action_taxonomy = incident.get("action_taxonomy") or {}
    accident_inventory = evidence.get("public_accident_report_inventory") or {}
    relevant_precedents = evidence.get("relevant_public_accident_precedents") or {}
    accidental_release = evidence.get("public_accidental_release_evidence") or {}
    controlled_flare = evidence.get("public_controlled_flare_evidence") or {}
    local_accident_coverage = evidence.get(
        "confidential_local_accident_response_coverage"
    ) or {}
    cross_station_bundle = evidence.get(
        "confidential_cross_station_bundle_recheck"
    ) or {}
    cross_station_transfer = evidence.get(
        "confidential_local_station_cross_bundle_transfer"
    ) or {}
    hitrf_storage = hitrf_reference.get("storage") or {}
    hitrf_thermal = hitrf_reference.get("dispensing_and_thermal") or {}
    envelope_screen = evidence.get("public_operating_envelope_screen") or {}
    public_measurement = evidence.get("public_measurement_instrumentation") or {}
    hytunnel_diagnostic = evidence.get(
        "public_hytunnel_failure_diagnostic"
    ) or {}
    methytrucks_tank = evidence.get("methytrucks_tank_diagnostic_boundary") or {}
    qra_multimethod = evidence.get("qra_multimethod_comparison") or {}
    preslhy = evidence.get("preslhy_validation_boundary") or {}
    closed_loop = evidence.get("closed_loop_validation_boundary") or {}
    release_boundary = evidence.get("proust_release_model_validation_boundary") or {}
    cross_campaign_release = evidence.get(
        "cross_campaign_release_validation_boundary"
    ) or {}
    thermal_observation = evidence.get("temperature_observation_semantic_boundary") or {}
    return {
        "runtime_calibration": manifest.get("runtime_calibration") or {},
        "runtime_geometry": manifest.get("runtime_geometry") or {},
        "runtime_vehicle_tank_calibration": manifest.get(
            "runtime_vehicle_tank_calibration"
        ) or {},
        "temperature_observation_semantic_boundary": {
            "evidence_role": thermal_observation.get("evidence_role"),
            "runtime_temperature_state": thermal_observation.get(
                "runtime_temperature_state"
            ),
            "candidate_observation_operators": list(
                thermal_observation.get("candidate_observation_operators") or []
            ),
            "cross_dataset_semantic_mismatch_detected": thermal_observation.get(
                "cross_dataset_semantic_mismatch_detected"
            ) is True,
            "runtime_thermal_observation_changed": thermal_observation.get(
                "runtime_thermal_observation_changed"
            ) is True,
            "operator_selection_prohibited": thermal_observation.get(
                "operator_selection_prohibited"
            ) is True,
            "validation_claim_supported": thermal_observation.get(
                "validation_claim_supported"
            ) is True,
            "claim_limit": thermal_observation.get("claim_limit"),
        },
        "measured_bank_pressure_envelope": manifest.get(
            "measured_bank_pressure_envelope"
        ) or {},
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
        "public_station_operation_practice_reference": {
            "source": operation_practice.get("source") or {},
            "reported_practices": operation_practice.get("reported_practices") or {},
            "allowed_use": operation_practice.get("allowed_use") or [],
            "not_allowed": operation_practice.get("not_allowed") or [],
            "claim_limit": operation_practice.get("claim_limit"),
        },
        "public_station_aggregate_benchmark_reference": {
            "source": aggregate_benchmark.get("source") or {},
            "reported_aggregate": aggregate_benchmark.get(
                "reported_aggregate"
            ) or {},
            "allowed_use": aggregate_benchmark.get("allowed_use") or [],
            "not_allowed": aggregate_benchmark.get("not_allowed") or [],
            "claim_limit": aggregate_benchmark.get("claim_limit"),
        },
        "public_threeemotion_operating_aggregate_reference": {
            "source": threeemotion_aggregate.get("source") or {},
            "reported_aggregate": threeemotion_aggregate.get(
                "reported_aggregate"
            ) or {},
            "allowed_use": threeemotion_aggregate.get("allowed_use") or [],
            "not_allowed": threeemotion_aggregate.get("not_allowed") or [],
            "claim_limit": threeemotion_aggregate.get("claim_limit"),
        },
        "public_hrs_measurement_leads": {
            "evidence_artifact": public_hrs_leads.get("artifact"),
            "evidence_role": public_hrs_leads.get("evidence_role"),
            "status": public_hrs_leads.get("status"),
            "leads": public_hrs_leads.get("leads") or [],
            "request_package_requirements": public_hrs_leads.get(
                "request_package_requirements"
            ) or [],
            "full_loop_external_validation_supported": (
                public_hrs_leads.get("full_loop_external_validation_supported")
                is True
            ),
            "parameter_fitting_supported": (
                public_hrs_leads.get("parameter_fitting_supported") is True
            ),
            "saga_effectiveness_supported": (
                public_hrs_leads.get("saga_effectiveness_supported") is True
            ),
            "claim_limit": public_hrs_leads.get("claim_limit"),
        },
        "public_vehicle_side_h2_measurement_leads": {
            "evidence_artifact": vehicle_side_leads.get("artifact"),
            "evidence_role": vehicle_side_leads.get("evidence_role"),
            "leads": vehicle_side_leads.get("leads") or [],
            "full_loop_external_validation_supported": False,
            "parameter_fitting_supported": False,
            "saga_effectiveness_supported": False,
            "claim_limit": vehicle_side_leads.get("claim_limit"),
        },
        "public_carb_hrs_inuse_field_benchmark": {
            "source": carb_field.get("source") or {},
            "population": carb_field.get("population") or {},
            "category_station_pass_rates": (
                carb_field.get("category_station_pass_rates") or {}
            ),
            "communication_results": carb_field.get("communication_results") or {},
            "digital_twin_functional_coverage": (
                carb_field.get("digital_twin_functional_coverage") or {}
            ),
            "full_loop_external_holdout_eligible": carb_field.get(
                "full_loop_external_holdout_eligible"
            ) is True,
            "dynamic_model_parameter_calibration_eligible": carb_field.get(
                "dynamic_model_parameter_calibration_eligible"
            ) is True,
            "claim_limit": carb_field.get("claim_limit"),
        },
        "public_measurement_instrumentation": {
            "source_count": public_measurement.get("source_count"),
            "file_count": public_measurement.get("file_count"),
            "sample_count": public_measurement.get("sample_count"),
            "observed_sampling_intervals_s": public_measurement.get(
                "observed_sampling_intervals_s"
            ),
            "workbooks_with_mass": public_measurement.get("workbooks_with_mass"),
            "mass_closure_session_count": public_measurement.get(
                "mass_closure_session_count"
            ),
            "mass_closure_comparable_session_count": public_measurement.get(
                "mass_closure_comparable_session_count"
            ),
            "mass_closure_non_comparable_session_count": public_measurement.get(
                "mass_closure_non_comparable_session_count"
            ),
            "mass_closure_screen_pass_count": public_measurement.get(
                "mass_closure_screen_pass_count"
            ),
            "mass_closure_comparable_pass_fraction": public_measurement.get(
                "mass_closure_comparable_pass_fraction"
            ),
            "mass_closure_pass_ratio_median": public_measurement.get(
                "mass_closure_pass_ratio_median"
            ),
            "mass_closure_comparable_ratio_median": public_measurement.get(
                "mass_closure_comparable_ratio_median"
            ),
            "mass_closure_comparable_absolute_relative_difference_pct_median": (
                public_measurement.get(
                    "mass_closure_comparable_absolute_relative_difference_pct_median"
                )
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
            "official_test_context": public_measurement.get(
                "official_test_context"
            ) or {},
            "group_a_c_vehicle_fill_eligible": public_measurement.get(
                "group_a_c_vehicle_fill_eligible"
            ) is True,
            "test_class_interpretation": public_measurement.get(
                "test_class_interpretation"
            ),
            "claim_limit": public_measurement.get("claim_limit"),
        },
        "local_public_validation_catalog": {
            "evidence_artifact": local_public_catalog.get("artifact"),
            "scope": local_public_catalog.get("scope") or {},
            "coverage_assessment": local_public_catalog.get(
                "coverage_assessment"
            ) or {},
            "claim_limit": local_public_catalog.get("claim_limit"),
        },
        "local_public_candidate_scan": {
            "evidence_artifact": local_public_candidate_scan.get("artifact"),
            "evidence_role": local_public_candidate_scan.get("evidence_role"),
            "scan": local_public_candidate_scan.get("scan") or {},
            "eligibility": local_public_candidate_scan.get("eligibility") or {},
            "claim_limit": local_public_candidate_scan.get("claim_limit"),
        },
        "confidential_local_station_attestation_request": {
            "evidence_artifact": local_attestation_request.get("artifact"),
            "status": local_attestation_request.get("status"),
            "observed_local_archive": local_attestation_request.get(
                "observed_local_archive"
            ) or {},
            "requested_attestations": local_attestation_request.get(
                "requested_attestations"
            ) or [],
            "current_gate_effect": local_attestation_request.get(
                "current_gate_effect"
            ) or {},
            "custodian_submission_contract": local_attestation_request.get(
                "custodian_submission_contract"
            ) or [],
            "claim_limit": local_attestation_request.get("claim_limit"),
        },
        "public_hytunnel_failure_diagnostic": {
            "artifact": hytunnel_diagnostic.get("artifact"),
            "evidence_role": hytunnel_diagnostic.get("evidence_role"),
            "source": hytunnel_diagnostic.get("source") or {},
            "holdout": hytunnel_diagnostic.get("holdout") or {},
            "regimes": hytunnel_diagnostic.get("regimes") or {},
            "findings": hytunnel_diagnostic.get("findings") or [],
            "runtime_parameter_application": hytunnel_diagnostic.get(
                "runtime_parameter_application"
            ) is True,
            "default_model_parameters_changed": hytunnel_diagnostic.get(
                "default_model_parameters_changed"
            ) is True,
            "claim_supported": hytunnel_diagnostic.get("claim_supported") is True,
            "claim_limit": hytunnel_diagnostic.get("claim_limit"),
        },
        "qra_multimethod_comparison": {
            key: qra_multimethod.get(key)
            for key in (
                "source", "evidence_role", "method_count", "retained_row_count",
                "matched_group_count", "maximum_matched_method_ratio",
                "runtime_case_count", "runtime_thermal_within_envelope_count",
                "runtime_overpressure_within_envelope_count", "cases",
                "automatic_calibration_performed", "experimental_validation",
                "operator_rule", "claim_limit",
            )
            if qra_multimethod.get(key) is not None
        },
        "methytrucks_tank_diagnostic_boundary": {
            "evidence_role": methytrucks_tank.get("evidence_role"),
            "source": methytrucks_tank.get("source") or {},
            "scope": methytrucks_tank.get("scope") or {},
            "candidate_244_l_diagnostic": methytrucks_tank.get(
                "candidate_244_l_diagnostic"
            ) or {},
            "alternate_77_l_sensitivity": methytrucks_tank.get(
                "alternate_77_l_sensitivity"
            ) or {},
            "mapping_boundary": methytrucks_tank.get("mapping_boundary") or {},
            "component_diagnostic_eligible": methytrucks_tank.get(
                "component_diagnostic_eligible"
            ) is True,
            "prospective_holdout_eligible": methytrucks_tank.get(
                "prospective_holdout_eligible"
            ) is True,
            "full_loop_validation_eligible": methytrucks_tank.get(
                "full_loop_validation_eligible"
            ) is True,
            "claim_supported": methytrucks_tank.get("claim_supported") is True,
            "required_next_step": methytrucks_tank.get("required_next_step"),
            "claim_limit": methytrucks_tank.get("claim_limit"),
        },
        "confidential_multisource_mapping_feasibility": {
            "co_located_workbook_candidates": multisource_feasibility.get(
                "co_located_workbook_candidates"
            ),
            "candidate_worksheet_count": multisource_feasibility.get(
                "candidate_worksheet_count"
            ),
            "sample_data_rows_structurally_inspected_in_memory": (
                multisource_feasibility.get(
                    "sample_data_rows_structurally_inspected_in_memory"
                ) is True
            ),
            "measurement_values_persisted": multisource_feasibility.get(
                "measurement_values_persisted"
            ) is True,
            "unambiguous_full_loop_mapping_available": multisource_feasibility.get(
                "unambiguous_full_loop_mapping_available"
            ) is True,
            "full_loop_holdout_eligible": multisource_feasibility.get(
                "full_loop_holdout_eligible"
            ) is True,
            "decision": multisource_feasibility.get("decision"),
            "claim_limit": multisource_feasibility.get("claim_limit"),
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
            "boundary_channel_screen": (
                evidence.get("public_tank_validation_boundary") or {}
            ).get("boundary_channel_screen") or {},
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
            "mixed_convection_diagnostic": closed_loop.get(
                "mixed_convection_diagnostic"
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
        "cross_campaign_release_validation_boundary": {
            "evidence_role": cross_campaign_release.get("evidence_role"),
            "campaigns": cross_campaign_release.get("campaigns") or {},
            "eligible_campaign_count": cross_campaign_release.get(
                "eligible_campaign_count"
            ),
            "supported_campaign_count": cross_campaign_release.get(
                "supported_campaign_count"
            ),
            "failed_campaign_count": cross_campaign_release.get(
                "failed_campaign_count"
            ),
            "ineligible_campaign_count": cross_campaign_release.get(
                "ineligible_campaign_count"
            ),
            "universal_release_validation_supported": cross_campaign_release.get(
                "universal_release_validation_supported"
            ) is True,
            "apparatus_resolved_holdout_received": cross_campaign_release.get(
                "apparatus_resolved_holdout_received"
            ) is True,
            "apparatus_resolved_holdout_run": cross_campaign_release.get(
                "apparatus_resolved_holdout_run"
            ) is True,
            "runtime_model_changed_after_outcomes": cross_campaign_release.get(
                "runtime_model_changed_after_outcomes"
            ) is True,
            "claim_limit": cross_campaign_release.get("claim_limit"),
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
        "public_reference_leak_detector_evidence": {
            key: reference_detector.get(key)
            for key in (
                "doi", "related_article_doi", "evidence_role", "observation_count",
                "detector_class_count", "evaluated_series_count", "series",
                "joint_pass", "runtime_application",
                "spatial_detector_transfer_gate_changed",
                "full_loop_validation_supported", "claim_limit",
            )
            if reference_detector.get(key) is not None
        },
        "public_actual_hydrogen_spatial_stratification_evidence": {
            key: spatial_stratification.get(key)
            for key in (
                "dataset_doi", "article_doi", "evidence_role",
                "experiment_count", "sensor_count_per_experiment",
                "sensor_case_observation_count",
                "top_placement_highest_case_mean_count", "placements",
                "near_source_bottom",
                "bounded_guidance", "post_access_descriptive_evidence",
                "runtime_application", "h2safe_gate_changed",
                "independent_spatial_validation_supported",
                "full_loop_validation_supported", "claim_limit",
            )
            if spatial_stratification.get(key) is not None
        },
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
            "hiad_public_source": incident.get("public_source") or {},
            "hiad_digital_twin_replay": {
                key: (incident.get("digital_twin_replay") or {}).get(key)
                for key in (
                    "backend", "case_count", "integration_trace_pass_count",
                    "direct_physical_case_count", "partial_proxy_case_count",
                    "response_only_case_count", "canonical_recipe_pass_count",
                    "canonical_recipe_count",
                    "case_narrative_used_for_physical_parameters", "claim_limit",
                )
                if (incident.get("digital_twin_replay") or {}).get(key) is not None
            },
            "hiad_action_taxonomy": incident.get("action_taxonomy", {}).get(
                "category_patterns_version"
            ) if isinstance(incident.get("action_taxonomy"), dict) else None,
            "public_report_count": accident_inventory.get("public_report_count"),
            "incident_code_count": accident_inventory.get("incident_code_count"),
            "khk_digital_twin_replay": {
                key: (accident_inventory.get("digital_twin_replay") or {}).get(key)
                for key in (
                    "backend", "public_report_count", "incident_code_count",
                    "integration_trace_pass_report_count",
                    "integration_trace_pass_incident_code_count",
                    "out_of_scope_report_count", "canonical_recipe_pass_count",
                    "canonical_recipe_count",
                    "report_narrative_used_for_physical_parameters", "claim_limit",
                )
                if (accident_inventory.get("digital_twin_replay") or {}).get(key)
                is not None
            },
            "accidental_release_zenodo_doi": accidental_release.get("zenodo_doi"),
            "accidental_release_full_loop": accidental_release.get(
                "full_loop_station_vehicle_holdout_eligible"
            ),
            "accidental_release_reported_findings": accidental_release.get(
                "reported_findings"
            ) or {},
            "action_category_counts": {
                str(key): value
                for key, value in (action_taxonomy.get("category_counts") or {}).items()
                if isinstance(value, int)
            },
            "relevant_precedents_by_response_plan": (
                relevant_precedents.get("by_response_plan") or {}
            ),
            "precedent_claim_limit": relevant_precedents.get("claim_limit"),
        },
        "public_controlled_flare_evidence": {
            "doi": controlled_flare.get("doi"),
            "license": controlled_flare.get("license"),
            "reported_findings": controlled_flare.get("reported_findings") or {},
            "runtime_use": controlled_flare.get("runtime_use") or {},
            "claim_limit": controlled_flare.get("claim_limit"),
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
        "confidential_cross_station_bundle_recheck": {
            "evidence_role": cross_station_bundle.get("evidence_role"),
            "bundle_count": cross_station_bundle.get("bundle_count"),
            "bundles": cross_station_bundle.get("bundles") or [],
            "station_side_transfer_candidate": (
                cross_station_bundle.get("station_side_transfer_candidate") is True
            ),
            "full_loop_external_validation_supported": False,
            "quantitative_consequence_validation_supported": False,
            "claim_limit": cross_station_bundle.get("claim_limit"),
        },
        "confidential_local_station_cross_bundle_transfer": {
            "evidence_role": cross_station_transfer.get("evidence_role"),
            "candidate_margin_mpa": cross_station_transfer.get(
                "candidate_margin_mpa"
            ),
            "calibration_bundle": cross_station_transfer.get(
                "calibration_bundle"
            ) or {},
            "transfer_bundle": cross_station_transfer.get("transfer_bundle") or {},
            "candidate_relative_transfer_median_error_percent": (
                cross_station_transfer.get(
                    "candidate_relative_transfer_median_error_percent"
                )
            ),
            "fixed_candidate_corroborated_on_transfer_bundle": (
                cross_station_transfer.get(
                    "fixed_candidate_corroborated_on_transfer_bundle"
                ) is True
            ),
            "full_loop_external_validation_supported": False,
            "runtime_parameter_application": False,
            "claim_limit": cross_station_transfer.get("claim_limit"),
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
        "confidential_station_recharge_dynamics_calibration": {
            "profile_id": recharge_dynamics.get("profile_id"),
            "evidence_artifact": recharge_dynamics.get("artifact"),
            "files_read": recharge_dynamics.get("files_read"),
            "sampled_rows": recharge_dynamics.get("sampled_rows"),
            "candidate_minimum_recharge_off_time_s": recharge_dynamics.get(
                "candidate_minimum_recharge_off_time_s"
            ),
            "temporal_holdout": recharge_dynamics.get("temporal_holdout") or {},
            "opt_in_runtime_parameter_available": recharge_dynamics.get(
                "opt_in_runtime_parameter_available"
            ) is True,
            "runtime_application_block_reason": recharge_dynamics.get(
                "runtime_application_block_reason"
            ),
            "prior_single_trace_profile_superseded": recharge_dynamics.get(
                "prior_single_trace_profile_superseded"
            ) is True,
            "default_model_parameters_changed": recharge_dynamics.get(
                "default_model_parameters_changed"
            ) is True,
            "observed_high_bank_restart_pressure_band": recharge_dynamics.get(
                "observed_high_bank_restart_pressure_band"
            ) or {},
            "full_station_vehicle_validation": recharge_dynamics.get(
                "full_station_vehicle_validation"
            ) is True,
            "claim_limit": recharge_dynamics.get("claim_limit"),
        },
        "confidential_station_cascade_sequence_holdout": {
            "evidence_artifact": cascade_sequence.get("artifact"),
            "files_read": cascade_sequence.get("files_read"),
            "calibration": cascade_sequence.get("calibration") or {},
            "holdout": cascade_sequence.get("holdout") or {},
            "cascade_controller_structure_supported": cascade_sequence.get(
                "cascade_controller_structure_supported"
            ) is True,
            "runtime_parameter_application": cascade_sequence.get(
                "runtime_parameter_application"
            ) is True,
            "vehicle_fill_validation": cascade_sequence.get(
                "vehicle_fill_validation"
            ) is True,
            "full_loop_holdout_eligible": cascade_sequence.get(
                "full_loop_holdout_eligible"
            ) is True,
            "independent_external_validation": cascade_sequence.get(
                "independent_external_validation"
            ) is True,
            "claim_limit": cascade_sequence.get("claim_limit"),
        },
        "confidential_station_recharge_pressure_forecast_holdout": {
            "evidence_artifact": recharge_forecast.get("artifact"),
            "files_read": recharge_forecast.get("files_read"),
            "sampled_rows": recharge_forecast.get("sampled_rows"),
            "calibration_case_count": recharge_forecast.get(
                "calibration_case_count"
            ),
            "holdout_case_count": recharge_forecast.get("holdout_case_count"),
            "fitted_continuation_gain_by_bank": recharge_forecast.get(
                "fitted_continuation_gain_by_bank"
            ) or {},
            "holdout_metrics": recharge_forecast.get("holdout_metrics") or {},
            "short_horizon_station_pressure_forecast_supported": (
                recharge_forecast.get(
                    "short_horizon_station_pressure_forecast_supported"
                ) is True
            ),
            "runtime_parameter_application": recharge_forecast.get(
                "runtime_parameter_application"
            ) is True,
            "vehicle_fill_validation": recharge_forecast.get(
                "vehicle_fill_validation"
            ) is True,
            "full_loop_holdout_eligible": recharge_forecast.get(
                "full_loop_holdout_eligible"
            ) is True,
            "independent_external_validation": recharge_forecast.get(
                "independent_external_validation"
            ) is True,
            "claim_limit": recharge_forecast.get("claim_limit"),
        },
        "confidential_station_lifecycle_pressure_alignment_holdout": {
            "evidence_artifact": lifecycle_alignment.get("artifact"),
            "files": lifecycle_alignment.get("files") or {},
            "rows": lifecycle_alignment.get("rows") or {},
            "counter_quality": lifecycle_alignment.get("counter_quality") or {},
            "calibration": lifecycle_alignment.get("calibration") or {},
            "holdout": lifecycle_alignment.get("holdout") or {},
            "recall_shift_by_bank": lifecycle_alignment.get(
                "recall_shift_by_bank"
            ) or {},
            "eligibility": lifecycle_alignment.get("eligibility") or {},
            "screens": lifecycle_alignment.get("screens") or {},
            "pressure_completion_counter_alignment_supported": (
                lifecycle_alignment.get(
                    "pressure_completion_counter_alignment_supported"
                ) is True
            ),
            "recharge_event_detector_corroborated": lifecycle_alignment.get(
                "recharge_event_detector_corroborated"
            ) is True,
            "runtime_parameter_application": lifecycle_alignment.get(
                "runtime_parameter_application"
            ) is True,
            "vehicle_fill_validation": lifecycle_alignment.get(
                "vehicle_fill_validation"
            ) is True,
            "full_loop_holdout_eligible": lifecycle_alignment.get(
                "full_loop_holdout_eligible"
            ) is True,
            "independent_external_validation": lifecycle_alignment.get(
                "independent_external_validation"
            ) is True,
            "claim_limit": lifecycle_alignment.get("claim_limit"),
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
        "confidential_station_thermal_dynamics": {
            "artifact": station_thermal.get("artifact"),
            "protocol": station_thermal.get("protocol"),
            "status": station_thermal.get("status"),
            "mapped_channel_family_counts": station_thermal.get(
                "mapped_channel_family_counts"
            ) or {},
            "proposed_engineering_units": station_thermal.get(
                "proposed_engineering_units"
            ) or {},
            "proposals_attested": station_thermal.get("proposals_attested") is True,
            "confirmation_required": station_thermal.get(
                "confirmation_required"
            ) or {},
            "result_available": station_thermal.get("result_available") is True,
            "channel_attestation": station_thermal.get("channel_attestation") or {},
            "temporal_stability": station_thermal.get("temporal_stability") or {},
            "station_component_thermal_envelope_supported": station_thermal.get(
                "station_component_thermal_envelope_supported"
            ) is True,
            "runtime_parameter_application": station_thermal.get(
                "runtime_parameter_application"
            ) is True,
            "vehicle_fill_thermal_validation": station_thermal.get(
                "vehicle_fill_thermal_validation"
            ) is True,
            "full_station_vehicle_validation": station_thermal.get(
                "full_station_vehicle_validation"
            ) is True,
            "full_loop_holdout_eligible": station_thermal.get(
                "full_loop_holdout_eligible"
            ) is True,
            "default_model_parameters_changed": station_thermal.get(
                "default_model_parameters_changed"
            ) is True,
            "claim_limit": station_thermal.get("claim_limit"),
        },
        "confidential_bank_role_pressure_envelopes": {
            "artifact": bank_pressure.get("artifact"),
            "profiles": bank_pressure.get("profiles") or [],
            "bank_role_mapping_attested": bank_pressure.get(
                "bank_role_mapping_attested"
            ) is True,
            "pressure_scale_mapping_attested": bank_pressure.get(
                "pressure_scale_mapping_attested"
            ) is True,
            "machine_readable_unit_dictionary_present": bank_pressure.get(
                "machine_readable_unit_dictionary_present"
            ) is True,
            "temperature_or_flow_roles_attested": bank_pressure.get(
                "temperature_or_flow_roles_attested"
            ) is True,
            "bank_role_pressure_diagnostic_supported": bank_pressure.get(
                "bank_role_pressure_diagnostic_supported"
            ) is True,
            "runtime_parameter_application": bank_pressure.get(
                "runtime_parameter_application"
            ) is True,
            "full_station_vehicle_validation": bank_pressure.get(
                "full_station_vehicle_validation"
            ) is True,
            "full_loop_holdout_eligible": bank_pressure.get(
                "full_loop_holdout_eligible"
            ) is True,
            "default_model_parameters_changed": bank_pressure.get(
                "default_model_parameters_changed"
            ) is True,
            "claim_limit": bank_pressure.get("claim_limit"),
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
        "confidential_operational_profile_recheck": {
            "profile_match": operational_profile_recheck.get("profile_match") is True,
            "fields_compared": operational_profile_recheck.get("fields_compared") or [],
            "fields_omitted_without_attestation": operational_profile_recheck.get(
                "fields_omitted_without_attestation"
            ) or [],
            "sampled_rows": operational_profile_recheck.get("sampled_rows"),
            "channel_roles": operational_profile_recheck.get("channel_roles") or [],
            "committed_profile_replaced": operational_profile_recheck.get(
                "committed_profile_replaced"
            ) is True,
            "measured_boundary_calibration_remains_opt_in": operational_profile_recheck.get(
                "measured_boundary_calibration_remains_opt_in"
            ) is True,
            "full_station_vehicle_validation": operational_profile_recheck.get(
                "full_station_vehicle_validation"
            ) is True,
            "claim_limit": operational_profile_recheck.get("claim_limit"),
        },
        "confidential_station_channel_quality_recheck": {
            "files_read": channel_quality_recheck.get("files_read"),
            "sampled_rows": channel_quality_recheck.get("sampled_rows"),
            "parseable_timestamp_fraction": channel_quality_recheck.get(
                "parseable_timestamp_fraction"
            ),
            "timebase": channel_quality_recheck.get("timebase") or {},
            "roles": channel_quality_recheck.get("roles") or {},
            "discrete_state_transition_count": channel_quality_recheck.get(
                "discrete_state_transition_count"
            ),
            "temperature_or_flow_parameter_fit_supported": channel_quality_recheck.get(
                "temperature_or_flow_parameter_fit_supported"
            ) is True,
            "full_station_vehicle_validation": channel_quality_recheck.get(
                "full_station_vehicle_validation"
            ) is True,
            "full_loop_holdout_eligible": channel_quality_recheck.get(
                "full_loop_holdout_eligible"
            ) is True,
            "claim_limit": channel_quality_recheck.get("claim_limit"),
        },
        "confidential_station_signal_consistency": {
            "artifact": signal_consistency.get("artifact"),
            "analysis_status": signal_consistency.get("analysis_status"),
            "candidate_pairs_evaluated": signal_consistency.get(
                "candidate_pairs_evaluated"
            ),
            "strong_consistency_pairs": signal_consistency.get(
                "strong_consistency_pairs"
            ),
            "files_with_strong_consistency_pair": signal_consistency.get(
                "files_with_strong_consistency_pair"
            ),
            "candidate_pair_aggregate": signal_consistency.get(
                "candidate_pair_aggregate"
            ) or {},
            "strong_pair_aggregate": signal_consistency.get(
                "strong_pair_aggregate"
            ) or {},
            "channel_roles_attested": signal_consistency.get(
                "channel_roles_attested"
            ) is True,
            "flow_units_attested": signal_consistency.get(
                "flow_units_attested"
            ) is True,
            "totalizer_reset_semantics_attested": signal_consistency.get(
                "totalizer_reset_semantics_attested"
            ) is True,
            "calibration_status_attested": signal_consistency.get(
                "calibration_status_attested"
            ) is True,
            "flow_parameter_fit_supported": signal_consistency.get(
                "flow_parameter_fit_supported"
            ) is True,
            "absolute_mass_flow_supported": signal_consistency.get(
                "absolute_mass_flow_supported"
            ) is True,
            "full_station_vehicle_validation": signal_consistency.get(
                "full_station_vehicle_validation"
            ) is True,
            "independent_holdout": signal_consistency.get(
                "independent_holdout"
            ) is True,
            "claim_limit": signal_consistency.get("claim_limit"),
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
        "confidential_local_station_data_utilization": {
            "evidence_artifact": local_station_utilization.get("artifact"),
            "inventory": local_station_utilization.get("inventory") or {},
            "utilization": local_station_utilization.get("utilization") or {},
            "semantic_attestation": local_station_utilization.get(
                "semantic_attestation"
            ) or {},
            "assessment": local_station_utilization.get("assessment") or {},
            "claim_limit": local_station_utilization.get("claim_limit"),
        },
        "validation_readiness": {
            key: readiness.get(key)
            for key in (
                "evidence_role", "status", "ledger_integrity", "generated_at",
                "gate_counts", "bounded_ijhe_submission_ready",
                "full_user_objective_ready", "goal_completion_permitted",
                "full_loop_external_validation_supported",
                "expert_effectiveness_evaluation_supported",
                "independent_expert_review_complete", "claim_boundary",
            )
            if readiness.get(key) is not None
        },
        "local_station_data_revalidation": {
            "evidence_role": local_revalidation.get("evidence_role"),
            "generated_at": local_revalidation.get("generated_at"),
            "inventory": local_revalidation.get("inventory") or {},
            "sampled_candidate_manifest": local_revalidation.get(
                "sampled_candidate_manifest"
            ) or {},
            "broader_local_screen": local_revalidation.get(
                "broader_local_screen"
            ) or {},
            "decision": local_revalidation.get("decision") or {},
            "claim_limit": local_revalidation.get("claim_boundary"),
        },
        "confidential_local_station_asset_screen": {
            "evidence_artifact": local_station_asset_screen.get("artifact"),
            "scenario_matrix": local_station_asset_screen.get("scenario_matrix") or {},
            "asset_bundles": local_station_asset_screen.get("asset_bundles") or {},
            "coverage": local_station_asset_screen.get("coverage") or {},
            "claim_limit": local_station_asset_screen.get("claim_limit"),
        },
        "confidential_local_station_data_discovery": {
            "evidence_artifact": local_station_discovery.get("artifact"),
            "candidate_groups": local_station_discovery.get("candidate_groups") or {},
            "coverage_assessment": local_station_discovery.get(
                "coverage_assessment"
            ) or {},
            "claim_limit": local_station_discovery.get("claim_limit"),
        },
        "confidential_local_data_deep_scan": {
            "evidence_artifact": local_data_deep_scan.get("artifact"),
            "measured_station_bundle": local_data_deep_scan.get(
                "measured_station_bundle"
            ) or {},
            "broad_candidate_inventory": local_data_deep_scan.get(
                "broad_candidate_inventory"
            ) or {},
            "candidate_classes": local_data_deep_scan.get(
                "candidate_classes"
            ) or [],
            "full_loop_decision": local_data_deep_scan.get(
                "full_loop_decision"
            ) or {},
            "claim_limit": local_data_deep_scan.get("claim_limit"),
        },
        "local_adjacent_hydrogen_process_context": {
            "evidence_artifact": adjacent_process.get("artifact"),
            "evidence_role": adjacent_process.get("evidence_role"),
            "domain_classification": adjacent_process.get("domain_classification"),
            "high_pressure_process": adjacent_process.get(
                "high_pressure_process"
            ) or {},
            "liquid_hydrogen_centre_context": adjacent_process.get(
                "liquid_hydrogen_centre_context"
            ) or {},
            "runtime_parameter_application": adjacent_process.get(
                "runtime_parameter_application"
            ) is True,
            "station_to_vehicle_full_loop_validation": adjacent_process.get(
                "station_to_vehicle_full_loop_validation"
            ) is True,
            "quantitative_consequence_validation": adjacent_process.get(
                "quantitative_consequence_validation"
            ) is True,
            "claim_limit": adjacent_process.get("claim_limit"),
        },
        "local_docudata_full_discovery": {
            "evidence_artifact": docudata_discovery.get("artifact"),
            "evidence_role": docudata_discovery.get("evidence_role"),
            "broad_scan": docudata_discovery.get("broad_scan") or {},
            "refined_header_screen": docudata_discovery.get(
                "refined_header_screen"
            ) or {},
            "eligibility": docudata_discovery.get("eligibility") or {},
            "claim_limit": docudata_discovery.get("claim_limit"),
        },
        "confidential_private_media_intake": {
            "artifact": private_media.get("artifact"),
            "image_count": private_media.get("image_count"),
            "video_count": private_media.get("video_count"),
            "video_decoded_count": private_media.get("video_decoded_count"),
            "video_probe_undecodable_count": private_media.get(
                "video_probe_undecodable_count"
            ),
            "screen_recorded_logger_candidate": private_media.get(
                "screen_recorded_logger_candidate"
            ) is True,
            "machine_readable_trace_present": private_media.get(
                "machine_readable_trace_present"
            ) is True,
            "parameter_fit_permitted": private_media.get(
                "parameter_fit_permitted"
            ) is True,
            "full_loop_holdout_eligible": private_media.get(
                "full_loop_holdout_eligible"
            ) is True,
            "claim_limit": private_media.get("claim_limit"),
        },
        "impact_status": (manifest.get("impact") or {}).get("calculation_status"),
        "evidence_digest": manifest.get("evidence_digest"),
    }
