"""Bounded empirical screening from public HyDelta cabinet experiments.

This module deliberately does not fit a concentration model.  The public
report provides ten table-level cases rather than machine-readable time
series.  Eight non-indicative cases define two exact cabinet families.  A
runtime case is therefore reported only as an exact measurement or as the
bracket formed by adjacent measurements in the same cabinet family.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


HYDELTA_VENTILATION_DOI = "10.5281/zenodo.8164602"
HYDELTA_VENTILATION_ARTIFACT = (
    "research/hydelta_natural_ventilation_evidence_2026_10_13.json"
)
HYDROGEN_NORMAL_DENSITY_KG_M3 = 0.08988
HYDROGEN_LFL_VOLPCT = 4.0


@dataclass(frozen=True, slots=True)
class CabinetVentilationCase:
    """One non-indicative report-table measurement."""

    cabinet_volume_m3: float
    hydrogen_flow_nm3_h: float
    maximum_inside_volpct_h2: float
    maximum_vent_opening_volpct_h2: float
    flammable_mixture_observed: bool


_CASES = (
    CabinetVentilationCase(0.5, 0.125, 2.9, 3.2, False),
    CabinetVentilationCase(0.5, 0.558, 6.9, 6.4, True),
    CabinetVentilationCase(0.5, 1.25, 11.0, 11.0, True),
    CabinetVentilationCase(0.5, 5.8, 24.0, 21.0, True),
    CabinetVentilationCase(4.0, 0.125, 1.0, 0.4, False),
    CabinetVentilationCase(4.0, 0.558, 2.2, 1.3, False),
    CabinetVentilationCase(4.0, 1.25, 5.5, 4.1, True),
    CabinetVentilationCase(4.0, 5.8, 12.0, 9.3, True),
)
_SUPPORTED_VOLUMES_M3 = (0.5, 4.0)
_CLAIM_LIMIT = (
    "HyDelta 저압 가스 정압기 캐비닛의 실제 수소 표 측정값을 같은 체적·유량 구간에서 "
    "대조한 경험적 스크리닝입니다. 농도를 보간·예측하지 않으며 H70 분산, 검지기 배치, "
    "경보 설정, ESD 효과, 현장 안전·대피거리 또는 안전상태 선언을 검증하지 않습니다."
)


def _base_result(
    enclosure_volume_m3: float | None,
    hydrogen_flow_nm3_h: float | None,
) -> dict[str, float | str | bool | None]:
    return {
        "cabinet_ventilation_screen_status": "NOT_EVALUATED",
        "cabinet_ventilation_public_domain": False,
        "cabinet_ventilation_volume_m3": enclosure_volume_m3,
        "cabinet_ventilation_input_flow_nm3_h": hydrogen_flow_nm3_h,
        "cabinet_ventilation_source_lfl_volpct_h2": HYDROGEN_LFL_VOLPCT,
        "cabinet_ventilation_basis": "HYDELTA_REPORT_TABLE_NO_INTERPOLATION",
        "cabinet_ventilation_classification": "NOT_EVALUATED",
        "cabinet_ventilation_requires_measured_clearance": True,
        "cabinet_ventilation_safety_clearance_authorized": False,
        "cabinet_ventilation_evidence_doi": HYDELTA_VENTILATION_DOI,
        "cabinet_ventilation_evidence_license": "CC BY 4.0",
        "cabinet_ventilation_evidence_artifact": HYDELTA_VENTILATION_ARTIFACT,
        "cabinet_ventilation_claim_limit": _CLAIM_LIMIT,
    }


def cabinet_ventilation_empirical_screen(
    *,
    enclosure_volume_m3: float | None,
    mass_flow_kg_s: float | None,
) -> dict[str, float | str | bool | None]:
    """Return an exact-case or adjacent-case HyDelta measurement bracket.

    ``mass_flow_kg_s`` is converted to normal cubic metres per hour solely to
    select the public report-table row.  No concentration interpolation or
    extrapolation is performed.  Unsupported cabinet volumes and flows return
    an explicit out-of-domain status with no measured concentration fields.
    """

    normal_flow = None
    if mass_flow_kg_s is not None and math.isfinite(float(mass_flow_kg_s)):
        normal_flow = (
            float(mass_flow_kg_s)
            * 3600.0
            / HYDROGEN_NORMAL_DENSITY_KG_M3
        )
    result = _base_result(enclosure_volume_m3, normal_flow)

    if (
        enclosure_volume_m3 is None
        or not math.isfinite(float(enclosure_volume_m3))
        or float(enclosure_volume_m3) <= 0.0
    ):
        result["cabinet_ventilation_screen_status"] = (
            "ENCLOSURE_VOLUME_NOT_CONFIGURED"
        )
        return result
    if normal_flow is None or normal_flow < 0.0:
        result["cabinet_ventilation_screen_status"] = "INVALID_RELEASE_FLOW"
        return result

    volume = next(
        (
            candidate
            for candidate in _SUPPORTED_VOLUMES_M3
            if math.isclose(
                float(enclosure_volume_m3), candidate, rel_tol=0.0, abs_tol=1.0e-6
            )
        ),
        None,
    )
    if volume is None:
        result["cabinet_ventilation_screen_status"] = (
            "OUTSIDE_PUBLIC_CABINET_VOLUME_DOMAIN"
        )
        return result

    cases = tuple(case for case in _CASES if case.cabinet_volume_m3 == volume)
    minimum_flow = cases[0].hydrogen_flow_nm3_h
    maximum_flow = cases[-1].hydrogen_flow_nm3_h
    if math.isclose(normal_flow, minimum_flow, rel_tol=1.0e-9, abs_tol=1.0e-9):
        normal_flow = minimum_flow
        result["cabinet_ventilation_input_flow_nm3_h"] = normal_flow
    elif math.isclose(
        normal_flow, maximum_flow, rel_tol=1.0e-9, abs_tol=1.0e-9
    ):
        normal_flow = maximum_flow
        result["cabinet_ventilation_input_flow_nm3_h"] = normal_flow
    if normal_flow < minimum_flow or normal_flow > maximum_flow:
        result["cabinet_ventilation_screen_status"] = (
            "OUTSIDE_PUBLIC_RELEASE_FLOW_DOMAIN"
        )
        result["cabinet_ventilation_domain_min_flow_nm3_h"] = minimum_flow
        result["cabinet_ventilation_domain_max_flow_nm3_h"] = maximum_flow
        return result

    exact = next(
        (
            case
            for case in cases
            if math.isclose(
                normal_flow,
                case.hydrogen_flow_nm3_h,
                rel_tol=1.0e-9,
                abs_tol=1.0e-9,
            )
        ),
        None,
    )
    if exact is not None:
        lower = upper = exact
        status = "EXACT_MEASURED_CASE"
        basis = "HYDELTA_REPORT_TABLE_EXACT_CASE"
        classification = (
            "FLAMMABLE_MIXTURE_REPORTED"
            if exact.flammable_mixture_observed
            else "BELOW_SOURCE_LFL_IN_REPORTED_CASE"
        )
    else:
        lower = max(
            (case for case in cases if case.hydrogen_flow_nm3_h < normal_flow),
            key=lambda case: case.hydrogen_flow_nm3_h,
        )
        upper = min(
            (case for case in cases if case.hydrogen_flow_nm3_h > normal_flow),
            key=lambda case: case.hydrogen_flow_nm3_h,
        )
        status = "BRACKETED_MEASURED_CASES"
        basis = "HYDELTA_REPORT_TABLE_ADJACENT_BRACKET_NO_INTERPOLATION"
        if lower.flammable_mixture_observed and upper.flammable_mixture_observed:
            classification = "FLAMMABLE_MIXTURE_REPORTED_AT_BOTH_BRACKETS"
        elif (
            not lower.flammable_mixture_observed
            and not upper.flammable_mixture_observed
        ):
            classification = "BELOW_SOURCE_LFL_AT_BOTH_BRACKETS"
        else:
            classification = "LFL_TRANSITION_BETWEEN_MEASURED_BRACKETS"

    result.update(
        {
            "cabinet_ventilation_screen_status": status,
            "cabinet_ventilation_public_domain": True,
            "cabinet_ventilation_volume_m3": volume,
            "cabinet_ventilation_basis": basis,
            "cabinet_ventilation_classification": classification,
            "cabinet_ventilation_lower_flow_nm3_h": lower.hydrogen_flow_nm3_h,
            "cabinet_ventilation_upper_flow_nm3_h": upper.hydrogen_flow_nm3_h,
            "cabinet_ventilation_lower_max_inside_volpct_h2": (
                lower.maximum_inside_volpct_h2
            ),
            "cabinet_ventilation_upper_max_inside_volpct_h2": (
                upper.maximum_inside_volpct_h2
            ),
            "cabinet_ventilation_lower_max_vent_volpct_h2": (
                lower.maximum_vent_opening_volpct_h2
            ),
            "cabinet_ventilation_upper_max_vent_volpct_h2": (
                upper.maximum_vent_opening_volpct_h2
            ),
            "cabinet_ventilation_lower_flammable_observed": (
                lower.flammable_mixture_observed
            ),
            "cabinet_ventilation_upper_flammable_observed": (
                upper.flammable_mixture_observed
            ),
        }
    )
    return result


__all__ = [
    "CabinetVentilationCase",
    "HYDELTA_VENTILATION_ARTIFACT",
    "HYDELTA_VENTILATION_DOI",
    "HYDROGEN_NORMAL_DENSITY_KG_M3",
    "cabinet_ventilation_empirical_screen",
]
