from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript/ijhe_manuscript_draft.tex"


def test_manuscript_keeps_station_to_vehicle_and_human_claim_limits_explicit() -> None:
    text = " ".join(MANUSCRIPT.read_text(encoding="utf-8").split())
    required_fragments = (
        "no synchronized station-to-vehicle full-loop holdout was available",
        "No openly reusable synchronized station-to-vehicle",
        "raw cohort was identified, so vehicle-side full-loop accuracy is outside the primary claim",
        "neither an independent holdout nor a substitute for expert review",
        "Holdout responses and ratings have not yet been collected",
        "does not test action correctness, operator usability or safety",
    )
    for fragment in required_fragments:
        assert fragment in text


def test_manuscript_reports_actual_incident_and_consequence_evidence_as_bounded() -> None:
    text = " ".join(MANUSCRIPT.read_text(encoding="utf-8").split())
    assert "All 34 HIAD metadata cases route to registered plans" in text
    assert "All 27 cases passed" in text
    assert "not outdoor jet radiation, station-loop control or a site-specific evacuation distance" in text
    assert "These are software-traceability results; no independent reviewer assessed unsafe omissions" in text


def test_manuscript_does_not_promote_same_site_holdout_to_external_full_loop() -> None:
    text = " ".join(MANUSCRIPT.read_text(encoding="utf-8").split())
    forbidden_claims = (
        "same-site station-side holdout is independent external validation",
        "same-site station-side data provide independent external full-loop validation",
        "validated full station-to-vehicle digital twin",
    )
    lowered = text.lower()
    for claim in forbidden_claims:
        assert claim not in lowered
