from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_private_station_pressure_lifecycle import audit  # noqa: E402


def test_private_audit_is_aggregate_and_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "owner-export.csv"
    source.write_text(
        "LocalTimeCol,PI_2005,HP_BankLifeCycle_CNT,FQI_0001A_RATE\n"
        "2025-01-01 12:00:00 AM,20,1,0\n"
        "2025-01-01 12:00:01 AM,21,2,1\n",
        encoding="utf-8",
    )

    report = audit(tmp_path)

    assert report["artifact_type"] == "confidential_private_station_pressure_lifecycle_audit"
    assert report["inventory"]["total_row_count"] == 2
    assert report["eligibility"]["station_side_pressure_replay_candidate"] is True
    assert report["eligibility"]["vehicle_or_receptacle_channels_present"] is False
    assert report["eligibility"]["full_loop_holdout_eligible"] is False
    serialized = json.dumps(report, ensure_ascii=False)
    assert "owner-export.csv" not in serialized
    assert str(tmp_path) not in serialized
    assert "PI_2005" not in serialized
    assert "2025-01-01" not in serialized


def test_private_audit_detects_counter_decrease_without_promoting_validation(tmp_path: Path) -> None:
    source = tmp_path / "owner-export.csv"
    source.write_text(
        "LocalTimeCol,HP_BankLifeCycle_CNT,PI_3002_XQ\n"
        "2025-01-01 12:00:00 AM,2,50\n"
        "2025-01-01 12:00:01 AM,1,51\n",
        encoding="utf-8",
    )

    report = audit(tmp_path)

    screen = report["lifecycle_counter_screen"]
    assert screen["counter_decrease_observations"] == 1
    assert screen["monotonicity_claim_supported"] is False
    assert report["eligibility"]["parameter_fit_authorized"] is False
