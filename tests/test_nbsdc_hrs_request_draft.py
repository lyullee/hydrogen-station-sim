from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "research" / "NBSDC_HRS_OPERATIONAL_DATA_REQUEST_2026_10_09.md"


def test_nbsdc_request_draft_is_specific_and_fails_closed():
    text = REQUEST.read_text(encoding="utf-8")
    assert "16666.11.nbsdc.aI3fJrzX" in text
    assert "common monotonic time base" in text
    assert "full-loop holdout candidate" in text
    assert "does not bypass" in text
    assert "Raw rows would remain outside the public repository" in text
