from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_face_validity_screen_is_hash_linked_and_claim_bounded():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_face_validity_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    source = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["source_manifest"]["candidate_count"] == len(source["candidates"]) == 17
    assert record["external_validation_status"] == "NOT_ESTABLISHED"
    assert record["full_loop_holdout_eligible"] is False
    assert record["goal_completion_permitted"] is False
    assert record["source_metrics"][0]["reported_cases"][1]["reported_peak_mass_flow_g_s"] == 36.0
    assert next(
        item for item in record["derived_checks"]
        if item["id"] == "heavy_duty_peak_flow_is_outside_default_dispenser_envelope"
    )["status"] == "NOT_COVERED"


def test_face_validity_screen_does_not_silently_expand_the_default_scope():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_face_validity_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    model = record["locked_model_reference"]
    assert model["default_vehicle_target_pressure_mpa"] == 70.0
    assert model["dispenser_maximum_mass_flow_g_s"] == 60.0
    assert any(
        item["status"] == "PASS"
        and "Endpoint compatibility only" in item["claim_limit"]
        for item in record["derived_checks"]
    )
    assert any(
        "heavy-duty" in limitation.lower() and "separately" in limitation
        for limitation in record["limitations"]
    )
