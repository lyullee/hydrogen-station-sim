from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from screen_private_full_loop_candidates import screen_manifest  # noqa: E402


FULL_HEADER = [
    "elapsed_time_s",
    "station_pressure_mpa",
    "delivered_gas_temperature_c",
    "mass_flow_g_s",
    "vehicle_pressure_mpa",
    "vehicle_temperature_c",
    "selected_cascade_bank",
    "precooler_outlet_temperature_c",
    "esd_state",
]


def _write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(FULL_HEADER)
        writer.writerows(rows)


def test_empty_schema_template_is_not_measured_candidate(tmp_path: Path) -> None:
    template = tmp_path / "template.csv"
    measured = tmp_path / "measured.csv"
    _write_csv(template, [])
    _write_csv(measured, [[0, 10, 20, 1, 9, 25, "low", -20, "ready"]])
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps([{"path": str(template)}, {"path": str(measured)}]),
        encoding="utf-8",
    )

    result = screen_manifest(manifest)
    assert result["screen"]["manifest_entry_count"] == 2
    assert result["screen"]["complete_nonempty_full_loop_schema_count"] == 1
    assert result["screen"]["empty_full_loop_schema_template_count"] == 1
    assert result["screen"]["aggregate_rows_in_complete_nonempty_candidates"] == 1
    assert result["eligibility"]["full_loop_holdout_eligible"] is False
    rendered = json.dumps(result, ensure_ascii=False)
    assert str(tmp_path) not in rendered
    assert "template.csv" not in rendered
    assert "vehicle_pressure_mpa" not in rendered
