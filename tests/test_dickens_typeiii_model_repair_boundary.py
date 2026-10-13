from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "research/dickens_typeiii_model_repair_boundary_2026_10_14.json"


def test_dickens_repair_boundary_is_fail_closed() -> None:
    payload = json.loads(BOUNDARY.read_text(encoding="utf-8"))

    assert payload["status"] == "REPAIR_BOUNDARY_ONLY"
    assert payload["frozen_validation_gate"] == "UNCHANGED_FAIL"
    assert payload["runtime_parameter_updated"] is False
    assert payload["runtime_promotion_allowed"] is False
    assert len(payload["unknown_source_metadata"]) >= 3
    assert len(payload["required_pre_access_inputs"]) >= 5
    assert "selecting a nozzle diameter from consumed outcomes" in payload[
        "prohibited_effects"
    ]
    assert "selecting an observation operator from consumed outcomes" in payload[
        "prohibited_effects"
    ]
