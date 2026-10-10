import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_recheck_preserves_full_loop_gate_boundary():
    record = json.loads(
        (ROOT / "research/external_full_loop_data_recheck_2026_10_11.json")
        .read_text(encoding="utf-8")
    )

    assert record["status"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET_IDENTIFIED"
    assert record["outcome"]["new_eligible_public_raw_set"] is False
    assert record["outcome"]["full_loop_gate_status_unchanged"] == "FAIL"
    assert len(record["candidates"]) == 3
    assert {item["decision"] for item in record["candidates"]} == {
        "REQUEST_RAW_TRACE",
        "REPORT_SUMMARY_ONLY",
    }
    for candidate in record["candidates"]:
        assert candidate["observed"]["machine_readable_common_timebase_public"] is False
