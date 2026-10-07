"""Aggregate a complete frozen controlled cohort without publishing raw hashes.

The private cohort protocol contains the exact expected trace digests.  Every
expected case must have one aggregate evaluator result.  A secret external salt
turns trace and result digests into stable cohort-local HMAC codes; the salt and
raw digests are never written to the registry.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SCOPES = frozenset({
    "station_to_vehicle_selected_bank_only",
    "cascade_resolved_station_to_vehicle",
})
BASE_METRICS = frozenset({
    "vehicle_pressure_mpa",
    "vehicle_temperature_c",
    "mass_flow_g_s",
    "delivered_temperature_c",
    "selected_source_pressure_mpa",
})
FULL_METRICS = frozenset({
    "cascade_low_pressure_mpa",
    "cascade_medium_pressure_mpa",
    "cascade_high_pressure_mpa",
})


def _outside_repository(path: Path, *, field: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{field} must be outside the repository worktree")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_digest(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _finite(value: object, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _hmac_code(salt: bytes, namespace: str, digest: str) -> str:
    value = hmac.new(salt, f"{namespace}:{digest.lower()}".encode(), hashlib.sha256).hexdigest()
    return f"{namespace}-{value[:16]}"


def _aggregate(values: list[float]) -> dict[str, float | int]:
    return {
        "case_count": len(values),
        "mean": float(statistics.fmean(values)),
        "median": float(statistics.median(values)),
        "minimum": float(min(values)),
        "maximum": float(max(values)),
    }


def build_registry(
    protocol_path: Path,
    result_paths: Iterable[Path],
    salt_path: Path,
) -> dict[str, Any]:
    protocol_path = _outside_repository(protocol_path, field="controlled cohort protocol")
    salt_path = _outside_repository(salt_path, field="registry HMAC salt")
    paths = [_outside_repository(path, field="controlled case result") for path in result_paths]
    protocol = _read_json(protocol_path)
    if protocol.get("schema_version") != 1 or protocol.get("artifact_type") != "controlled_hrs_frozen_cohort_protocol":
        raise ValueError("cohort protocol type or schema is invalid")
    if protocol.get("frozen_before_case_outcomes") is not True:
        raise ValueError("cohort protocol must be frozen before case outcomes")
    scope = protocol.get("evaluation_scope")
    if scope not in SCOPES:
        raise ValueError("cohort evaluation_scope is unsupported")
    model_commit = protocol.get("model_commit")
    if not isinstance(model_commit, str) or not model_commit.strip():
        raise ValueError("cohort model_commit is required")
    expected = protocol.get("expected_trace_sha256")
    if not isinstance(expected, list) or not expected or not all(_is_digest(value) for value in expected):
        raise ValueError("cohort expected_trace_sha256 must be a nonempty digest list")
    expected_normalized = [value.lower() for value in expected]
    if len(set(expected_normalized)) != len(expected_normalized):
        raise ValueError("cohort protocol contains duplicate traces")
    acceptance = protocol.get("cohort_acceptance")
    if not isinstance(acceptance, dict):
        raise ValueError("cohort_acceptance is required")
    minimum_cases = acceptance.get("minimum_case_count")
    if not isinstance(minimum_cases, int) or minimum_cases < 8:
        raise ValueError("minimum_case_count must be at least 8")
    minimum_fraction = _finite(
        acceptance.get("minimum_case_pass_fraction"), field="minimum_case_pass_fraction",
    )
    if not 0.8 <= minimum_fraction <= 1.0:
        raise ValueError("minimum_case_pass_fraction must be in [0.8, 1]")
    if len(expected_normalized) < minimum_cases:
        raise ValueError("frozen cohort has fewer expected traces than minimum_case_count")
    criteria = protocol.get("individual_acceptance_criteria")
    if not isinstance(criteria, dict) or not criteria:
        raise ValueError("individual_acceptance_criteria is required")
    if any(value is None for value in criteria.values()):
        raise ValueError("individual_acceptance_criteria still contains null values")
    design = protocol.get("evidence_design")
    if not isinstance(design, dict):
        raise ValueError("evidence_design is required")
    design_keys = (
        "independent_holdout",
        "model_developers_blinded_to_case_outcomes_before_freeze",
        "rights_cleared_for_controlled_evaluation",
    )
    if any(not isinstance(design.get(key), bool) for key in design_keys):
        raise ValueError("every evidence_design declaration must be boolean")

    salt = salt_path.read_bytes()
    if len(salt) < 32:
        raise ValueError("registry HMAC salt must contain at least 32 bytes")
    if len(paths) != len(expected_normalized):
        raise ValueError("one and only one result is required for every frozen cohort trace")

    results = []
    seen: set[str] = set()
    metric_names: set[str] | None = None
    state_names: set[str] | None = None
    required_metrics = BASE_METRICS | (FULL_METRICS if scope == "cascade_resolved_station_to_vehicle" else frozenset())
    for index, path in enumerate(paths, start=1):
        result = _read_json(path)
        if result.get("schema_version") != 1 or result.get("artifact_type") != "controlled_hrs_frozen_evaluation_result":
            raise ValueError(f"result {index} type or schema is invalid")
        trace_digest = result.get("trace_sha256")
        if not _is_digest(trace_digest):
            raise ValueError(f"result {index} has no usable trace digest")
        trace_digest = trace_digest.lower()
        if trace_digest in seen:
            raise ValueError("duplicate controlled trace result")
        seen.add(trace_digest)
        if trace_digest not in set(expected_normalized):
            raise ValueError("result trace is not in the frozen cohort")
        if result.get("evaluation_scope") != scope:
            raise ValueError("result evaluation_scope differs from cohort protocol")
        if result.get("source_commit") != model_commit or result.get("source_worktree_clean") is not True:
            raise ValueError("result source commit/cleanliness differs from cohort protocol")
        if any(result.get(key) is not False for key in (
            "raw_rows_persisted", "source_identifiers_published", "absolute_timestamps_published",
        )):
            raise ValueError("result privacy declarations are not safe for aggregation")
        if _canonical(result.get("acceptance_criteria")) != _canonical(criteria):
            raise ValueError("result individual acceptance criteria differ from frozen cohort")
        decisions = result.get("acceptance_by_metric")
        if not isinstance(decisions, dict) or not decisions or any(not isinstance(value, bool) for value in decisions.values()):
            raise ValueError("result acceptance_by_metric is invalid")
        expected_decision = "FROZEN_EVALUATION_PASS" if all(decisions.values()) else "FROZEN_EVALUATION_FAIL"
        if result.get("decision") != expected_decision:
            raise ValueError("result decision is inconsistent with its metric decisions")
        metrics = result.get("metrics")
        if not isinstance(metrics, dict) or not required_metrics.issubset(metrics):
            raise ValueError("result does not contain the required metrics for its scope")
        current_metric_names = set(metrics)
        if metric_names is None:
            metric_names = current_metric_names
        elif current_metric_names != metric_names:
            raise ValueError("all cohort results must expose the same metric set")
        state_metrics = result.get("state_metrics")
        if not isinstance(state_metrics, dict):
            raise ValueError("result state_metrics must be an object")
        if scope == "cascade_resolved_station_to_vehicle" and not {"selected_bank", "compressor_active"}.issubset(state_metrics):
            raise ValueError("full-loop result lacks dispatch/compressor state metrics")
        current_state_names = set(state_metrics)
        if state_names is None:
            state_names = current_state_names
        elif current_state_names != state_names:
            raise ValueError("all cohort results must expose the same state metric set")
        safe_metrics = {}
        for name, values in metrics.items():
            if not isinstance(values, dict):
                raise ValueError(f"metric {name} is invalid")
            safe_metrics[name] = {
                field: _finite(values.get(field), field=f"{name}.{field}")
                for field in ("rmse", "mae", "final_error", "maximum_absolute_error")
            }
        safe_states = {}
        for name, values in state_metrics.items():
            if not isinstance(values, dict):
                raise ValueError(f"state metric {name} is invalid")
            accuracy = _finite(values.get("accuracy"), field=f"{name}.accuracy")
            if not 0.0 <= accuracy <= 1.0:
                raise ValueError(f"state metric {name}.accuracy must be in [0, 1]")
            safe_states[name] = {"accuracy": accuracy}
        result_digest = _sha256(path)
        results.append({
            "case_code": _hmac_code(salt, "case", trace_digest),
            "result_code": _hmac_code(salt, "result", result_digest),
            "decision": expected_decision,
            "metrics": safe_metrics,
            "state_metrics": safe_states,
        })
    if seen != set(expected_normalized):
        raise ValueError("one or more frozen cohort traces has no result")
    results.sort(key=lambda row: row["case_code"])

    metric_aggregate = {
        name: {
            field: _aggregate([case["metrics"][name][field] for case in results])
            for field in ("rmse", "mae", "final_error", "maximum_absolute_error")
        }
        for name in sorted(metric_names or ())
    }
    state_aggregate = {
        name: {"accuracy": _aggregate([case["state_metrics"][name]["accuracy"] for case in results])}
        for name in sorted(state_names or ())
    }
    pass_count = sum(case["decision"] == "FROZEN_EVALUATION_PASS" for case in results)
    pass_fraction = pass_count / len(results)
    numerical_screen = len(results) >= minimum_cases and pass_fraction >= minimum_fraction
    provenance_ready = all(design[key] for key in design_keys)
    full_loop_supported = bool(
        numerical_screen and provenance_ready
        and scope == "cascade_resolved_station_to_vehicle"
    )
    return {
        "schema_version": 1,
        "artifact_type": "controlled_hrs_privacy_bounded_cohort_registry",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_scope": scope,
        "source_commit": model_commit,
        "controlled_protocol_code": _hmac_code(salt, "protocol", _sha256(protocol_path)),
        "case_count": len(results),
        "case_pass_count": pass_count,
        "case_pass_fraction": pass_fraction,
        "cohort_acceptance": {
            **acceptance,
            "numerical_screen_passed": numerical_screen,
        },
        "evidence_design": design,
        "provenance_screen_passed": provenance_ready,
        "full_loop_external_validation_supported": full_loop_supported,
        "individual_acceptance_criteria": criteria,
        "metric_aggregate": metric_aggregate,
        "state_metric_aggregate": state_aggregate,
        "cases": results,
        "privacy": {
            "raw_trace_hashes_published": False,
            "raw_result_hashes_published": False,
            "hmac_salt_published": False,
            "source_identifiers_published": False,
            "absolute_timestamps_published": False,
            "raw_rows_persisted": False,
        },
        "claim_boundary": (
            "This registry reports every case in one pre-frozen controlled cohort. "
            "Full-loop external validation is supported only when the numerical, "
            "independence, blinding, rights and cascade-resolved scope gates all pass."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--results", type=Path, nargs="+", required=True)
    parser.add_argument("--salt-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("cohort registry output must not already exist")
    registry = build_registry(args.protocol, args.results, args.salt_file)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "case_count": registry["case_count"],
        "case_pass_fraction": registry["case_pass_fraction"],
        "full_loop_external_validation_supported": registry["full_loop_external_validation_supported"],
    }, ensure_ascii=False))
    return 0 if registry["cohort_acceptance"]["numerical_screen_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
