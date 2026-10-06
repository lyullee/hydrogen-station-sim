from __future__ import annotations

import json
from pathlib import Path

from h2station.controlled_station_replay import (
    TraceMapping,
    summarize_pressure_channel_envelopes,
)


def test_pressure_channel_envelopes_are_indexed_and_bounded(tmp_path: Path):
    source = tmp_path / "private.csv"
    source.write_text(
        "LocalTimeCol,PRIVATE_TAG_A,PRIVATE_TAG_B\n"
        "01/01/2026 12:00:00 AM,40,80\n"
        "01/01/2026 12:01:00 AM,41,81\n"
        "01/01/2026 12:02:00 AM,42,82\n"
        "01/01/2026 12:03:00 AM,43,83\n",
        encoding="utf-8",
    )
    summaries = summarize_pressure_channel_envelopes(
        source,
        TraceMapping(
            time_column="LocalTimeCol",
            pressure_columns=(
                ("station_pressure", "PRIVATE_TAG_A"),
                ("station_pressure", "PRIVATE_TAG_B"),
            ),
            time_format="%m/%d/%Y %I:%M:%S %p",
            time_is_absolute=True,
        ),
        stride=1,
        max_rows_per_file=100,
    )
    assert len(summaries) == 2
    public = [summary.to_public_dict() for summary in summaries]
    assert public[0]["pressure_mpa"]["median"] == 41.5
    assert public[1]["pressure_mpa"]["median"] == 81.5
    assert "PRIVATE_TAG_A" not in json.dumps(public)
    assert "PRIVATE_TAG_B" not in json.dumps(public)


def test_public_channel_artifact_has_no_station_identity():
    artifact = Path(__file__).parents[1] / (
        "research/confidential_station_boundary_channel_envelopes_2026_10_06.json"
    )
    record = json.loads(artifact.read_text(encoding="utf-8"))
    assert record["raw_rows_persisted"] is False
    assert record["source_identifiers_published"] is False
    assert record["exact_source_dates_published"] is False
    assert record["eligibility"]["bank_role_mapping_attested"] is False
    assert record["eligibility"]["runtime_parameter_application"] is False
    serialized = json.dumps(record, ensure_ascii=False)
    assert "C:\\Users" not in serialized
    assert "코하이젠" not in serialized
