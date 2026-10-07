from __future__ import annotations

import json
from pathlib import Path

import pytest

from h2station.controlled_station_replay import TraceMapping
from h2station.restricted_attestation import load_restricted_channel_attestation
from h2station.restricted_attestation_review import (
    build_restricted_attestation_review,
    render_restricted_attestation_review_markdown,
)


def _mapping() -> TraceMapping:
    return TraceMapping(
        time_column="C:/private/company/time_tag",
        pressure_columns=(
            ("medium_storage_pressure", "SECRET.PRESSURE.1"),
            ("unknown-private-role", "SECRET.PRESSURE.2"),
        ),
        temperature_columns=(("compressor_temperature", "SECRET.TEMP"),),
        state_columns=(("compressor_load", "SECRET.STATE"),),
        pressure_scale_pa_per_unit=1.0e5,
        temperature_scale_k_per_unit=1.0,
        temperature_offset_k=273.15,
    )


def test_review_is_unconfirmed_and_does_not_leak_source_fields():
    private, public = build_restricted_attestation_review(
        _mapping(),
        mapping_bytes=b'{"contains":"private source mapping"}',
        profile_id="station_equipment_generic_v1",
    )
    rendered = json.dumps({"private": private, "public": public})

    for secret in (
        "SECRET.PRESSURE.1",
        "SECRET.PRESSURE.2",
        "SECRET.TEMP",
        "SECRET.STATE",
        "C:/private/company/time_tag",
        "unknown-private-role",
    ):
        assert secret not in rendered
    assert private["review_status"] == "UNCONFIRMED"
    assert public["review_status"] == "UNCONFIRMED"
    assert private["eligibility"]["station_component_calibration_supported"] is False
    assert public["eligibility"]["full_loop_holdout_eligible"] is False
    assert public["mapped_channel_family_counts"] == {
        "pressure": 2,
        "temperature": 1,
        "flow": 0,
        "discrete_state": 1,
        "lifecycle": 0,
    }


def test_review_proposes_units_without_claiming_attestation():
    private, public = build_restricted_attestation_review(
        _mapping(), mapping_bytes=b"mapping", profile_id="generic"
    )

    assert public["proposed_engineering_units"]["pressure"] == ["bar"]
    assert public["proposed_engineering_units"]["temperature"] == ["degC"]
    assert private["role_review"]["pressure"][0]["pressure_reference"].startswith(
        "UNCONFIRMED"
    )
    assert private["role_review"]["discrete_state"][0]["value_semantics"] == "UNCONFIRMED"
    assert "SECRET" not in render_restricted_attestation_review_markdown(private)


def test_generated_draft_cannot_unlock_calibration_before_confirmation(tmp_path: Path):
    private, _ = build_restricted_attestation_review(
        _mapping(), mapping_bytes=b"mapping", profile_id="generic"
    )
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(private), encoding="utf-8")

    with pytest.raises(ValueError, match="custodian confirmation"):
        load_restricted_channel_attestation(path, _mapping())


def test_generated_draft_requires_role_level_confirmation(tmp_path: Path):
    private, _ = build_restricted_attestation_review(
        _mapping(), mapping_bytes=b"mapping", profile_id="generic"
    )
    private["review_status"] = "CUSTODIAN_CONFIRMED"
    private["pressure_role_and_unit_semantics_attested"] = True
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(private), encoding="utf-8")

    with pytest.raises(ValueError, match="all pressure roles"):
        load_restricted_channel_attestation(path, _mapping())


def test_confirmed_pressure_review_unlocks_only_component_boundary(tmp_path: Path):
    private, _ = build_restricted_attestation_review(
        _mapping(), mapping_bytes=b"mapping", profile_id="generic"
    )
    private["review_status"] = "CUSTODIAN_CONFIRMED"
    private["timebase_semantics_attested"] = True
    private["timebase_review"]["chronology_and_clock_basis"] = "local monotonic logger clock"
    private["timebase_review"]["semantics_confirmed"] = True
    private["calibration_metadata_attested"] = True
    private["calibration_metadata_review"]["confirmed"] = True
    private["pressure_role_and_unit_semantics_attested"] = True
    for row in private["role_review"]["pressure"]:
        row["pressure_reference"] = "absolute"
        row["role_and_unit_confirmed"] = True
    path = tmp_path / "confirmed.json"
    path.write_text(json.dumps(private), encoding="utf-8")

    checked = load_restricted_channel_attestation(path, _mapping())

    assert checked.station_boundary_calibration_supported is True
    assert checked.temperature_boundary_supported is False
    assert checked.recharge_state_calibration_supported is False
    assert checked.to_public_dict()["eligibility"]["full_loop_holdout_eligible"] is False
