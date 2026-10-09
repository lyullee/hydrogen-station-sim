from pathlib import Path

import pytest

from h2station.privacy_safe_full_loop_intake import (
    build_privacy_safe_freeze_manifest,
)


def _event(path: Path) -> None:
    path.write_text(
        "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase\n"
        "0,20,20,1,start\n"
        "1,21,21,1.2,fill\n",
        encoding="utf-8",
    )


def _event_with_vehicle(path: Path) -> None:
    path.write_text(
        "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase,vehicle_pressure_mpa,vehicle_temperature_c\n"
        "0,20,20,1,start,5,25\n"
        "1,21,21,1.2,fill,6,28\n",
        encoding="utf-8",
    )


def _roles() -> dict[str, str]:
    return {
        "elapsed_time_s": "event-relative logger time",
        "station_pressure_mpa": "station delivery boundary pressure",
        "delivered_gas_temperature_c": "delivery gas temperature",
        "protocol_phase": "controller phase label",
        "mass_or_transferred_mass": "calibrated mass-flow channel",
    }


def test_freeze_manifest_hashes_only_and_never_supports_scoring(tmp_path: Path) -> None:
    events = []
    for index in range(3):
        path = tmp_path / f"event-{index}.csv"
        _event(path)
        events.append(path)
    protocol = tmp_path / "protocol.json"
    model = tmp_path / "model.py"
    evaluator = tmp_path / "evaluator.py"
    protocol.write_text("protocol-v1", encoding="utf-8")
    model.write_text("model-v1", encoding="utf-8")
    evaluator.write_text("evaluator-v1", encoding="utf-8")

    manifest = build_privacy_safe_freeze_manifest(
        events,
        protocol_path=protocol,
        model_path=model,
        evaluator_path=evaluator,
        channel_roles=_roles(),
    )

    assert manifest["status"] == "FROZEN_BEFORE_OUTCOME_ACCESS"
    assert manifest["freeze"]["post_freeze_parameter_tuning_prohibited"] is True
    assert manifest["eligibility"]["model_scoring_performed"] is False
    assert manifest["eligibility"]["full_loop_external_validation_supported"] is False
    assert len(manifest["bundle"]["event_sha256"]) == 3
    assert all(len(value) == 64 for value in manifest["locked_files"].values())
    assert "event-0.csv" not in str(manifest)
    assert str(tmp_path) not in str(manifest)


def test_freeze_manifest_requires_role_attestation(tmp_path: Path) -> None:
    events = []
    for index in range(3):
        path = tmp_path / f"event-{index}.csv"
        _event(path)
        events.append(path)
    protocol = tmp_path / "protocol.json"
    model = tmp_path / "model.py"
    evaluator = tmp_path / "evaluator.py"
    for path in (protocol, model, evaluator):
        path.write_text("locked", encoding="utf-8")

    with pytest.raises(ValueError, match="channel-role"):
        build_privacy_safe_freeze_manifest(
            events,
            protocol_path=protocol,
            model_path=model,
            evaluator_path=evaluator,
            channel_roles={},
        )


def test_full_loop_candidate_requires_vehicle_role_attestation(tmp_path: Path) -> None:
    events = []
    for index in range(3):
        path = tmp_path / f"event-{index}.csv"
        _event_with_vehicle(path)
        events.append(path)
    protocol = tmp_path / "protocol.json"
    model = tmp_path / "model.py"
    evaluator = tmp_path / "evaluator.py"
    for path in (protocol, model, evaluator):
        path.write_text("locked", encoding="utf-8")

    manifest = build_privacy_safe_freeze_manifest(
        events,
        protocol_path=protocol,
        model_path=model,
        evaluator_path=evaluator,
        channel_roles=_roles(),
    )

    assert manifest["eligibility"]["full_loop_protocol_freeze_candidate"] is False
    assert manifest["eligibility"]["missing_vehicle_boundary_roles"] == [
        "vehicle_pressure_mpa",
        "vehicle_temperature_c",
    ]
