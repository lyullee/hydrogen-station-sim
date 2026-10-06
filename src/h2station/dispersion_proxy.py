"""Public-data-derived concentration proxy for the virtual detector heads.

The digital twin does not contain a CFD field solver.  This module therefore
keeps the detector proxy deliberately small and auditable: a robust coefficient
is derived from the public USN/FFI concentration traces and is multiplied by
the existing ventilation/wind envelope.  It is an advisory simulation signal,
not a detector-placement, outdoor-dispersion, or ESD validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any


ARTIFACT_RELATIVE_PATH = "research/dispersion_concentration_proxy_calibration_2026_10_06.json"
PUBLIC_SOURCE_DOI = "10.23642/usn.26117989.v2"
PUBLIC_SOURCE_LICENSE = "CC BY 4.0"

# Used only if a packaged deployment does not include the research artifact.
# The value is the median coefficient recorded by the artifact, not a tunable
# station parameter.
FALLBACK_COEFFICIENT_VOLPCT_PER_G_S = 28.449493830243835


@dataclass(frozen=True)
class DispersionProxyPolicy:
    coefficient_volpct_per_g_s: float
    source_artifact: str
    source_doi: str
    source_license: str
    status: str
    claim_limit: str
    case_count: int
    statistic: str

    def metadata(self) -> dict[str, Any]:
        return {
            "source_artifact": self.source_artifact,
            "source_doi": self.source_doi,
            "source_license": self.source_license,
            "status": self.status,
            "coefficient_volpct_per_g_s": self.coefficient_volpct_per_g_s,
            "case_count": self.case_count,
            "statistic": self.statistic,
            "formula": "clip(release_mass_flow_g_s * coefficient * ventilation_multiplier, 0, 100)",
            "claim_limit": self.claim_limit,
        }


def _artifact_path(root: Path | None = None) -> Path:
    if root is not None:
        return root / ARTIFACT_RELATIVE_PATH
    return Path(__file__).resolve().parents[2] / ARTIFACT_RELATIVE_PATH


def load_public_dispersion_proxy(root: Path | None = None) -> DispersionProxyPolicy:
    """Load a validated, precomputed public-data proxy policy.

    A malformed or missing artifact fails closed to the same recorded fallback
    coefficient and marks the result as a fallback.  It never silently loads a
    user-provided runtime tuning value.
    """

    path = _artifact_path(root)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        source = record.get("source") or {}
        method = record.get("method") or {}
        coefficient = float(method["coefficient_volpct_per_g_s"])
        case_count = int(method["case_count"])
        if (
            record.get("status") != "derived_bounded_dispersion_concentration_proxy"
            or source.get("doi") != PUBLIC_SOURCE_DOI
            or source.get("license") != PUBLIC_SOURCE_LICENSE
            or case_count < 20
            or not math.isfinite(coefficient)
            or coefficient <= 0.0
        ):
            raise ValueError("dispersion proxy artifact failed provenance checks")
        return DispersionProxyPolicy(
            coefficient_volpct_per_g_s=coefficient,
            source_artifact=ARTIFACT_RELATIVE_PATH,
            source_doi=PUBLIC_SOURCE_DOI,
            source_license=PUBLIC_SOURCE_LICENSE,
            status="PUBLIC_DISPERSION_PROXY_APPLIED",
            claim_limit=str(record.get("claim_boundary") or ""),
            case_count=case_count,
            statistic=str(method.get("statistic") or ""),
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return DispersionProxyPolicy(
            coefficient_volpct_per_g_s=FALLBACK_COEFFICIENT_VOLPCT_PER_G_S,
            source_artifact=ARTIFACT_RELATIVE_PATH,
            source_doi=PUBLIC_SOURCE_DOI,
            source_license=PUBLIC_SOURCE_LICENSE,
            status="PUBLIC_DISPERSION_PROXY_FALLBACK",
            claim_limit=(
                "The public dispersion artifact was unavailable or invalid; the "
                "recorded coefficient is retained only for deterministic advisory simulation."
            ),
            case_count=0,
            statistic="recorded fallback",
        )


PUBLIC_DISPERSION_PROXY = load_public_dispersion_proxy()


def concentration_volpct(
    mass_flow_g_s: float,
    *,
    multiplier: float = 1.0,
    policy: DispersionProxyPolicy = PUBLIC_DISPERSION_PROXY,
) -> float:
    """Convert a release rate to the bounded advisory detector concentration."""

    try:
        flow = float(mass_flow_g_s)
        scale = float(multiplier)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(flow) or not math.isfinite(scale) or flow <= 0.0 or scale <= 0.0:
        return 0.0
    return min(100.0, max(0.0, flow * policy.coefficient_volpct_per_g_s * scale))


__all__ = [
    "ARTIFACT_RELATIVE_PATH",
    "DispersionProxyPolicy",
    "FALLBACK_COEFFICIENT_VOLPCT_PER_G_S",
    "PUBLIC_DISPERSION_PROXY",
    "concentration_volpct",
    "load_public_dispersion_proxy",
]
