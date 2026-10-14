import json
from pathlib import Path

from scripts.validate_dickens_typeiii_protocol import validate_protocol


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/dickens_typeiii_geometry_resolved_prospective_protocol_2026_10_10.json"


def test_geometry_resolved_protocol_is_valid_but_still_blocks_outcome_access():
    result = validate_protocol(PROTOCOL)

    assert result["protocol_valid"] is True
    assert result["outcome_access_allowed"] is False
    assert result["numerical_values_inspected"] is False
    assert result["reasons"] == []
    assert len(result["protocol_sha256"]) == 64


def test_validator_fails_closed_when_inlet_temperature_contract_is_removed(tmp_path):
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    payload["required_input_contract"].pop("inlet_temperature_k")
    candidate = tmp_path / "protocol.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    result = validate_protocol(candidate)

    assert result["protocol_valid"] is False
    assert result["outcome_access_allowed"] is False
    assert any("inlet_temperature_k" in reason for reason in result["reasons"])
