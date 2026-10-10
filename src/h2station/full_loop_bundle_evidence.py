"""Privacy-bounded loader for a controlled station-to-vehicle bundle.

The controlled exporters write their receipt and frozen-evaluation result
outside this repository.  This module admits only quality aggregates to the
LLM evidence envelope.  A ready trace or a passing single-event evaluation is
never promoted to the repository-level full-loop validation gate here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_VARIABLE = "H2STATION_FULL_LOOP_RECEIPT"
RESULT_ENVIRONMENT_VARIABLE = "H2STATION_FULL_LOOP_RESULT"
_ARTIFACT_TYPES = frozenset({
    "controlled_deidentified_hrs_full_loop_export_receipt",
    "controlled_deidentified_hrs_multisource_export_receipt",
})
_SCOPES = frozenset({
    "station_to_vehicle_selected_bank_only",
    "cascade_resolved_station_to_vehicle",
})
_CLAIM_LIMIT = (
    "Controlled de-identified station-to-vehicle evaluator input only. "
    "The receipt does not establish an independent holdout, field safety, "
    "SAGA effectiveness, or the repository-level full-loop validation gate."
)
_RESULT_CLAIM_LIMIT = (
    "A single controlled trace was compared with a frozen model configuration. "
    "This bounded result is not a safety certification and does not by itself "
    "close the independent full-loop or IJHE readiness gates."
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


def _bounded_text(value: object, *, maximum: int = 96) -> str | None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        return None
    if any(ord(char) < 32 for char in value):
        return None
    return value.strip()


def _safe_receipt(record: dict[str, Any]) -> dict[str, Any] | None:
    if record.get("schema_version") != 1:
        return None
    if record.get("artifact_type") not in _ARTIFACT_TYPES:
        return None
    required_false = (
        "source_identifiers_published",
        "absolute_timestamps_published",
        "original_column_names_published",
        "raw_rows_persisted_in_repository",
    )
    if any(record.get(key) is not False for key in required_false):
        return None
    if record.get("controlled_access_only") is not True:
        return None
    if record.get("temperature_observation_semantics_attested") is not True:
        return None
    if record.get("station_to_vehicle_trace_ready") is not True:
        return None
    scope = record.get("evaluation_scope")
    if scope not in _SCOPES:
        return None
    rows = record.get("rows")
    if isinstance(rows, bool) or not isinstance(rows, int) or rows < 2:
        return None
    duration = record.get("time_duration_s")
    if not _finite(duration) or float(duration) <= 0.0:
        return None
    if not isinstance(record.get("cascade_dispatch_evaluable"), bool):
        return None
    if not isinstance(record.get("full_loop_trace_ready"), bool):
        return None
    if record["full_loop_trace_ready"] and not record["cascade_dispatch_evaluable"]:
        return None
    if not _bounded_text(record.get("claim_boundary"), maximum=1200):
        return None
    safe: dict[str, Any] = {
        "evidence_role": "controlled de-identified station-to-vehicle bundle",
        "status": "available",
        "rows": rows,
        "time_duration_s": float(duration),
        "evaluation_scope": scope,
        "station_to_vehicle_trace_ready": True,
        "cascade_dispatch_evaluable": record["cascade_dispatch_evaluable"],
        "full_loop_trace_ready": record["full_loop_trace_ready"],
        "evaluation_input_ready": True,
        "frozen_evaluation_required": True,
        "full_loop_external_validation_supported": False,
        "runtime_parameter_application": False,
        "claim_limit": _CLAIM_LIMIT,
    }
    for field in ("intake_decision", "quality_decision"):
        text = _bounded_text(record.get(field))
        if text is not None:
            safe[field] = text
    return safe


def _safe_result(record: dict[str, Any]) -> dict[str, Any] | None:
    if record.get("schema_version") != 1:
        return None
    if record.get("artifact_type") != "controlled_hrs_frozen_evaluation_result":
        return None
    if record.get("raw_rows_persisted") is not False:
        return None
    if record.get("source_identifiers_published") is not False:
        return None
    if record.get("absolute_timestamps_published") is not False:
        return None
    if record.get("evaluation_scope") not in _SCOPES:
        return None
    decision = record.get("decision")
    if decision not in {"FROZEN_EVALUATION_PASS", "FROZEN_EVALUATION_FAIL"}:
        return None
    model_samples = record.get("model_sample_count")
    observed_samples = record.get("observed_sample_count")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 2
        for value in (model_samples, observed_samples)
    ):
        return None
    metrics = record.get("metrics")
    acceptance = record.get("acceptance_by_metric")
    if not isinstance(metrics, dict) or not isinstance(acceptance, dict):
        return None
    safe_metrics: dict[str, dict[str, float | int]] = {}
    for name, raw_metric in metrics.items():
        if not isinstance(name, str) or not isinstance(raw_metric, dict):
            return None
        safe_metric: dict[str, float | int] = {}
        for key in ("sample_count", "rmse", "mae", "final_error", "maximum_absolute_error"):
            if key not in raw_metric:
                continue
            value = raw_metric[key]
            if key == "sample_count":
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    return None
                safe_metric[key] = value
            else:
                if not _finite(value):
                    return None
                safe_metric[key] = float(value)
        if not safe_metric:
            return None
        safe_metrics[name] = safe_metric
    if any(not isinstance(value, bool) for value in acceptance.values()):
        return None
    return {
        "status": "available",
        "decision": decision,
        "evaluation_scope": record["evaluation_scope"],
        "model_sample_count": model_samples,
        "observed_sample_count": observed_samples,
        "metrics": safe_metrics,
        "acceptance_by_metric": {
            str(key): value for key, value in acceptance.items()
        },
        "frozen_single_trace_result": True,
        "full_loop_external_validation_supported": False,
        "runtime_parameter_application": False,
        "claim_limit": _RESULT_CLAIM_LIMIT,
    }


def full_loop_bundle_evidence(frame: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return a sanitized controlled full-loop receipt and optional result."""

    frame = frame or {}
    inline = frame.get("full_loop_receipt")
    if isinstance(inline, dict):
        result = _safe_receipt(inline)
        if result is None:
            return None
        inline_result = frame.get("full_loop_result")
        if isinstance(inline_result, dict):
            result["frozen_evaluation_result"] = _safe_result(inline_result)
        return result

    raw_path = frame.get("full_loop_receipt_path") or os.environ.get(ENVIRONMENT_VARIABLE)
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path).expanduser().resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        return None
    result = _safe_receipt(_read(path) or {})
    if result is None:
        return None
    result_path = frame.get("full_loop_result_path") or os.environ.get(
        RESULT_ENVIRONMENT_VARIABLE
    )
    if isinstance(result_path, str) and result_path.strip():
        resolved_result = Path(result_path).expanduser().resolve()
        try:
            resolved_result.relative_to(ROOT.resolve())
        except ValueError:
            result["frozen_evaluation_result"] = _safe_result(_read(resolved_result) or {})
    return result


__all__ = [
    "ENVIRONMENT_VARIABLE",
    "RESULT_ENVIRONMENT_VARIABLE",
    "full_loop_bundle_evidence",
]
