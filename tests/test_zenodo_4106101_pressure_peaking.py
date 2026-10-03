import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_zenodo_4106101_protocol_is_frozen_before_outcomes():
    protocol = json.loads(
        (ROOT / "research/zenodo_4106101_pressure_peaking_protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["status"] == "prospective_protocol_frozen_before_data_access"
    assert protocol["evidence_role"] == "prospective_external_consequence_validation_protocol"
    assert protocol["freeze"]["outcomes_accessed_before_freeze"] is False
    assert protocol["freeze"]["protocol_frozen_before_raw_download"] is True
    assert protocol["source"]["doi"] == "10.5281/zenodo.4106101"


def test_zenodo_4106101_result_is_transparent_exploratory_screen():
    result = json.loads(
        (ROOT / "research/zenodo_4106101_pressure_peaking_result.json").read_text(
            encoding="utf-8"
        )
    )
    aggregate = result["aggregate"]
    assert result["status"] == "completed_prospective_protocol_execution"
    assert result["evidence_role"] == "prospective_external_consequence_validation_result"
    assert aggregate["eligible_case_count"] == 10
    assert aggregate["excluded_case_count"] == 0
    assert aggregate["joint_primary_pass_count"] == 7
    assert aggregate["joint_primary_pass_fraction"] == 0.7
    assert aggregate["confirmatory_rule_met"] is False
    assert len(result["cases"]) == 10
    assert "not validation of the full HRS fueling loop" in result["claim_boundary"]
