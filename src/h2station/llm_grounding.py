"""Machine-readable evidence envelopes for LLM decision support.

The envelope is deliberately small and deterministic.  It records what the
assistant was allowed to see; it does not turn a simulation into a field
measurement or make a consequence result more authoritative than its source.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any, Iterable


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
    canonical = json.dumps(envelope, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"), default=str).encode("utf-8")
    envelope["evidence_digest"] = "sha256:" + sha256(canonical).hexdigest()
    return envelope
