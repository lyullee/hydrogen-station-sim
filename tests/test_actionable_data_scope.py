from __future__ import annotations

from h2station.llm_grounding import build_evidence_manifest, prompt_decision_evidence
from h2station.api import _provider_evidence_basis


def _manifest():
    return build_evidence_manifest(
        {
            "time_s": 12.0,
            "header_pressure_mpa": 65.0,
            "header_temperature_c": 25.0,
            "header_mass_kg": 40.0,
            "header_inflow_g_s": 0.0,
        },
        {},
        [],
        False,
        question="로컬 충전소 압력 데이터와 공개 실험 데이터를 사용해 분석해줘",
    )


def test_actionable_data_scope_is_privacy_bounded_and_nonempty() -> None:
    manifest = _manifest()
    scope = manifest["response_evidence"]["local_actionable_data_scope"]
    assert scope["runtime_usable_now"]
    assert scope["runtime_usable_now"][0]["holdout_cases"] == 394
    transfer = next(
        item for item in scope["runtime_usable_now"]
        if item["id"] == "station_pressure_cross_bundle_transfer_corroboration"
    )
    assert transfer["transfer_cycles"] == 225
    assert transfer["screen_pass"] is True
    assert transfer["independent_external_validation"] is False
    assert scope["available_but_not_runtime_promoted"][0]["holdout_consistent"] is False
    assert scope["full_loop_holdout"]["synchronized_trace_count"] == 0
    assert [item["id"] for item in scope["minimum_data_tiers"]] == [
        "tier_0_current",
        "tier_1_component_pilot",
        "tier_2_full_loop_holdout",
    ]
    assert scope["decision"]["request_smallest_next_bundle_first"] == "tier_1_component_pilot"
    assert scope["artifact"] == "research/local_data_actionable_scope_2026_10_09.json"
    official = scope["official_public_access_check"]
    assert official["eligible_full_loop_source_count"] == 0
    assert official["official_station_to_vehicle_raw_trace_confirmed"] is False
    assert official["smallest_next_request"] == "tier_1_component_pilot"
    rendered = str(scope)
    assert "raw_rows" not in rendered
    assert "source_paths" not in rendered


def test_decision_prompt_names_usable_data_before_full_loop_boundary() -> None:
    manifest = _manifest()
    decision = prompt_decision_evidence(manifest)
    scope = decision["decision_support_evidence"]["local_actionable_data_scope"]
    assert scope["runtime_usable_now"]
    assert scope["full_loop_holdout"]["synchronized_trace_count"] == 0
    assert decision["decision_support_evidence"]
    assert manifest["response_evidence"]["local_actionable_data_scope"]["decision"][
        "request_smallest_next_bundle_first"
    ] == "tier_1_component_pilot"

    station_scope = decision["station_side_data_scope"]
    assert station_scope["runtime_usable_now"]
    forecast = next(
        item for item in station_scope["runtime_usable_now"]
        if item["id"] == "station_pressure_forecast"
    )
    assert forecast["holdout_cases"] == 394
    assert station_scope["full_loop_holdout"]["synchronized_trace_count"] == 0
    assert station_scope["decision"]["use_station_side_and_component_evidence_now"] is True
    assert "source_paths" not in str(station_scope)
    assert "C:\\" not in str(station_scope)

    provider_basis = _provider_evidence_basis(manifest)
    assert "station_side_data_scope" in provider_basis
    assert provider_basis["station_side_data_scope"]["runtime_usable_now"]
    assert provider_basis["station_side_data_scope"]["full_loop_holdout"][
        "synchronized_trace_count"
    ] == 0

    protocol = decision["decision_support_evidence"][
        "public_h2protocol_validation_boundary"
    ]
    assert protocol["case_count"] == 36
    assert protocol["screening_pass_count"] == 0
    assert protocol["fresh_holdout_available"] is False
    assert protocol["full_loop_external_holdout_eligible"] is False
    assert protocol["claim_supported"] is False
    assert "fresh independent holdout" in protocol["claim_limit"]
    provider_protocol = provider_basis["public_h2protocol_validation_boundary"]
    assert provider_protocol["case_count"] == 36
    assert provider_protocol["fresh_holdout_available"] is False
    # Direct questions receive the same privacy-bounded provenance summary as
    # sensor-analysis turns, so the provider cannot collapse station-side
    # evidence into a generic "no data" answer.
    assert provider_basis["data_used"]["station_data"][
        "deduplicated_rows"
    ] == 56_854_143
    assert provider_basis["data_used"]["station_data"][
        "full_loop_validation"
    ] is False
