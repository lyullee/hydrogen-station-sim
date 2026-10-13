"""Evidence-bounded source-flow sensitivity for high-pressure H2 releases.

The runtime keeps its configured point model unchanged.  This module adds a
separate model-and-experiment envelope from the independent Proust et al. and
HyTunnel-CS campaigns so operators and LLM consumers can see when a single
discharge coefficient gives false precision.  Both intervals are sensitivity
screens, not confidence intervals, calibration, or safety-distance validation.
"""

from __future__ import annotations

import math

from ..dispenser import IsentropicRealGasRestriction, RestrictionParameters


PROUST_RELEASE_DOI = "10.1016/j.ijhydene.2010.04.055"
PROUST_RELEASE_ARTIFACT = (
    "research/proust_discharge_coefficient_sensitivity_2026_10_06.json"
)
PROUST_RELEASE_SOURCE_ID = "PROUST_25L_TERMINAL_ORIFICE"

HYTUNNEL_RELEASE_DATASET_DOI = "10.23642/USN.14405903"
HYTUNNEL_RELEASE_ARTICLE_DOI = "10.3390/en14113008"
HYTUNNEL_RELEASE_LICENSE = "CC BY 4.0"
HYTUNNEL_RELEASE_ARTIFACT = (
    "research/hytunnel_carpark_effective_cd_diagnostic_2026_10_12.json"
)
HYTUNNEL_RELEASE_SOURCE_ID = "HYTUNNEL_CS_0_5MM_BLOWDOWN"
HYTUNNEL_DIAMETER_MM = 0.5
HYTUNNEL_EFFECTIVE_CD_LOWER = 1.0041187478943512
HYTUNNEL_EFFECTIVE_CD_UPPER = 1.1309962417552797
HYTUNNEL_PRESSURE_MIN_MPA_ABS = 1.6845012465949765
HYTUNNEL_PRESSURE_MAX_MPA_ABS = 71.46548263865114
HYTUNNEL_TEMPERATURE_MIN_K = 262.1306734699999
HYTUNNEL_TEMPERATURE_MAX_K = 296.0776879419419

# P10/P90 ratios of measured flow to the frozen unit-Cd real-gas aperture
# model.  These values are post-outcome diagnostics, retained by nominal
# aperture instead of being collapsed into a fitted production coefficient.
_EFFECTIVE_CD_BY_DIAMETER_MM = (
    (1.0, 1.0217752369302118, 1.1776503580201678),
    (2.0, 0.6188402262344721, 0.7470895354225713),
    (3.0, 0.49668176848127416, 0.6530014904476614),
)


def _interpolated_effective_cd(diameter_mm: float) -> tuple[float, float]:
    """Linearly interpolate inside the campaign and clamp outside it."""

    if diameter_mm <= _EFFECTIVE_CD_BY_DIAMETER_MM[0][0]:
        return _EFFECTIVE_CD_BY_DIAMETER_MM[0][1:]
    if diameter_mm >= _EFFECTIVE_CD_BY_DIAMETER_MM[-1][0]:
        return _EFFECTIVE_CD_BY_DIAMETER_MM[-1][1:]
    for left, right in zip(
        _EFFECTIVE_CD_BY_DIAMETER_MM,
        _EFFECTIVE_CD_BY_DIAMETER_MM[1:],
    ):
        if left[0] <= diameter_mm <= right[0]:
            fraction = (diameter_mm - left[0]) / (right[0] - left[0])
            return (
                left[1] + fraction * (right[1] - left[1]),
                left[2] + fraction * (right[2] - left[2]),
            )
    raise AssertionError("unreachable aperture interpolation")


def _is_hytunnel_aperture(diameter_mm: float) -> bool:
    """Return true only for the measured 0.5 mm HyTunnel nozzle family."""

    return math.isclose(diameter_mm, HYTUNNEL_DIAMETER_MM, abs_tol=1.0e-9)


