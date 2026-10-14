from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_type4_burst_intake_is_integrity_checked_and_claim_bounded() -> None:
    artifact = json.loads(
        (
            ROOT
            / "research/zenodo_10983652_type4_burst_dataset_intake_2026_10_14.json"
        ).read_text(encoding="utf-8")
    )
    source = artifact["source"]
    scope = artifact["measurement_scope"]
    classification = artifact["evidence_classification"]

    assert artifact["status"] == "PUBLIC_ARCHIVE_INTEGRITY_VERIFIED"
    assert source["dataset_doi"] == "10.5281/zenodo.10983652"
    assert source["license"] == "CC BY 4.0"
    assert source["archive_file"]["md5"] == "c20c9cea381a2f34446a09739fa5ddcb"
    assert scope["test_fluid"] == "water (hydraulic burst test; not hydrogen)"
    assert scope["pressure_raw_sample_rate_hz"] == 100
    assert scope["strain_raw_sample_rate_hz"] == 300
    assert scope["synchronized_sample_rate_hz"] == 10
    assert scope["strain_channel_count"] == 18
    assert classification["public_rights_cleared"] is True
    assert classification["component_mechanical_boundary"] is True
    assert classification["runtime_parameter_application"] is False
    assert classification["readiness_gate_effect"] is False

