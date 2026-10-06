from __future__ import annotations

import json

from h2station.lifecycle_evidence import load_lifecycle_evidence


def _record() -> dict[str, object]:
    return {
        "artifact_type": "confidential_lifecycle_counter_summary",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "sampled_rows": 4,
        "counter_semantics": "full-bank recharge counter",
        "counters": {
            "medium_bank_cycles": {
                "sample_count": 4,
                "observed_min": 1,
                "observed_max": 2,
                "positive_increment_count": 1,
                "total_positive_increment": 1,
                "maximum_single_increment": 1,
            }
        },
        "attestation": {
            "status": "custodian_attested",
            "counter_semantics_attested": True,
            "threshold_units_attested": True,
            "degradation_relationship_attested": False,
            "full_recharge_threshold_bar": {
                "medium_bank": 450,
                "high_bank": 850,
            },
        },
        "claim_boundary": "history only",
    }


def test_attested_lifecycle_evidence_is_bounded(tmp_path):
    path = tmp_path / "lifecycle.json"
    path.write_text(json.dumps(_record()), encoding="utf-8")
    profile = load_lifecycle_evidence(path)
    assert profile is not None
    metadata = profile.runtime_metadata()
    assert metadata["full_recharge_threshold_bar"] == {
        "medium_bank": 450.0,
        "high_bank": 850.0,
    }
    assert metadata["degradation_relationship_attested"] is False


def test_unattested_lifecycle_evidence_is_rejected(tmp_path):
    record = _record()
    record["attestation"] = {
        "status": "pending_custodian_confirmation",
        "counter_semantics_attested": False,
        "threshold_units_attested": False,
    }
    path = tmp_path / "pending.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert load_lifecycle_evidence(path) is None


def test_default_lifecycle_evidence_is_attested_but_not_a_degradation_model():
    profile = load_lifecycle_evidence()
    assert profile is not None
    assert profile.sampled_rows == 41752
    assert profile.full_recharge_threshold_bar == {
        "medium_bank": 450.0,
        "high_bank": 850.0,
    }
    assert profile.degradation_relationship_attested is False
