from __future__ import annotations

import json
from pathlib import Path

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
    prompt_evidence_summary,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/carb_2024_hrs_inuse_field_benchmark_2026_10_08.json"


def _artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_carb_field_benchmark_preserves_report_counts_and_boundaries():
    record = _artifact()
    assert record["artifact_type"] == "public_real_station_field_benchmark"
    assert record["source"]["local_source_hash_verified"] is True
    assert record["population"]["stations_tested"] == 22
    assert record["population"]["stations_passing_all_hgv_4_3_tests"] == 0
    assert record["population"]["in_use_protocol_counts"] == {
        "mc_formula_based": 16,
        "table_based": 6,
    }
    assert record["category_station_pass_rates"] == {
        "general_fault": 0.455,
        "protocol_fault": 0.409,
        "communications": 0.5,
        "fueling_performance": 0.182,
    }
    for section in record["tables"].values():
        for counts in section["results"].values():
            assert len(counts) == 3
            assert sum(counts) in {6, 16, 22}

    eligibility = record["eligibility"]
    assert eligibility["field_relevance_benchmark"] is True
    assert eligibility["functional_gap_audit"] is True
    assert eligibility["dynamic_model_parameter_calibration"] is False
    assert eligibility["full_loop_external_holdout"] is False
    assert eligibility["vehicle_trace_validation"] is False
    assert "no synchronized" in record["claim_boundary"].lower()


def test_carb_gap_audit_keeps_observed_communication_failures_actionable():
    record = _artifact()
    communications = record["tables"]["communications"]["results"]
    assert communications["abort_signal"] == [19, 2, 1]
    assert communications["data_loss_and_resumed_fueling"] == [15, 4, 3]
    assert communications["invalid_crc"] == [13, 8, 1]
    assert communications["invalid_defined_data_value"] == [13, 8, 1]
    coverage = record["digital_twin_functional_coverage"]
    represented = " ".join(coverage["represented"])
    missing = " ".join(coverage["missing"])
    assert "abort" in represented.lower()
    assert "crc" in represented.lower()
    assert "communication loss" in represented.lower()
    assert "resumed-fueling" in missing.lower()


def test_carb_field_benchmark_is_grounded_without_claiming_trace_validation():
    manifest = build_evidence_manifest(
        {"time_s": 10.0}, {}, [], False,
        question="충전 통신 CRC 오류가 나면 어떻게 대응해야 해?",
    )
    field = manifest["response_evidence"][
        "public_carb_hrs_inuse_field_benchmark"
    ]
    assert field["population"]["stations_tested"] == 22
    assert field["communication_results"]["invalid_crc"] == [13, 8, 1]
    assert field["full_loop_external_holdout_eligible"] is False
    assert field["dynamic_model_parameter_calibration_eligible"] is False

    summary = prompt_evidence_summary(manifest)[
        "public_carb_hrs_inuse_field_benchmark"
    ]
    assert summary["category_station_pass_rates"]["communications"] == 0.5
    header = prompt_evidence_header(manifest)
    assert header["public_carb_hrs_inuse_field_benchmark"][
        "communication_results"
    ]["invalid_defined_data_value"] == [13, 8, 1]
    assert any(
        item["id"] == "PUBLIC_CARB_2024_HRS_INUSE"
        for item in header["public_source_links"]
    )

    decision = prompt_decision_evidence(manifest)["decision_support_evidence"]
    carb = decision["carb_22_station_field_benchmark"]
    assert carb["stations"] == 22
    assert carb["communication_fail_counts"]["invalid_crc"] == 8
    assert carb["dynamic_model_validation"] is False


def test_carb_detail_stays_out_of_unrelated_compact_decision_prompt():
    manifest = build_evidence_manifest(
        {"time_s": 10.0}, {}, [], False,
        question="현재 저장뱅크 재고만 알려줘",
    )
    decision = prompt_decision_evidence(manifest)["decision_support_evidence"]
    assert "carb_22_station_field_benchmark" not in decision
