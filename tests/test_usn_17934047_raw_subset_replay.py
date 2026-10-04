import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/usn_17934047_raw_subset_replay_2026_10_05.json"


def test_usn_raw_subset_replay_is_hash_locked_and_synchronized():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "completed_raw_channel_timebase_replay"
    assert result["source"]["doi"] == "10.23642/USN.17934047"
    assert result["source"]["license"] == "CC BY 4.0"
    integrity = result["replay_integrity"]
    assert integrity["file_count"] == 3
    assert integrity["all_files_present"] is True
    assert integrity["all_file_identities_match"] is True
    assert integrity["all_channel_replays_valid"] is True
    assert integrity["model_comparison_performed"] is False


def test_usn_raw_subset_replay_preserves_component_only_boundary():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["eligibility"]["consequence_component_evidence"] is True
    assert result["eligibility"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert result["eligibility"]["saga_effectiveness_eligible"] is False
    assert all(
        item["channel_replay"]["sigma_shape"] == [999999, 7]
        and item["channel_replay"]["gen3i_shape"][1] == 3
        for item in result["files"]
    )
