import json
from pathlib import Path

from scripts.audit_h2safe_hvac_input_readiness import audit


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data/public_validation/raw/h2safe_2026/HVAC_information.docx"
ARTIFACT = ROOT / "research/h2safe_hvac_input_readiness_2026_10_12.json"


def test_h2safe_hvac_audit_parses_all_public_release_and_hvac_records():
    result = audit(METADATA)
    parsed = result["parsed_metadata"]
    assert len(parsed["release_tests"]["lab_1"]) == 1
    assert len(parsed["release_tests"]["lab_2"]) == 4
    assert parsed["lab_1_vent_count"] == 10
    assert parsed["lab_2_duct_count"] == 8
    assert parsed["lab_2_recirculation_fan_count"] == 2
    assert parsed["coordinates"]["declared_common_sensor_reference_frame"] is True


def test_h2safe_hvac_audit_fails_closed_without_common_frame_vectors():
    result = audit(METADATA)
    decision = result["decision"]
    assert decision["status"] == "NOT_READY_FOR_PREACCESS_SPATIAL_VALIDATION"
    assert decision["runtime_application"] is False
    assert set(decision["missing_inputs"]) == {
        "release_direction_vector",
        "ventilation_velocity_vectors",
        "obstruction_geometry",
        "release_to_trace_time_crosswalk",
    }


def test_h2safe_hvac_committed_artifact_matches_current_parser():
    expected = audit(METADATA)
    committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert committed["source"]["metadata_sha256"] == expected["source"]["metadata_sha256"]
    assert committed["parsed_metadata"] == expected["parsed_metadata"]
    assert committed["required_common_frame_inputs"] == expected["required_common_frame_inputs"]
    assert committed["decision"] == expected["decision"]
