"""Run a frozen apparatus-resolved campaign and archive aggregate-only evidence."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from h2station.apparatus_release_validation import (
    evaluate_apparatus_release_case,
    load_apparatus_release_csv,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "src" / "h2station" / "release_network.py"
EVALUATOR_PATH = ROOT / "src" / "h2station" / "apparatus_release_validation.py"
PROTOCOL_PATH = ROOT / "research" / "apparatus_resolved_release_protocol.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _validate_freeze(manifest: dict[str, Any]) -> None:
    freeze = manifest.get("freeze") or {}
    required_true = (
        "protocol_frozen_before_outcome_access",
        "model_frozen_before_outcome_access",
        "case_manifest_hashed_before_model_run",
        "post_freeze_parameter_tuning_prohibited",
        "failed_case_exclusion_prohibited",
    )
    if any(freeze.get(key) is not True for key in required_true):
        raise RuntimeError("campaign freeze declarations are incomplete")
    expected = {
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "model_sha256": _sha256(MODEL_PATH),
        "evaluator_sha256": _sha256(EVALUATOR_PATH),
        "runner_sha256": _sha256(Path(__file__).resolve()),
    }
    for field, actual in expected.items():
        if str(manifest.get(field, "")).upper() != actual:
            raise RuntimeError(f"campaign {field} does not match the frozen repository artifact")


def run_campaign(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_freeze(manifest)
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("campaign manifest requires at least one case")
    aliases = [str(item.get("case_id", "")) for item in cases]
    if any(not alias for alias in aliases) or len(set(aliases)) != len(aliases):
        raise ValueError("case_id values must be non-empty and unique")

    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case["case_id"])
        groups = case.get("strata") or {}
        record: dict[str, Any] = {
            "case_id": case_id,
            "source_pressure_group": str(groups.get("source_pressure_group", "")),
            "geometry_group": str(groups.get("geometry_group", "")),
            "valve_opening_group": str(groups.get("valve_opening_group", "")),
            "input_sha256": str(case.get("raw_data_sha256", "")).upper(),
            "evaluation_error": None,
            "joint_case_pass": False,
        }
        try:
            raw_path = Path(str(case["data_file"]))
            if not raw_path.is_absolute():
                raw_path = manifest_path.parent / raw_path
            actual_hash = _sha256(raw_path)
            if actual_hash != record["input_sha256"]:
                raise RuntimeError("raw data SHA-256 mismatch")
            trace = load_apparatus_release_csv(raw_path)
            model_parameters = dict(manifest.get("default_model_parameters") or {})
            model_parameters.update(case.get("model_parameter_overrides") or {})
            result = evaluate_apparatus_release_case(
                trace,
                model_parameters=model_parameters,
            )
            record.update(_json_safe(asdict(result)))
        except Exception as exc:  # every declared case remains in the result
            record["evaluation_error"] = f"{type(exc).__name__}: {exc}"
        results.append(record)

    pressure_groups = {item["source_pressure_group"] for item in results if item["source_pressure_group"]}
    geometry_groups = {item["geometry_group"] for item in results if item["geometry_group"]}
    valve_groups = {item["valve_opening_group"] for item in results if item["valve_opening_group"]}
    coverage = {
        "minimum_cases_met": len(results) >= 8,
        "two_source_pressure_groups_met": len(pressure_groups) >= 2,
        "two_geometry_groups_met": len(geometry_groups) >= 2,
        "two_valve_opening_groups_met": len(valve_groups) >= 2,
    }
    joint_passes = sum(item.get("joint_case_pass") is True for item in results)
    pass_fraction = joint_passes / len(results)
    coverage_pass = all(coverage.values())
    aggregate_pass = coverage_pass and pass_fraction >= 0.7
    return {
        "schema_version": 1,
        "artifact_type": "apparatus_resolved_release_external_holdout",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": str(manifest.get("campaign_id", "anonymous-campaign")),
        "manifest_sha256": _sha256(manifest_path),
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "model_sha256": _sha256(MODEL_PATH),
        "evaluator_sha256": _sha256(EVALUATOR_PATH),
        "privacy": {
            "source_identifiers_published": False,
            "raw_rows_persisted": False,
            "raw_paths_persisted": False,
            "exact_dates_published": False,
            "manufacturer_details_published": False,
        },
        "freeze": manifest["freeze"],
        "coverage": coverage,
        "aggregate": {
            "declared_cases": len(results),
            "evaluation_error_count": sum(bool(item["evaluation_error"]) for item in results),
            "joint_case_pass_count": joint_passes,
            "joint_case_pass_fraction": pass_fraction,
            "predeclared_minimum_joint_pass_fraction": 0.7,
            "claim_supported": aggregate_pass,
        },
        "decision": {
            "status": "PASS" if aggregate_pass else "FAIL",
            "claim_supported": aggregate_pass,
            "failed_cases_retained": True,
        },
        "cases": results,
        "claim_boundary": (
            "Apparatus-resolved source-line-valve-terminal pressure and mass-flow "
            "trajectory validation only. This result does not validate ignition, "
            "dispersion, harm distance, station control, or SAGA effectiveness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_campaign(args.manifest.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(args.output)
    print(report["decision"]["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
