"""Integration guard for the production HyRAM adapter translation layer."""

import numpy as np
import pytest

pytest.importorskip("hyram")

from hyram.phys import api

from h2station.risk.hyram_adapter import AmbientCondition, HyRAMRiskMonitor, LeakScenario
from h2station.thermo_types import ThermoState


def _state(pressure: float, temperature: float) -> ThermoState:
    return ThermoState(pressure, temperature, *(float("nan") for _ in range(10)))


def test_adapter_matches_direct_hyram_api_for_all_consequence_outputs():
    pressure = 45.0e6
    temperature = 298.15
    diameter = 0.001
    coefficient = 0.8
    locations = ((1.0, 0.0, 1.0), (2.0, 0.0, 1.0), (5.0, 0.0, 1.0))
    ambient = api.create_fluid("air", temp=298.15, pres=101_325.0)
    release = api.create_fluid("H2", temp=temperature, pres=pressure)
    initial_flow = float(np.asarray(api.compute_mass_flow(
        release, diameter, amb_pres=101_325.0, is_steady=True,
        dis_coeff=coefficient, create_plot=False,
    )["rates"]).reshape(-1)[0])
    plume = api.analyze_jet_plume(
        ambient, release, diameter, mass_flow=initial_flow, rel_angle=0.0,
        dis_coeff=coefficient, nozzle_model="yuce", create_plot=False,
        contours=[0.04],
    )
    modeled_flow = float(plume["mass_flow_rate"])
    flame = api.jet_flame_analysis(
        ambient, release, diameter, mass_flow=modeled_flow, dis_coeff=coefficient,
        rel_angle=0.0, nozzle_key="yuce", rel_humid=0.5,
        create_temp_plot=False, analyze_flux=True, create_flux_plot=False,
        flux_coordinates=list(locations),
    )
    blast = api.compute_overpressure(
        "bst", list(locations), ambient, release, diameter,
        mass_flow=float(flame[3]), release_angle=0.0,
        discharge_coefficient=coefficient, nozzle_model="yuce",
        bst_flame_speed=0.35, tnt_factor=0.03,
        create_overpressure_plot=False, create_impulse_plot=False,
    )

    result = HyRAMRiskMonitor().evaluate(
        0.0, _state(pressure, temperature),
        LeakScenario(
            orifice_diameter=diameter, locations=locations,
            discharge_coefficient=coefficient,
        ),
        AmbientCondition(relative_humidity=0.5),
    )

    assert result.mass_flow_rate == pytest.approx(float(flame[3]), rel=1e-12)
    assert result.heat_fluxes == pytest.approx(np.asarray(flame[2]).reshape(-1), rel=1e-12)
    assert result.overpressures == pytest.approx(blast["overpressures"], rel=1e-12)
    assert result.impulses == pytest.approx(blast["impulses"], rel=1e-12)
    assert result.visible_flame_length == pytest.approx(float(flame[5]), rel=1e-12)
    assert result.radiant_fraction == pytest.approx(float(flame[6]), rel=1e-12)
    assert result.flammable_streamline_distance == pytest.approx(
        float(np.asarray(plume["streamline_dists"]).reshape(-1)[0]), rel=1e-12
    )
    contour = plume["mole_frac_dists"][0.04]
    assert result.flammable_x_extent == pytest.approx(contour[0], rel=1e-12)
    assert result.flammable_y_extent == pytest.approx(contour[1], rel=1e-12)
