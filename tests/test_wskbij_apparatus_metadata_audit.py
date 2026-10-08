from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "research/wskbij_apparatus_metadata_audit_2026_10_08.json"
CONTRACT_PATH = ROOT / "research/wskbij_apparatus_input_contract.schema.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_apparatus_audit_fails_closed_on_missing_geometry() -> None:
    audit = _load(AUDIT_PATH)
    eligibility = audit["eligibility"]

    assert audit["dataset"]["doi"] == "10.18710/WSKBIJ"
    assert audit["decision"] == "INSUFFICIENT_PUBLIC_METADATA_FOR_APPARATUS_AWARE_MODEL"
    assert eligibility["contract"] == "research/wskbij_apparatus_input_contract.schema.json"
    assert eligibility["apparatus_aware_rank_model"] is False
    assert eligibility["absolute_overpressure_model"] is False
    assert eligibility["sensor_distance_attenuation_model"] is False

    missing = set(audit["metadata_inventory"]["required_but_missing"])
    assert {
        "case_to_obstructed_or_unobstructed_mapping",
        "case_resolved_obstacle_coordinates_and_nozzle_distance",
        "ignition_position_code_to_xyz_mapping",
        "P01_to_P04_xyz_coordinates",
        "case_resolved_ambient_conditions",
    } <= missing
    assert "fit geometry corrections" in " ".join(audit["prohibited_use"])
    assert audit["claim_boundary"]


def test_raw_header_samples_span_both_acquisition_schemas() -> None:
    audit = _load(AUDIT_PATH)
    inspected = {item["name"]: item for item in audit["inspected_public_files"]}

    assert {"00_Readme.txt", "Experimental_results_.xlsx", "Test001.txt", "Test013.txt", "Test028.txt", "Test051.txt"} <= set(inspected)
    assert all(len(item["observed_sha256"]) == 64 for item in inspected.values())

    schemas = audit["observed_raw_schemas"]
    first = schemas["experiments_1_to_27"]
    second = schemas["experiments_28_to_51"]
    assert first["header"][1:5] == ["P01", "P02", "P03", "P04"]
    assert first["units"][1:5] == ["kPa"] * 4
    assert "MFR" in first["header"]
    assert "Sound" in second["header"]
    assert first["sample_interval_s"] == second["sample_interval_s"] == 0.000002


def test_contract_requires_spatial_case_mapping_and_publisher_provenance() -> None:
    contract = _load(CONTRACT_PATH)

    assert contract["$schema"].endswith("2020-12/schema")
    assert contract["properties"]["dataset_doi"]["const"] == "10.18710/WSKBIJ"
    assert contract["properties"]["pressure_sensor_layout"]["minItems"] == 4
    case_required = set(contract["$defs"]["case"]["required"])
    assert {
        "release_origin",
        "release_direction_unit_vector",
        "ignition",
        "obstacles",
        "ambient",
    } <= case_required
    assert contract["properties"]["provenance"]["properties"]["authenticated_by_publisher"]["const"] is True
