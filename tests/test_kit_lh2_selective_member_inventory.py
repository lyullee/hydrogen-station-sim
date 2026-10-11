import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/kit_lh2_selective_member_inventory_2026_10_11.json"


def test_kit_selective_inventory_preserves_stage1_boundary():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert data["status"] == "PARTIAL_ARCHIVE_MEMBER_INVENTORY"
    assert data["source"]["doi"] == "10.35097/1483"
    assert data["acquisition"]["full_publisher_checksum_verified"] is False
    assert data["stage1_boundary"]["numeric_signal_values_opened"] is False
    assert data["stage1_boundary"]["xlsx_cells_read"] is False
    assert data["stage1_boundary"]["stage2_eligible"] is False
    members = data["members"]
    assert len(members) == 4
    assert {m["name"].split("/")[-1] for m in members} == {
        "ignited_trial_15_28-10-2019alldata.xlsx",
        "ignited_trial_16_28-10-2019alldata.xlsx",
        "ignited_trial_17_28-10-2019alldata.xlsx",
        "ignited_trial_19_28-10-2019alldata.xlsx",
    }
    expected_sheets = {
        "Flexlogger",
        "Radiometers",
        "Blastlogger",
        "BlastloggerClip",
        "Xensor",
        "Flowmeter",
        "LocalWeather",
    }
    assert all(set(m["sheet_names"]) == expected_sheets for m in members)
