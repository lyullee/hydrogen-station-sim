import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load():
    return json.loads(
        (ROOT / "research" / "local_private_archive_recheck_2026_10_10.json").read_text(
            encoding="utf-8"
        )
    )


def test_private_recheck_is_deidentified_and_station_side_only():
    report = _load()
    assert report["source_identifiers_published"] is False
    assert report["source_paths_published"] is False
    assert report["original_headers_published"] is False
    assert report["raw_rows_persisted"] is False
    assert report["candidate_counts"]["full_loop_candidate"] == 0
    assert report["candidate_counts"]["vehicle_fill_candidate"] == 0
    assert report["attestation"]["vehicle_or_receptacle_channel_attested"] is False
    assert report["attestation"]["station_side_pressure_cascade_evidence_usable"] is True


def test_private_recheck_matches_declared_measurement_inventory():
    report = _load()
    assert report["measurement_csv_count"] == report["schema_inventory"]["measurement_like_tables"]
    assert report["schema_inventory"]["unreadable_tables"] == 0
    assert report["schema_inventory"]["exact_full_loop_cluster_count"] == 0
