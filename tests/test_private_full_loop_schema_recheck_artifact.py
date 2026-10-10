import json
from pathlib import Path


def test_private_full_loop_recheck_is_explicitly_non_admitting_and_redacted():
    root = Path(__file__).resolve().parents[1]
    path = root / "research/private_full_loop_schema_recheck_2026_10_10.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    aggregate = report["aggregate"]
    assert aggregate["csv_files_seen"] == 8
    assert aggregate["readable_csv_files"] == 8
    assert aggregate["files_with_all_required_full_loop_groups"] == 0
    assert report["admission"]["full_loop_external_holdout_eligible"] is False
    assert report["scope"]["raw_rows_persisted"] is False
    assert report["scope"]["original_headers_persisted"] is False
    serialized = path.read_text(encoding="utf-8")
    assert "candidate_" not in serialized
    assert "C:\\Users" not in serialized

