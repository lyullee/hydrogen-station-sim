import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _record() -> dict:
    path = ROOT / "research/usn_open_channel_dataverseno_recheck_2026_10_12.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_dataverseno_recheck_is_hash_locked_without_raw_redistribution() -> None:
    record = _record()
    assert record["artifact_type"] == "dataverseno_recheck_of_usn_open_channel_hydrogen_dispersion"
    assert record["source"]["doi"] == "10.23642/USN.26117989"
    assert record["source"]["license"] == "CC BY 4.0"
    assert record["source"]["file_count"] == 23
    assert record["archive_download"]["raw_files_committed"] is False
    assert record["archive_download"]["raw_rows_committed"] is False
    assert len(record["archive_download"]["package_sha256"]) == 64


def test_dataverseno_recheck_confirms_all_experiment_archives() -> None:
    record = _record()
    files = record["file_manifest"]
    archives = [item for item in files if item["name"].lower().endswith(".zip")]
    assert len(archives) == 22
    assert all(item["local_present"] for item in archives)
    assert all(item["md5_matches"] is True for item in archives)
    assert record["schema_audit"]["csv_count"] == 22
    assert record["schema_audit"]["sensor_count_per_csv"] == [29]
    assert record["schema_audit"]["column_counts"] == [37]


def test_dataverseno_recheck_keeps_paper_claim_boundary() -> None:
    record = _record()
    boundary = record["claim_boundary"]
    assert boundary["protocol_status"] == "POST_ACCESS_DEVELOPMENT_ONLY"
    assert boundary["outcome_independence"] is False
    assert "independent actual-hydrogen open-channel validation" in boundary["not_eligible_for"]
    assert boundary["runtime_parameter_application"] is False
    assert "station-to-vehicle full-loop validation" in boundary["not_eligible_for"]
    assert "SAGA human-effectiveness claim" in boundary["not_eligible_for"]
