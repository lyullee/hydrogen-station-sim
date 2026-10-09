from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_data_coverage_summary import build_summary


ROOT = Path(__file__).resolve().parents[1]


def test_data_coverage_summary_preserves_claim_boundary() -> None:
    summary = build_summary(ROOT)

    assert summary["privacy"]["raw_rows_persisted"] is False
    assert summary["decision"]["data_volume_is_primary_blocker"] is False
    assert summary["decision"]["continue_component_validation"] is True
    assert summary["decision"]["full_loop_gate_remains_open"] is True
    assert summary["minimum_next_input"]["event_count"] == 3

    station = next(
        item for item in summary["validated_or_actionable_now"]
        if item["id"] == "owner_station_side_dynamics"
    )
    assert station["coverage"]["deduplicated_rows"] == 56854143
    assert station["coverage"]["ordered_high_bank_pressure_cycles"] == 16770

    station_tank = next(
        item for item in summary["validated_or_actionable_now"]
        if item["id"] == "public_station_tank_boundary"
    )
    assert station_tank["coverage"]["sample_count"] == 351
    assert station_tank["coverage"]["tank_count"] == 7
    assert station_tank["coverage"]["partial_station_to_tank_boundary_eligible"] is True
    assert station_tank["coverage"]["full_loop_holdout_eligible"] is False

    accidents = next(
        item for item in summary["validated_or_actionable_now"]
        if item["id"] == "public_accident_precedents"
    )
    assert accidents["coverage"]["mapped_response_family_count"] == 8
    assert accidents["coverage"]["unmatched_response_family_count"] == 0

    metrology = next(
        item for item in summary["validated_or_actionable_now"]
        if item["id"] == "public_field_metrology"
    )
    assert metrology["coverage"]["field_draft_count"] == 7
    assert metrology["coverage"]["maximum_method_agreement_percent"] == 1.53
    assert metrology["not_allowed"] == "원시 station-to-vehicle holdout, 제어기·ESD·사고영향 검증"

    dispersion = next(
        item for item in summary["validated_or_actionable_now"]
        if item["id"] == "public_actual_h2_spatial_dispersion"
    )
    assert dispersion["coverage"]["archive_count"] == 22
    assert dispersion["coverage"]["sensor_count_per_archive"] == 29
    assert dispersion["coverage"]["sensor_coordinate_count"] == 29
    assert dispersion["coverage"]["machine_readable_sensor_coordinates_public"] is True
    assert dispersion["coverage"]["spatial_holdout_ready"] is False

    tank_boundary = next(
        item for item in summary["validated_or_actionable_now"]
        if item["id"] == "public_hytf_tank_boundary"
    )
    assert tank_boundary["coverage"]["sample_count"] == 2536
    assert tank_boundary["coverage"]["tank_thermocouple_count"] == 14
    assert "full-loop" in tank_boundary["not_allowed"]

    export = summary["privacy_safe_export_contract"]
    assert export["custodian_keeps_raw_data"] is True
    assert export["minimum_event_bundle"] == 3
    assert export["validator_status"] == "implemented_and_tested"
    assert export["guide"].endswith("PRIVACY_SAFE_FULL_LOOP_INTAKE_2026_10_10.md")
    assert "site or company identity" in export["must_not_include"]
