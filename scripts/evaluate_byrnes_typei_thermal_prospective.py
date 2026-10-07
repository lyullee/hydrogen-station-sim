"""Retain the frozen Byrnes Type-I intake decision without channel guessing."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "research/byrnes_typei_thermal_prospective_protocol_2026_10_08.json"
DEFAULT_SOURCE = ROOT / "tmp/hyddown-v0.50.0"
DEFAULT_OUTPUT = ROOT / "research/byrnes_typei_thermal_prospective_result_2026_10_08.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def evaluate(source_root: Path, protocol_path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    expected = protocol["source"]["selected_files"]
    files: list[dict[str, Any]] = []
    mapping_failures: list[str] = []
    for relative in expected:
        path = source_root / relative
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        validation = document.get("validation") or {}
        temperature = validation.get("temperature") or {}
        pressure = validation.get("pressure") or {}
        observed_temperature_channels = sorted(temperature)
        pressure_value_keys = sorted(set(pressure) - {"time"})
        missing = []
        if "gas_high" not in temperature:
            missing.append("validation.temperature.gas_high")
        if "gas_low" not in temperature:
            missing.append("validation.temperature.gas_low")
        if missing:
            mapping_failures.extend(f"{Path(relative).name}:{item}" for item in missing)
        files.append({
            "name": Path(relative).name,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
            "observed_temperature_channels": observed_temperature_channels,
            "observed_pressure_value_keys": pressure_value_keys,
            "frozen_upper_lower_mapping_resolved": not missing,
            "numeric_values_committed": False,
        })
    prior = protocol["source"].get("correction") or {}
    prior_outcome_access = bool(
        protocol["source"].get("numerical_validation_arrays_accessed_before_freeze")
    )
    eligible = not prior_outcome_access and not mapping_failures and len(files) == 3
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_invalidated_prospective_attempt",
        "decision": (
            "MODEL_READY_FOR_FROZEN_SCREEN" if eligible
            else "PROTOCOL_INVALID_PRIOR_OUTCOME_ACCESS"
            if prior_outcome_access
            else "MODEL_NOT_RUN_FROZEN_CHANNEL_MAPPING_MISMATCH"
        ),
        "evidence_role": "retained_protocol_invalidation",
        "execution_commit": _commit(),
        "protocol": {
            "path": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
            "protocol_id": protocol["protocol_id"],
            "frozen_before_numeric_yaml_access": False,
            "prior_outcome_access_discovered_after_freeze": prior_outcome_access,
            "prior_artifact": prior.get("prior_artifact"),
            "prior_source_doi": prior.get("prior_source_doi"),
            "selected_files_replaced": False,
            "mapping_or_thresholds_changed_after_access": False,
        },
        "source": {
            "repository": protocol["source"]["repository"],
            "release_tag": protocol["source"]["release_tag"],
            "commit": protocol["source"]["commit"],
            "license": "MIT",
            "files": files,
            "raw_files_committed": False,
        },
        "eligibility": {
            "eligible": eligible,
            "prior_outcome_access": prior_outcome_access,
            "required_case_count": 3,
            "resolved_case_count": sum(
                item["frozen_upper_lower_mapping_resolved"] for item in files
            ),
            "frozen_mapping_failures": mapping_failures,
            "observed_unmapped_alternative": (
                "Each selected file reports gas_mean and wall_mean rather than the "
                "predeclared gas_high and gas_low pair. The alternative was not substituted."
            ),
        },
        "model_evaluation": {
            "executed": False,
            "metrics": None,
            "case_specific_fitting_performed": False,
            "reason": (
                "The same numerical files had already been accessed through a Zenodo "
                "archive, invalidating the prospective claim. Independently, the frozen "
                "upper/lower endpoint does not match the observed gas_mean schema."
            ),
        },
        "gate_impact": {
            "thermal_external_validation_supported": False,
            "eligible_case_count_contributed": 0,
            "status": "remains_open",
        },
        "claim_boundary": (
            "This retained invalidation is neither a prospective validation nor a "
            "numerical thermal-model failure. The same Byrnes values were already "
            "classified as post-access exploratory evidence."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = evaluate(args.source.resolve(), args.protocol.resolve())
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "mapping_failures": len(result["eligibility"]["frozen_mapping_failures"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
