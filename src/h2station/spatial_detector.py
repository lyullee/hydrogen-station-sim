"""Geometry-ranked virtual gas-detector development diagnostic.

The station does not solve a transient CFD concentration field.  This module
therefore limits itself to selecting the two detector heads most plausibly
exposed by a release.  The concentration magnitude and alarm policy remain in
``dispersion_proxy`` and ``detector_policy`` respectively.

The rank law was frozen before the public H2SAFE helium-surrogate traces were
opened.  A post-access screen showed useful, but incomplete, transfer: the
coordinate convention with Y as elevation improved four of five experiments,
while the horizontal-release case remained a clear failure.  The failed law is
not used to route runtime alarms; it remains available for a reproducible
diagnostic and for testing coordinate consistency.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


H2SAFE_DOI = "10.7799/17118570"
H2SAFE_DIAGNOSTIC_ARTIFACT = (
    "research/h2safe_spatial_response_diagnostic_2026_10_08.json"
)
H2SAFE_ORIENTATION_DEVELOPMENT_ARTIFACT = (
    "research/h2safe_orientation_development_2026_10_08.json"
)


@dataclass(frozen=True)
class Point3D:
    x: float
    y: float
    z: float


# These are the same station-local coordinates rendered in web/station3d.js.
# Y is elevation in both the station scene and the H2SAFE coordinate files.
DETECTOR_POSITIONS: Mapping[str, Point3D] = {
    "GD-0101": Point3D(-22.0, 2.70, 5.00),
    "GD-0201": Point3D(-22.0, 2.50, -8.00),
    "GD-0601": Point3D(-6.0, 2.80, -4.00),
    "GD-0701": Point3D(-2.0, 2.70, -5.00),
    "GD-0801": Point3D(1.0, 2.70, -5.00),
    "GD-0901": Point3D(5.0, 2.70, -5.00),
    "GD-1001": Point3D(8.0, 2.70, -3.00),
    "GD-1301": Point3D(0.0, 4.66, 4.25),
    "GD-1701": Point3D(8.0, 4.66, 4.25),
    "GD-1901": Point3D(11.0, 2.70, -4.00),
    "GD-2001": Point3D(12.0, 2.80, -3.00),
    "GD-2101": Point3D(-6.0, 3.80, -3.00),
    "GD-2201": Point3D(3.0, 3.70, -5.00),
    "GD-2301": Point3D(4.0, 4.70, 4.00),
    "GD-2302": Point3D(11.0, 3.50, -4.00),
}


# Release origins are equipment centres/nozzle regions in the same scene frame.
# They are intentionally coarse and are exposed in metadata as unvalidated.
SOURCE_POSITIONS: Mapping[str, Point3D] = {
    "supply": Point3D(-22.0, 1.0, 5.0),
    "unloading": Point3D(-22.0, 1.0, -8.0),
    "compressor": Point3D(-6.0, 1.0, -4.0),
    "cascade.low": Point3D(-2.0, 1.0, -5.0),
    "cascade.medium": Point3D(1.0, 1.0, -5.0),
    "cascade.high": Point3D(5.0, 1.0, -5.0),
    "header": Point3D(8.0, 1.0, -3.0),
    "pcv": Point3D(0.0, 1.0, 4.0),
    "dispenser.hose": Point3D(0.0, 1.0, 4.0),
    "dispenser_2.hose": Point3D(8.0, 1.0, 4.0),
    "vehicle.tank": Point3D(0.0, 1.0, 4.0),
    "vehicle_2.tank": Point3D(8.0, 1.0, 4.0),
    "dispenser": Point3D(0.0, 1.0, 4.0),
    "dispenser_2": Point3D(8.0, 1.0, 4.0),
    "cooler": Point3D(11.0, 1.0, -4.0),
    "vent": Point3D(12.0, 2.5, -3.0),
}


def geometry_score(source: Point3D, detector: Point3D) -> float:
    """Return the frozen buoyant-gas rank score using Y as elevation."""

    vertical = detector.y - source.y
    horizontal = math.hypot(detector.x - source.x, detector.z - source.z)
    return math.exp(
        0.7 * max(vertical, 0.0) - 1.2 * max(-vertical, 0.0)
    ) / (0.25 + horizontal * horizontal + 0.35 * abs(vertical))


def orientation_aware_geometry_score(
    source: Point3D,
    detector: Point3D,
    release_orientation: str,
) -> float:
    """Return the fixed post-access orientation-class development score.

    A vertical release keeps the original buoyant ranking.  A horizontal
    release with unknown azimuth is treated as direction-marginalized: sensor
    height separation is penalized symmetrically rather than being rewarded
    simply because the detector is above the source.  The public H2SAFE
    package declares ``horizontal`` versus ``vertical`` but not the horizontal
    nozzle vector, so this function intentionally does not invent an azimuth.

    This candidate was selected after H2SAFE outcomes had been opened.  It is
    available for reproducible development and a future pre-access holdout;
    it must not be used to claim independent validation or route runtime
    detector alarms.
    """

    orientation = str(release_orientation or "").strip().lower()
    if orientation == "vertical":
        return geometry_score(source, detector)
    if orientation != "horizontal":
        raise ValueError("release_orientation must be 'vertical' or 'horizontal'")
    vertical = detector.y - source.y
    horizontal = math.hypot(detector.x - source.x, detector.z - source.z)
    return math.exp(-0.5 * abs(vertical)) / (
        0.25 + horizontal * horizontal + 0.35 * abs(vertical)
    )


def source_key_for_target(target: str) -> str:
    normalized = str(target or "").strip().lower()
    matches = [
        key
        for key in SOURCE_POSITIONS
        if normalized == key or normalized.startswith(key + ".")
    ]
    return max(matches, key=len, default="header")


def ranked_detector_tags(target: str) -> tuple[str, ...]:
    source = SOURCE_POSITIONS[source_key_for_target(target)]
    ranked = sorted(
        DETECTOR_POSITIONS,
        key=lambda tag: (-geometry_score(source, DETECTOR_POSITIONS[tag]), tag),
    )
    return tuple(ranked)


def detector_weights(target: str) -> dict[str, float]:
    """Return diagnostic-only top-two weights for a station target.

    Runtime code must not call this helper while the joint H2SAFE screen remains
    failed.  The first and second heads retain the existing 1.0/0.45 multipliers,
    and no numerical H2SAFE amplitude is fitted or transferred from helium data.
    """

    ranked = ranked_detector_tags(target)
    return {ranked[0]: 1.0, ranked[1]: 0.45}


def spatial_proxy_metadata() -> dict[str, object]:
    return {
        "status": "EVALUATED_NOT_APPLIED_FAILED_JOINT_SCREEN",
        "source_doi": H2SAFE_DOI,
        "diagnostic_artifact": H2SAFE_DIAGNOSTIC_ARTIFACT,
        "vertical_axis": "Y",
        "rank_formula": (
            "exp(0.7*max(dy,0)-1.2*max(-dy,0)) / "
            "(0.25 + horizontal_distance_m^2 + 0.35*abs(dy))"
        ),
        "runtime_application": False,
        "orientation_development_candidate": {
            "status": "POST_ACCESS_DEVELOPMENT_ONLY_NOT_RUNTIME",
            "artifact": H2SAFE_ORIENTATION_DEVELOPMENT_ARTIFACT,
            "runtime_application": False,
        },
        "amplitude_policy": "not applied; existing zone mapping and amplitudes retained",
        "claim_limit": (
            "Post-access helium-surrogate screening did not pass all frozen spatial screens, "
            "so the coordinate-only ranking is not used for runtime detector routing and is "
            "not CFD, H2 concentration, detector placement, alarm-setpoint or ESD validation."
        ),
    }


__all__ = [
    "DETECTOR_POSITIONS",
    "SOURCE_POSITIONS",
    "Point3D",
    "detector_weights",
    "geometry_score",
    "orientation_aware_geometry_score",
    "ranked_detector_tags",
    "source_key_for_target",
    "spatial_proxy_metadata",
]
