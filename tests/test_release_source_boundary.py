"""Release source boundaries distinguish free holes from flow-limited lines."""

import pytest
from pydantic import ValidationError

from h2station.api import FaultInput
from h2station.risk.live import DynamicLeakModel, LeakScenario, LeakSourceState


def test_flow_limited_line_caps_free_orifice_release() -> None:
    source = LeakSourceState(35.0e6, 288.15)
    free = LeakScenario(
        release_id="free",
        component_id="dispenser.hose",
        location="N13",
        start_time_s=0.0,
        orifice_diameter_m=0.01,
    )
    limited = LeakScenario(
        release_id="limited",
        component_id="dispenser.hose",
        location="N13",
        start_time_s=0.0,
        orifice_diameter_m=0.01,
        release_boundary="flow_limited_line",
        maximum_mass_flow_kg_s=0.06,
    )

    model = DynamicLeakModel()
    assert model.mass_flow_kg_s(free, source) > 0.06
    assert model.mass_flow_kg_s(limited, source) == pytest.approx(0.06)


def test_fault_api_requires_limit_for_flow_limited_release() -> None:
    with pytest.raises(ValidationError, match="positive maximum mass flow"):
        FaultInput(
            event_id="missing-limit",
            kind="hydrogen-leak",
            target="dispenser.hose",
            start_time_s=0.0,
            leak_diameter_mm=10.0,
            release_boundary="flow_limited_line",
        )

    event = FaultInput(
        event_id="metered-line",
        kind="hydrogen-leak",
        target="dispenser.hose",
        start_time_s=0.0,
        leak_diameter_mm=10.0,
        release_boundary="flow_limited_line",
        maximum_release_mass_flow_g_s=60.0,
    ).to_event()
    assert event.release_boundary == "flow_limited_line"
    assert event.maximum_release_mass_flow_kg_s == pytest.approx(0.06)


def test_non_leak_cannot_carry_release_boundary() -> None:
    with pytest.raises(ValidationError, match="apply only to hydrogen leaks"):
        FaultInput(
            event_id="bad-boundary",
            kind="sensor-bias",
            target="PT-0901",
            start_time_s=0.0,
            magnitude=1.0,
            release_boundary="flow_limited_line",
            maximum_release_mass_flow_g_s=60.0,
        )
