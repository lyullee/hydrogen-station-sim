"""Frozen development candidate for a future spatial detector holdout.

The coefficients in this module were selected after outcomes from the public
HyTunnel-CS actual-hydrogen and H2SAFE helium-surrogate cohorts were visible.
Consequently this is a *prospective candidate*, not validation evidence.  It
is deliberately absent from the API and HAZOP runtime import graph.  A new,
untouched actual-hydrogen cohort must pass the frozen protocol before runtime
use may be considered.

The score is a rank-only geometric heuristic.  It does not predict hydrogen
concentration, alarm time, flammable volume, or a safety distance.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .spatial_detector import Point3D


@dataclass(frozen=True)
class ProspectiveSpatialRankParameters:
    """Fixed coefficients for the post-outcome pooled candidate."""

    upward_vertical_weight: float = 0.3
    downward_vertical_penalty: float = 0.1
    vertical_denominator_weight: float = 0.2
    denominator_power: float = 1.0
    horizontal_distance_power: float = 1.25
    denominator_offset: float = 0.25


FROZEN_PARAMETERS = ProspectiveSpatialRankParameters()


def _finite_point(name: str, point: Point3D) -> None:
    if not all(math.isfinite(value) for value in (point.x, point.y, point.z)):
        raise ValueError(f"{name} coordinates must be finite")


def prospective_spatial_rank_score(source: Point3D, detector: Point3D) -> float:
    """Return the frozen rank score with ``y`` declared as elevation.

    Coordinates must be expressed in metres in one common Cartesian frame.
    The returned value is meaningful only for ordering sensors within a case.
    It must not be interpreted as a concentration or probability.
    """

    _finite_point("source", source)
    _finite_point("detector", detector)
    p = FROZEN_PARAMETERS
    vertical = detector.y - source.y
    horizontal = math.hypot(detector.x - source.x, detector.z - source.z)
    numerator = math.exp(
        p.upward_vertical_weight * max(vertical, 0.0)
        - p.downward_vertical_penalty * max(-vertical, 0.0)
    )
    denominator = (
        p.denominator_offset
        + horizontal**p.horizontal_distance_power
        + p.vertical_denominator_weight * abs(vertical)
    ) ** p.denominator_power
    score = numerator / denominator
    if not math.isfinite(score) or score <= 0.0:
        raise ValueError("prospective spatial rank score is not finite and positive")
    return score


def prospective_spatial_rank_metadata() -> dict[str, object]:
    """Return claim-bounded metadata for reports and future protocols."""

    return {
        "candidate_id": "pooled_spatial_rank_v1",
        "status": "POST_OUTCOME_DEVELOPMENT_ONLY_NOT_RUNTIME",
        "vertical_axis": "y",
        "coordinate_unit": "m",
        "parameters": {
            field: getattr(FROZEN_PARAMETERS, field)
            for field in FROZEN_PARAMETERS.__dataclass_fields__
        },
        "permitted_use": "rank sensors within a future frozen holdout case",
        "prohibited_uses": [
            "runtime detector routing",
            "hydrogen concentration prediction",
            "alarm or trip setpoint calibration",
            "flammable volume or safety-distance prediction",
            "CFD or ESD validation",
        ],
    }


__all__ = [
    "FROZEN_PARAMETERS",
    "ProspectiveSpatialRankParameters",
    "prospective_spatial_rank_metadata",
    "prospective_spatial_rank_score",
]
