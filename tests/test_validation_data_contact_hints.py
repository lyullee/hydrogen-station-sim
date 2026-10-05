import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contact_hints_are_public_routes_and_not_sent():
    record = json.loads(
        (
            ROOT / "research/validation_data_contact_hints_2026_10_05.json"
        ).read_text(encoding="utf-8")
    )
    assert record["status"] == "PUBLIC_CONTACT_HINTS_ONLY_NOT_SENT"
    assert len(record["contacts"]) >= 5
    for item in record["contacts"]:
        assert item["source"].startswith("https://")
        assert "request_draft" in item
        assert "password" not in item["email"].lower()

