"""Small, reproducible metrics for the digital-twin research prototype.

The protocol audit checks the public schedule boundary implemented by this
project.  It must not be described as SAE J2601 certification: the licensed
tables, station qualification and hardware test matrix are outside this code.

The decision-support score is deliberately transparent.  It measures whether
an answer contains the situation, ordered actions, prevention and calculated
impact concepts supplied by a fixed evaluation case.  It does not ask another
LLM to judge the answer, which keeps repeated A/B runs comparable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
from typing import Iterable, Mapping, Sequence

import numpy as np

from .protocol import FuelingSchedule


@dataclass(frozen=True)
class ProtocolAudit:
    case_id: str
    sample_count: int
    active_duration_s: float
    scheduled_aprr_mpa_min: float
    observed_aprr_mpa_min: float
    aprr_error_percent: float
    pressure_tracking_rmse_mpa: float
    final_pressure_mpa: float
    final_soc_percent: float
    target_soc_percent: float
    soc_shortfall_percent: float
    soc_target_pass: bool
    peak_mass_flow_g_s: float
    peak_gas_temperature_c: float
    hard_pressure_margin_mpa: float
    temperature_margin_c: float
    flow_margin_g_s: float
    completion_reason: str
    completion_pass: bool
    safety_envelope_pass: bool
    protocol_boundary_pass: bool
    failures: tuple[str, ...]
    scope: str = (
        "Public SAE J2601-compatible schedule-boundary audit; not SAE J2601 "
        "certification or station qualification."
    )

    def to_dict(self) -> dict:
        return asdict(self)


def audit_fueling_protocol(
    *,
    case_id: str,
    schedule: FuelingSchedule,
    time_s: Sequence[float],
    pressure_pa: Sequence[float],
    reference_pressure_pa: Sequence[float],
    gas_temperature_k: Sequence[float],
    mass_flow_kg_s: Sequence[float],
    soc: Sequence[float],
    completion_reason: str | None,
    hard_pressure_limit_pa: float | None = None,
    aprr_tolerance_percent: float = 20.0,
) -> ProtocolAudit:
    """Audit one simulated fill against its externally supplied schedule.

    Only samples through the last non-trivial flow are used for APRR and
    pressure-tracking metrics.  Safety maxima use the complete supplied trace.
    """

    arrays = [np.asarray(values, dtype=float) for values in (
        time_s, pressure_pa, reference_pressure_pa, gas_temperature_k,
        mass_flow_kg_s, soc,
    )]
    time, pressure, reference, temperature, flow, state_of_charge = arrays
    if any(values.ndim != 1 for values in arrays):
        raise ValueError("Protocol audit inputs must be one-dimensional")
    if len({len(values) for values in arrays}) != 1 or len(time) < 2:
        raise ValueError("Protocol audit inputs must have equal length >= 2")
    if np.any(np.diff(time) <= 0.0) or not all(np.all(np.isfinite(v)) for v in arrays):
        raise ValueError("Protocol audit inputs must be finite with increasing time")

    active = np.flatnonzero(flow > 1.0e-7)
    first = int(active[0]) if active.size else 0
    last = int(active[-1]) if active.size else len(time) - 1
    if last <= first:
        first, last = 0, len(time) - 1
    active_slice = slice(first, last + 1)
    duration = float(time[last] - time[first])
    observed_aprr = (
        float(pressure[last] - pressure[first]) / max(duration, 1.0e-12)
    ) * 60.0 / 1.0e6
    scheduled_aprr = schedule.average_pressure_ramp_rate_pa_s * 60.0 / 1.0e6
    aprr_error = 100.0 * abs(observed_aprr - scheduled_aprr) / scheduled_aprr
    tracking_rmse = float(np.sqrt(np.mean(
        (pressure[active_slice] - reference[active_slice]) ** 2
    ))) / 1.0e6

    hard_limit = hard_pressure_limit_pa or 1.25 * schedule.nominal_working_pressure_pa
    peak_pressure = float(np.max(pressure))
    peak_temperature = float(np.max(temperature))
    peak_flow = float(np.max(np.maximum(flow, 0.0)))
    final_pressure = float(pressure[-1])
    final_soc = float(state_of_charge[-1])
    reason = completion_reason or "not-completed"

    pressure_complete = final_pressure >= schedule.target_pressure_pa - 2.5e5
    soc_complete = final_soc >= schedule.target_soc - 0.005
    completion_pass = reason in {"target-pressure", "target-soc"} and (
        pressure_complete or soc_complete
    )
    failures: list[str] = []
    if peak_pressure > hard_limit + 1.0e4:
        failures.append("hard-pressure-limit")
    if peak_temperature > schedule.maximum_gas_temperature_k + 0.05:
        failures.append("gas-temperature-limit")
    if peak_flow > schedule.maximum_mass_flow_kg_s + 1.0e-5:
        failures.append("mass-flow-limit")
    if np.any(np.diff(reference[active_slice]) < -1.0):
        failures.append("non-monotonic-pressure-reference")
    if aprr_error > aprr_tolerance_percent:
        failures.append("aprr-tracking")
    safety_pass = not any(item in failures for item in (
        "hard-pressure-limit", "gas-temperature-limit", "mass-flow-limit",
        "non-monotonic-pressure-reference",
    ))
    if not completion_pass:
        failures.append("completion")

    return ProtocolAudit(
        case_id=case_id,
        sample_count=len(time),
        active_duration_s=duration,
        scheduled_aprr_mpa_min=scheduled_aprr,
        observed_aprr_mpa_min=observed_aprr,
        aprr_error_percent=aprr_error,
        pressure_tracking_rmse_mpa=tracking_rmse,
        final_pressure_mpa=final_pressure / 1.0e6,
        final_soc_percent=100.0 * final_soc,
        target_soc_percent=100.0 * schedule.target_soc,
        soc_shortfall_percent=max(0.0, 100.0 * (schedule.target_soc - final_soc)),
        soc_target_pass=soc_complete,
        peak_mass_flow_g_s=1000.0 * peak_flow,
        peak_gas_temperature_c=peak_temperature - 273.15,
        hard_pressure_margin_mpa=(hard_limit - peak_pressure) / 1.0e6,
        temperature_margin_c=schedule.maximum_gas_temperature_k - peak_temperature,
        flow_margin_g_s=1000.0 * (schedule.maximum_mass_flow_kg_s - peak_flow),
        completion_reason=reason,
        completion_pass=completion_pass,
        safety_envelope_pass=safety_pass,
        protocol_boundary_pass=safety_pass and completion_pass and aprr_error <= aprr_tolerance_percent,
        failures=tuple(dict.fromkeys(failures)),
    )


@dataclass(frozen=True)
class DecisionSupportRubric:
    case_id: str
    situation_concepts: tuple[tuple[str, ...], ...]
    ordered_action_concepts: tuple[tuple[str, ...], ...]
    prevention_concepts: tuple[tuple[str, ...], ...] = ()
    impact_concepts: tuple[tuple[str, ...], ...] = ()
    grounded_numeric_concepts: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class DecisionSupportScore:
    case_id: str
    variant: str
    score: float
    situation_coverage: float
    action_coverage: float
    action_order: float
    prevention_coverage: float
    impact_coverage: float
    grounded_numeric_coverage: float
    unsupported_numeric_claims: tuple[str, ...]
    response_characters: int
    latency_ms: float | None = None
    answer_text: str = ""
    provider: str = ""
    model: str = ""
    repeat_index: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


def _normalized(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _concept_positions(answer: str, groups: Iterable[tuple[str, ...]]) -> list[int | None]:
    compact = _normalized(answer)
    positions: list[int | None] = []
    for alternatives in groups:
        found = [compact.find(_normalized(term)) for term in alternatives]
        found = [position for position in found if position >= 0]
        positions.append(min(found) if found else None)
    return positions


_NUMBER_WITH_UNIT = re.compile(
    r"(?<![\w.-])(-?\d+(?:\.\d+)?)\s*(MPa|kPa|Pa|°C|℃|vol%_?H2|vol%|g/s|kg/s|kW/m²|kW/m2|m)",
    re.IGNORECASE,
)


def _numeric_claims(text: str) -> set[str]:
    claims = set()
    for number, unit in _NUMBER_WITH_UNIT.findall(text):
        normalized_unit = unit.lower().replace("℃", "°c").replace("kw/m²", "kw/m2")
        if normalized_unit.startswith("vol%"):
            normalized_unit = "vol%"
        claims.add(f"{float(number):g}{normalized_unit}")
    return claims


def score_decision_support(
    *,
    answer: str,
    allowed_evidence: str,
    rubric: DecisionSupportRubric,
    variant: str,
    latency_ms: float | None = None,
    provider: str = "",
    model: str = "",
    repeat_index: int = 1,
) -> DecisionSupportScore:
    """Score one answer without model-based judging or hidden reference text."""

    situation_positions = _concept_positions(answer, rubric.situation_concepts)
    action_positions = _concept_positions(answer, rubric.ordered_action_concepts)
    prevention_positions = _concept_positions(answer, rubric.prevention_concepts)
    impact_positions = _concept_positions(answer, rubric.impact_concepts)
    grounded_numeric_positions = _concept_positions(answer, rubric.grounded_numeric_concepts)

    def coverage(positions: Sequence[int | None]) -> float:
        return 1.0 if not positions else sum(item is not None for item in positions) / len(positions)

    matched_actions = [item for item in action_positions if item is not None]
    action_order = (
        0.0 if not matched_actions
        else 1.0 if len(action_positions) == 1
        else 0.0 if len(matched_actions) == 1
        else sum(left < right for left, right in zip(matched_actions, matched_actions[1:]))
        / (len(matched_actions) - 1)
    )
    situation = coverage(situation_positions)
    actions = coverage(action_positions)
    prevention = coverage(prevention_positions)
    impact = coverage(impact_positions)
    grounded_numeric = coverage(grounded_numeric_positions)
    unsupported = tuple(sorted(_numeric_claims(answer) - _numeric_claims(allowed_evidence)))
    score = 100.0 * (
        0.25 * situation + 0.35 * actions + 0.10 * action_order
        + 0.15 * prevention + 0.15 * impact
    )
    if unsupported:
        score = max(0.0, score - min(20.0, 5.0 * len(unsupported)))
    return DecisionSupportScore(
        case_id=rubric.case_id,
        variant=variant,
        score=round(score, 2),
        situation_coverage=round(situation, 4),
        action_coverage=round(actions, 4),
        action_order=round(action_order, 4),
        prevention_coverage=round(prevention, 4),
        impact_coverage=round(impact, 4),
        grounded_numeric_coverage=round(grounded_numeric, 4),
        unsupported_numeric_claims=unsupported,
        response_characters=len(answer),
        latency_ms=None if latency_ms is None or not math.isfinite(latency_ms) else round(latency_ms, 2),
        answer_text=answer,
        provider=provider,
        model=model,
        repeat_index=repeat_index,
    )
