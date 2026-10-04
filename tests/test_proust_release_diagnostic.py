import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_proust_postaccess_diagnostic_does_not_promote_failed_gate():
    record = json.loads(
        (
            ROOT
            / "research/proust_release_postaccess_residual_diagnostic_2026_10_04.json"
        ).read_text(encoding="utf-8")
    )
    assert record["evidence_role"] == "post_access_exploratory_diagnostic"
    assert record["observed_primary_result"]["claim_supported"] is False
    assert record["gate_impact"] == "no_change_proust_gate_remains_failed"
    assert len(record["inferred_local_discharge_coefficient"]) == 3
    assert "must not be used as a fitted correction" in record["interpretation"][1]
