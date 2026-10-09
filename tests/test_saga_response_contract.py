"""Safety-response structure is complete before it is handed to the UI/LLM."""

from h2station.hazop.response import (
    load_playbooks,
    response_guidance_contract_issues,
    structured_guidance,
)


def test_every_playbook_has_a_traceable_five_stage_guidance_contract():
    selection = [
        {"plan": plan, "evidence": ["contract test"], "score": 1}
        for plan in load_playbooks()["plans"]
    ]
    guidance = structured_guidance(selection, actual_alert=False)
    assert guidance is not None
    assert response_guidance_contract_issues(guidance) == []
    assert len(guidance["plans"]) == len(selection)


def test_active_alert_contract_requires_common_steps():
    plan = load_playbooks()["plans"][0]
    guidance = structured_guidance(
        [{"plan": plan, "evidence": ["alarm"], "score": 1}],
        actual_alert=True,
    )
    assert guidance is not None
    assert guidance["common_steps"]
    assert response_guidance_contract_issues(guidance) == []

    broken = {**guidance, "common_steps": []}
    assert "active alerts require common_steps" in response_guidance_contract_issues(broken)


def test_contract_rejects_missing_stage_and_untraceable_source():
    issues = response_guidance_contract_issues({
        "actual_alert": False,
        "common_steps": [],
        "plans": [{
            "title": "누출",
            "recognition": ["확인"],
            "immediate": ["차단"],
            "stabilize": [],
            "restart": ["승인"],
            "prevention": ["점검"],
            "sources": [{"title": "untrusted", "url": "http://example.invalid"}],
        }],
    })
    assert "plans[0].stabilize is empty" in issues
    assert "plans[0].sources[0] is not traceable" in issues
