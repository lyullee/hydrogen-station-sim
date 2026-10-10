import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_figshare_intake_is_traceable_and_claim_bounded() -> None:
    path = ROOT / "research/figshare_h2_dispersion_intake_2026_10_10.json"
    record = json.loads(path.read_text(encoding="utf-8"))

    assert record["artifact_type"] == "figshare_open_channel_hydrogen_dispersion_intake"
    assert record["source"]["doi"] == "10.23642/usn.26117989.v2"
    assert record["source"]["license"] == "CC BY 4.0"
    assert record["source"]["file_count"] == 23
    assert record["eligibility"]["classification"] == "DISPERSION_COMPONENT_HOLDOUT_CANDIDATE"
    assert record["eligibility"]["full_loop_external_holdout_eligible"] is False
    assert record["eligibility"]["raw_files_committed"] is False
    assert record["decision"]["admit_to_full_loop_gate"] is False


def test_figshare_exemplar_schema_is_explicit() -> None:
    path = ROOT / "research/figshare_h2_dispersion_intake_2026_10_10.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    files = record["local_file_audit"]["files"]
    assert record["local_file_audit"]["audited_zip_count"] == 22
    exemplar = files[0]
    schema = exemplar["csv_schema"]
    assert schema["header_found"] is True
    assert schema["sensor_column_count"] == 29
    assert schema["flow_time_monotonic"] is True
    assert schema["sensor_time_monotonic"] is True
    assert exemplar["sha256"]
    assert exemplar["api_size_matches"] is True
    assert exemplar["api_md5_available"] is False
    assert exemplar["api_md5_matches"] is None
