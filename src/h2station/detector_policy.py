"""Data-backed detector threshold policy for the virtual safety PLC.

The public detector replay is deliberately limited to threshold/persistence
logic.  It does not calibrate dispersion, detector placement, or ESD response.
This module makes that boundary explicit while allowing the runtime to use the
same rule that was replayed against the public concentration traces.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DetectorPolicy:
    """Alarm/trip rule plus provenance for a virtual detector policy."""

    alarm_volume_fraction: float
    trip_volume_fraction: float
    persistence_s: float
    source_artifact: str
    source_doi: str
    source_license: str
    evidence_status: str
    claim_limit: str

    @property
    def alarm_threshold_volpct_h2(self) -> float:
        return self.alarm_volume_fraction * 100.0

    @property
    def trip_threshold_volpct_h2(self) -> float:
        return self.trip_volume_fraction * 100.0


_DEFAULT_POLICY = DetectorPolicy(
    alarm_volume_fraction=0.01,
    trip_volume_fraction=0.02,
    persistence_s=0.5,
    source_artifact="runtime safety defaults",
    source_doi="",
    source_license="",
    evidence_status="DEFAULT_FALLBACK",
    claim_limit=(
        "공개 검지기 재현 기록이 없을 때의 보수적 기본값이며, "
        "현장 검지기 응답·배치·ESD 효과를 검증하지 않음"
    ),
)


def _valid_number(value: object, *, minimum: float = 0.0) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= minimum:
        return None
    return number


def load_public_detector_policy(root: Path | None = None) -> DetectorPolicy:
    """Load the frozen public detector rule, falling back safely if absent.

    The record is accepted only when its status, licence and rule fields are
    intact.  No values are fitted to the station simulation or changed based
    on an individual case.
    """

    project_root = root or Path(__file__).resolve().parents[2]
    path = project_root / "research/dispersion_detector_logic_validation.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return _DEFAULT_POLICY
    if (
        record.get("status") != "completed_bounded_instrumented_detector_logic_evidence"
        or record.get("evidence_role") != "instrumented_detector_logic_evidence"
    ):
        return _DEFAULT_POLICY
    source = record.get("source") or {}
    if source.get("license") != "CC BY 4.0" or not source.get("doi"):
        return _DEFAULT_POLICY
    rule = record.get("rule") or {}
    alarm_pct = _valid_number(rule.get("alarm_threshold_percent"))
    trip_pct = _valid_number(rule.get("trip_threshold_percent"))
    persistence_s = _valid_number(rule.get("persistence_s"), minimum=-1.0)
    if alarm_pct is None or trip_pct is None or persistence_s is None:
        return _DEFAULT_POLICY
    if alarm_pct >= trip_pct or persistence_s < 0.0:
        return _DEFAULT_POLICY
    return DetectorPolicy(
        alarm_volume_fraction=alarm_pct / 100.0,
        trip_volume_fraction=trip_pct / 100.0,
        persistence_s=persistence_s,
        source_artifact="research/dispersion_detector_logic_validation.json",
        source_doi=str(source["doi"]),
        source_license=str(source["license"]),
        evidence_status="PUBLIC_REPLAY_RULE_APPLIED",
        claim_limit=str(record.get("claim_boundary") or _DEFAULT_POLICY.claim_limit),
    )


__all__ = ["DetectorPolicy", "load_public_detector_policy"]
