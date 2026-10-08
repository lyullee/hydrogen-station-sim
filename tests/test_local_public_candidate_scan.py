from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/local_public_candidate_scan_2026_10_09.json"


def test_public_candidate_scan_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "privacy_bounded_local_workspace_candidate_scan"
    assert all(value is False for value in record["privacy"].values())


def test_public_candidate_scan_does_not_promote_static_qra_tables() -> None:
    scan = json.loads(ARTIFACT.read_text(encoding="utf-8"))["scan"]
    classes = scan["coarse_candidate_classes"]
    assert scan["machine_readable_files"] == 263
    assert scan["csv_tsv_headers_screened"] == 159
    assert classes["release_rig_experiment_candidate"] == 58
    assert classes["vehicle_or_dispenser_candidate"] == 2
    assert classes.get("vehicle_pressure_temperature_candidate", 0) == 0
