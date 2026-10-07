"""Bounded public calibration for the reference Type-IV vehicle tank.

The virtual station uses a 4.7 kg / 70 MPa Type-IV surrogate by default.  A
public, frozen split of laboratory fills is available for that tank model when
*measured* mass-flow and inlet-temperature histories are its boundaries.  The
profile in this module deliberately affects only the two validated tank
parameters; it must not be read as a calibration of the compressor, cascade,
dispenser, protocol controller, or a real vehicle.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import math
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2]
_PROFILE_PATH = _ROOT / "research" / "tank_model_validation_v2.json"
_LIMITS = {
    "pressure_rmse_mpa": 5.0,
    "temperature_rmse_c": 10.0,
    "soc_rmse_percentage_points": 5.0,
}


@dataclass(frozen=True)
class PublicTypeIVTankCalibrationProfile:
    """Two public tank-fit values and their narrow validation boundary."""

    effective_volume_multiplier: float
    gas_liner_ua_multiplier: float
    validation_case_count: int
    validation_metrics: dict[str, float]
    evidence_artifact: str

    def runtime_metadata(self) -> dict[str, object]:
        return {
            "status": "active",
            "id": "public_type_iv_tank_v1",
            "evidence_artifact": self.evidence_artifact,
            "effective_volume_multiplier": self.effective_volume_multiplier,
            "gas_liner_ua_multiplier": self.gas_liner_ua_multiplier,
            "validation_case_count": self.validation_case_count,
            "validation_mean_metrics": dict(self.validation_metrics),
            "validation_boundary": (
                "Public Type-IV tank-only validation with measured mass-flow "
                "and inlet-temperature boundaries; not station-to-vehicle, "
                "controller, dispenser, field-safety, or vehicle certification."
            ),
        }


@lru_cache(maxsize=1)
def load_public_type_iv_tank_calibration(
    path: Path | None = None,
) -> PublicTypeIVTankCalibrationProfile | None:
    """Load only a passing, frozen public Type-IV tank calibration profile.

    The strict reader makes a missing or degraded evidence artifact fail
    closed.  The caller can then choose the transparent reference profile
    instead of silently using unverifiable fitted values.
    """

    candidate = path or _PROFILE_PATH
    try:
        record = json.loads(candidate.read_text(encoding="utf-8"))
        fit = record["fit"]
        validation = record["validation"]
        effective_volume_multiplier = float(fit["effective_volume_multiplier"])
        gas_liner_ua_multiplier = float(fit["gas_liner_ua_multiplier"])
        validation_case_count = int(validation["case_count"])
        metrics = {
            key: float(validation[key]["mean"])
            for key in _LIMITS
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None

    if (
        record.get("scope")
        != "Type-IV tank model with measured mass-flow and inlet-temperature boundaries"
        or record.get("split_rule") != "validation when lab_test_number modulo 3 equals 0"
        or record.get("experimental_quality_screen_applied") is not True
        or fit.get("optimizer_success") is not True
        or validation_case_count < 10
        or not all(math.isfinite(value) and value > 0.0 for value in (
            effective_volume_multiplier,
            gas_liner_ua_multiplier,
            *metrics.values(),
        ))
        or any(metrics[key] > limit for key, limit in _LIMITS.items())
    ):
        return None

    try:
        artifact = candidate.relative_to(_ROOT).as_posix()
    except ValueError:
        artifact = candidate.name
    return PublicTypeIVTankCalibrationProfile(
        effective_volume_multiplier=effective_volume_multiplier,
        gas_liner_ua_multiplier=gas_liner_ua_multiplier,
        validation_case_count=validation_case_count,
        validation_metrics=metrics,
        evidence_artifact=artifact,
    )
