import json
from pathlib import Path

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_summary,
)


ROOT = Path(__file__).resolve().parents[1]


def test_equipment_coupling_diagnostic_is_privacy_bounded_and_non_promoting():
    record = json.loads(
        (
            ROOT
            / "research/confidential_station_equipment_coupling_diagnostic_2026_10_10.json"
        ).read_text(encoding="utf-8")
    )
    assert record["artifact_type"] == "confidential_station_equipment_coupling_diagnostic"
    assert record["source_identifiers_published"] is False
    assert record["raw_rows_persisted"] is False
    assert record["absolute_timestamps_published"] is False
    assert record["calendar_dates_published"] is False
    assert record["tag_names_published"] is False
    assert record["source_paths_published"] is False
    assert record["diagnostic_interpretation"]["not_a_calibration"] is True
    assert record["runtime_decision"]["default_model_parameters_changed"] is False
    assert record["eligibility"]["station_component_calibration_supported"] is False
    assert record["eligibility"]["full_station_vehicle_validation"] is False
    assert len(record["regimes"]) == 3


def test_coupling_diagnostic_is_available_to_grounding_but_keeps_runtime_off():
    manifest = build_evidence_manifest({"time_s": 0.0}, {}, [], False)
    response = manifest["response_evidence"][
        "confidential_station_equipment_coupling_diagnostic"
    ]
    assert response["runtime_decision"]["default_model_parameters_changed"] is False
    assert response["eligibility"]["station_component_calibration_supported"] is False
    summary = prompt_evidence_summary(manifest)
    assert summary["confidential_station_equipment_coupling_diagnostic"][
        "observation"
    ]["rows"] == 85543
    decision = prompt_decision_evidence(manifest)
    assert "station_equipment_coupling_diagnostic" not in decision["validation_boundaries"]
