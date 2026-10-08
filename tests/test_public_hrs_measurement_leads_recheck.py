"""Regression checks for public HRS measurement-lead boundaries."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/public_hrs_measurement_leads_recheck_2026_10_09.json"


def test_public_hrs_leads_are_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert all(value is False for value in record["privacy"].values())


def test_reported_measurements_are_not_mistaken_for_raw_holdouts() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    leads = {lead["id"]: lead for lead in record["leads"]}
    korean = leads["an_2024_sustainability_hrs_safety_model"]
    assert korean["reported_scope"]["sample_count"] == 885
    assert korean["reported_scope"]["sampling_interval"] == "1 s"
    assert korean["raw_trace_public"] is False
    assert "independent full-loop holdout" in korean["ineligible_use"]

    hungarian = leads["hasulyo_2026_hungarian_hrs_digital_twin"]
    assert hungarian["raw_trace_public"] is False
    assert "legal restrictions" in hungarian["data_availability_boundary"]


def test_metrology_and_aggregate_sources_keep_their_boundaries() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    leads = {lead["id"]: lead for lead in record["leads"]}
    nist = leads["nist_transient_flow_facility"]
    assert nist["reported_scope"]["reported_time_resolution"] == "100 ms or less"
    assert nist["raw_trace_public"] is False
    nlr = leads["nlr_hydrogen_station_composite_data_products"]
    assert nlr["reported_scope"]["machine_readable_synchronized_trace_public"] is False
    assert record["gate_impact"]["goal_completion_permitted"] is False


def test_field_and_real_fueling_sources_are_bounded_without_raw_traces() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    leads = {lead["id"]: lead for lead in record["leads"]}
    bam = leads["kim_2026_bam_hrs_anomaly_platform"]
    assert bam["reported_scope"]["vehicle_refueling_test_and_plc_integration_reported"] is True
    assert bam["reported_scope"]["actual_abnormal_events_collected"] is False
    assert bam["raw_trace_public"] is False
    assert "actual accident-label validation" in bam["ineligible_use"]

    dtu = leads["dtu_hydrogen_fuelling_library_h2logic_test"]
    assert dtu["reported_scope"]["real_fueling_test"] is True
    assert dtu["reported_scope"]["raw_machine_readable_trace_public"] is False
    assert "independent full-loop holdout" in dtu["ineligible_use"]
