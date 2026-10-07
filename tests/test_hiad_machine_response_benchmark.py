from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_hiad_machine_response_benchmark import (  # noqa: E402
    paired_bootstrap,
    score_answer,
)


def test_machine_proxy_scores_expected_action_and_stages_without_numeric_invention():
    answer = (
        "The observation suggests a hydrogen release, but the cause is uncertain. "
        "Immediately stop fueling, isolate the supply, evacuate the exclusion zone, "
        "and notify emergency services. Monitor gas concentration and ventilate the "
        "area. Restart only after a leak test and authorized approval. Prevent recurrence "
        "through inspection, maintenance, and procedure review."
    )
    score = score_answer(
        answer,
        expected_categories=[
            "shutdown_isolation_depressurization",
            "detection_alarm_monitoring",
            "evacuation_perimeter_access",
            "emergency_communication_coordination",
            "inspection_leak_test_repair",
            "procedure_interlock_training_design",
            "ventilation_purge",
        ],
        allowed_input_text="confirmed hydrogen release",
    )
    assert score["category_recall"] == 1.0
    assert score["stage_coverage"] == 1.0
    assert score["unsupported_value_unit_claims"] == []
    assert score["machine_proxy_score"] == 1.0


def test_machine_proxy_flags_only_value_unit_claims_missing_from_input():
    score = score_answer(
        "Evacuate a 25 m zone and wait 10 minutes.",
        expected_categories=["evacuation_perimeter_access"],
        allowed_input_text="No distance or duration is supplied.",
    )
    assert score["category_recall"] == 1.0
    assert set(score["unsupported_value_unit_claims"]) == {"25 m", "10 minutes"}


def test_paired_bootstrap_is_deterministic_and_preserves_direction():
    result = paired_bootstrap(
        [0.1, 0.2, 0.3], [0.4, 0.5, 0.6], seed=20261008, replicates=1000,
    )
    assert abs(result["mean_paired_difference"] - 0.3) < 1.0e-12
    assert result["bootstrap_95_ci"][0] > 0.0


def test_protocol_freezes_the_runner_before_cohort_response_collection():
    protocol = json.loads(
        (ROOT / "research/hiad_machine_response_benchmark_protocol_2026_10_08.json")
        .read_text(encoding="utf-8")
    )
    assert protocol["status"] == "frozen_before_cohort_model_response_collection"
    assert protocol["cohort"]["case_count"] == 34
    assert protocol["outcome_history"]["cohort_model_outputs_accessed_before_freeze"] is False
    assert protocol["outcome_history"]["confirmatory_or_prospective_claim_permitted"] is False
    runner = ROOT / protocol["frozen_inputs"]["runner"]
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == protocol["frozen_inputs"][
        "runner_sha256"
    ]
