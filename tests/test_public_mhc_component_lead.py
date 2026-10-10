from __future__ import annotations

import json
from pathlib import Path


def test_public_mhc_component_lead_is_explicitly_bounded() -> None:
    root = Path(__file__).resolve().parents[1]
    leads = json.loads(
        (root / "research/public_component_data_leads_2026_10_10.json")
        .read_text(encoding="utf-8")
    )
    mhc = next(
        item for item in leads["related_public_leads"]
        if item["id"] == "zenodo_mhc_compressor_v1_1_18213166"
    )
    assert mhc["license"] == "CC BY 4.0"
    assert mhc["experiment_count"] == 29
    assert mhc["full_loop_external_holdout_eligible"] is False
    assert mhc["runtime_parameter_application"] is False

    protocol = json.loads(
        (root / "research/public_mhc_compressor_component_protocol_2026_10_10.json")
        .read_text(encoding="utf-8")
    )
    assert protocol["status"] == "protocol_frozen_diagnostic_only"
    assert protocol["protocol"]["raw_rows_persisted"] is False
    assert "dispenser and vehicle/receptacle response" in protocol["boundary"]["excluded"]

    screen = json.loads(
        (root / "research/public_mhc_experiment15_screen_2026_10_10.json")
        .read_text(encoding="utf-8")
    )
    assert screen["protocol"]["holdout_accessed_after_protocol_freeze"] is True
    assert screen["screen"]["schema_screen_pass"] is True
    assert screen["screen"]["direct_runtime_model_compatibility"] is False
    assert screen["decision"]["runtime_parameter_application"] is False
