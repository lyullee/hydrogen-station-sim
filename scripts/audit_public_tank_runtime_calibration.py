"""Prove that the split-validated Type-IV tank fit reaches runtime defaults.

The public tank experiment is deliberately a component validation: measured
mass-flow and inlet-temperature traces drive the tank model.  This audit links
that frozen evidence to the simulator's default configuration without copying
experimental rows, workbook names, or a station-controller claim into a release
record.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.api import SimulationInput  # noqa: E402
from h2station.llm_grounding import build_evidence_manifest  # noqa: E402
from h2station.public_tank_calibration import (  # noqa: E402
    load_public_type_iv_tank_calibration,
)
from h2station.risk.runtime_backend import UnavailableHyRAMBackend  # noqa: E402
from h2station.scenario import ReferenceScenario, build_reference_scenario  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_record(root: Path = ROOT) -> dict[str, Any]:
    """Return a privacy-safe runtime/evidence integrity record."""

    profile = load_public_type_iv_tank_calibration()
    if profile is None:
        raise RuntimeError("validated public Type-IV tank profile is unavailable")
    scenario = build_reference_scenario(
        ReferenceScenario(), UnavailableHyRAMBackend()
    )
    api_default = SimulationInput().vehicle_tank_calibration
    fit = scenario.station.partial_station.vehicle_tank.fit
    manifest = build_evidence_manifest(
        {"time_s": 0.0, "vehicle_tank_calibration": api_default},
        {}, [], False,
    )
    runtime_evidence = manifest.get("runtime_vehicle_tank_calibration") or {}
    recheck_path = root / "research/public_type_iv_tank_validation_recheck_2026_10_07.json"
    recheck = json.loads(recheck_path.read_text(encoding="utf-8"))

    runtime_match = (
        api_default == "public_type_iv"
        and fit.effective_volume_multiplier == profile.effective_volume_multiplier
        and fit.gas_liner_ua_multiplier == profile.gas_liner_ua_multiplier
        and runtime_evidence.get("status") == "active"
        and runtime_evidence.get("id") == "public_type_iv_tank_v1"
        and runtime_evidence.get("validation_case_count") == profile.validation_case_count
    )
    recheck_match = bool((recheck.get("comparison") or {}).get("matches") is True)
    return {
        "schema_version": 1,
        "artifact_type": "public_type_iv_tank_runtime_calibration_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_experimental_rows_persisted": False,
        "source_workbook_names_persisted": False,
        "runtime_match": runtime_match,
        "runtime": {
            "api_default_mode": api_default,
            "effective_volume_multiplier": fit.effective_volume_multiplier,
            "gas_liner_ua_multiplier": fit.gas_liner_ua_multiplier,
            "llm_evidence_status": runtime_evidence.get("status"),
            "llm_evidence_id": runtime_evidence.get("id"),
            "validation_case_count": runtime_evidence.get("validation_case_count"),
        },
        "recheck": {
            "artifact": recheck_path.relative_to(root).as_posix(),
            "matches_frozen_expected_result": recheck_match,
            "sha256": _sha256(recheck_path),
        },
        "source_hashes": {
            relative: _sha256(root / relative)
            for relative in (
                "research/tank_model_validation_v2.json",
                "src/h2station/public_tank_calibration.py",
                "src/h2station/scenario.py",
                "src/h2station/api.py",
                "src/h2station/llm_grounding.py",
                "scripts/audit_public_tank_runtime_calibration.py",
            )
        },
        "claim_boundary": (
            "This proves only that the frozen public Type-IV tank fit is the "
            "runtime default and is disclosed to LLM evidence. The fit was "
            "validated with measured mass-flow and inlet-temperature boundaries; "
            "it does not validate a station-to-vehicle controller, compressor, "
            "cascade topology, dispenser, field safety, or vehicle certification."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/public_type_iv_tank_runtime_calibration_2026_10_07.json",
    )
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    record = build_record(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Keep the versioned audit deterministic across Windows and POSIX hosts.
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
