from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/confidential_station_thermal_dynamics_protocol_2026_10_08.json"


def test_station_thermal_protocol_is_frozen_and_attestation_gated():
    payload = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    assert payload["status"] == "frozen_awaiting_custodian_attestation"
    assert payload["required_attestation"]["current_status"] == "UNCONFIRMED"
    assert payload["generic_component_mapping"]["proposals_are_attested"] is False
    assert payload["analysis"]["raw_smoothing"] is False
    assert payload["analysis"]["imputation"] is False
    assert payload["promotion_boundary"]["runtime_parameter_application"] is False
    assert payload["promotion_boundary"]["full_loop_holdout_eligible"] is False


def test_station_thermal_protocol_never_names_private_sources():
    text = PROTOCOL.read_text(encoding="utf-8")

    for forbidden in (
        "PROPRIETARY.COLUMN",
        "restricted/source/path",
        "company_or_station_identity",
        "absolute_measurement_timestamp",
    ):
        assert forbidden not in text
