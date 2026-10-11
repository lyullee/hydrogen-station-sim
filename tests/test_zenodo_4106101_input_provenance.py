from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_zenodo_input_provenance_audit_separates_temperature_boundary():
    payload = json.loads(
        (ROOT / "research/zenodo_4106101_input_provenance_audit_2026_10_11.json").read_text(
            encoding="utf-8"
        )
    )
    geometry = payload["documented_boundaries"]["geometry_and_vent_area"]
    temperature = payload["documented_boundaries"]["temperature"]
    status = payload["runner_boundary_status"]
    assert geometry["matches_runner_constants"] is True
    assert temperature["per_case_temperature_boundary_in_metadata"] is False
    assert status["runtime_parameter_changed"] is False
    assert status["result_reclassification"] == (
        "exploratory_only_until_temperature_provenance_or_channel_is independently archived"
    )
