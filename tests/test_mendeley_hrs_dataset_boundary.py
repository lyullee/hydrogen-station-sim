from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mendeley_hrs_dataset_is_explicitly_simulation_only():
    report = json.loads(
        (ROOT / "research/hrs_mendeley_simulation_dataset_boundary_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "PUBLIC_MENDELEY_HRS_METADATA_RECHECKED"
    assert report["source"]["doi"] == "10.17632/mnjs94yzfc.1"
    assert report["metadata_integrity"]["cc_by_4_present"] is True
    assert report["dataset_characterization"]["simulation_only"] is True
    assert report["dataset_characterization"]["real_station_full_loop"] is False
    assert report["eligibility_decision"]["full_loop_external_holdout_eligible"] is False
    assert report["claim_boundary"]
