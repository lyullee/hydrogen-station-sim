from __future__ import annotations

import pytest

from h2station.risk.runtime_backend import mass_flow_override_metadata


def test_missing_override_is_explicitly_model_calculated():
    result = mass_flow_override_metadata(None, 0.04)
    assert result["mass_flow_override_requested"] is False
    assert result["mass_flow_override_status"] == "MODEL_CALCULATED"
    assert result["mass_flow_override_ratio"] is None


def test_close_override_is_reported_as_retained():
    result = mass_flow_override_metadata(0.04, 0.041)
    assert result["mass_flow_override_status"] == "OVERRIDE_RETAINED"
    assert result["mass_flow_override_ratio"] == pytest.approx(1.025)


def test_choked_model_mismatch_is_not_silently_presented_as_measurement():
    result = mass_flow_override_metadata(0.04, 0.202)
    assert result["mass_flow_override_status"] == "HYRAM_CHOKED_MODEL_EXCEEDS_REQUEST"
    assert result["mass_flow_override_ratio"] == pytest.approx(5.05)
    assert "not be described as a measured release" in result["mass_flow_override_claim_limit"]
