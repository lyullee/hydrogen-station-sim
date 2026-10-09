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
