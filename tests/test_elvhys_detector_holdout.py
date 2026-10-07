from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_elvhys_detector_holdout import (  # noqa: E402
    baseline_corrected_maximum,
    evaluate_trace,
    first_sustained_time,
)


PROTOCOL = ROOT / "research/elvhys_detector_holdout_protocol_2026_10_07.json"


def test_frozen_protocol_excludes_previously_accessed_outcomes_and_pins_runner():
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert record["status"] == "frozen_before_selected_outcome_download"
    assert record["selection"]["outcomes_accessed_before_freeze"] is False
    selected = {row["test_id"] for row in record["selected_cases"]}
    assert len(selected) == 12
    assert not selected.intersection({3, 24, 29, 30, 31, 45})
    runner = ROOT / record["frozen_implementation"]["runner"]
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == record[
        "frozen_implementation"
    ]["runner_sha256"]


def test_sustained_crossing_and_baseline_correction_are_deterministic():
    time = np.arange(0.0, 6.1, 0.1)
    values = np.where(time >= 3.0, 1.2, 0.0)
    assert first_sustained_time(
        time, values, threshold=1.0, persistence_s=0.5,
    ) == 3.5
    concentration = {
        "Time": time,
        "H2A": np.where(time >= 3.0, 2.5, 0.2),
        "H2B": np.where(time >= 3.0, 1.0, -0.1),
    }
    returned_time, maximum, sensors = baseline_corrected_maximum(
        concentration,
        release_onset_s=3.0,
        baseline_guard_s=0.5,
        minimum_baseline_samples=20,
    )
    assert sensors == ["H2A", "H2B"]
    assert np.array_equal(returned_time, time)
    assert maximum[0] == 0.0
    assert maximum[-1] == 2.3


def test_measured_trace_routes_all_expected_gas_rules_without_false_event():
    time = np.arange(0.0, 8.1, 0.1)
    concentration = np.where(time >= 3.0, 2.5, 0.0)
    thresholds = [
        {"rule_id": "HZ-141", "threshold_volpct_h2": 0.4, "persistence_s": 1.0},
        {"rule_id": "HZ-142", "threshold_volpct_h2": 1.0, "persistence_s": 0.5},
        {"rule_id": "HZ-143", "threshold_volpct_h2": 2.0, "persistence_s": 0.5},
    ]
    replay = evaluate_trace(
        time, concentration, release_onset_s=3.0, thresholds=thresholds,
    )
    assert replay["pre_release_events"] == []
    assert all(not row["missed_expected_trigger"] for row in replay["checks"])
    assert all(not row["unexpected_trigger"] for row in replay["checks"])
    assert max(row["timing_error_s"] for row in replay["checks"]) <= 1.0e-9
