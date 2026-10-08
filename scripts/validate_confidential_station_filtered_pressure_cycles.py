"""Run the frozen causal-filter revision of the station pressure-cycle holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.confidential_pressure_cycle_filtered_holdout import (  # noqa: E402
    evaluate_filtered_pressure_cycle_holdout,
)
from h2station.confidential_pressure_cycle_holdout import PressureCycleRules  # noqa: E402


def _outside_repository(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{label} must remain outside the repository")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "research/confidential_station_filtered_pressure_cycle_protocol_2026_10_08.json",
    )
    arguments = parser.parse_args()
    source = _outside_repository(arguments.input, label="input")
    mapping_path = _outside_repository(arguments.mapping, label="mapping")
    output = _outside_repository(arguments.output, label="output")
    protocol_path = arguments.protocol.resolve()
    protocol_path.relative_to(ROOT.resolve())
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    report = evaluate_filtered_pressure_cycle_holdout(
        source,
        mapping,
        rules=PressureCycleRules(**protocol["frozen_rules"]),
        role=str(protocol["target"]["role"]),
        frozen_candidate_mpa=float(protocol["target"]["candidate_mpa"]),
        median_window_samples=int(protocol["filter"]["window_samples"]),
    )
    report["protocol"] = {
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": _sha256(protocol_path),
        "mapping_sha256": _sha256(mapping_path),
        "revision_frozen_before_filtered_cycle_outcome_access": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "files_read": report["files_read"],
        "raw_data_rows": report["raw_data_rows"],
        "calibration_cycles": report["calibration"]["pressure_drop_mpa"]["count"],
        "holdout_cycles": report["holdout"]["pressure_drop_mpa"]["count"],
        "decision": report["decision"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
