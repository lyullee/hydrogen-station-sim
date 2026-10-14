from h2station.runtime_evidence_gate import runtime_evidence_gate


def test_component_screen_is_advisory_but_cannot_actuate():
    decision = runtime_evidence_gate({
        "status": "calculated",
        "consequence_validation_status": "COMPONENT_ONLY_NO_FULL_LOOP",
        "consequence_validation_scope": "COMPONENT_SCREENING_BOUNDED",
        "site_specific_safety_distance_supported": False,
        "consequence_validation_artifacts": "research/example.json",
        "release_flow_uncertainty_status": "PUBLIC_EXPERIMENT_ENVELOPE_IN_DOMAIN",
    })
    assert decision["operator_advisory_authorized"] is True
    assert decision["automatic_actuation_authorized"] is False
    assert "NO_FULL_LOOP_SITE_VALIDATION" in decision["automatic_actuation_blockers"]


def test_bad_input_blocks_advisory_and_actuation():
    decision = runtime_evidence_gate({"status": "calculated"}, input_quality="BAD")
    assert decision["operator_advisory_authorized"] is False
    assert decision["automatic_actuation_authorized"] is False
    assert "INPUT_QUALITY_NOT_GOOD" in decision["automatic_actuation_blockers"]


def test_only_declared_full_loop_site_validation_can_authorize_model_action():
    decision = runtime_evidence_gate({
        "status": "calculated",
        "consequence_validation_status": "FULL_LOOP_SITE_VALIDATED",
        "consequence_validation_scope": "SITE_BOUND",
        "site_specific_safety_distance_supported": True,
        "consequence_validation_artifacts": "signed/site-validation.json",
    })
    assert decision["automatic_actuation_authorized"] is True
    assert decision["automatic_actuation_blockers"] == []
