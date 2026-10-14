import json
from pathlib import Path

from h2station.llm_grounding import (
    _public_zenodo_17913628_release_evidence,
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_summary,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/jankuj_zenodo_17913628_postaccess_diagnostic_2026_10_14.json"
PROTOCOL = ROOT / "research/jankuj_zenodo_17913628_pressure_holdout_protocol_2026_10_14.json"


def test_jankuj_holdout_protocol_cannot_be_reused_as_prospective_evidence():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "INVALIDATED_PRIOR_OUTCOME_ACCESS"
    assert protocol["protocol_valid"] is False
    assert protocol["source"]["raw_accessed_before_freeze"] is True
    assert protocol["invalidation"]["independent_holdout"] is False
    assert protocol["invalidation"]["validation_gate_effect"] == "none"
    assert protocol["invalidation"]["prior_artifact"] == (
        "research/jankuj_2026_pressure_decay_transfer_result_2026_10_08.json"
    )


def test_jankuj_diagnostic_is_bounded_actual_hydrogen_evidence():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["source"]["dataset_doi"] == "10.5281/zenodo.17913628"
    assert record["source"]["actual_hydrogen"] is True
    assert record["status"].startswith("POST_ACCESS_DESCRIPTIVE")
    assert record["provenance_boundary"]["raw_accessed_before_this_artifact"] is True
    assert not Path(record["protocol_reference"]).is_absolute()
    assert record["provenance_boundary"]["independent_holdout"] is False
    assert record["eligibility"]["quantitative_release_model_validation"] is False
    assert record["pressure"]["primary_descriptive_channel"] == "pressure_n2"
    assert record["pressure"]["channels"][1]["sample_count"] == 2754
    assert record["temperature"][0]["channel_count"] == 6
    assert record["temperature"][1]["channel_count"] == 6


def test_jankuj_reader_rejects_claim_promotion_and_keeps_aggregate_values():
    evidence = _public_zenodo_17913628_release_evidence()
    assert evidence is not None
    assert evidence["claim_supported"] is False
    assert evidence["validation_gate_effect"] == "none"
    assert evidence["runtime_parameter_application"] is False
    assert evidence["pressure"]["primary_descriptive_channel"] == "pressure_n2"
    assert evidence["pressure"]["channels"][1]["half_pressure_time_s"] == 1.304


def test_jankuj_evidence_is_routed_to_summary_and_decision_projection():
    frame = {"time_s": 0.0, "signals": []}
    manifest = build_evidence_manifest(
        frame=frame,
        sensor_values=[],
        impact_results=[],
        active_conditions=[],
        question="수소 누출 압력강하와 자발점화 대응을 설명해줘",
        selected_sensor=None,
        impact_calculation_attempted=False,
    )
    evidence = manifest["response_evidence"][
        "public_jankuj_actual_hydrogen_release_diagnostic"
    ]
    assert evidence["claim_supported"] is False
    summary = prompt_evidence_summary(manifest)
    assert summary["public_jankuj_actual_hydrogen_release_diagnostic"][
        "source"
    ]["dataset_doi"] == "10.5281/zenodo.17913628"
    decision = prompt_decision_evidence(manifest)
    routed = decision["decision_support_evidence"][
        "public_jankuj_actual_hydrogen_release"
    ]
    assert routed["ignition_scenario_context"] is True
    assert routed["validation_gate_effect"] == "none"
