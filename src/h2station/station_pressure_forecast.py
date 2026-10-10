"""Privacy-bounded station-side pressure forecast advisory.

The forecast gain is taken from the frozen, same-site chronological holdout
in ``research/confidential_station_recharge_pressure_forecast_holdout_2026_10_08.json``.
It is deliberately an advisory projection: it never changes the simulator
state, compressor capacity, restart thresholds, safety limits or ESD logic.
The runtime only applies it when a pressure-recharge operation is flowing and
the current frame contains a causal ten-second pressure prefix.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping


_ROOT = Path(__file__).resolve().parents[2]
_RESULT_PATH = _ROOT / (
    "research/confidential_station_recharge_pressure_forecast_holdout_"
    "2026_10_08.json"
)
_PROTOCOL_PATH = _ROOT / (
    "research/confidential_station_recharge_pressure_forecast_protocol_"
    "2026_10_08.json"
)
_BANKS = ("medium", "high")
_PREFIX_DURATION_S = 10.0
_FORECAST_DURATION_S = 30.0
_MIN_PREFIX_SPAN_S = 8.0
_MIN_RISE_MPA = 0.1
_DOMINANCE_RATIO = 1.5
_DOMINANCE_FLOOR_MPA = 0.05


def _finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


@lru_cache(maxsize=1)
def validated_profile() -> dict[str, Any] | None:
    """Load only the privacy-safe, positive forecast artifact."""

    try:
        result = json.loads(_RESULT_PATH.read_text(encoding="utf-8"))
        protocol = json.loads(_PROTOCOL_PATH.read_text(encoding="utf-8"))
        protocol_hash = hashlib.sha256(_PROTOCOL_PATH.read_bytes()).hexdigest()
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    privacy_keys = (
        "source_identifiers_published", "source_paths_published",
        "source_filenames_published", "source_headers_published",
        "raw_rows_persisted", "absolute_timestamps_published",
        "calendar_dates_published", "tag_names_published",
        "manufacturer_or_model_published",
    )
    decision = result.get("decision") or {}
    if (
        result.get("artifact_type")
        != "confidential_station_recharge_pressure_forecast_holdout"
        or not all(result.get(key) is False for key in privacy_keys)
        or (result.get("protocol") or {}).get("protocol_sha256") != protocol_hash
        or protocol.get("schema_version") != 1
        or decision.get("short_horizon_station_pressure_forecast_supported") is not True
        or decision.get("runtime_parameter_application") is not False
        or decision.get("default_model_parameters_changed") is not False
        or decision.get("vehicle_fill_validation") is not False
        or decision.get("full_loop_holdout_eligible") is not False
        or decision.get("independent_external_validation") is not False
        or not all((result.get("eligibility") or {}).values())
        or not all((result.get("screens") or {}).values())
    ):
        return None
    gains = (result.get("calibration") or {}).get(
        "fitted_continuation_gain_by_bank"
    ) or {}
    if any(_finite(gains.get(bank)) is None for bank in _BANKS):
        return None
    holdout = (result.get("holdout") or {}).get("combined") or {}
    return {
        "artifact": _RESULT_PATH.relative_to(_ROOT).as_posix(),
        "protocol": _PROTOCOL_PATH.relative_to(_ROOT).as_posix(),
        "sampled_rows": result.get("sampled_rows"),
        "calibration_case_count": (result.get("calibration") or {}).get("case_count"),
        "holdout_case_count": (result.get("holdout") or {}).get("case_count"),
        "gains": {bank: float(gains[bank]) for bank in _BANKS},
        "holdout_metrics": {
            key: holdout.get(key)
            for key in (
                "median_absolute_error_mpa", "p90_absolute_error_mpa",
                "mae_improvement_over_persistence_fraction",
                "positive_direction_fraction",
            )
        },
        "claim_limit": str(result.get("claim_boundary") or ""),
    }


def _activity_is_flowing(frame: Mapping[str, Any]) -> bool:
    activity = frame.get("process_activity") or {}
    recharge = activity.get("pressure_recharge") or {}
    return str(recharge.get("state") or "").casefold() == "flowing"


def _pressure_samples(
    frames: Iterable[Mapping[str, Any]],
    *,
    now_s: float,
) -> list[Mapping[str, Any]]:
    # Runtime frames are appended in chronological order.  Walk that common
    # path backwards and stop once the causal prefix is covered; otherwise a
    # long replay would still scan its entire history on every forecast call.
    if isinstance(frames, (list, tuple)):
        selected: list[Mapping[str, Any]] = []
        lower = now_s - _PREFIX_DURATION_S
        for frame in reversed(frames):
            time_s = _finite(frame.get("time_s"))
            if time_s is None or time_s > now_s:
                continue
            if time_s < lower:
                break
            selected.append(frame)
        selected.reverse()
        return selected
    selected: list[Mapping[str, Any]] = []
    lower = now_s - _PREFIX_DURATION_S
    for frame in frames:
        time_s = _finite(frame.get("time_s"))
        if time_s is not None and lower <= time_s <= now_s:
            selected.append(frame)
    selected.sort(key=lambda row: float(row.get("time_s")))
    return selected


def forecast_storage_pressure(
    frames: Iterable[Mapping[str, Any]],
    *,
    horizon_s: float = _FORECAST_DURATION_S,
) -> dict[str, Any]:
    """Return a causal advisory for medium/high storage pressure.

    The function is intentionally fail-closed and side-effect free.  A
    ``not_available`` result is normal while idle, during startup, or before
    ten seconds of usable pressure history have accumulated.
    """

    profile = validated_profile()
    if profile is None:
        return {
            "status": "not_available",
            "reason": "validated_profile_unavailable",
            "runtime_parameter_application": False,
        }
    rows = list(frames)
    if not rows:
        return {"status": "not_available", "reason": "no_frame"}
    current = rows[-1]
    now_s = _finite(current.get("time_s"))
    if now_s is None:
        return {"status": "not_available", "reason": "time_unavailable"}
    if not _activity_is_flowing(current):
        return {
            "status": "not_available",
            "reason": "pressure_recharge_not_flowing",
            "runtime_parameter_application": False,
        }
    samples = _pressure_samples(rows, now_s=now_s)
    if len(samples) < 2:
        return {"status": "not_available", "reason": "prefix_not_ready"}
    first_time = _finite(samples[0].get("time_s"))
    last_time = _finite(samples[-1].get("time_s"))
    if first_time is None or last_time is None or last_time - first_time < _MIN_PREFIX_SPAN_S:
        return {
            "status": "not_available",
            "reason": "prefix_not_ready",
            "prefix_span_s": max(0.0, (last_time or 0.0) - (first_time or 0.0)),
        }

    pressures: dict[str, tuple[float, float]] = {}
    current_pressures = current.get("bank_pressure_mpa") or {}
    for bank in _BANKS:
        first = _finite((samples[0].get("bank_pressure_mpa") or {}).get(bank))
        last = _finite((samples[-1].get("bank_pressure_mpa") or {}).get(bank))
        present = _finite(current_pressures.get(bank))
        if first is not None and last is not None and present is not None:
            pressures[bank] = (last - first, present)
    if len(pressures) != 2:
        return {"status": "not_available", "reason": "bank_pressure_not_ready"}
    rises = {bank: delta for bank, (delta, _) in pressures.items()}
    target = max(_BANKS, key=lambda bank: (rises[bank], bank))
    other = "high" if target == "medium" else "medium"
    if (
        rises[target] < _MIN_RISE_MPA
        or rises[target] < _DOMINANCE_RATIO * max(rises[other], _DOMINANCE_FLOOR_MPA)
    ):
        return {
            "status": "not_available",
            "reason": "bank_response_not_dominant",
            "prefix_span_s": round(last_time - first_time, 3),
        }
    span_s = last_time - first_time
    rate_mpa_s = rises[target] / span_s
    gain = profile["gains"][target]
    delta = rate_mpa_s * float(horizon_s) * gain
    current_mpa = pressures[target][1]
    p90_error = _finite(
        (profile.get("holdout_metrics") or {}).get("p90_absolute_error_mpa")
    )
    forecast_pressure = current_mpa + delta
    uncertainty: dict[str, Any] = {
        "method": "same_site_chronological_holdout_p90_absolute_error",
        "claim": "empirical forecast-error envelope, not a safety limit",
    }
    interval: dict[str, float] | None = None
    if p90_error is not None and p90_error >= 0.0:
        uncertainty["absolute_error_p90_mpa"] = round(p90_error, 6)
        interval = {
            "lower_mpa": round(max(0.0, forecast_pressure - p90_error), 6),
            "upper_mpa": round(forecast_pressure + p90_error, 6),
        }
    return {
        "status": "available",
        "bank": target,
        "current_pressure_mpa": round(current_mpa, 6),
        "forecast_pressure_mpa": round(forecast_pressure, 6),
        "forecast_delta_mpa": round(delta, 6),
        "prefix_span_s": round(span_s, 3),
        "horizon_s": float(horizon_s),
        "prefix_rise_mpa": round(rises[target], 6),
        "prefix_rate_mpa_s": round(rate_mpa_s, 9),
        "continuation_gain": gain,
        "uncertainty": uncertainty,
        "forecast_interval_mpa": interval,
        "basis": {
            "type": "causal_station_side_holdout_advisory",
            "artifact": profile["artifact"],
            "sampled_rows": profile["sampled_rows"],
            "calibration_case_count": profile["calibration_case_count"],
            "holdout_case_count": profile["holdout_case_count"],
            "holdout_metrics": profile["holdout_metrics"],
            "runtime_parameter_application": False,
            "vehicle_fill_validation": False,
            "full_loop_holdout_eligible": False,
            "claim_limit": profile["claim_limit"],
        },
    }


__all__ = ["forecast_storage_pressure", "validated_profile"]
