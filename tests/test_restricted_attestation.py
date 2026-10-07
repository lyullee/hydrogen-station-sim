from __future__ import annotations

import json
from pathlib import Path

import pytest

from h2station.controlled_station_replay import TraceMapping
from h2station.restricted_attestation import load_restricted_channel_attestation


def _mapping(*, temperature_boundary: bool = False) -> TraceMapping:
    return TraceMapping(
        time_column="restricted_timestamp",
        pressure_columns=(("station_pressure", "secret_pressure_tag"),),
        temperature_columns=(("station_temperature", "secret_temperature_tag"),),
        flow_column="secret_flow_tag",
        state_columns=(("compressor_load", "secret_state_tag"),),
        authorized_boundary_roles=(
            ("station_pressure", "station_temperature")
            if temperature_boundary else ("station_pressure",)
        ),
        temperature_boundary_role=("station_temperature" if temperature_boundary else None),
    )


def _record(*, temperature: bool = False) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "tag_names_published": False,
        "source_paths_published": False,
        "timebase_semantics_attested": True,
        "pressure_role_and_unit_semantics_attested": True,
        "temperature_role_and_unit_semantics_attested": temperature,
        "flow_role_and_unit_semantics_attested": False,
        "state_semantics_attested": True,
        "lifecycle_semantics_attested": False,
        "calibration_metadata_attested": True,
        "authorized_boundary_roles": (
            ["station_pressure", "station_temperature"]
            if temperature else ["station_pressure"]
        ),
    }


def test_attestation_sanitizes_a_private_mapping(tmp_path: Path):
    path = tmp_path / "restricted-attestation.json"
    path.write_text(json.dumps(_record()), encoding="utf-8")

    checked = load_restricted_channel_attestation(path, _mapping())
    public = checked.to_public_dict()

    assert checked.station_boundary_calibration_supported is True
    assert checked.recharge_state_calibration_supported is True
    assert checked.temperature_boundary_supported is False
    assert public["eligibility"]["full_loop_holdout_eligible"] is False
    rendered = json.dumps(public)
    assert "secret_pressure_tag" not in rendered
    assert "restricted_timestamp" not in rendered
    assert public["mapped_channel_families"] == [
        "pressure", "temperature", "flow", "discrete_state"
    ]


def test_temperature_boundary_requires_custodian_unit_attestation(tmp_path: Path):
    path = tmp_path / "restricted-attestation.json"
    record = _record(temperature=True)
    record["temperature_role_and_unit_semantics_attested"] = False
    path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="temperature boundary"):
        load_restricted_channel_attestation(path, _mapping(temperature_boundary=True))


def test_attestation_rejects_any_publication_flag(tmp_path: Path):
    value = _record()
    value["tag_names_published"] = True
    path = tmp_path / "restricted-attestation.json"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="prohibit publication"):
        load_restricted_channel_attestation(path, _mapping())
