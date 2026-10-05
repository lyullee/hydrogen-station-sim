import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/grune_2014_publisher_access_recheck_2026_10_06.json"


def test_grune_publisher_recheck_records_official_source_without_promoting_holdout():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "publisher_access_recheck_completed"
    assert result["source"]["doi"] == "10.1016/j.ijhydene.2013.08.076"
    assert result["source"]["official_repository"].startswith("https://publikationen.bibliothek.kit.edu/")
    assert result["access_result"]["official_metadata_found"] is True
    assert result["access_result"]["machine_readable_pressure_time_trace_found"] is False
    assert result["access_result"]["trace_specific_half_pressure_endpoint_verified"] is False
    assert result["eligibility"]["full_raw_holdout_eligible"] is False
    assert result["eligibility"]["grune_2014_pressure_decay_gate_closed"] is False
