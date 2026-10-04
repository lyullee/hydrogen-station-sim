import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/dataverse_hydrogen_explosion_dataset_inventory_2026_10_05.json"
REPORT = ROOT / "research/DATAVERSE_HYDROGEN_EXPLOSION_DATASET_INVENTORY_2026_10_05.md"


def test_dataverse_explosion_inventory_is_public_and_bounded():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "completed_dataverse_provenance_and_summary_inventory"
    assert len(result["sources"]) == 2
    assert {item["doi"] for item in result["sources"]} == {"10.18710/WSKBIJ", "10.18710/X044QK"}
    assert all(item["license"] == "CC0 1.0" for item in result["sources"])
    assert all(item["summary_file_identity_match"] for item in result["sources"])
    assert result["validation_status"]["model_comparison_performed"] is False
    assert result["validation_status"]["numeric_validation_gate_closed"] is False
    assert result["validation_status"]["full_loop_external_validation_supported"] is False


def test_dataverse_summary_workbooks_have_expected_experiment_coverage():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    wsk = next(item for item in result["sources"] if item["doi"] == "10.18710/WSKBIJ")
    x044 = next(item for item in result["sources"] if item["doi"] == "10.18710/X044QK")
    assert wsk["published_summary"]["experiment_count"] == 51
    assert wsk["published_summary"]["explosion_pressure_sensor_count"] == 4
    assert x044["published_summary"]["experiment_count"] == 40
    assert x044["published_summary"]["commented_experiments"]


def test_dataverse_report_preserves_claim_boundary():
    report = REPORT.read_text(encoding="utf-8")
    assert "not a model-validation result" in report
    assert "Full-loop external validation supported: **False**" in report
    assert "SAGA effectiveness" in report
