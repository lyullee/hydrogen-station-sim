from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_mc_temperature_observation_diagnostic import (  # noqa: E402
    Replay,
    TEMPERATURE_OBSERVATIONS,
    _thermal_observations,
)


def test_predefined_observation_operators_are_distinct_and_unweighted():
    replay = Replay(
        time_s=np.asarray([0.0, 1.0]),
        observed_temperature_c=np.asarray([20.0, 21.0]),
        gas_temperature_c=np.asarray([20.0, 40.0]),
        liner_temperature_c=np.asarray([20.0, 30.0]),
        shell_temperature_c=np.asarray([20.0, 24.0]),
    )

    observations = _thermal_observations(replay)

    assert set(observations) == set(TEMPERATURE_OBSERVATIONS)
    assert observations["liner_shell_mean"].tolist() == [20.0, 27.0]
    assert observations["gas_temperature"].tolist() == [20.0, 40.0]


def test_committed_semantic_diagnostic_is_explicitly_non_promotional():
    report = json.loads(
        (ROOT / "research" / "mc_temperature_observation_diagnostic_2026_10_07.json")
        .read_text(encoding="utf-8")
    )

    assert report["evidence_role"] == "post_outcome_semantic_diagnostic_only"
    assert report["parameter_fitting"] is False
    assert report["runtime_thermal_observation_changed"] is False
    assert report["observation_mapping_selection_prohibited"] is True
    assert report["promotion_to_validation_prohibited"] is True
    assert report["raw_experimental_rows_persisted"] is False
    assert len(report["cases"]) == 8
    assert set(report["aggregate"]) == set(TEMPERATURE_OBSERVATIONS)
