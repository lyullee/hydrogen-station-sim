import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_operational_benchmark_recheck_preserves_raw_trace_boundary():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["result"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET"
    assert record["gate_impact"] == "full_loop_external_validation_remains_open"
    assert len(record["candidates"]) == 4
    assert all(
        item["decision"] != "FULL_LOOP_HOLDOUT" for item in record["candidates"]
    )
    required = set(record["eligibility_boundary"]["full_loop_required_channels"])
    assert required == {
        "common elapsed time or timestamp",
        "vehicle or receptacle pressure",
        "mass flow or transferred mass",
    }


def test_recheck_explicitly_contains_real_station_but_non_raw_sources():
    record = json.loads(
        (ROOT / "research/public_operational_benchmark_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    real_station = [
        item for item in record["candidates"]
        if item["id"] in {"calstate_la_multi_year_ijhe_2023", "uci_nfcrc_early_hrs_ijhe_2020"}
    ]
    assert len(real_station) == 2
    assert all("request" in item["use"].lower() for item in real_station)
