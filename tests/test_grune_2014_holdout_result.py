from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research" / "grune_2014_holdout_result.json"
PROTOCOL = ROOT / "research" / "grune_2014_holdout_protocol.json"
DATA = ROOT / "data" / "public_validation" / "derived" / "grune_2014_figure2.csv"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_grune_result_retains_ineligibility_and_source_hashes():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["protocol_sha256"] == _sha256(PROTOCOL)
    assert result["data_sha256"] == _sha256(DATA)
    assert result["eligibility"]["minimum_unique_points_met"] is True
    assert result["eligibility"]["measured_half_pressure_time_observed"] is False
    assert result["eligibility"]["minimum_requirements_met"] is False
    assert result["claim_supported"] is False
    assert result["result"]["points"] == 51
    assert result["result"]["experimental_half_pressure_time_s"] is None
    assert result["result"]["predicted_half_pressure_time_s"] is None


def test_grune_locked_runner_remains_byte_identical_after_archiving():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["locked_runner"]["sha256"] == _sha256(
        ROOT / protocol["locked_runner"]["path"]
    )
