import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/elvhys_4_2_public_dataset_inventory_2026_10_12.json"


def test_elvhys_inventory_captures_actual_cryogenic_hydrogen_scope():
    result = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    source = result["source"]
    scope = result["dataset_scope"]
    eligibility = result["eligibility"]

    assert source["doi"] == "10.18710/JXJP0H"
    assert source["license"] == "CC0 1.0"
    assert scope["actual_cryogenic_hydrogen"] is True
    assert scope["published_test_plan_count"] == 48
    assert scope["case_id_count_with_public_data"] == 40
    assert scope["file_family_counts"]["concentration"] == 40
    assert scope["file_family_counts"]["pressure"] == 40
    assert scope["file_family_counts"]["temperature"] == 40
    assert scope["test_plan_type_counts"]["pressure_peaking"] == 3
    assert scope["test_plan_type_counts"]["ignition"] == 11
    assert eligibility["schema_screen_pass"] is True
    assert eligibility["independent_actual_cryogenic_hydrogen_component_candidate"] is True
    assert eligibility["station_to_vehicle_full_loop"] is False
    assert eligibility["runtime_parameter_application"] is False


def test_elvhys_inventory_excludes_raw_rows_and_source_filenames():
    rendered = ARTIFACT.read_text(encoding="utf-8")
    result = json.loads(rendered)
    assert result["integrity"]["raw_rows_committed"] is False
    assert result["integrity"]["source_filenames_committed"] is False
    assert "ELE402HSE" not in rendered
    assert "C:\\Temp" not in rendered
    assert result["claim_boundary"].startswith("Public ELVHYS 4.2")

