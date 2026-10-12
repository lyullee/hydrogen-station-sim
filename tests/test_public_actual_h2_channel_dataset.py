import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/public_actual_h2_channel_dataset_inventory_2026_10_12.json"


def test_public_actual_h2_channel_inventory_has_bounded_schema_evidence():
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    source = result["source"]
    scope = result["dataset_scope"]
    eligibility = result["eligibility"]

    assert source["doi"].lower() == "10.23642/usn.26117989.v2"
    assert source["article_doi"] == "10.1016/j.jlp.2025.105669"
    assert source["license"] == "CC BY 4.0"
    assert scope["experiment_count"] == 22
    assert scope["sensor_count"] == 29
    assert eligibility["schema_screen_pass"] is True
    assert eligibility["independent_actual_hydrogen_component_candidate"] is True
    assert eligibility["runtime_parameter_application"] is False
    assert eligibility["validation_gate_promoted"] is False


def test_public_actual_h2_channel_inventory_does_not_commit_raw_rows_or_paths():
    result = ARTIFACT.read_text(encoding="utf-8")
    assert "raw_rows_committed" in result
    assert '"raw_rows_committed": false' in result
    assert "C:\\Temp" not in result
    assert "C:\\Users" not in result
