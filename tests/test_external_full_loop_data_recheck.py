import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_recheck_preserves_full_loop_gate_boundary():
    record = json.loads(
        (ROOT / "research/external_full_loop_data_recheck_2026_10_11.json")
        .read_text(encoding="utf-8")
    )

    assert record["status"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET_IDENTIFIED"
    assert record["outcome"]["new_eligible_public_raw_set"] is False
    assert record["outcome"]["full_loop_gate_status_unchanged"] == "FAIL"
    candidates = {item["id"]: item for item in record["candidates"]}
    assert {
        "fch2rail_2025_dispenser_measurement",
        "zbt_2026_hrs_sampling_experiment",
        "nrel_h2iq_2024_hd_fast_flow_summary",
    } <= candidates.keys()
    assert {
        "kit_preslhy_e31_part_a_open_data",
        "kit_preslhy_e31_part_b_open_data",
        "kit_preslhy_e51_ignited_open_data",
    } <= candidates.keys()
    assert {
        item["decision"] for item in record["candidates"]
    } <= {
        "REQUEST_RAW_TRACE",
        "REPORT_SUMMARY_ONLY",
        "COMPONENT_ONLY_NOT_FULL_LOOP",
    }
    for candidate in record["candidates"]:
        observed = candidate["observed"]
        assert observed.get(
            "machine_readable_common_timebase_public",
            observed.get("common_timebase_station_to_vehicle_public"),
        ) is False
