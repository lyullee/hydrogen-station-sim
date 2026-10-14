import json
from pathlib import Path

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
)


ROOT = Path(__file__).resolve().parents[1]


def test_bam_context_records_article_only_boundary():
    record = json.loads(
        (
            ROOT
            / "research/bam_hrs_anomaly_detection_context_2026_10_14.json"
        ).read_text(encoding="utf-8")
    )
    assert record["artifact_type"] == "public_hrs_anomaly_detection_context"
    assert record["source"]["doi"] == "10.3390/app16157856"
    assert record["experiment_scope"]["field_hydrogen_refueling_station"] is True
    assert record["experiment_scope"]["raw_time_series_committed"] is False
    assert record["runtime_use"]["runtime_model_parameter_application"] is False
    assert record["runtime_use"]["validation_gate_changed"] is False


def test_bam_context_is_selective_and_cannot_be_runtime_validation():
    frame = {"time_s": 1.0, "header_pressure_mpa": 45.0}
    idle = build_evidence_manifest(frame, {}, [], False, question="현재 상태")
    assert "public_bam_hrs_anomaly_detection_context" not in prompt_decision_evidence(
        idle
    )["decision_support_evidence"]

    question = build_evidence_manifest(
        frame,
        {},
        [],
        False,
        selected_sensor="PT-0901",
        question="정상운전 센서 품질과 이상 감지 방법을 설명해줘",
    )
    support = prompt_decision_evidence(question)["decision_support_evidence"][
        "public_bam_hrs_anomaly_detection_context"
    ]
    assert support["experiment_scope"]["sensor_count"] == 8
    assert support["reported_methods"]["point_anomaly_model"] == "LSTM-VAE"
    assert support["runtime_threshold_calibration"] is False
    assert support["independent_external_holdout_supported"] is False

    header = prompt_evidence_header(question)
    assert header["public_bam_hrs_anomaly_detection_context"]["source"]["doi"] == (
        "10.3390/app16157856"
    )
    assert any(
        item["id"] == "PUBLIC_BAM_HRS_ANOMALY_CONTEXT"
        and "10.3390/app16157856" in item["url"]
        for item in header["public_source_links"]
    )

