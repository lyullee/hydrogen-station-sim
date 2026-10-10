"""Privacy-bounded loader for the optional component-intake receipt.

The receipt is produced outside the repository by
``export_confidential_component_bundle.py``. Only aggregate quality metadata
is admitted to the LLM evidence envelope; source paths, filenames, hashes and
measurement rows are intentionally discarded.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_VARIABLE = "H2STATION_COMPONENT_BUNDLE_RECEIPT"
REPLAY_ENVIRONMENT_VARIABLE = "H2STATION_COMPONENT_BUNDLE_REPLAY"

# Free-form text from a custodian receipt is not trusted input for the LLM
# envelope.  Keep the wording owned by this package so a receipt cannot smuggle
# a path, identifier, prompt fragment, or an overlong narrative into grounding.
_COMPONENT_CLAIM_LIMIT = (
    "Controlled de-identified station/dispenser component evidence only; "
    "raw rows and source identity are withheld. It does not establish "
    "station-to-vehicle full-loop validation, safety-distance validity, "
    "SAGA effectiveness, or runtime parameter application."
)
_REPLAY_CLAIM_LIMIT = (
    "Controlled de-identified station/dispenser replay diagnostic only; "
    "measured boundary values are exogenous and no predictive accuracy, "
    "vehicle-filling, safety-distance, SAGA-effectiveness, or full-loop "
    "validation claim is admitted."
)


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _finite(value: object) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number and abs(number) != float("inf")


def _safe_aggregate(record: dict[str, Any]) -> dict[str, Any] | None:
    if record.get("schema_version") != 1:
        return None
    if record.get("artifact_type") != "controlled_deidentified_hrs_component_bundle_receipt":
        return None
    if record.get("component_bundle_ready") is not True:
        return None
    if record.get("raw_rows_persisted_in_repository") is not False:
        return None
    if record.get("source_identifiers_published") is not False:
        return None
    if record.get("runtime_parameter_application") is not False:
        return None
    if record.get("full_loop_holdout_eligible") is not False:
        return None
    event_count = record.get("event_count")
    if isinstance(event_count, bool) or not isinstance(event_count, int) or event_count < 3:
        return None
    raw_summaries = record.get("event_summaries")
    if not isinstance(raw_summaries, list) or len(raw_summaries) != event_count:
        return None
    summaries: list[dict[str, Any]] = []
    required = ("rows", "duration_s", "min_pressure_mpa_abs", "max_pressure_mpa_abs", "max_mass_flow_g_s")
    for item in raw_summaries:
        if not isinstance(item, dict) or any(key not in item for key in required):
            return None
        try:
            rows = int(item["rows"])
            values = {key: float(item[key]) for key in required[1:]}
        except (TypeError, ValueError):
            return None
        if rows < 20 or any(not _finite(value) for value in values.values()):
            return None
        summaries.append({"rows": rows, **values})
    claim_boundary = record.get("claim_boundary")
    if not isinstance(claim_boundary, str) or not claim_boundary.strip():
        return None
    return {
        "evidence_role": "controlled de-identified HRS component bundle",
        "status": "available",
        "event_count": event_count,
        "event_summaries": summaries,
        "component_bundle_ready": True,
        "station_to_dispenser_boundary_replay_supported": True,
        "operating_range_face_validity_supported": True,
        "full_loop_external_validation_supported": False,
        "runtime_parameter_application": False,
        "claim_boundary_attested": True,
        "claim_limit": _COMPONENT_CLAIM_LIMIT,
    }


def _safe_replay(record: dict[str, Any]) -> dict[str, Any] | None:
    """Admit only aggregate replay diagnostics, never rows or source identity."""

    if record.get("schema_version") != 1:
        return None
    if record.get("artifact_type") != "controlled_component_bundle_replay_diagnostic":
        return None
    if record.get("raw_rows_persisted") is not False:
        return None
    if record.get("source_identifiers_published") is not False:
        return None
    if record.get("predictive_validation") is not False:
        return None
    if record.get("runtime_parameter_application") is not False:
        return None
    if record.get("full_loop_holdout_eligible") is not False:
        return None
    event_count = record.get("event_count")
    if isinstance(event_count, bool) or not isinstance(event_count, int) or event_count < 3:
        return None
    events = record.get("events")
    if not isinstance(events, list) or len(events) != event_count:
        return None
    safe_events: list[dict[str, Any]] = []
    for expected_index, item in enumerate(events, start=1):
        if not isinstance(item, dict):
            return None
        if item.get("event_index") != expected_index:
            return None
        observed = item.get("observed") or {}
        envelope = item.get("fixed_envelope") or {}
        runtime = item.get("runtime_replay") or {}
        if not isinstance(observed, dict) or not isinstance(envelope, dict) or not isinstance(runtime, dict):
            return None

        def numeric_map(source: dict[str, Any], keys: tuple[str, ...]) -> dict[str, float]:
            values: dict[str, float] = {}
            for key in keys:
                if key not in source or isinstance(source[key], bool):
                    continue
                try:
                    number = float(source[key])
                except (TypeError, ValueError):
                    return {}
                if not _finite(number):
                    return {}
                values[key] = number
            return values

        observed_values = numeric_map(
            observed,
            (
                "rows", "duration_s", "min_pressure_mpa_abs",
                "max_pressure_mpa_abs", "max_mass_flow_g_s",
                "integrated_mass_kg", "pressure_rise_mpa",
                "active_mean_mass_flow_g_s", "median_sample_period_s",
            ),
        )
        if not observed_values or "rows" not in observed_values:
            return None
        runtime_values = numeric_map(
            runtime,
            (
                "model_sample_count", "model_duration_s",
                "max_hose_pressure_mpa", "max_model_vehicle_temperature_c",
                "max_model_mass_flow_g_s",
            ),
        )
        # A runtime replay may be unavailable, but if a value is present it
        # must be a finite aggregate number rather than an arbitrary string.
        if any(key in runtime for key in (
            "model_sample_count", "model_duration_s", "max_hose_pressure_mpa",
            "max_model_vehicle_temperature_c", "max_model_mass_flow_g_s",
        )) and not runtime_values:
            return None
        replay_status = item.get("replay_status")
        if replay_status not in {"EXECUTED", "FAILED"}:
            return None
        fueling_stop_reason = runtime.get("fueling_stop_reason")
        if fueling_stop_reason is not None:
            if not isinstance(fueling_stop_reason, str) or len(fueling_stop_reason) > 160:
                return None
            if any(ord(char) < 32 for char in fueling_stop_reason):
                return None
        safe_events.append({
            "event_index": expected_index,
            "observed": {
                key: observed_values[key] for key in observed_values
            },
            "fixed_envelope": {
                key: envelope.get(key) is True
                for key in (
                    "pressure_within_model_envelope",
                    "temperature_within_fueling_envelope",
                    "mass_flow_within_model_envelope",
                )
            },
            "replay_status": replay_status,
            "runtime_replay": {
                **runtime_values,
                "esd_triggered": runtime.get("esd_triggered")
                if isinstance(runtime.get("esd_triggered"), bool) else False,
                **({"fueling_stop_reason": fueling_stop_reason}
                   if fueling_stop_reason is not None else {}),
            },
        })
    claim_boundary = record.get("claim_boundary")
    if not isinstance(claim_boundary, str) or not claim_boundary.strip():
        return None
    return {
        "status": "available",
        "decision": record.get("decision")
        if record.get("decision") in {"COMPONENT_REPLAY_DIAGNOSTIC_PASS", "COMPONENT_REPLAY_REVIEW"}
        else "COMPONENT_REPLAY_REVIEW",
        "event_count": event_count,
        "envelope_pass": record.get("envelope_pass") is True,
        "runtime_replay_pass": record.get("runtime_replay_pass") is True,
        "predictive_validation": False,
        "full_loop_holdout_eligible": False,
        "raw_rows_persisted": False,
        "source_identifiers_published": False,
        "events": safe_events,
        "claim_boundary_attested": True,
        "claim_limit": _REPLAY_CLAIM_LIMIT,
    }


def component_bundle_evidence(frame: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return a sanitized component receipt from a frame or opt-in env path."""

    frame = frame or {}
    inline = frame.get("component_bundle_receipt")
    if isinstance(inline, dict):
        result = _safe_aggregate(inline)
        if result is None:
            return None
        replay = frame.get("component_bundle_replay")
        if isinstance(replay, dict):
            result["replay_diagnostic"] = _safe_replay(replay)
        return result
    raw_path = frame.get("component_bundle_receipt_path") or os.environ.get(ENVIRONMENT_VARIABLE)
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path).expanduser().resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        return None
    result = _safe_aggregate(_read(path) or {})
    if result is None:
        return None
    replay_raw_path = frame.get("component_bundle_replay_path") or os.environ.get(
        REPLAY_ENVIRONMENT_VARIABLE
    )
    if isinstance(replay_raw_path, str) and replay_raw_path.strip():
        replay_path = Path(replay_raw_path).expanduser().resolve()
        try:
            replay_path.relative_to(ROOT.resolve())
        except ValueError:
            result["replay_diagnostic"] = _safe_replay(_read(replay_path) or {})
    return result


__all__ = [
    "ENVIRONMENT_VARIABLE",
    "REPLAY_ENVIRONMENT_VARIABLE",
    "component_bundle_evidence",
]
