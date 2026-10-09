import json
from pathlib import Path

from scripts.build_hiad_hrs_consequence_aggregate import build


ROOT = Path(__file__).resolve().parents[1]


def test_hiad_consequence_aggregate_preserves_unreported_as_unknown():
    aggregate = build()["aggregate"]
    assert aggregate["case_count"] == 34
    assert aggregate["reported_injured_persons_total"] == 2
    assert aggregate["reported_fatalities_total"] == 0
    assert aggregate["records_with_reported_injury_count"] == 2
    assert aggregate["records_without_reported_injury_count"] == 32
    assert aggregate["records_without_reported_fatality_count"] == 34
    assert aggregate["reported_fields_are_not_exposure_denominators"] is True


def test_committed_hiad_consequence_aggregate_is_source_linked_and_narrative_free():
    record = json.loads(
        (ROOT / "research/hiad_hrs_consequence_aggregate_2026_10_10.json").read_text(
            encoding="utf-8"
        )
    )
    fresh = build()
    assert record == fresh
    assert record["source"]["raw_case_rows_included"] is False
    assert record["source"]["narrative_text_included"] is False
    assert "event_id" not in json.dumps(record)
