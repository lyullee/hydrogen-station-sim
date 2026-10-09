from __future__ import annotations

import json
from pathlib import Path

from h2station.llm_grounding import build_evidence_manifest, prompt_decision_evidence

ROOT = Path(__file__).resolve().parents[1]


def test_preslhy_e35_public_file_audit_records_raw_access_without_full_loop_claim() -> None:
    path = ROOT / "research/preslhy_e35_public_file_access_2026_10_09.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["status"] == "PUBLIC_RAW_COMPONENT_CONSEQUENCE_FILE_ACCESSED"
    assert record["source"]["doi"] == "10.35097/1481"
    assert record["source"]["license"] == "CC BY-SA 4.0"
    assert record["file"]["raw_file_committed"] is False
    assert record["file"]["numerical_rows_persisted"] is False
    assert record["eligibility"]["public_raw_component_consequence_data"] is True
    assert record["eligibility"]["release_source_and_detector_diagnostic"] is True
    assert record["eligibility"]["full_loop_station_vehicle_validation_eligible"] is False
    assert {sheet["name"] for sheet in record["sheets"]} == {
        "Flexlogger", "Draeger", "Xensor", "LocalWeather", "Flowmeter"
    }
    assert record["observed_channels"]["hydrogen_detector_percent_channels"] == 60
    assert record["observed_channels"]["hydrogen_detector_ppm_channels"] == 30


def test_public_file_boundary_is_available_to_llm_without_full_loop_promotion() -> None:
    manifest = build_evidence_manifest(
        {"time_s": 1.0, "header_pressure_mpa": 20.0},
        {},
        [],
        False,
        question="공개 수소 방출 실험 데이터의 활용 범위를 알려줘",
    )
    evidence = manifest["response_evidence"]["public_preslhy_e35_file_access"]
    assert evidence["source"]["doi"] == "10.35097/1481"
    assert evidence["file"]["raw_file_committed"] is False
    assert evidence["eligibility"]["public_raw_component_consequence_data"] is True
    assert evidence["eligibility"]["full_loop_station_vehicle_validation_eligible"] is False

    compact = prompt_decision_evidence(manifest)["decision_support_evidence"]
    compact_evidence = compact["public_preslhy_e35_file_access"]
    assert compact_evidence["source_doi"] == "10.35097/1481"
    assert compact_evidence["full_loop_station_vehicle_validation_eligible"] is False
