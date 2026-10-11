from __future__ import annotations

import json
from pathlib import Path

from scripts.archive_nrel_h2fills_geometry_sensitivity import build_archive


ROOT = Path(__file__).resolve().parents[1]


def test_archive_preserves_post_access_boundary_and_aggregate_result() -> None:
    source_path = ROOT / "data/public_validation/results/nrel_h2fills_hdvs_typeiv/geometry_sensitivity.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    archive = build_archive(source, source_path=source_path)
    assert archive["status"] == "post_access_development_diagnostic"
    assert archive["governance"]["outcomes_accessed_before_diagnostic"] is True
    assert archive["governance"]["runtime_default_changed"] is False
    assert archive["governance"]["validation_gate_effect"] == "none"
    preferred = archive["variants"]["capacity_eos_no_volume_fit"]
    assert preferred["screening_pass_count"] == 7
    assert archive["finding"]["preferred_screen_total"] == 7
    assert archive["source"].get("workbook_path") is None
    assert "not authorize a runtime" in archive["claim_boundary"]
