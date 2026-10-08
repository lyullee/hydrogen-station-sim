"""Experiment-backed screening correlation for delayed ignition of H2 free jets.

The implementation follows Equation (5) and its inverse form in Cirrone et al.
(2022), DOI 10.3390/hydrogen3040027.  The correlation was built from 78
experiments.  It predicts a conservative blast-wave envelope around the centre
of the fast-burning, near-stoichiometric part of an under-expanded free jet.

This module intentionally does not turn the radial distance into a site safety
or evacuation radius.  Doing that requires the position of the 30 vol% H2
cloud centre, the actual release direction, obstacles and site geometry.
"""

from __future__ import annotations

import math
from typing import Final


CIRRONE_DOI: Final[str] = "10.3390/hydrogen3040027"
CIRRONE_SOURCE_URL: Final[str] = "https://doi.org/10.3390/hydrogen3040027"

MIN_PRESSURE_PA: Final[float] = 0.5e6
MAX_PRESSURE_PA: Final[float] = 65.0e6
MIN_TEMPERATURE_K: Final[float] = 80.0
MAX_TEMPERATURE_K: Final[float] = 300.0
MIN_DIAMETER_M: Final[float] = 0.5e-3
MAX_DIAMETER_M: Final[float] = 52.5e-3

NO_HARM_OVERPRESSURE_PA: Final[float] = 1_350.0
INJURY_OVERPRESSURE_PA: Final[float] = 16_500.0
FATALITY_OVERPRESSURE_PA: Final[float] = 100_000.0


def _positive_finite(name: str, value: float) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return parsed


def delayed_ignition_overpressure_pa(
    storage_pressure_pa: float,
    release_diameter_m: float,
    wave_distance_from_cloud_centre_m: float,
    *,
    ambient_pressure_pa: float = 101_325.0,
) -> float:
    """Return the Equation (5) conservative delayed-ignition overpressure.

    ``wave_distance_from_cloud_centre_m`` is Rw in the paper: distance from the
    centre of the 25--35 vol% H2 region, not distance from the leak opening.
    """

    storage = _positive_finite("storage_pressure_pa", storage_pressure_pa)
    ambient = _positive_finite("ambient_pressure_pa", ambient_pressure_pa)
    diameter = _positive_finite("release_diameter_m", release_diameter_m)
    distance = _positive_finite(
        "wave_distance_from_cloud_centre_m",
        wave_distance_from_cloud_centre_m,
    )
    dimensionless = (storage / ambient) ** 0.5 * (diameter / distance) ** 2
    return ambient * 5_000.0 * dimensionless**0.95


def delayed_ignition_radial_distance_m(
    storage_pressure_pa: float,
    release_diameter_m: float,
    overpressure_threshold_pa: float,
    *,
    ambient_pressure_pa: float = 101_325.0,
) -> float:
    """Invert Equation (5) for radial distance from the cloud centre."""

    storage = _positive_finite("storage_pressure_pa", storage_pressure_pa)
    ambient = _positive_finite("ambient_pressure_pa", ambient_pressure_pa)
    diameter = _positive_finite("release_diameter_m", release_diameter_m)
    threshold = _positive_finite(
        "overpressure_threshold_pa", overpressure_threshold_pa
    )
    return (
        diameter
        * (storage / ambient) ** 0.25
        * (5_000.0 * ambient / threshold) ** (1.0 / 1.9)
    )


def delayed_ignition_envelope(
    *,
    storage_pressure_pa: float,
    storage_temperature_k: float,
    release_diameter_m: float,
    ambient_pressure_pa: float = 101_325.0,
    release_boundary: str = "free_orifice",
) -> dict[str, float | str | bool | None]:
    """Return claim-bounded literature screening distances for a release.

    A process-flow cap cannot be represented by this pressure/diameter-only
    correlation.  Such sources fail closed instead of substituting an
    equivalent orifice that the paper did not validate.
    """

    storage = _positive_finite("storage_pressure_pa", storage_pressure_pa)
    temperature = _positive_finite("storage_temperature_k", storage_temperature_k)
    diameter = _positive_finite("release_diameter_m", release_diameter_m)
    ambient = _positive_finite("ambient_pressure_pa", ambient_pressure_pa)
    base: dict[str, float | str | bool | None] = {
        "literature_delayed_ignition_model": "CIRRONE_2022_EQUATION_5",
        "literature_delayed_ignition_doi": CIRRONE_DOI,
        "literature_delayed_ignition_source_url": CIRRONE_SOURCE_URL,
        "literature_delayed_ignition_experiment_count": 78.0,
        "literature_delayed_ignition_distance_origin": (
            "CENTRE_OF_25_TO_35_VOL_PERCENT_H2_CLOUD"
        ),
        "literature_delayed_ignition_site_safety_distance": False,
        "literature_delayed_ignition_claim_limit": (
            "자유 수소 제트의 지연점화 최대 과압을 25~35 vol% 수소 혼합운 중심에서 "
            "평가하는 문헌 상관식입니다. 누출구 중심 안전거리·대피거리·발생확률이 아니며 "
            "장애물, 충돌제트, 밀폐·반밀폐 공간은 반영하지 않습니다."
        ),
    }
    if release_boundary != "free_orifice":
        return {
            **base,
            "literature_delayed_ignition_status": "NOT_APPLICABLE_FLOW_LIMITED_SOURCE",
            "literature_delayed_ignition_in_validation_domain": False,
            "literature_delayed_ignition_5kpa_radial_distance_m": None,
            "literature_delayed_ignition_no_harm_radial_distance_m": None,
            "literature_delayed_ignition_injury_radial_distance_m": None,
            "literature_delayed_ignition_fatality_radial_distance_m": None,
        }

    in_domain = (
        MIN_PRESSURE_PA <= storage <= MAX_PRESSURE_PA
        and MIN_TEMPERATURE_K <= temperature <= MAX_TEMPERATURE_K
        and MIN_DIAMETER_M <= diameter <= MAX_DIAMETER_M
    )
    status = "CALCULATED_IN_VALIDATION_DOMAIN" if in_domain else "CALCULATED_EXTRAPOLATED"
    distance = lambda threshold: delayed_ignition_radial_distance_m(
        storage,
        diameter,
        threshold,
        ambient_pressure_pa=ambient,
    )
    return {
        **base,
        "literature_delayed_ignition_status": status,
        "literature_delayed_ignition_in_validation_domain": in_domain,
        "literature_delayed_ignition_pressure_domain_mpa": "0.5-65",
        "literature_delayed_ignition_temperature_domain_k": "80-300",
        "literature_delayed_ignition_diameter_domain_mm": "0.5-52.5",
        "literature_delayed_ignition_5kpa_radial_distance_m": distance(5_000.0),
        "literature_delayed_ignition_no_harm_threshold_pa": NO_HARM_OVERPRESSURE_PA,
        "literature_delayed_ignition_no_harm_radial_distance_m": distance(
            NO_HARM_OVERPRESSURE_PA
        ),
        "literature_delayed_ignition_injury_threshold_pa": INJURY_OVERPRESSURE_PA,
        "literature_delayed_ignition_injury_radial_distance_m": distance(
            INJURY_OVERPRESSURE_PA
        ),
        "literature_delayed_ignition_fatality_threshold_pa": FATALITY_OVERPRESSURE_PA,
        "literature_delayed_ignition_fatality_radial_distance_m": distance(
            FATALITY_OVERPRESSURE_PA
        ),
    }
