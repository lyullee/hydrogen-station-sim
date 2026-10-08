import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/uci_early_hrs_supplementary_recheck_2026_10_09.json"


def test_uci_supplementary_recheck_is_privacy_bounded() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert all(value is False for value in record["privacy"].values())


def test_uci_supplementary_recheck_keeps_full_loop_closed() -> None:
    observed = json.loads(ARTIFACT.read_text(encoding="utf-8"))["observed_structure"]
    assert observed["embedded_chart_count"] == 4
    assert observed["monthly_chart_point_count"] == 30
    assert observed["synchronized_event_table_present"] is False
    assert observed["vehicle_or_receptacle_pressure_temperature_present"] is False
