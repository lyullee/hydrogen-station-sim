from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recheck_public_type_iv_tank_validation import build_record, compare  # noqa: E402


def _record(value: float = 1.0) -> dict:
    return {
        "fit": {
            "effective_volume_multiplier": value,
            "gas_liner_ua_multiplier": 2.0,
        },
        "validation": {
            "case_count": 12,
            "pressure_rmse_mpa": {"mean": 3.0},
            "temperature_rmse_c": {"mean": 4.0},
            "soc_rmse_percentage_points": {"mean": 2.0},
        },
    }


def test_recheck_only_retains_derived_aggregates_and_detects_a_difference(tmp_path: Path):
    expected_path = tmp_path / "expected.json"
    fresh_path = tmp_path / "fresh.json"
    expected_path.write_text(json.dumps(_record()), encoding="utf-8")
    fresh_path.write_text(json.dumps(_record()), encoding="utf-8")
    comparison = compare(_record(), _record())
    assert comparison["matches"] is True
    output = build_record(expected_path, fresh_path, comparison)
    assert output["raw_experimental_rows_persisted"] is False
    assert output["source_workbook_names_persisted"] is False
    assert "station-to-vehicle validation" in output["claim_boundary"]
    assert compare(_record(), _record(1.1))["matches"] is False


def test_committed_recheck_matches_the_public_tank_validation_record():
    expected = json.loads((ROOT / "research/tank_model_validation_v2.json").read_text(encoding="utf-8"))
    recheck = json.loads(
        (ROOT / "research/public_type_iv_tank_validation_recheck_2026_10_07.json")
        .read_text(encoding="utf-8")
    )
    assert recheck["comparison"] == compare(expected, expected)
    assert recheck["comparison"]["matches"] is True
