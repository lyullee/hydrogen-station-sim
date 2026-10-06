"""Privacy-bounded lifecycle-counter evidence for operator guidance.

The owner-controlled station exports contain counters whose meaning has been
attested as a full-bank recharge count.  That evidence is useful for showing
operating history and planning inspection questions, but it is not a
degradation law.  This module therefore exposes only a sanitized, attested
profile and deliberately refuses to turn counters into capacity, leak-rate or
relief-threshold changes.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class LifecycleEvidenceProfile:
    """Owner-attested cycle evidence safe to include in decision support."""

    evidence_artifact: str
    sampled_rows: int
    counter_semantics: str
    counters: Mapping[str, Mapping[str, float | int]]
    full_recharge_threshold_bar: Mapping[str, float]
    counter_semantics_attested: bool
    threshold_units_attested: bool
    degradation_relationship_attested: bool
    claim_boundary: str

    def runtime_metadata(self) -> dict[str, object]:
        """Return bounded metadata; no source paths, tags, dates or identities."""

        return {
            "artifact": self.evidence_artifact,
            "sampled_rows": self.sampled_rows,
            "counter_semantics": self.counter_semantics,
            "counters": {
                role: dict(values) for role, values in self.counters.items()
            },
            "full_recharge_threshold_bar": dict(self.full_recharge_threshold_bar),
            "counter_semantics_attested": self.counter_semantics_attested,
            "threshold_units_attested": self.threshold_units_attested,
            "degradation_relationship_attested": self.degradation_relationship_attested,
            "claim_boundary": self.claim_boundary,
        }


_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _ROOT / "research" / (
    "confidential_lifecycle_counter_summary_2026_10_06.json"
)


def _finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def load_lifecycle_evidence(
    path: Path | None = None,
) -> LifecycleEvidenceProfile | None:
    """Load an attested aggregate, rejecting unsafe or incomplete artifacts.

    A missing attestation is intentionally a hard reject.  The simulator can
    still run and the raw/private data can still be reviewed offline, but an
    unverified counter must not enter the operator or LLM evidence envelope.
    """

    candidate = path or _DEFAULT_PATH
    try:
        record = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(record, dict):
        return None
    attestation = record.get("attestation")
    if not isinstance(attestation, dict):
        return None
    if (
        record.get("artifact_type") != "confidential_lifecycle_counter_summary"
        or record.get("source_identifiers_published") is not False
        or record.get("raw_rows_persisted") is not False
        or record.get("exact_source_dates_published") is not False
        or attestation.get("status") != "custodian_attested"
        or attestation.get("counter_semantics_attested") is not True
        or attestation.get("threshold_units_attested") is not True
    ):
        return None
    try:
        sampled_rows = int(record["sampled_rows"])
    except (KeyError, TypeError, ValueError):
        return None
    if sampled_rows < 1:
        return None

    thresholds_raw = attestation.get("full_recharge_threshold_bar")
    if not isinstance(thresholds_raw, dict):
        return None
    thresholds: dict[str, float] = {}
    for role in ("medium_bank", "high_bank"):
        value = _finite_number(thresholds_raw.get(role))
        if value is None or not 0.0 < value <= 2_000.0:
            return None
        thresholds[role] = value

    raw_counters = record.get("counters")
    if not isinstance(raw_counters, dict):
        return None
    counters: dict[str, dict[str, float | int]] = {}
    for role, values in raw_counters.items():
        if not isinstance(role, str) or not isinstance(values, dict):
            return None
        bounded: dict[str, float | int] = {}
        for key in (
            "sample_count", "observed_min", "observed_max",
            "positive_increment_count", "total_positive_increment",
            "maximum_single_increment",
        ):
            if key not in values:
                continue
            number = _finite_number(values[key])
            if number is None or number < 0.0:
                return None
            bounded[key] = int(number) if key.endswith("count") else number
        if not bounded:
            return None
        counters[role] = bounded
    if not counters:
        return None
    try:
        artifact = candidate.relative_to(_ROOT).as_posix()
    except ValueError:
        artifact = candidate.name
    return LifecycleEvidenceProfile(
        evidence_artifact=artifact,
        sampled_rows=sampled_rows,
        counter_semantics=str(record.get("counter_semantics") or ""),
        counters=counters,
        full_recharge_threshold_bar=thresholds,
        counter_semantics_attested=True,
        threshold_units_attested=True,
        degradation_relationship_attested=(
            attestation.get("degradation_relationship_attested") is True
        ),
        claim_boundary=str(record.get("claim_boundary") or ""),
    )
