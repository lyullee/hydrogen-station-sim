"""Create a privacy-bounded, generic bank-role pressure envelope.

The raw CSV directory and custodian mapping are supplied at run time.  The
generated artifact contains only anonymized profile IDs, generic medium/high
storage roles, and aggregate pressure statistics.  It is diagnostic evidence
for review and LLM grounding; it is deliberately not copied into the runtime
controller or used to claim full station-to-vehicle validation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from h2station.controlled_station_replay import TraceMapping, summarize_pressure_channel_envelopes


def _mapping(path: Path) -> TraceMapping:
    value = json.loads(path.read_text(encoding="utf-8"))
    return TraceMapping(
        time_column=(str(value["time_column"]) if value.get("time_column") else None),
        time_column_index=(
            int(value["time_column_index"])
            if value.get("time_column_index") is not None else None
        ),
        pressure_columns=tuple(
            (str(item[0]), str(item[1]))
            for item in value.get("pressure_columns", [])
        ),
        pressure_scale_pa_per_unit=float(value.get("pressure_scale_pa_per_unit", 1.0e6)),
        time_format=value.get("time_format"),
        time_is_absolute=bool(value.get("time_is_absolute", False)),
        encoding=str(value.get("encoding", "utf-8-sig")),
    )


def _generic_profile(
    profile_id: str,
    input_path: Path,
    mapping_path: Path,
    *,
    stride: int,
    max_rows_per_file: int,
    value_cap_per_channel: int,
) -> dict[str, Any]:
    mapping = _mapping(mapping_path)
    summaries = summarize_pressure_channel_envelopes(
        input_path,
        mapping,
        stride=stride,
        max_rows_per_file=max_rows_per_file,
        value_cap_per_channel=value_cap_per_channel,
    )
    roles = ("medium_storage_pressure", "high_storage_pressure")
    banks: dict[str, Any] = {}
    for role, summary in zip(roles, summaries):
        values = summary.to_public_dict()
        banks[role] = {
            "sampled_rows": values.get("sampled_rows"),
            "pressure_mpa": values.get("pressure_mpa") or {},
            "positive_pressure_ramp_p95_pa_s": values.get(
                "positive_pressure_ramp_p95_pa_s"
            ),
            "recommended_restart_margin_pa": values.get(
                "recommended_restart_margin_pa"
            ),
            "pressure_semantics_attested": values.get(
                "pressure_semantics_attested"
            ) is True,
        }
    return {
        "profile_id": profile_id,
        "bank_roles": banks,
        "sampled_rows": sum(int(row.get("sampled_rows") or 0) for row in banks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-a-input", type=Path, required=True)
    parser.add_argument("--profile-a-mapping", type=Path, required=True)
    parser.add_argument("--profile-b-input", type=Path, required=True)
    parser.add_argument("--profile-b-mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=600)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    parser.add_argument("--value-cap-per-channel", type=int, default=50_000)
    args = parser.parse_args()

    profiles = [
        _generic_profile(
            "owner_station_profile_a",
            args.profile_a_input,
            args.profile_a_mapping,
            stride=args.stride,
            max_rows_per_file=args.max_rows_per_file,
            value_cap_per_channel=args.value_cap_per_channel,
        ),
        _generic_profile(
            "owner_station_profile_b",
            args.profile_b_input,
            args.profile_b_mapping,
            stride=args.stride,
            max_rows_per_file=args.max_rows_per_file,
            value_cap_per_channel=args.value_cap_per_channel,
        ),
    ]
    result = {
        "schema_version": 1,
        "artifact_type": "confidential_bank_role_pressure_envelopes",
        "recorded_at": "2026-10-06",
        "evidence_role": "privacy_bounded_bank_role_pressure_diagnostic",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "exact_source_dates_published": False,
        "tag_names_published": False,
        "manufacturer_or_model_published": False,
        "sampling": {
            "stride": args.stride,
            "max_rows_per_file": args.max_rows_per_file,
            "value_cap_per_channel": args.value_cap_per_channel,
        },
        "profiles": profiles,
        "attestation": {
            "bank_role_mapping_attested": True,
            "pressure_scale_mapping_attested": True,
            "machine_readable_unit_dictionary_present": False,
            "temperature_or_flow_roles_attested": False,
        },
        "eligibility": {
            "bank_role_pressure_diagnostic_supported": True,
            "runtime_parameter_application": False,
            "full_station_vehicle_validation": False,
            "full_loop_holdout_eligible": False,
            "default_model_parameters_changed": False,
        },
        "claim_boundary": (
            "비식별화된 저장탱크 역할별 압력 envelope를 운전범위 점검과 LLM 근거로만 사용한다. "
            "원본 태그·사업장·날짜·제조사·차량측 채널은 보존하지 않으며, 안전한계·차량측 정확도·"
            "현장 피해거리·full-loop 검증을 의미하지 않는다."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
