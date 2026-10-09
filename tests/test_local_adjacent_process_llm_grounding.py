from __future__ import annotations

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


def _manifest():
    return build_evidence_manifest(
        {"time_s": 1.0, "header_pressure_mpa": 44.0},
        {},
        [],
        False,
        question="로컬 수소 데이터가 충분한지와 어떤 자료를 쓸 수 있는지 알려줘",
    )


def test_adjacent_process_inventory_is_bounded_and_not_full_loop_validation():
    manifest = _manifest()
    evidence = manifest["response_evidence"][
        "local_adjacent_hydrogen_process_context"
    ]
    process = evidence["high_pressure_process"]
    assert process["csv_event_log_count"] == 18
    assert process["csv_event_row_count"] == 2_411_774
    assert process["logical_key_count"] == 273
    assert evidence["runtime_parameter_application"] is False
    assert evidence["station_to_vehicle_full_loop_validation"] is False
    assert "source_paths_published" not in str(evidence)
    assert "source_filenames_published" not in str(evidence)


def test_full_docudata_scan_reaches_prompt_views_without_promoting_candidates():
    manifest = _manifest()
    summary = prompt_evidence_summary(manifest)["local_docudata_full_discovery"]
    assert summary["broad_scan"]["machine_readable_files_screened"] == 38_528
    assert summary["refined_header_screen"][
        "vehicle_pressure_temperature_flow_time_candidates"
    ] == 0
    assert summary["eligibility"][
        "eligible_synchronized_station_dispenser_vehicle_cohort"
    ] == 0

    decision = prompt_decision_evidence(manifest)["validation_boundaries"]
    adjacent = decision["local_adjacent_hydrogen_process_context"]
    assert adjacent["runtime_parameter_application"] is False
    assert adjacent["station_to_vehicle_full_loop_validation"] is False
    docudata = decision["local_docudata_full_discovery"]
    assert docudata["machine_readable_files_screened"] == 38_528
    assert docudata["eligible_synchronized_station_dispenser_vehicle_cohort"] == 0

    header = prompt_evidence_header(manifest)
    assert header["local_docudata_full_discovery"]["eligibility"][
        "runtime_parameter_application"
    ] is False
    assert "source_headers_published" not in str(header["local_adjacent_hydrogen_process_context"])
