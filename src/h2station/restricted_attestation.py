"""Privacy-safe attestation for restricted station measurement mappings.

Raw logger mappings necessarily contain proprietary column names.  This module
keeps those names in the controlled environment while producing a small,
generic record that says which *roles* have had their units, direction and
meaning confirmed by the data custodian.  A role that is not attested stays
diagnostic-only; it must not become a calibration or replay boundary merely
because its source column resembles a familiar instrument tag.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping

from .controlled_station_replay import TraceMapping


_REQUIRED_PRIVATE_FLAGS = (
    "source_identifiers_published",
    "raw_rows_persisted",
    "absolute_timestamps_published",
    "tag_names_published",
    "source_paths_published",
)


def _flag(record: Mapping[str, object], key: str) -> bool:
    """Treat only literal JSON ``true`` as a positive custodian attestation."""

    return record.get(key) is True


def _mapping_roles(mapping: TraceMapping) -> set[str]:
    """Return generic roles without retaining proprietary source columns."""

    roles: set[str] = set()
    if mapping.pressure_columns:
        roles.add("station_pressure")
    if mapping.temperature_columns:
        roles.add("station_temperature")
    roles.update(role for role, _ in mapping.temperature_columns)
    if mapping.flow_column:
        roles.add("mass_flow")
    roles.update(role for role, _ in mapping.state_columns)
    roles.update(role for role, _ in mapping.lifecycle_columns)
    return roles


def _require_generated_review_confirmations(record: Mapping[str, object]) -> None:
    """Keep generated drafts unusable until every claimed family is reviewed."""

    if "review_status" not in record:
        return
    if record.get("review_status") != "CUSTODIAN_CONFIRMED":
        raise ValueError("generated attestation draft requires custodian confirmation")
    timebase = record.get("timebase_review")
    if _flag(record, "timebase_semantics_attested") and (
        not isinstance(timebase, Mapping)
        or timebase.get("semantics_confirmed") is not True
        or str(timebase.get("chronology_and_clock_basis", "")).startswith("UNCONFIRMED")
    ):
        raise ValueError("confirmed timebase attestation requires completed timebase review")
    metadata = record.get("calibration_metadata_review")
    if _flag(record, "calibration_metadata_attested") and (
        not isinstance(metadata, Mapping) or metadata.get("confirmed") is not True
    ):
        raise ValueError(
            "confirmed calibration metadata attestation requires completed metadata review"
        )
    role_review = record.get("role_review")
    if not isinstance(role_review, Mapping):
        raise ValueError("generated attestation requires role_review")
    requirements = {
        "pressure_role_and_unit_semantics_attested": ("pressure", "role_and_unit_confirmed"),
        "temperature_role_and_unit_semantics_attested": (
            "temperature", "role_and_unit_confirmed"
        ),
        "flow_role_and_unit_semantics_attested": ("flow", "role_and_unit_confirmed"),
        "state_semantics_attested": ("discrete_state", "semantics_confirmed"),
        "lifecycle_semantics_attested": ("lifecycle", "semantics_confirmed"),
    }
    for attestation_flag, (family, confirmation_key) in requirements.items():
        if not _flag(record, attestation_flag):
            continue
        rows = role_review.get(family)
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{attestation_flag} requires mapped {family} review rows")
        if any(
            not isinstance(row, Mapping) or row.get(confirmation_key) is not True
            for row in rows
        ):
            raise ValueError(f"{attestation_flag} requires all {family} roles to be confirmed")
        if family == "pressure" and any(
            str(row.get("pressure_reference", "")).startswith("UNCONFIRMED")
            for row in rows
        ):
            raise ValueError("pressure attestation requires absolute/gauge reference review")
        if family == "temperature" and any(
            row.get("physical_location_and_role_confirmed") is not True for row in rows
        ):
            raise ValueError("temperature attestation requires physical-location review")
        if family == "flow" and any(
            str(row.get("positive_direction", "")).startswith("UNCONFIRMED")
            for row in rows
        ):
            raise ValueError("flow attestation requires positive-direction review")
        if family == "discrete_state" and any(
            str(row.get(key, "")).startswith("UNCONFIRMED")
            for row in rows
            for key in ("value_semantics", "normal_value", "active_or_trip_value")
        ):
            raise ValueError("state attestation requires explicit value semantics")
        if family == "lifecycle" and any(
            str(row.get("counter_unit_and_reset_semantics", "")).startswith("UNCONFIRMED")
            for row in rows
        ):
            raise ValueError("lifecycle attestation requires counter/reset semantics")


@dataclass(frozen=True)
class RestrictedChannelAttestation:
    """Sanitized proof of what a restricted mapping is permitted to drive."""

    schema_version: int
    timebase_semantics_attested: bool
    pressure_role_and_unit_semantics_attested: bool
    temperature_role_and_unit_semantics_attested: bool
    flow_role_and_unit_semantics_attested: bool
    state_semantics_attested: bool
    lifecycle_semantics_attested: bool
    calibration_metadata_attested: bool
    authorized_boundary_roles: tuple[str, ...]
    mapped_channel_families: tuple[str, ...]

    @property
    def station_boundary_calibration_supported(self) -> bool:
        return (
            self.timebase_semantics_attested
            and self.pressure_role_and_unit_semantics_attested
            and self.calibration_metadata_attested
            and "station_pressure" in self.authorized_boundary_roles
        )

    @property
    def temperature_boundary_supported(self) -> bool:
        return (
            self.station_boundary_calibration_supported
            and self.temperature_role_and_unit_semantics_attested
            and any(role != "station_pressure" for role in self.authorized_boundary_roles)
        )

    @property
    def recharge_state_calibration_supported(self) -> bool:
        return (
            self.station_boundary_calibration_supported
            and self.state_semantics_attested
        )

    def to_public_dict(self) -> dict[str, object]:
        """Return only generic capabilities, never raw source-map fields."""

        return {
            "schema_version": self.schema_version,
            "source_identifiers_published": False,
            "raw_rows_persisted": False,
            "absolute_timestamps_published": False,
            "tag_names_published": False,
            "source_paths_published": False,
            "timebase_semantics_attested": self.timebase_semantics_attested,
            "pressure_role_and_unit_semantics_attested": (
                self.pressure_role_and_unit_semantics_attested
            ),
            "pressure_boundary_semantics_attested": (
                self.pressure_role_and_unit_semantics_attested
            ),
            "temperature_role_and_unit_semantics_attested": (
                self.temperature_role_and_unit_semantics_attested
            ),
            "temperature_boundary_role_attested": self.temperature_boundary_supported,
            "flow_role_and_unit_semantics_attested": (
                self.flow_role_and_unit_semantics_attested
            ),
            "mass_flow_units_attested": self.flow_role_and_unit_semantics_attested,
            "state_semantics_attested": self.state_semantics_attested,
            "lifecycle_semantics_attested": self.lifecycle_semantics_attested,
            "calibration_metadata_attested": self.calibration_metadata_attested,
            "authorized_boundary_roles": list(self.authorized_boundary_roles),
            "mapped_channel_families": list(self.mapped_channel_families),
            "eligibility": {
                "station_boundary_calibration_supported": (
                    self.station_boundary_calibration_supported
                ),
                "temperature_boundary_supported": self.temperature_boundary_supported,
                "recharge_state_calibration_supported": (
                    self.recharge_state_calibration_supported
                ),
                "full_station_vehicle_validation": False,
                "full_loop_holdout_eligible": False,
            },
            "claim_boundary": (
                "Custodian attestation of generic measurement roles only. "
                "It is not a calibration result, a station-to-vehicle "
                "validation result, a safety limit, or a safety certification."
            ),
        }


def load_restricted_channel_attestation(
    path: Path,
    mapping: TraceMapping,
) -> RestrictedChannelAttestation:
    """Validate a restricted generic-role attestation against a live mapping.

    ``path`` stays outside version control with the raw mapping.  It may name
    only generic roles; source column names and file paths are rejected so an
    accidentally committed output cannot reveal the controlled data source.
    """

    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("restricted channel attestation must be valid JSON") from exc
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise ValueError("restricted channel attestation schema_version must be 1")
    _require_generated_review_confirmations(record)
    if any(record.get(key) is not False for key in _REQUIRED_PRIVATE_FLAGS):
        raise ValueError("attestation must explicitly prohibit publication of restricted data")

    raw_roles = record.get("authorized_boundary_roles", ["station_pressure"])
    if not isinstance(raw_roles, list) or not raw_roles:
        raise ValueError("authorized_boundary_roles must be a non-empty list")
    authorized_roles = tuple(str(role) for role in raw_roles)
    if len(set(authorized_roles)) != len(authorized_roles):
        raise ValueError("authorized_boundary_roles must be unique")
    known_roles = _mapping_roles(mapping)
    unknown = set(authorized_roles) - known_roles
    if unknown:
        raise ValueError(
            "authorized roles are not present in the generic mapping: "
            + ", ".join(sorted(unknown))
        )
    if tuple(mapping.authorized_boundary_roles) != authorized_roles:
        raise ValueError(
            "attestation authorized_boundary_roles must exactly match the restricted mapping"
        )

    pressure_attested = _flag(record, "pressure_role_and_unit_semantics_attested")
    temperature_attested = _flag(record, "temperature_role_and_unit_semantics_attested")
    flow_attested = _flag(record, "flow_role_and_unit_semantics_attested")
    state_attested = _flag(record, "state_semantics_attested")
    lifecycle_attested = _flag(record, "lifecycle_semantics_attested")
    timebase_attested = _flag(record, "timebase_semantics_attested")
    calibration_metadata_attested = _flag(record, "calibration_metadata_attested")

    if "station_pressure" in authorized_roles and not pressure_attested:
        raise ValueError("station-pressure boundary use requires pressure/unit attestation")
    if any(role != "station_pressure" for role in authorized_roles) and not temperature_attested:
        raise ValueError("temperature boundary use requires temperature/unit attestation")
    if mapping.temperature_boundary_role is not None and not temperature_attested:
        raise ValueError("temperature_boundary_role requires temperature/unit attestation")

    families: list[str] = []
    if mapping.pressure_columns:
        families.append("pressure")
    if mapping.temperature_columns:
        families.append("temperature")
    if mapping.flow_column:
        families.append("flow")
    if mapping.state_columns:
        families.append("discrete_state")
    if mapping.lifecycle_columns:
        families.append("lifecycle")
    return RestrictedChannelAttestation(
        schema_version=1,
        timebase_semantics_attested=timebase_attested,
        pressure_role_and_unit_semantics_attested=pressure_attested,
        temperature_role_and_unit_semantics_attested=temperature_attested,
        flow_role_and_unit_semantics_attested=flow_attested,
        state_semantics_attested=state_attested,
        lifecycle_semantics_attested=lifecycle_attested,
        calibration_metadata_attested=calibration_metadata_attested,
        authorized_boundary_roles=authorized_roles,
        mapped_channel_families=tuple(families),
    )
