import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_jankuj_pressure_decay_transfer_retains_invalidated_negative_diagnostic():
    result = json.loads(
        (ROOT / "research/jankuj_2026_pressure_decay_transfer_result_2026_10_08.json")
        .read_text(encoding="utf-8")
    )
    protocol = ROOT / "research/jankuj_2026_pressure_decay_protocol_2026_10_08.json"
    assert result["status"] == "INVALIDATED_PRIOR_OUTCOME_ACCESS"
    assert result["evidence_role"] == "post_access_diagnostic_only"
    assert result["protocol"]["protocol_frozen_before_first_numeric_outcome_access"] is False
    assert result["protocol"]["prospective_protocol_valid"] is False
    assert result["protocol"]["sha256"] == _sha256(protocol)
    assert result["prior_outcome_access"]["pressure_workbook_numeric_rows"] == 2754
    assert result["prior_outcome_access"]["matches_current_workbook"] is True
    assert result["model"]["source_sha256"] == _sha256(
        ROOT / result["model"]["source"]
    )
    assert result["model"]["holdout_refitted"] is False
    assert result["development_curve"]["large_positive_jump_count"] >= 1
    assert result["joint_primary_screen_pass"] is False
    assert result["source_depletion_transfer_validation_supported"] is False
    assert result["holdout_curve"]["metrics"]["pressure_nrmse_screen_pass"] is False
    assert result["holdout_curve"]["metrics"]["median_ape_screen_pass"] is False
    assert result["holdout_curve"]["metrics"]["half_pressure_time_screen_pass"] is False
