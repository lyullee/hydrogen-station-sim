from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = (
    ROOT
    / "research/release_network_natural_convection_amendment_2026_10_13.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_amendment_locks_current_model_and_protocols() -> None:
    record = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    amended = record["amended_revision"]

    assert amended["model_sha256"] == _sha256(ROOT / amended["model"])
    assert amended["apparatus_protocol_sha256"] == _sha256(
        ROOT / amended["apparatus_protocol"]
    )
    assert amended["secondary_protocol_sha256"] == _sha256(
        ROOT / amended["secondary_protocol"]
    )


def test_amendment_is_prospective_and_does_not_promote_claims() -> None:
    record = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    freeze = record["freeze_declarations"]
    impact = record["claim_impact"]

    assert freeze["qualifying_target_campaign_received"] is False
    assert freeze["qualifying_target_campaign_numerical_outcome_accessed"] is False
    assert freeze["post_outcome_mode_or_length_selection_prohibited"] is True
    assert impact["external_validation_status"] == "NOT_ESTABLISHED"
    assert impact["ijhe_gate_impact"] == "no_change"
    assert impact["production_runtime_updated"] is False
    assert impact["goal_completion_permitted"] is False
