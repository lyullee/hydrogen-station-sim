from __future__ import annotations

from h2station.api import _provider_evidence_basis
from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_summary,
)


def test_kit_lh2_exploratory_evidence_is_bounded_and_traceable():
    manifest = build_evidence_manifest(
        {"time_s": 0.0},
        {},
        [],
        False,
        question="공개 LH2 피해영향 실험 자료와 검증 한계를 알려줘",
    )
    evidence = manifest["response_evidence"]["public_kit_lh2_exploratory_evidence"]
    assert evidence["source"]["doi"] == "10.35097/1483"
    assert evidence["case_count"] == 4
    assert "Blastlogger" in evidence["channel_families"]
    assert "Flowmeter" in evidence["channel_families"]
    assert evidence["archive_status"]["full_archive_checksum_verified"] is False
    assert evidence["validation_gate_effect"] == "none"
    assert "numeric_ranges" not in evidence

    compact = prompt_evidence_summary(manifest)
    assert compact["public_kit_lh2_exploratory_evidence"]["case_count"] == 4
    assert "numeric_ranges" not in compact["public_kit_lh2_exploratory_evidence"]
    assert any(
        link.get("id") == "PUBLIC_KIT_LH2_EXPLORATORY"
        for link in compact["public_source_links"]
    )

    decision = prompt_decision_evidence(manifest)["decision_support_evidence"]
    projected = decision["public_kit_lh2_exploratory_evidence"]
    assert projected["validation_gate_effect"] == "none"
    assert projected["station_vehicle_full_loop_supported"] is False
    assert "numeric_ranges" not in projected

    provider = _provider_evidence_basis(manifest)
    assert provider["public_kit_lh2_exploratory_evidence"]["case_count"] == 4
    assert "numeric_ranges" not in provider["public_kit_lh2_exploratory_evidence"]


def test_kit_lh2_exploratory_evidence_stays_out_of_unrelated_provider_turns():
    manifest = build_evidence_manifest(
        {"time_s": 0.0},
        {},
        [],
        False,
        question="현재 저장뱅크 압력과 온도 상태를 알려줘",
    )
    provider = _provider_evidence_basis(manifest)
    assert "public_kit_lh2_exploratory_evidence" not in provider

