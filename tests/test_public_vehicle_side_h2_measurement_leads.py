import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_vehicle_side_lead_is_claim_bounded() -> None:
    record = json.loads(
        (ROOT / "research/public_vehicle_side_h2_measurement_leads_2026_10_09.json")
        .read_text(encoding="utf-8")
    )
    lead = record["leads"][0]
    assert lead["article_doi"] == "10.3390/en17071510"
    assert lead["raw_trace_status"] == "not_confirmed_from_public_record"
    assert lead["full_loop_eligibility"] is False
    assert "synchronized timestamped" in " ".join(lead["next_access_request"])
    assert "independent station-to-vehicle time-series holdout" in lead["ineligible_use"]

    sampling_lead = record["leads"][1]
    assert sampling_lead["article_doi"] == "10.3390/cleantech8030091"
    assert sampling_lead["full_loop_eligibility"] is False
    assert "synchronized_full_loop_raw_trace_not_confirmed" in sampling_lead[
        "raw_trace_status"
    ]
    assert "mass-flow plausibility range and instrumentation sensitivity" in sampling_lead[
        "eligible_use"
    ]
