import json
from pathlib import Path

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
)


ROOT = Path(__file__).resolve().parents[1]


def test_zhang_context_records_actual_lh2_article_boundary():
    record = json.loads(
        (
            ROOT
            / "research/zhang_large_volume_lh2_release_context_2026_10_14.json"
        ).read_text(encoding="utf-8")
    )
    assert record["artifact_type"] == "public_actual_lh2_release_spatial_context"
    assert record["source"]["doi"] == "10.3390/app14093645"
    assert record["experiment_scope"]["actual_liquid_hydrogen"] is True
    assert record["experiment_scope"]["raw_time_series_committed"] is False
    assert record["runtime_use"]["runtime_safety_distance_calibration"] is False


def test_zhang_context_is_selective_and_not_a_validation_gate():
    frame = {"time_s": 1.0, "header_pressure_mpa": 45.0}
    idle = build_evidence_manifest(frame, {}, [], False, question="현재 상태")
    assert "public_zhang_lh2_release_context" not in prompt_decision_evidence(
        idle
    )["decision_support_evidence"]

    question = build_evidence_manifest(
        frame,
        {},
        [],
        False,
        selected_sensor="GD-0901",
        question="액체수소 극저온 방출의 피해영향과 위험거리를 설명해줘",
    )
    support = prompt_decision_evidence(question)["decision_support_evidence"][
        "public_zhang_lh2_release_context"
    ]
    assert support["experiment_scope"]["sensor_heights_m"] == [2, 8, 12, 20]
    assert support["reported_findings"]["near_source_high_concentration_cloud"] is True
    assert support["runtime_safety_distance_calibration"] is False
    assert support["validation_gate_changed"] is False

    header = prompt_evidence_header(question)
    assert header["public_zhang_lh2_release_context"]["source"]["doi"] == (
        "10.3390/app14093645"
    )
    assert any(
        item["id"] == "PUBLIC_ZHANG_LH2_RELEASE_CONTEXT"
        and "10.3390/app14093645" in item["url"]
        for item in header["public_source_links"]
    )
