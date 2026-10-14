import json
from pathlib import Path

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
)


ROOT = Path(__file__).resolve().parents[1]


def test_tudelft_context_artifact_is_explicitly_bounded():
    path = ROOT / "research/tudelft_metering_cabinet_sensor_context_2026_10_14.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "public_actual_hydrogen_detector_placement_context"
    assert record["experiment_scope"]["actual_hydrogen"] is True
    assert record["experiment_scope"]["experiment_count"] == 7
    assert record["experiment_scope"]["raw_time_series_available"] is False
    assert record["source"]["license_identified"] is False
    assert record["runtime_use"]["runtime_detector_routing"] is False
    assert record["runtime_use"]["runtime_threshold_calibration"] is False


def test_tudelft_context_is_routed_only_for_detector_questions():
    frame = {"time_s": 1.0, "header_pressure_mpa": 45.0}
    idle = build_evidence_manifest(frame, {}, [], False, question="현재 상태")
    idle_decision = prompt_decision_evidence(idle)
    assert "public_tudelft_detector_placement_context" not in idle_decision[
        "decision_support_evidence"
    ]

    detector = build_evidence_manifest(
        frame,
        {},
        [],
        False,
        selected_sensor="GD-0901",
        question="수소 검지기 위치와 환기 영향을 설명해줘",
    )
    decision = prompt_decision_evidence(detector)
    context = decision["decision_support_evidence"][
        "public_tudelft_detector_placement_context"
    ]
    assert context["experiment_scope"]["experiment_count"] == 7
    assert context["reported_findings"][
        "top_center_location_had_highest_response"
    ] is True
    assert context["runtime_detector_routing"] is False
    assert context["numeric_spatial_holdout_eligible"] is False

    header = prompt_evidence_header(detector)
    links = header["public_source_links"]
    assert any(
        item["id"] == "PUBLIC_TUDELFT_DETECTOR_PLACEMENT_CONTEXT"
        and "repository.tudelft.nl" in item["url"]
        for item in links
    )

