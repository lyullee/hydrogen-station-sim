import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_kgs_hrs_request_lead_preserves_no_raw_data_boundary():
    record = json.loads(
        (
            ROOT
            / "research/kgs_hrs_validation_data_request_lead_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["source"]["reported_scenarios"] == 6
    assert record["source"]["public_raw_logger_available"] is False
    assert record["gate_impact"] == "independent_full_loop_gate_remains_open"
    assert "pre-outcome freeze" in record["claim_boundary"]
    assert (ROOT / record["request_draft"]).is_file()
