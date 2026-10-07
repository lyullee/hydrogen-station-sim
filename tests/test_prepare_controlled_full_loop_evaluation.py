import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_controlled_full_loop_evaluation import draft_protocol  # noqa: E402


def _receipt(scope: str) -> dict:
    return {
        "trace_sha256": "a" * 64,
        "station_to_vehicle_trace_ready": True,
        "cascade_dispatch_evaluable": scope == "cascade_resolved_station_to_vehicle",
        "full_loop_trace_ready": scope == "cascade_resolved_station_to_vehicle",
        "evaluation_scope": scope,
    }


def test_draft_carries_only_hash_scope_and_preoutcome_placeholders(tmp_path):
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(_receipt("cascade_resolved_station_to_vehicle")), encoding="utf-8")

    draft = draft_protocol(receipt_path)

    assert draft["frozen_before_outcomes"] is False
    assert draft["expected_trace_sha256"] == "a" * 64
    assert draft["station"]["initial_bank_pressure_mpa"]["high"] is None
    assert draft["acceptance_criteria"]["dispatch_accuracy_min"] is None
    assert "cascade_bank_pressure_rmse_mpa_max" in draft["acceptance_criteria"]


def test_draft_rejects_selected_bank_scope_when_receipt_claims_full_dispatch(tmp_path):
    receipt_path = tmp_path / "receipt.json"
    payload = _receipt("station_to_vehicle_selected_bank_only")
    payload["cascade_dispatch_evaluable"] = True
    receipt_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="cascade-resolved receipt"):
        draft_protocol(receipt_path)
