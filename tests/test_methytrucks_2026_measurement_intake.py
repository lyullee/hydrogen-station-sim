from __future__ import annotations

import json
from pathlib import Path
import sys

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_methytrucks_2026_measurements import summarize_workbook  # noqa: E402


def test_synthetic_workbook_detects_timebase_and_flow_mass_closure(tmp_path: Path):
    path = tmp_path / "trace.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Zeit", "QT_D02 ValueY", "FWg35_Masse ValueY"])
    flow_values = [
        10.0 if 5 <= index <= 15 or 45 <= index <= 55 else 0.0
        for index in range(61)
    ]
    cumulative_mass = 0.0
    for index, flow_g_s in enumerate(flow_values):
        elapsed_s = index * 0.5
        if index:
            cumulative_mass += (
                flow_values[index - 1] + flow_values[index]
            ) / 2.0 * 0.5 / 1000.0
        sheet.append([elapsed_s + 100.0, flow_g_s, cumulative_mass])
    workbook.save(path)

    result = summarize_workbook(path)

    assert result["sample_count"] == 61
    assert result["sampling_interval_s"] == 0.5
    assert result["time_monotonic"] is True
    assert result["has_flow_channel"] is True
    assert result["has_mass_channel"] is True
    assert len(result["mass_closure_sessions"]) == 1
    assert result["mass_closure_sessions"][0]["descriptive_closure_screen_pass"] is True


def test_committed_public_intake_is_complete_and_claim_bounded():
    result = json.loads(
        (ROOT / "research/methytrucks_2026_public_measurement_intake.json").read_text(
            encoding="utf-8"
        )
    )

    assert result["status"] == "PASS"
    assert result["aggregate"]["record_count"] == 3
    assert result["aggregate"]["workbook_count"] == 15
    assert result["aggregate"]["sample_count"] == 58_440
    assert result["aggregate"]["sampling_intervals_s"] == [0.5]
    assert result["aggregate"]["workbooks_with_flow"] == 15
    assert result["aggregate"]["workbooks_with_mass"] == 6
    assert result["aggregate"]["mass_closure_screen_pass_count"] == 8
    assert result["eligibility"]["flow_mass_consistency_diagnostic_supported"] is True
    assert result["eligibility"]["prospective_holdout_eligible"] is False
    assert result["eligibility"]["full_loop_station_vehicle_validation_eligible"] is False
    assert result["mapping_boundary"]["publisher_channel_dictionary_present"] is False
    assert "does not establish prospective validation" in result["claim_boundary"]
