import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/grune_2014_archive_access_recheck_2026_10_05.json"


def test_grune_archive_recheck_verifies_complete_public_archive_without_promoting_trace():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    archive = result["local_archive"]
    assert result["status"] == "completed_archive_access_recheck"
    assert result["source"]["doi"] == "10.5281/zenodo.4668554"
    assert result["source"]["license"] == "CC BY 4.0"
    assert archive["file_count"] == 7
    assert archive["archive_complete"] is True
    assert archive["archive_identity_verified"] is True
    assert result["eligibility"]["pressure_time_trace_present"] is False
    assert result["eligibility"]["measured_half_pressure_time_observed"] is False
    assert result["eligibility"]["minimum_requirements_met"] is False
    assert result["eligibility"]["decision"] == "ARCHIVE_RECHECK_INELIGIBLE_FOR_GRUNE_PRESSURE_DECAY_HOLDOUT"


def test_grune_archive_recheck_classifies_non_trace_artifacts():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    files = {item["name"]: item for item in result["local_archive"]["files"]}
    assert files["HTE2440PS006MIXED_300321.zip"]["classification"] == "cad_geometry_archive"
    assert files["HTE2440PS000MIXED_300321.pdf"]["classification"] == "documentation_pdf"
    workbook = files["HTE2440PS001MIXED_300321.xlsx"]
    assert workbook["inspection"]["kind"] == "spatial_or_flow_field_summary_workbook"
    assert workbook["inspection"]["pressure_time_columns_found"] is False
