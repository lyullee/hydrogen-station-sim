from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/byrnes_typei_thermal_prospective_protocol_2026_10_08.json"


def test_byrnes_protocol_freezes_exact_files_model_and_thresholds() -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert payload["status"] == "prospective_protocol_frozen_before_numeric_yaml_access"
    assert payload["source"]["numerical_validation_arrays_accessed_before_freeze"] is False
    assert payload["source"]["commit"] == "1040d758b819533451086baa5cf2a47b4292a22f"
    assert payload["source"]["selected_files"] == [
        "validation/Byrnes_run7.yml",
        "validation/Byrnes_run8.yml",
        "validation/Byrnes_run9.yml",
    ]
    assert payload["aggregate_decision"]["minimum_joint_case_passes"] == 2
    assert payload["aggregate_decision"]["required_case_count"] == 3
    assert payload["locked_model"]["pressure_role"].startswith("measured boundary")
    assert "release diameter" in payload["locked_model"]["prohibited_inputs"]


def test_byrnes_protocol_records_frozen_model_hash() -> None:
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    model = ROOT / payload["locked_model"]["path"]
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    assert payload["locked_model"]["sha256"] == digest
