"""Post-access spatial detector candidates kept outside the runtime model.

This module is intentionally separate from :mod:`spatial_detector`.  The
runtime module's frozen hash is used by the independent HyTunnel holdout, so a
development candidate must not change that file until a new pre-access cohort
has been evaluated.  Nothing in the API imports this module for alarm routing.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from .spatial_detector import Point3D, orientation_aware_geometry_score


@dataclass(frozen=True)
class VentilationVector:
    """Declared local air-flow vector in the release/detector coordinate frame."""

    direction: Point3D
    speed_m_s: float
    area_m2: float | None = None


@dataclass(frozen=True)
class ObstructionBox:
    """Axis-aligned equipment/wall volume for a development visibility term."""

    minimum: Point3D
    maximum: Point3D


def directional_obstruction_geometry_score(
    source: Point3D,
    detector: Point3D,
    release_orientation: str,
    *,
    release_direction: Point3D | None = None,
    ventilation: tuple[VentilationVector, ...] = (),
    obstructions: tuple[ObstructionBox, ...] = (),
) -> float:
    """Return a transparent, non-fitted spatial development score.

    The score adds three declared physical cues to the frozen orientation
    candidate: a release-jet direction, same-frame ventilation velocity and
    segment intersections with equipment/walls. Coefficients are fixed design
    priors, not fitted to H2SAFE outcomes. The helper is not used by runtime
    detector routing and is not CFD or a concentration model.
    """

    base = orientation_aware_geometry_score(source, detector, release_orientation)
    displacement = Point3D(
        detector.x - source.x,
        detector.y - source.y,
        detector.z - source.z,
    )
    distance = math.sqrt(
        displacement.x * displacement.x
        + displacement.y * displacement.y
        + displacement.z * displacement.z
    )
    if distance <= 1e-12:
        return base

    def _unit(point: Point3D) -> Point3D | None:
        magnitude = math.sqrt(point.x * point.x + point.y * point.y + point.z * point.z)
        if magnitude <= 1e-12:
            return None
        return Point3D(point.x / magnitude, point.y / magnitude, point.z / magnitude)

    target_direction = _unit(displacement)
    direction_factor = 1.0
    release_unit = _unit(release_direction) if release_direction is not None else None
    if release_unit is not None and target_direction is not None:
        alignment = max(
            0.0,
            release_unit.x * target_direction.x
            + release_unit.y * target_direction.y
            + release_unit.z * target_direction.z,
        )
        direction_factor += 0.75 * alignment * math.exp(-distance / 10.0)

    ventilation_factor = 1.0
    if target_direction is not None:
        for field in ventilation:
            vent_unit = _unit(field.direction)
            speed = max(0.0, float(field.speed_m_s))
            if vent_unit is None or speed == 0.0:
                continue
            alignment = max(
                0.0,
                vent_unit.x * target_direction.x
                + vent_unit.y * target_direction.y
                + vent_unit.z * target_direction.z,
            )
            ventilation_factor *= 1.0 + 0.25 * min(speed / 5.0, 1.0) * alignment

    def _segment_intersects(box: ObstructionBox) -> bool:
        lo = (
            min(box.minimum.x, box.maximum.x),
            min(box.minimum.y, box.maximum.y),
            min(box.minimum.z, box.maximum.z),
        )
        hi = (
            max(box.minimum.x, box.maximum.x),
            max(box.minimum.y, box.maximum.y),
            max(box.minimum.z, box.maximum.z),
        )
        start = (source.x, source.y, source.z)
        delta = (displacement.x, displacement.y, displacement.z)
        t_min, t_max = 0.0, 1.0
        for axis in range(3):
            if abs(delta[axis]) <= 1e-12:
                if start[axis] < lo[axis] or start[axis] > hi[axis]:
                    return False
                continue
            t1 = (lo[axis] - start[axis]) / delta[axis]
            t2 = (hi[axis] - start[axis]) / delta[axis]
            t_low, t_high = min(t1, t2), max(t1, t2)
            t_min, t_max = max(t_min, t_low), min(t_max, t_high)
            if t_min > t_max:
                return False
        return True

    obstruction_count = sum(_segment_intersects(box) for box in obstructions)
    obstruction_factor = 0.6 ** obstruction_count
    return base * direction_factor * ventilation_factor * obstruction_factor


__all__ = [
    "ObstructionBox",
    "VentilationVector",
    "directional_obstruction_geometry_score",
]
