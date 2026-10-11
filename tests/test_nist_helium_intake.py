from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nist_intake_preserves_component_only_boundary() -> None:
    artifact = json.loads(
        (ROOT / "research/nist_helium_garage_2011_intake_2026_10_11.json").read_text(
            encoding="utf-8"
        )
    )
    assert artifact["archive"]["workbook_count"] == 18
    assert artifact["eligibility_decision"]["schema_integrity_pass"] is True
    assert artifact["eligibility_decision"]["prospective_validation_eligible"] is False
    assert artifact["eligibility_decision"]["full_loop_hrs_validation_eligible"] is False
    assert artifact["source"]["test_gas"] == "helium surrogate for hydrogen"
    assert all(
        0.99 < workbook["median_sample_interval_s"] < 1.01
        for workbook in artifact["archive"]["workbooks"]
    )
