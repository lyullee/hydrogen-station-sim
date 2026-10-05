import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _record():
    return json.loads(
        (ROOT / "research/nrel_hd_protocol_experiment_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )


def test_nrel_report_preserves_real_experiment_but_not_raw_holdout_status():
    record = _record()
    assert record["decision"] == "REAL_HD_EXPERIMENT_PLOT_ONLY"
    assert record["raw_time_series"] is False
    assert record["full_loop_holdout_eligible"] is False
    assert record["gate_impact"] == "independent_full_loop_gate_remains_open"
    assert record["source"]["sha256"] == "32204900c67fccfebc868d7d78235db5f2d1a3b10371b3ffce78581c6e586ba6"
    assert record["source"]["byte_count"] == 5632458
    assert record["source"]["text_version_url"].endswith("text-version")


def test_nrel_reported_fill_values_are_traceable():
    observed = _record()["reported_experiment"]
    assert observed["mass_transfer_kg"] == 73.0
    assert observed["total_fill_time_s"] == 423.5
    assert observed["average_mass_flow_g_s"] == 172.3
    assert observed["peak_mass_flow_g_s"] == 483.33
    assert observed["starting_pressure_mpa"] == 5.5
    assert observed["ending_pressure_mpa"] == 74.6
    assert "mass flow" in observed["reported_plot_channels"]
    assert "vehicle tank pressure" in observed["reported_plot_channels"]
