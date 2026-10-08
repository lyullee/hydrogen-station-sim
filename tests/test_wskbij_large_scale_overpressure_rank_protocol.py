import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    ROOT / "research/wskbij_large_scale_overpressure_rank_protocol_2026_10_08.json"
)


def _protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_wskbij_protocol_freezes_identity_model_and_outcome_boundary() -> None:
    protocol = _protocol()

    assert protocol["status"] == (
        "FROZEN_AFTER_AGGREGATE_SUMMARY_ACCESS_BEFORE_ROW_LEVEL_MODEL_COMPARISON"
    )
    assert protocol["source"]["dataset_doi"] == "10.18710/WSKBIJ"
    assert protocol["source"]["dataset_license"] == "CC0 1.0"
    assert protocol["source"]["summary_workbook_datafile_id"] == 268155
    assert protocol["source"]["summary_workbook_expected_sha256"] == (
        "5ca3813fd7e9ade6c0d1aa623d2a7f5346760334b1c8b014a4ea3235ae5dbd34"
    )
    assert protocol["preaccess_disclosure"][
        "summary_workbook_accessed_by_inventory_software"
    ] is True
    assert protocol["preaccess_disclosure"][
        "individual_pressure_outcome_rows_reviewed_or_used_for_design"
    ] is False
    assert protocol["selection_rule"]["selection_uses_pressure_magnitude_or_order"] is False
    assert protocol["selection_rule"]["expected_scored_case_count"] == 44
    assert protocol["locked_model"]["configuration"]["case_specific_fitting"] is False
    assert protocol["diagnostics"]["runtime_parameter_update_allowed"] is False


def test_wskbij_protocol_has_fixed_joint_decision_and_bounded_claim() -> None:
    protocol = _protocol()
    metrics = protocol["primary_metrics"]

    assert metrics["pooled_spearman_rank_correlation"]["threshold"] == 0.5
    assert metrics["within_stratum_rank_spearman"]["threshold"] == 0.45
    assert metrics["within_stratum_pairwise_order_concordance"]["threshold"] == 0.65
    assert metrics["within_stratum_top_third_recall"]["threshold"] == 0.5
    assert metrics["scored_case_count"]["threshold"] == 40
    assert "all five primary screens" in protocol["decision_rule"]
    boundary = protocol["claim_boundary"].lower()
    for phrase in (
        "relative source-severity ordering",
        "would not validate absolute overpressure",
        "full-loop dynamics",
        "regulatory compliance",
    ):
        assert phrase in boundary


def test_wskbij_protocol_file_has_stable_sha256_shape() -> None:
    digest = hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
    assert len(digest) == 64
    assert set(digest) <= set("0123456789abcdef")
