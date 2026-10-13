from __future__ import annotations

import subprocess

from scripts.refresh_runtime_evidence_chain import (
    READINESS_MIRRORS,
    ROOT,
    STEPS,
    RefreshStep,
    refresh,
)


def test_refresh_plan_preserves_hash_dependency_order() -> None:
    names = [step.name for step in STEPS]

    assert names.index("hydelta_cabinet_runtime_grounding") < names.index(
        "ijhe_readiness"
    )
    assert names.index("hiad_digital_twin_replay") < names.index(
        "hiad_event_category_concordance"
    )
    assert names.index("hiad_event_category_concordance") < names.index(
        "incident_evidence_traceability"
    )
    assert names.index("incident_evidence_traceability") < names.index(
        "hiad_runtime_response_handoff"
    )
    assert names.index("ijhe_readiness") < names.index(
        "ijhe_claim_evidence_matrix"
    )
    assert names.index("ijhe_readiness") < names.index(
        "validation_gap_current"
    )
    assert names.index("validation_gap_current") < names.index(
        "ijhe_blocker_matrix"
    )


def test_readiness_mirrors_come_from_the_authoritative_manuscript_outputs() -> None:
    assert READINESS_MIRRORS == (
        (
            "manuscript/ijhe_readiness_audit.json",
            "research/ijhe_readiness_audit.json",
        ),
        (
            "manuscript/IJHE_READINESS_AUDIT.md",
            "research/ijhe_readiness_audit.md",
        ),
        (
            "manuscript/IJHE_READINESS_AUDIT.md",
            "research/IJHE_READINESS_REPORT.md",
        ),
    )


def test_refresh_stops_after_the_first_failed_generator(monkeypatch) -> None:
    calls: list[str] = []
    environments: list[dict[str, str]] = []

    def fake_run(command, **kwargs):
        calls.append(command[1])
        environments.append(kwargs["env"])
        return subprocess.CompletedProcess(
            command,
            2 if command[1].endswith("fail.py") else 0,
            stdout=str(ROOT) + "\n" + str(ROOT).replace("\\", "\\\\"),
            stderr="failed" if command[1].endswith("fail.py") else "",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    steps = (
        RefreshStep("first", "scripts/first.py"),
        RefreshStep("failure", "scripts/fail.py"),
        RefreshStep("must_not_run", "scripts/last.py"),
    )

    report = refresh(steps, python="python")

    assert report["status"] == "FAIL"
    assert report["failed_step"] == "failure"
    assert len(calls) == 2
    assert not calls[-1].endswith("last.py")
    assert all(env["PYTHONIOENCODING"] == "utf-8" for env in environments)
    assert str(ROOT) not in report["steps"][0]["output_tail"]
    assert report["steps"][0]["output_tail"].count("<repository>") == 2
