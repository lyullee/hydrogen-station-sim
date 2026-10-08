from __future__ import annotations

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def _manifest():
    return build_evidence_manifest(
        {
            "time_s": 1.0,
            "nozzle_flow_g_s": 0.0,
            "header_pressure_mpa": 44.0,
            "header_temperature_c": 25.0,
            "header_mass_kg": 0.2,
            "header_inflow_g_s": 0.0,
        },
        {"PT-0901": {"value": 44.0, "unit": "MPa", "quality": "GOOD"}},
        [],
        False,
        question="로컬 충전소 데이터가 충분한가?",
    )


def test_local_discovery_is_grounded_without_raw_provenance():
    manifest = _manifest()
    discovery = manifest["response_evidence"][
        "confidential_local_station_data_discovery"
    ]
    assert discovery["candidate_groups"][
        "confidential_station_measurement_bundle"
    ]["physical_rows"] == 59_272_300
    coverage = discovery["coverage_assessment"]
    assert coverage["local_station_data_is_sparse"] is False
    assert coverage["station_side_dynamic_evidence_is_substantial"] is True
    assert coverage["vehicle_side_full_loop_validation_ready"] is False
    assert "source_paths_published" not in discovery
    assert "source_filenames_published" not in discovery


def test_local_discovery_reaches_bounded_prompt_views():
    manifest = _manifest()
    summary = prompt_evidence_summary(manifest)[
        "confidential_local_station_data_discovery"
    ]
    assert summary["coverage_assessment"][
        "quantitative_consequence_validation_ready"
    ] is False
    decision = prompt_decision_evidence(manifest)["validation_boundaries"][
        "local_station_data_discovery"
    ]
    assert decision["station_data_is_sparse"] is False
    assert decision["vehicle_side_full_loop_validation_ready"] is False
    header = prompt_evidence_header(manifest)[
        "confidential_local_station_data_discovery"
    ]
    assert header["candidate_groups"][
        "derived_simulator_telemetry_exports"
    ]["independence"] == "not_independent_measured_data"
