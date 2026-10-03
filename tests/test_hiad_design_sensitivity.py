from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_hiad_design_sensitivity import build_report, simulate_power  # noqa: E402


def test_power_simulation_is_seeded_and_increases_for_large_effect():
    first = simulate_power(
        event_count=24, simulations=2_000, effects=(0.0, 0.5, 1.0), seed=2601
    )
    second = simulate_power(
        event_count=24, simulations=2_000, effects=(0.0, 0.5, 1.0), seed=2601
    )
    assert first == second
    assert first[0]["estimated_power"] < first[1]["estimated_power"]
    assert first[1]["estimated_power"] < first[2]["estimated_power"]
    assert 0.02 < first[0]["estimated_power"] < 0.08
    assert first[2]["estimated_power"] > 0.95


def test_zero_event_bound_remains_material_for_24_events():
    report = build_report(event_count=24, simulations=1_000, seed=2601)
    bound = report["zero_unsafe_event_exact_two_sided_95_percent_upper_bound"]
    assert 0.13 < bound < 0.16
    assert report["event_count"] == 24
    assert report["analysis_timing"].startswith("before holdout")
