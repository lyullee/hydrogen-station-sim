from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_elvhys_detector_holdout_v2 import (  # noqa: E402
    baseline_corrected_maximum,
    evaluate_trace,
)


PROTOCOL = ROOT / "research/elvhys_detector_holdout_protocol_v2_2026_10_07.json"


def test_v2_freeze_uses_a_disjoint_uninspected_holdout_and_pins_implementation():
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert record["status"] == "frozen_before_v2_selected_outcome_download"
    assert record["selection"]["v2_selected_outcomes_accessed_before_freeze"] is False
    selected = {row["test_id"] for row in record["selected_cases"]}
    excluded = set(record["selection"]["all_excluded_previously_accessed_tests"])
    assert len(selected) == 15
    assert not selected.intersection(excluded)
    assert record["missing_value_policy"]["nonfinite_measurement_values"] == (
        "retain as missing and never impute"
    )
    runner = ROOT / record["frozen_implementation"]["runner"]
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == record[
        "frozen_implementation"
    ]["runner_sha256"]


def test_missing_concentration_values_are_not_imputed_or_fatal():
    time = np.arange(0.0, 8.1, 0.1)
    first = np.where(time >= 3.0, 2.5, 0.2)
    second = np.where(time >= 3.0, 1.5, -0.1)
    first[5] = np.nan
    second[6] = np.nan
    returned_time, maximum, sensors, missing = baseline_corrected_maximum(
        {"Time": time, "H2A": first, "H2B": second},
        release_onset_s=3.0,
        baseline_guard_s=0.5,
        minimum_baseline_samples=20,
    )
    assert np.array_equal(returned_time, time)
    assert sensors == ["H2A", "H2B"]
    assert missing["dropped_sensor_count"] == 0
    assert missing["invalid_time_sample_count"] == 0
    assert np.isfinite(maximum).all()


def test_all_missing_timestamp_is_skipped_without_imputation():
    time = np.arange(0.0, 8.1, 0.1)
    first = np.where(time >= 3.0, 2.5, 0.0)
    second = first.copy()
    first[40] = np.nan
    second[40] = np.nan
    _, maximum, _, missing = baseline_corrected_maximum(
        {"Time": time, "H2A": first, "H2B": second},
        release_onset_s=3.0,
        baseline_guard_s=0.5,
        minimum_baseline_samples=20,
    )
    assert missing["invalid_time_sample_count"] == 1
    valid = np.isfinite(maximum)
    replay = evaluate_trace(
        time[valid], maximum[valid], release_onset_s=3.0,
        thresholds=[
            {"rule_id": "HZ-141", "threshold_volpct_h2": 0.4, "persistence_s": 1.0},
            {"rule_id": "HZ-142", "threshold_volpct_h2": 1.0, "persistence_s": 0.5},
            {"rule_id": "HZ-143", "threshold_volpct_h2": 2.0, "persistence_s": 0.5},
        ],
    )
    assert replay["pre_release_events"] == []
    assert all(not row["missed_expected_trigger"] for row in replay["checks"])
