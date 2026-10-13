from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_usn_orientation_transfer_is_reproducible_but_not_independent_validation() -> None:
    artifact = json.loads(
        (ROOT / "research/usn_orientation_class_spatial_transfer_diagnostic_2026_10_14.json")
        .read_text(encoding="utf-8")
    )
    assert artifact["status"] == "POST_ACCESS_REPRODUCIBILITY_DIAGNOSTIC_NOT_INDEPENDENT_VALIDATION"
    assert artifact["aggregate"]["experiment_count"] == 22
    assert artifact["aggregate"]["joint_screen_pass"] is True
    assert artifact["provenance_boundary"]["independent_holdout"] is False
    assert artifact["provenance_boundary"]["prospective_validation"] is False
    assert artifact["decision"]["runtime_detector_routing_changed"] is False
    assert artifact["decision"]["gate_changed"] is False
