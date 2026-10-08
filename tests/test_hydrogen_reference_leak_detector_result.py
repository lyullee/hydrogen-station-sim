import json
from pathlib import Path

import numpy as np
import pytest

from scripts.evaluate_hydrogen_reference_leak_detectors import pairwise_order_concordance


ROOT = Path(__file__).resolve().parents[1]


def test_pairwise_order_concordance_counts_cross_level_pairs_and_ties() -> None:
    references = np.asarray([1.0, 1.0, 2.0, 2.0])
    responses = np.asarray([1.0, 2.0, 2.0, 3.0])
    assert pairwise_order_concordance(references, responses) == pytest.approx(0.875)


def test_reference_leak_detector_result_passes_only_bounded_ordering_claim() -> None:
    result = json.loads(
        (ROOT / "research/hydrogen_reference_leak_detector_result_2026_10_08.json").read_text(
            encoding="utf-8"
        )
    )

    assert result["status"] == "COMPLETED_FROZEN_PROTOCOL_PASS"
    assert result["source"]["identity_match"] is True
    assert result["source"]["test_gas"] == "hydrogen"
    assert result["protocol"]["raw_outcomes_accessed_before_freeze"] is False
    assert result["protocol"]["parameters_fitted"] is False
    assert result["results"]["total_observation_count"] == 45
    assert result["results"]["evaluated_series_count"] == 3
    assert all(item["joint_pass"] for item in result["results"]["series"])
    assert result["decision"]["bounded_actual_hydrogen_response_ordering_supported"] is True
    assert result["decision"]["runtime_application"] is False
    assert result["decision"]["spatial_detector_transfer_gate_changed"] is False
    assert result["decision"]["full_loop_validation_supported"] is False
