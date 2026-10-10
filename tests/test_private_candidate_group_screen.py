from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_private_candidate_group_screen import screen


def test_private_candidate_group_screen_is_aggregate_only(tmp_path: Path) -> None:
    private_root = tmp_path / "private"
    private_root.mkdir()
    trace = private_root / "trace.csv"
    trace.write_text(
        "time,station_pressure,temperature,flow,vehicle\n"
        "0,1,20,0,vehicle-1\n"
        "1,2,21,1,vehicle-1\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps([{"group_id": "opaque", "path": str(trace)}]),
        encoding="utf-8",
    )

    result = screen(manifest)

    assert result["artifact_type"] == "privacy_bounded_private_candidate_group_screen"
    assert result["privacy_boundary"]["raw_rows_persisted"] is False
    assert result["privacy_boundary"]["source_paths_persisted"] is False
    assert result["manifest_scope"]["candidate_records_screened"] == 1
    assert result["aggregate"]["roots_with_all_required_contract_groups"] == 0
    assert result["aggregate"]["roots_with_vehicle_semantic_group"] == 1
    assert result["admission"]["full_loop_external_holdout_eligible"] is False
    serialized = json.dumps(result, ensure_ascii=False)
    assert "trace.csv" not in serialized
    assert "opaque" not in serialized
