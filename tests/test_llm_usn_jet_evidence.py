from __future__ import annotations

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_summary,
)
from h2station.api import _provider_evidence_basis


def test_usn_jet_dataset_is_grounded_as_post_access_component_diagnostic():
    manifest = build_evidence_manifest(
        {"time_s": 0.0},
        {},
        [],
        False,
        question="공개 점화제트 과압 실험 근거와 피해영향 범위를 알려줘",
    )
    evidence = manifest["response_evidence"][
        "public_usn_ignited_jet_dataset_diagnostic"
    ]
    assert evidence["source"]["dataset_doi"] == "10.18710/X044QK"
    assert evidence["component_consequence_candidate"] is True
    assert evidence["current_validation_status"] == "NOT_REPLAYED"
    boundary = evidence["publisher_calibration_boundary"]
    assert boundary["raw_pressure_unit"] == "V"
    assert boundary["campaign_voltage_to_pressure_transfer_published"] is False
    assert boundary["numeric_replay_blocked"] is True
    assert boundary["validation_gate_promoted"] is False
    assert evidence["hrs_dispenser_validation_supported"] is False
    assert evidence["station_vehicle_full_loop_supported"] is False
    assert evidence["runtime_parameter_application"] is False

    compact = prompt_evidence_summary(manifest)
    assert compact["public_usn_ignited_jet_dataset_diagnostic"][
        "current_validation_status"
    ] == "NOT_REPLAYED"
    assert compact["public_usn_ignited_jet_dataset_diagnostic"][
        "publisher_calibration_boundary"
    ]["numeric_replay_blocked"] is True
    decision = prompt_decision_evidence(manifest)["decision_support_evidence"]
    assert decision["public_usn_ignited_jet_dataset_diagnostic"][
        "station_vehicle_full_loop_supported"
    ] is False
    assert any(
        link.get("id") == "PUBLIC_USN_IGNITED_JET_DATASET"
        for link in compact["public_source_links"]
    )
    provider = _provider_evidence_basis(manifest)
    assert provider["public_usn_ignited_jet_dataset_diagnostic"][
        "current_validation_status"
    ] == "NOT_REPLAYED"
    assert provider["public_usn_ignited_jet_dataset_diagnostic"][
        "publisher_calibration_boundary"
    ]["raw_pressure_unit"] == "V"
    assert provider["public_usn_ignited_jet_dataset_diagnostic"][
        "station_vehicle_full_loop_supported"
    ] is False


def test_usn_jet_dataset_stays_out_of_unrelated_provider_turns():
    manifest = build_evidence_manifest(
        {"time_s": 0.0},
        {},
        [],
        False,
        question="현재 저장뱅크 압력과 온도 상태를 알려줘",
    )
    provider = _provider_evidence_basis(manifest)
    assert "public_usn_ignited_jet_dataset_diagnostic" not in provider
