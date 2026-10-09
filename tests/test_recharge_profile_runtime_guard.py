from __future__ import annotations

from h2station.api import ProcessSettings, _effective_recharge_restart_margins
from h2station.calibration_profiles import load_measured_boundary_calibration


def test_measured_station_margin_cannot_weaken_default_bank_margins() -> None:
    profile = load_measured_boundary_calibration()
    assert profile is not None

    margins = _effective_recharge_restart_margins(
        ProcessSettings().model_dump(), profile
    )

    # The aggregate 0.54 MPa profile is a lower bound.  It must not replace
    # the observed 4.5 MPa high-bank restart band or the operator defaults.
    assert margins == {"low": 2.0, "medium": 3.0, "high": 4.5}


def test_explicit_operator_margin_remains_authoritative_above_measured_floor() -> None:
    profile = load_measured_boundary_calibration()
    assert profile is not None
    settings = ProcessSettings(
        recharge_restart_margin_low_mpa=0.3,
        recharge_restart_margin_medium_mpa=0.8,
        recharge_restart_margin_high_mpa=7.0,
    ).model_dump()

    margins = _effective_recharge_restart_margins(settings, profile)

    assert margins == {"low": 0.54, "medium": 0.8, "high": 7.0}
