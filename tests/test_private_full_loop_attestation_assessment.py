import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from assess_private_full_loop_attestation import assess  # noqa: E402


def _template() -> dict:
    return json.loads(
        (
            ROOT
            / "research/PRIVATE_FULL_LOOP_ATTESTATION_TEMPLATE_2026_10_11.json"
        ).read_text(encoding="utf-8")
    )


def _schema(roles: set[str]) -> dict:
    return {
        "scope": {"raw_rows_persisted": False, "original_headers_persisted": False},
        "aggregate": {"observed_full_loop_contract_groups": sorted(roles)},
    }


def test_current_template_cannot_admit_private_holdout():
    report = json.loads(
        (
            ROOT
            / "research/local_private_full_loop_schema_recheck_2026_10_11.json"
        ).read_text(encoding="utf-8")
    )
    result = assess(_schema(set(report["aggregate"]["observed_full_loop_contract_groups"])), _template())
    assert result["privacy_boundary_ok"] is True
    assert result["candidate_ready_for_independent_review"] is False
    assert result["external_holdout_eligibility"] is False
    assert "vehicle_pressure" in result["missing_schema_roles"]


def test_complete_attestation_is_ready_for_review_but_not_validation():
    document = _template()
    document["custodian_attestation"].update(
        authorized_data_owner=True,
        release_rights_for_research=True,
    )
    for row in document["channel_attestations"]:
        row["present"] = True
        if row["role"] == "common_time":
            row["clock_alignment_method"] = "bounded common-clock alignment"
            row["clock_alignment_uncertainty_s"] = 0.01
        if row["role"] in {
            "station_pressure",
            "delivered_temperature",
            "mass_flow",
            "vehicle_pressure",
            "vehicle_temperature",
        }:
            row["calibration_status"] = "attested"
            row["uncertainty"] = 0.1
    document["holdout_controls"].update(
        split_manifest_hash="masked-hash",
        model_and_parameters_frozen_before_outcome_access=True,
        independent_reviewer_confirmed=True,
    )
    roles = {row["role"] for row in document["channel_attestations"]}
    result = assess(_schema(roles), document)
    assert result["candidate_ready_for_independent_review"] is True
    assert result["holdout_controls"]["minimum_event_count_met"] is True
    # The assessor cannot turn metadata into a validation result.
    assert result["external_holdout_eligibility"] is False
    assert result["validation_gate_effect"] == "none"

