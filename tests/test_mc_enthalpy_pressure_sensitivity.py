from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mc_enthalpy_pressure_sensitivity_keeps_boundary_ambiguity_explicit():
    record = json.loads(
        (ROOT / "research/mc_enthalpy_pressure_sensitivity_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["diagnostic_type"] == "MC inlet enthalpy pressure-basis sensitivity"
    assert record["evidence_role"] == "development_diagnostic_only"
    assert record["post_outcome"] is True
    assert record["parameter_fitting"] is False
    assert len(record["runs"]) == 3
    assert "nozzle-upstream pressure" in record["claim_boundary"]