def release_flow_uncertainty_envelope(
    *,
    source_pressure_pa: float,
    source_temperature_k: float,
    ambient_pressure_pa: float,
    orifice_diameter_m: float,
    model_discharge_coefficient: float,
    point_mass_flow_kg_s: float,
    release_boundary: str,
    process_flow_limit_kg_s: float | None,
) -> dict[str, float | str | bool | None]:
    """Return an explicit public-experiment source-flow sensitivity range.

    A declared line-flow cap is authoritative for the source boundary and is
    not widened using terminal-orifice data.  Free-orifice cases retain the
    configured point estimate and combine it with the aperture-specific
    Proust P10/P90 effective-Cd range.  Outside the public campaign domain the
    nearest aperture evidence is shown only as an extrapolated sensitivity.
    """

    numeric = (
        source_pressure_pa,
        source_temperature_k,
        ambient_pressure_pa,
        orifice_diameter_m,
        model_discharge_coefficient,
        point_mass_flow_kg_s,
    )
    if not all(math.isfinite(float(value)) for value in numeric):
        raise ValueError("release-flow envelope inputs must be finite")
    if source_temperature_k <= 0.0 or ambient_pressure_pa <= 0.0:
        raise ValueError("release-flow envelope temperatures and pressures are invalid")
    if orifice_diameter_m <= 0.0 or model_discharge_coefficient <= 0.0:
        raise ValueError("release-flow envelope aperture and coefficient must be positive")

    point = max(0.0, float(point_mass_flow_kg_s))
    diameter_mm = float(orifice_diameter_m) * 1000.0
    hytunnel_aperture = _is_hytunnel_aperture(diameter_mm)
    if hytunnel_aperture:
        evidence = {
            "release_flow_evidence_source_id": HYTUNNEL_RELEASE_SOURCE_ID,
            "release_flow_evidence_doi": HYTUNNEL_RELEASE_DATASET_DOI,
            "release_flow_evidence_article_doi": HYTUNNEL_RELEASE_ARTICLE_DOI,
            "release_flow_evidence_license": HYTUNNEL_RELEASE_LICENSE,
            "release_flow_evidence_artifact": HYTUNNEL_RELEASE_ARTIFACT,
            "release_flow_empirical_diameter_mm": HYTUNNEL_DIAMETER_MM,
            "release_flow_envelope_kind": (
                "MODEL_AND_PUBLIC_ACTUAL_HYDROGEN_SENSITIVITY"
            ),
            "release_flow_claim_limit": (
                "HyTunnel-CS 0.5 mm actual-hydrogen blowdown central ranges "
                "are shown as a post-outcome source-flow sensitivity. They "
                "are not a confidence interval, fitted runtime coefficient, "
                "station leak validation, consequence distance, or safety "
                "distance. The frozen validation result remains unchanged."
            ),
        }
    else:
        evidence = {
            "release_flow_evidence_source_id": PROUST_RELEASE_SOURCE_ID,
            "release_flow_evidence_doi": PROUST_RELEASE_DOI,
            "release_flow_evidence_article_doi": PROUST_RELEASE_DOI,
            "release_flow_evidence_license": None,
            "release_flow_evidence_artifact": PROUST_RELEASE_ARTIFACT,
            "release_flow_empirical_diameter_mm": diameter_mm,
            "release_flow_envelope_kind": (
                "MODEL_AND_PUBLIC_EXPERIMENT_SENSITIVITY"
            ),
            "release_flow_claim_limit": (
                "Proust 1-3 mm digitised mass-flow evidence is shown as a "
                "model sensitivity range. It is not a confidence interval, "
                "fitted site coefficient, measured station release, or "
                "safety distance."
            ),
        }

    common: dict[str, float | str | bool | None] = {
        "release_flow_point_kg_s": point,
        "release_flow_lower_bound_kg_s": point,
        "release_flow_upper_bound_kg_s": point,
        "release_flow_lower_multiplier": 1.0 if point > 0.0 else None,
        "release_flow_upper_multiplier": 1.0 if point > 0.0 else None,
        "release_flow_model_discharge_coefficient": float(
            model_discharge_coefficient
        ),
        "release_flow_empirical_cd_lower": None,
        "release_flow_empirical_cd_upper": None,
        "release_flow_public_domain": False,
        **evidence,
    }

    if source_pressure_pa <= ambient_pressure_pa or point <= 0.0:
        return {**common, "release_flow_uncertainty_status": "NO_PRESSURIZED_RELEASE"}

    if release_boundary == "flow_limited_line":
        cap = (
            max(0.0, float(process_flow_limit_kg_s))
            if process_flow_limit_kg_s is not None
            else point
        )
        bounded = min(point, cap)
        return {
            **common,
            "release_flow_point_kg_s": bounded,
            "release_flow_lower_bound_kg_s": bounded,
            "release_flow_upper_bound_kg_s": bounded,
            "release_flow_uncertainty_status": "PROCESS_FLOW_LIMIT_PRESERVED",
            "release_flow_claim_limit": (
                "The declared process-flow cap is preserved. Public terminal-"
                "orifice coefficients are not applied to a line-limited source; "
                "line/valve uncertainty remains unquantified."
            ),
        }

    if hytunnel_aperture:
        empirical_low = HYTUNNEL_EFFECTIVE_CD_LOWER
        empirical_high = HYTUNNEL_EFFECTIVE_CD_UPPER
    else:
        empirical_low, empirical_high = _interpolated_effective_cd(diameter_mm)
    coefficient_low = min(empirical_low, float(model_discharge_coefficient))
    coefficient_high = max(empirical_high, float(model_discharge_coefficient))
    area = math.pi * float(orifice_diameter_m) ** 2 / 4.0
    unit_cd_flow = IsentropicRealGasRestriction(
        RestrictionParameters(
            flow_area_m2=area,
            discharge_coefficient=1.0,
            minimum_pressure_pa=max(1.0, float(ambient_pressure_pa)),
        )
    ).mass_flow_kg_s(
        float(source_pressure_pa),
        float(source_temperature_k),
        float(ambient_pressure_pa),
    )
    lower = min(point, unit_cd_flow * coefficient_low)
    upper = max(point, unit_cd_flow * coefficient_high)
    if hytunnel_aperture:
        in_domain = (
            HYTUNNEL_PRESSURE_MIN_MPA_ABS * 1.0e6
            <= source_pressure_pa
            <= HYTUNNEL_PRESSURE_MAX_MPA_ABS * 1.0e6
            and HYTUNNEL_TEMPERATURE_MIN_K
            <= source_temperature_k
            <= HYTUNNEL_TEMPERATURE_MAX_K
        )
        in_domain_status = "PUBLIC_ACTUAL_HYDROGEN_ENVELOPE_IN_DOMAIN"
        extrapolated_status = (
            "PUBLIC_ACTUAL_HYDROGEN_ENVELOPE_EXTRAPOLATED"
        )
    else:
        in_domain = (
            1.0 <= diameter_mm <= 3.0
            and 10.0e6 <= source_pressure_pa <= 90.0e6
            and 220.0 <= source_temperature_k <= 330.0
        )
        in_domain_status = "PUBLIC_EXPERIMENT_ENVELOPE_IN_DOMAIN"
        extrapolated_status = "PUBLIC_EXPERIMENT_ENVELOPE_EXTRAPOLATED"
    return {
        **common,
        "release_flow_lower_bound_kg_s": lower,
        "release_flow_upper_bound_kg_s": upper,
        "release_flow_lower_multiplier": lower / point,
        "release_flow_upper_multiplier": upper / point,
        "release_flow_empirical_cd_lower": empirical_low,
        "release_flow_empirical_cd_upper": empirical_high,
        "release_flow_public_domain": in_domain,
        "release_flow_uncertainty_status": (
            in_domain_status if in_domain else extrapolated_status
        ),
    }
