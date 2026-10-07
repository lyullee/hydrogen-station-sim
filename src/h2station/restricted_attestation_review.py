"""Build a privacy-safe custodian review from a restricted channel mapping.

The input mapping can contain proprietary logger column names.  The returned
records contain only allow-listed generic roles, channel-family counts and
engineering-unit proposals derived from numeric conversion factors.  Every
proposal remains explicitly unconfirmed until a data custodian reviews it.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

from .controlled_station_replay import TraceMapping


_PUBLIC_ROLE_LABELS = {
    "station_pressure": "station_pressure",
    "low_storage_pressure": "low_storage_pressure",
    "medium_storage_pressure": "medium_storage_pressure",
    "high_storage_pressure": "high_storage_pressure",
    "station_temperature": "station_temperature",
    "compressor_temperature": "compressor_temperature",
    "cooler_inlet_temperature": "cooler_inlet_temperature",
    "cooler_outlet_temperature": "cooler_outlet_temperature",
    "compressor_load": "compressor_load",
    "cooling_run": "cooling_run",
    "hp_oil_trip": "hp_oil_trip",
}


def _generic_role(role: str, family: str, ordinal: int) -> str:
    """Return an allow-listed role or a family-only placeholder."""

    return _PUBLIC_ROLE_LABELS.get(role, f"{family}_channel_{ordinal}")


def _pressure_unit(scale: float) -> str:
    for expected, unit in ((1.0, "Pa"), (1.0e3, "kPa"), (1.0e5, "bar"), (1.0e6, "MPa")):
        if math.isclose(scale, expected, rel_tol=0.0, abs_tol=expected * 1.0e-12):
            return unit
    return "UNCONFIRMED"


def _temperature_unit(scale: float, offset: float) -> str:
    if math.isclose(scale, 1.0, abs_tol=1.0e-12) and math.isclose(
        offset, 273.15, abs_tol=1.0e-9
    ):
        return "degC"
    if math.isclose(scale, 1.0, abs_tol=1.0e-12) and math.isclose(
        offset, 0.0, abs_tol=1.0e-12
    ):
        return "K"
    return "UNCONFIRMED"


def _flow_unit(scale: float) -> str:
    if math.isclose(scale, 1.0, abs_tol=1.0e-12):
        return "kg/s"
    if math.isclose(scale, 1.0e-3, abs_tol=1.0e-15):
        return "g/s"
    return "UNCONFIRMED"


def _role_rows(mapping: TraceMapping) -> dict[str, list[dict[str, Any]]]:
    pressure = [
        {
            "generic_role": _generic_role(role, "pressure", index),
            "proposed_source_unit": _pressure_unit(mapping.pressure_scale_pa_per_unit),
            "source_to_pa_scale": mapping.pressure_scale_pa_per_unit,
            "pressure_reference": "UNCONFIRMED_ABSOLUTE_OR_GAUGE",
            "role_and_unit_confirmed": False,
        }
        for index, (role, _) in enumerate(mapping.pressure_columns, start=1)
    ]
    temperature = [
        {
            "generic_role": _generic_role(role, "temperature", index),
            "proposed_source_unit": _temperature_unit(
                mapping.temperature_scale_k_per_unit,
                mapping.temperature_offset_k,
            ),
            "source_to_k_scale": mapping.temperature_scale_k_per_unit,
            "source_to_k_offset": mapping.temperature_offset_k,
            "physical_location_and_role_confirmed": False,
            "role_and_unit_confirmed": False,
        }
        for index, (role, _) in enumerate(mapping.temperature_columns, start=1)
    ]
    flow = []
    if mapping.flow_column:
        flow.append(
            {
                "generic_role": "mass_flow",
                "proposed_source_unit": _flow_unit(mapping.flow_scale_kg_s_per_unit),
                "source_to_kg_s_scale": mapping.flow_scale_kg_s_per_unit,
                "positive_direction": "UNCONFIRMED",
                "role_and_unit_confirmed": False,
            }
        )
    state = [
        {
            "generic_role": _generic_role(role, "discrete_state", index),
            "value_semantics": "UNCONFIRMED",
            "normal_value": "UNCONFIRMED",
            "active_or_trip_value": "UNCONFIRMED",
            "semantics_confirmed": False,
        }
        for index, (role, _) in enumerate(mapping.state_columns, start=1)
    ]
    lifecycle = [
        {
            "generic_role": _generic_role(role, "lifecycle", index),
            "counter_unit_and_reset_semantics": "UNCONFIRMED",
            "semantics_confirmed": False,
        }
        for index, (role, _) in enumerate(mapping.lifecycle_columns, start=1)
    ]
    return {
        "pressure": pressure,
        "temperature": temperature,
        "flow": flow,
        "discrete_state": state,
        "lifecycle": lifecycle,
    }


def build_restricted_attestation_review(
    mapping: TraceMapping,
    *,
    mapping_bytes: bytes,
    profile_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return an editable private draft and a publishable status record."""

    roles = _role_rows(mapping)
    counts = {family: len(items) for family, items in roles.items()}
    authorized = [
        _generic_role(role, "boundary", index)
        for index, role in enumerate(mapping.authorized_boundary_roles, start=1)
    ]
    private = {
        "schema_version": 1,
        "artifact_type": "restricted_station_channel_attestation_draft",
        "review_status": "UNCONFIRMED",
        "profile_id": profile_id,
        "mapping_sha256": sha256(mapping_bytes).hexdigest(),
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "tag_names_published": False,
        "source_paths_published": False,
        "timebase_semantics_attested": False,
        "pressure_role_and_unit_semantics_attested": False,
        "temperature_role_and_unit_semantics_attested": False,
        "flow_role_and_unit_semantics_attested": False,
        "state_semantics_attested": False,
        "lifecycle_semantics_attested": False,
        "calibration_metadata_attested": False,
        "authorized_boundary_roles": authorized,
        "timebase_review": {
            "declared_time_format_present": bool(mapping.time_format),
            "declared_absolute_numeric_time": mapping.time_is_absolute,
            "chronology_and_clock_basis": "UNCONFIRMED",
            "semantics_confirmed": False,
        },
        "calibration_metadata_review": {
            "calibration_or_quality_records_exist": "UNCONFIRMED",
            "records_cover_the_mapped_measurement_period": "UNCONFIRMED",
            "confirmed": False,
        },
        "role_review": roles,
        "completion_instructions": [
            "Confirm only roles, units and state meanings supported by controlled records.",
            "Set each reviewed item and matching family attestation to true.",
            "Set review_status to CUSTODIAN_CONFIRMED only after the review is complete.",
            "Keep this file outside the public repository.",
        ],
        "eligibility": {
            "station_component_calibration_supported": False,
            "temperature_boundary_supported": False,
            "recharge_state_calibration_supported": False,
            "full_station_vehicle_validation": False,
            "full_loop_holdout_eligible": False,
        },
    }
    public = {
        "schema_version": 1,
        "artifact_type": "confidential_station_attestation_request_status",
        "profile_id": profile_id,
        "review_status": "UNCONFIRMED",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "tag_names_published": False,
        "source_paths_published": False,
        "mapped_channel_family_counts": counts,
        "proposed_engineering_units": {
            "pressure": sorted({row["proposed_source_unit"] for row in roles["pressure"]}),
            "temperature": sorted(
                {row["proposed_source_unit"] for row in roles["temperature"]}
            ),
            "flow": sorted({row["proposed_source_unit"] for row in roles["flow"]}),
        },
        "confirmation_required": {
            "timebase": True,
            "pressure_reference_and_roles": bool(roles["pressure"]),
            "temperature_location_roles_and_units": bool(roles["temperature"]),
            "flow_direction_and_units": bool(roles["flow"]),
            "discrete_state_value_semantics": bool(roles["discrete_state"]),
            "lifecycle_counter_semantics": bool(roles["lifecycle"]),
            "calibration_metadata": True,
        },
        "eligibility": private["eligibility"],
        "claim_boundary": (
            "This record only reports a pending custodian review of generic channel "
            "families. It contains no measurement rows or source identifiers, does not "
            "attest the proposed units, and cannot support calibration or validation."
        ),
    }
    return private, public


