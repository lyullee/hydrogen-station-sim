"""Claim-bounded literature comparison for hydrogen jet-flame length.

Molkov and Saffers (2011) restate the dimensional correlation
``L_F = 76 (m_dot d_N)^0.347`` and assess hydrogen jet-fire experiments
covering buoyant through highly under-expanded releases.  This module uses
the physical release diameter and the mass flow actually carried into the
consequence calculation.  It is a flame-length comparison, not a thermal
harm, separation, or evacuation distance.
"""

from __future__ import annotations

import math
from typing import Final


MOLKOV_SAFFERS_DOI: Final[str] = "10.3801/IAFSS.FSS.10-933"
MOLKOV_SAFFERS_SOURCE_URL: Final[str] = (
    "https://doi.org/10.3801/IAFSS.FSS.10-933"
)

# Published overall experiment envelope.  The mass-flow bounds below are the
# narrower, directly transcribed high-pressure Table 1 subset used by this
# project's implementation benchmark; using them prevents the UI from calling
# an untested runtime point "validated" merely because its diameter is in range.
PUBLICATION_MIN_DIAMETER_M: Final[float] = 0.4e-3
PUBLICATION_MAX_DIAMETER_M: Final[float] = 51.7e-3
PUBLICATION_MAX_STORAGE_PRESSURE_PA: Final[float] = 90.0e6
BENCHMARK_MIN_DIAMETER_M: Final[float] = 1.0e-3
BENCHMARK_MAX_DIAMETER_M: Final[float] = 7.94e-3
BENCHMARK_MIN_MASS_FLOW_KG_S: Final[float] = 1.1e-3
BENCHMARK_MAX_MASS_FLOW_KG_S: Final[float] = 0.360


def _positive_finite(name: str, value: float) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return parsed


def jet_flame_length_m(
    mass_flow_kg_s: float,
    release_diameter_m: float,
) -> float:
    """Return the Molkov dimensional-correlation visible flame length."""

    mass_flow = _positive_finite("mass_flow_kg_s", mass_flow_kg_s)
    diameter = _positive_finite("release_diameter_m", release_diameter_m)
    return 76.0 * (mass_flow * diameter) ** 0.347


def jet_flame_envelope(
    *,
    mass_flow_kg_s: float,
    release_diameter_m: float,
    storage_pressure_pa: float | None = None,
    mass_flow_basis: str = "MODELED_CONSEQUENCE_FLOW",
) -> dict[str, float | str | bool | None]:
    """Return a bounded literature flame-length comparison for a release."""

    flow = float(mass_flow_kg_s)
    diameter = _positive_finite("release_diameter_m", release_diameter_m)
    if not math.isfinite(flow) or flow < 0.0:
        raise ValueError("mass_flow_kg_s must be non-negative and finite")
    pressure = None if storage_pressure_pa is None else _positive_finite(
        "storage_pressure_pa", storage_pressure_pa
    )
    base: dict[str, float | str | bool | None] = {
        "literature_jet_flame_model": "MOLKOV_2009_DIMENSIONAL_CORRELATION_RESTATED_2011",
        "literature_jet_flame_doi": MOLKOV_SAFFERS_DOI,
        "literature_jet_flame_source_url": MOLKOV_SAFFERS_SOURCE_URL,
        "literature_jet_flame_experiment_count": 123.0,
        "literature_jet_flame_mass_flow_basis": str(mass_flow_basis),
        "literature_jet_flame_is_harm_distance": False,
        "literature_jet_flame_publication_diameter_domain_mm": "0.4-51.7",
        "literature_jet_flame_publication_pressure_domain_mpa": "near-atmospheric-90",
        "literature_jet_flame_benchmark_mass_flow_domain_g_s": "1.1-360",
        "literature_jet_flame_benchmark_diameter_domain_mm": "1-7.94",
        "literature_jet_flame_geometry": "FREE_JET_IN_STILL_AIR",
        "literature_jet_flame_claim_limit": (
            "정지 공기 중 비예혼합 자유 수소 제트의 가시 화염길이 문헌 비교값입니다. "
            "열복사 피해거리·안전거리·대피거리가 아니며 충돌제트, 장애물, 바람, "
            "밀폐·반밀폐 공간과 화염 방향은 반영하지 않습니다."
        ),
    }
    if flow == 0.0:
        return {
            **base,
            "literature_jet_flame_status": "NOT_ACTIVE_NO_RELEASE",
            "literature_jet_flame_in_validation_domain": False,
            "literature_jet_flame_length_m": 0.0,
        }

    in_benchmark_domain = (
        BENCHMARK_MIN_MASS_FLOW_KG_S <= flow <= BENCHMARK_MAX_MASS_FLOW_KG_S
        and BENCHMARK_MIN_DIAMETER_M <= diameter <= BENCHMARK_MAX_DIAMETER_M
        and (pressure is None or pressure <= PUBLICATION_MAX_STORAGE_PRESSURE_PA)
    )
    return {
        **base,
        "literature_jet_flame_status": (
            "CALCULATED_IN_VALIDATION_DOMAIN"
            if in_benchmark_domain
            else "CALCULATED_EXTRAPOLATED"
        ),
        "literature_jet_flame_in_validation_domain": in_benchmark_domain,
        "literature_jet_flame_length_m": jet_flame_length_m(flow, diameter),
    }
