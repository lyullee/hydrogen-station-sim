from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_local_longform_hydrogen_archive import audit_archive  # noqa: E402


def _write_longform(path: Path) -> None:
    columns = ["entity_type", "entity_id", "key", "ts", "bool_v", "long_v", "dbl_v", "str_v"]
    rows = [
        ["DEVICE", "secret-1", "H2 PRESSURE", "2026-01-01T00:00:00Z", "", "", "70.0", ""],
        ["DEVICE", "secret-1", "H2 TEMPERATURE", "2026-01-01T00:30:00Z", "", "", "25.0", ""],
        ["DEVICE", "secret-2", "H2 INSTANT FLOW", "2026-01-01T01:00:00Z", "", "10", "", ""],
        ["DEVICE", "secret-2", "ESD STATE", "2026-01-01T01:00:00Z", "false", "", "", ""],
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


def test_longform_screen_is_aggregate_only(tmp_path: Path) -> None:
    source = tmp_path / "private.csv"
    _write_longform(source)
    result = audit_archive(source)

    assert result["decision"] == "COMPONENT_OR_STATION_SIDE_CANDIDATE_ONLY"
    assert result["aggregate"]["row_count"] == 4
    assert result["aggregate"]["unique_entity_count"] == 2
    assert result["aggregate"]["unique_key_count"] == 4
    assert result["aggregate"]["observed_span_hours"] == 1.0
    assert result["aggregate"]["candidate_key_family_counts"]["hydrogen_process"] == 3
    assert result["eligibility"]["independent_full_loop_hrs_validation_eligible"] is False
    assert result["coverage_effect"]["new_validation_gate_opened"] is False

    rendered = json.dumps(result, ensure_ascii=False)
    assert "secret-1" not in rendered
    assert "private.csv" not in rendered
    assert str(tmp_path) not in rendered
    assert "2026-01-01" not in rendered
    assert result["privacy"]["raw_rows_persisted"] is False


def test_committed_recheck_has_no_private_identifiers() -> None:
    artifact = ROOT / "research/local_longform_hydrogen_archive_recheck_2026_10_11.json"
    result = json.loads(artifact.read_text(encoding="utf-8"))
    assert result["decision"] == "COMPONENT_OR_STATION_SIDE_CANDIDATE_ONLY"
    assert result["aggregate"]["row_count"] == 2410985
    assert result["aggregate"]["observed_span_hours"] == 24.0
    assert result["eligibility"]["independent_full_loop_hrs_validation_eligible"] is False
    assert result["coverage_effect"]["new_validation_gate_opened"] is False
    assert all(value is False for value in result["privacy"].values())
    rendered = json.dumps(result, ensure_ascii=False)
    assert "C:\\" not in rendered
    assert "20260822" not in rendered
    assert "secret-" not in rendered
