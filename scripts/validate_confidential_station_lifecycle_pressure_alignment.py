"""Run the frozen confidential lifecycle-counter/pressure alignment holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.confidential_lifecycle_pressure_alignment import (  # noqa: E402
    LifecyclePressureAlignmentRules,
    evaluate_lifecycle_pressure_alignment,
)


PROTOCOL_ID = "CONFIDENTIAL-STATION-LIFECYCLE-PRESSURE-ALIGNMENT-001"


def _outside_repository(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{label} must remain outside the repository")


def _git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = _outside_repository(args.input, label="input")
    mapping_path = _outside_repository(args.mapping, label="mapping")
    output = _outside_repository(args.output, label="output")
    protocol_path = args.protocol.resolve()
    protocol_path.relative_to(ROOT.resolve())
    protocol_bytes = protocol_path.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    if protocol.get("protocol_id") != PROTOCOL_ID:
        parser.error("unexpected protocol_id")
    if protocol.get("joint_alignment_outcomes_seen_before_freeze") is not False:
        parser.error("protocol is not prospective for the joint alignment")
    mapping_bytes = mapping_path.read_bytes()
    result = evaluate_lifecycle_pressure_alignment(
        source,
        json.loads(mapping_bytes.decode("utf-8")),
        rules=LifecyclePressureAlignmentRules(**protocol["rules"]),
    )
    result["protocol"] = {
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "mapping_sha256": hashlib.sha256(mapping_bytes).hexdigest(),
        "frozen_before_joint_alignment_outcome_access": True,
    }
    result["runner_git_commit"] = _git_head()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "files": result["files"],
        "calibration": result["calibration"]["combined"],
        "holdout": result["holdout"]["combined"],
        "decision": result["decision"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