def render_restricted_attestation_review_markdown(draft: dict[str, Any]) -> str:
    """Render a compact Korean checklist without proprietary identifiers."""

    roles = draft["role_review"]
    lines = [
        "# 제한자료 계측 의미 확인서",
        "",
        f"- 검토 상태: **{draft['review_status']}**",
        f"- 비식별 프로필: `{draft['profile_id']}`",
        "- 이 문서는 원시 태그·회사·위치·제조사·절대 날짜를 포함하지 않습니다.",
        "",
        "## 확인 항목",
        "",
        "- [ ] 시간 순서와 시간 기준이 실제 운전 순서를 보존한다.",
        "- [ ] 압력 기준이 절대압인지 게이지압인지 확인했다.",
        "- [ ] 계측기 교정 또는 품질 메타데이터의 존재를 확인했다.",
    ]
    for family, title in (
        ("pressure", "압력"),
        ("temperature", "온도"),
        ("flow", "유량"),
        ("discrete_state", "상태"),
        ("lifecycle", "수명주기"),
    ):
        if not roles[family]:
            continue
        lines.extend(["", f"### {title}", ""])
        for item in roles[family]:
            unit = item.get("proposed_source_unit")
            suffix = f" · 제안 단위 `{unit}`" if unit else ""
            lines.append(f"- [ ] `{item['generic_role']}` 역할·의미 확인{suffix}")
    lines.extend(
        [
            "",
            "## 적용 제한",
            "",
            "확인 전에는 모든 채널이 진단 전용입니다. 확인 후에도 차량 측 계측이 없으면 "
            "충전소-차량 전체 루프 검증이나 안전인증 근거로 사용할 수 없습니다.",
            "",
        ]
    )
    return "\n".join(lines)


def write_restricted_attestation_review(
    mapping: TraceMapping,
    *,
    mapping_path: Path,
    profile_id: str,
    private_draft_path: Path,
    private_markdown_path: Path,
    public_status_path: Path,
) -> None:
    """Write the review artifacts without reading any measurement rows."""

    mapping_bytes = mapping_path.read_bytes()
    private, public = build_restricted_attestation_review(
        mapping,
        mapping_bytes=mapping_bytes,
        profile_id=profile_id,
    )
    private_draft_path.parent.mkdir(parents=True, exist_ok=True)
    private_markdown_path.parent.mkdir(parents=True, exist_ok=True)
    public_status_path.parent.mkdir(parents=True, exist_ok=True)
    private_draft_path.write_text(
        json.dumps(private, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    private_markdown_path.write_text(
        render_restricted_attestation_review_markdown(private), encoding="utf-8"
    )
    public_status_path.write_text(
        json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
