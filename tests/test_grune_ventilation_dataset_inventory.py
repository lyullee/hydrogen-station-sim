import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research" / "grune_ventilation_dataset_inventory_2026_10_05.json"
REPORT = ROOT / "research" / "GRUNE_VENTILATION_DATASET_INVENTORY_2026_10_05.md"


def test_grune_inventory_is_reproducible_and_bounded():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "completed_provenance_and_measurement_inventory"
    assert result["source"]["doi"] == "10.5281/zenodo.4668554"
    assert result["source"]["license"] == "CC BY 4.0"
    inventory = result["inventory"]
    assert inventory["source_identity_all_match"] is True
    assert inventory["profile_count"] == 42
    assert inventory["spatial_point_count"] == 5256
    assert inventory["workbook_errors"] == []
    assert result["validation_status"]["model_comparison_performed"] is False
    assert result["validation_status"]["numeric_validation_gate_closed"] is False


def test_grune_inventory_report_states_claim_boundary():
    report = REPORT.read_text(encoding="utf-8")
    assert "not a model-validation result" in report
    assert "Full-loop external validation supported: **False**" in report
