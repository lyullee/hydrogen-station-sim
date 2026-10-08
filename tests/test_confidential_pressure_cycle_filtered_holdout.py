from __future__ import annotations

import hashlib
import json
from pathlib import Path

from h2station.confidential_pressure_cycle_filtered_holdout import causal_median_filter
from h2station.confidential_pressure_cycle_holdout import detect_pressure_cycles


ROOT = Path(__file__).resolve().parents[1]


def test_causal_median_filter_recovers_a_noisy_station_scale_cycle() -> None:
    samples = []
    for index in range(80):
        if index < 10:
            base = 85.0
        elif index <= 42:
            base = 85.0 - (index - 10) * 4.5 / 32.0
        elif index <= 54:
            base = 80.5 + (index - 42) * 4.5 / 12.0
        else:
            base = 85.0
        noise = (0.16, -0.14, 0.12, -0.11, 0.08, -0.07, 0.0)[index % 7]
        samples.append((index * 10.0, base + noise))
    filtered = causal_median_filter(samples, window_samples=7)
    cycles = detect_pressure_cycles(filtered)
    assert len(cycles) >= 1
    assert 4.0 <= cycles[0].pressure_drop_mpa <= 5.0


def test_causal_median_filter_requires_an_odd_physical_window() -> None:
    for invalid in (0, 1, 2, 4, 6):
        try:
            causal_median_filter([(0.0, 1.0), (1.0, 2.0)], window_samples=invalid)
        except ValueError:
            pass
        else:  # pragma: no cover - assertion branch
            raise AssertionError(f"window {invalid} should be rejected")


def test_filtered_revision_is_hash_locked_and_discloses_prior_failure() -> None:
    protocol = json.loads(
        (ROOT / "research/confidential_station_filtered_pressure_cycle_protocol_2026_10_08.json")
        .read_text(encoding="utf-8")
    )
    assert protocol["status"] == (
        "sequential_method_revision_frozen_before_filtered_cycle_outcome_access"
    )
    assert protocol["target"]["candidate_changed_after_first_result"] is False
    assert protocol["filter"]["window_samples"] == 7
    assert protocol["decision_boundary"]["independent_external_validation"] is False
    for path_key, hash_key in (
        ("evaluator", "evaluator_sha256"),
        ("runner", "runner_sha256"),
        ("base_detector", "base_detector_sha256"),
    ):
        path = ROOT / protocol["locked_implementation"][path_key]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == (
            protocol["locked_implementation"][hash_key]
        )
