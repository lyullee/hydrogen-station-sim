from __future__ import annotations

import json
import math
from pathlib import Path

from h2station.confidential_recharge_flow import audit_confidential_recharge_flow


def _mapping() -> dict[str, object]:
    return {
        "pressure_columns": [
            ["medium_storage_pressure", "PRIVATE.P1"],
            ["high_storage_pressure", "PRIVATE.P2"],
        ],
        "state_columns": [["compressor_load", "PRIVATE.LOAD"]],
    }


def test_quantized_recharge_episode_is_aggregated_without_identifiers(tmp_path: Path):
    source = tmp_path / "private-site-name"
    source.mkdir()
    rows = [
        "time,PRIVATE.P1,PRIVATE.P2,flow,total,PRIVATE.LOAD,STATUS.XV_PRIVATE"
    ]
    cumulative = 0.0
    reported = 0.0
    for index in range(1_200):
        active = 100 <= index <= 900
        flow_per_minute = (
            0.48 + 0.08 * math.sin(2.0 * math.pi * index / 240.0)
            if active else 0.0
        )
        cumulative += flow_per_minute / 60.0
        if index % 15 == 0:
            reported = round(cumulative, 3)
        rows.append(
            f"{index},{40 + index / 1000},{70 + index / 1000},"
            f"{flow_per_minute},{reported},{int(active)},{int(active)}"
        )
    (source / "secret-date.csv").write_text(
        "\n".join(rows) + "\n", encoding="utf-8"
    )

    result = audit_confidential_recharge_flow(source, _mapping())
    encoded = json.dumps(result)

    assert result["screen"]["eligible_equipment_tables"] == 1
    assert result["screen"]["eligible_recharge_episodes"] == 1
    assert result["screen"]["anonymous_valve_mode_count"] == 1
    closure = result["screen"]["integrated_signal_to_totalizer_ratio"]
    assert closure is not None
    assert 0.95 <= closure["median"] <= 1.05
    assert result["eligibility"]["runtime_parameter_update_permitted"] is False
    assert result["eligibility"]["full_station_vehicle_validation"] is False
    assert "PRIVATE" not in encoded
    assert "private-site-name" not in encoded
    assert "secret-date" not in encoded


def test_missing_mapped_load_channel_is_not_eligible(tmp_path: Path):
    source = tmp_path / "controlled"
    source.mkdir()
    (source / "trace.csv").write_text(
        "time,PRIVATE.P1,PRIVATE.P2,flow,total\n"
        + "\n".join(f"{i},40,70,0,0" for i in range(100))
        + "\n",
        encoding="utf-8",
    )

    result = audit_confidential_recharge_flow(source, _mapping())

    assert result["screen"]["eligible_equipment_tables"] == 0
    assert result["screen"]["eligible_recharge_episodes"] == 0
    assert result["eligibility"][
        "conditional_reference_compressor_flow_consistency_supported"
    ] is False
