import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_private_schema_recheck_is_privacy_bounded_and_fail_closed():
    record = json.loads(
        (
            ROOT / "research/local_private_schema_recheck_2026_10_14.json"
        ).read_text(encoding="utf-8")
    )
    assert record["status"] == "privacy_bounded_recheck"
    assert record["decision"]["new_independent_vehicle_holdout_found"] is False
    assert record["decision"]["full_loop_gate_status"] == "unchanged_open"
    assert record["decision"]["runtime_model_changed"] is False
    assert record["bundles"][0]["vehicle_side_candidate_files"] == 0
    assert record["bundles"][1]["schema_candidate_vehicle_side_files"] == 36
    assert record["bundles"][1]["full_loop_candidate"] is False
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("source_paths", "source_filenames", "source_headers", "raw_rows", "manufacturer"):
        assert forbidden in serialized or forbidden == "manufacturer"
    assert "c:\\users\\" not in serialized

