"""Run the frozen station thermal method without claiming tag attestation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.station_thermal_diagnostic import (  # noqa: E402
    diagnose_unattested_station_thermal_stability,
)

from calibrate_confidential_station_data import _mapping  # noqa: E402


def _outside_repository(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{label} must be outside the repository worktree")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "research/confidential_station_thermal_dynamics_protocol_2026_10_08.json",
    )
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    arguments = parser.parse_args()
    source = _outside_repository(arguments.input, label="input")
    mapping_path = _outside_repository(arguments.mapping, label="mapping")
    output = _outside_repository(arguments.output, label="output")
    protocol_path = arguments.protocol.resolve()
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("status") != "frozen_awaiting_custodian_attestation":
        parser.error("thermal protocol is not in the expected frozen state")
    analysis = protocol.get("analysis") or {}
    report = diagnose_unattested_station_thermal_stability(
        source,
        _mapping(mapping_path),
        cooling_state_role="cooling_run",
        cooling_active_state_values=("1",),
        component_by_temperature_role={
            "compressor_temperature": "compressor",
            "cooler_inlet_temperature": "cooler_inlet",
            "cooler_outlet_temperature": "cooler_outlet",
        },
        calibration_fraction=float(analysis.get("calibration_fraction", 0.70)),
        minimum_holdout_rows=int(analysis.get("minimum_holdout_rows", 100)),
        stride=arguments.stride,
        max_rows_per_file=arguments.max_rows_per_file,
    )
    report["protocol"] = {
        "protocol_id": protocol.get("protocol_id"),
        "protocol_sha256": _sha256(protocol_path),
        "frozen_before_numerical_outcome_access": True,
        "attestation_pending_at_execution": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
