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
    accidental_release = _public_accidental_release_evidence()
    if accidental_release is not None:
        envelope["response_evidence"]["public_accidental_release_evidence"] = accidental_release
    confidential_boundary = _confidential_measured_boundary_evidence()
    if confidential_boundary is not None:
        envelope["response_evidence"]["confidential_measured_boundary_replay"] = confidential_boundary
    public_benchmarks = _public_experimental_benchmarks()
    if public_benchmarks is not None:
        envelope["response_evidence"]["public_experimental_benchmarks"] = public_benchmarks
    canonical = json.dumps(envelope, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), default=str).encode("utf-8")
    envelope["evidence_digest"] = "sha256:" + sha256(canonical).hexdigest()
    return envelope
