import importlib.util
import json
from pathlib import Path

import pytest

from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
)
from h2station.hazop.response import load_playbooks


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_hydelta_evidence_is_bounded_and_runtime_grounded():
    evidence = json.loads((
        ROOT / "research/hydelta_controlled_flare_evidence_2026_10_08.json"
    ).read_text(encoding="utf-8"))
    assert evidence["status"] == "verified_report_level_controlled_flare_evidence"
    assert evidence["source"]["doi"] == "10.5281/zenodo.20817291"
    assert evidence["source"]["license"] == "CC BY 4.0"
    assert evidence["source"]["publisher_file_identity"]["identity_match"] is True
    assert all(evidence["claim_checks"].values())
    runtime = evidence["runtime_use"]
    assert runtime["emergency_response_grounding"] is True
    assert runtime["applies_only_to_engineered_approved_controlled_flare"] is True
    assert runtime["ad_hoc_ignition_of_vent_stream_authorized"] is False
    assert runtime["station_release_model_validation"] is False
    assert runtime["site_safety_distance_validation"] is False

    playbooks = load_playbooks()
    assert playbooks["sources"]["HYDELTA_FLARE_2026"]["license"] == "CC BY 4.0"
    plans = {item["id"]: item for item in playbooks["plans"]}
    assert all(
        "HYDELTA_FLARE_2026" in plans[plan_id]["sources"]
        for plan_id in ("relief_discharge", "vent_fault")
    )
    text = " ".join(plans["relief_discharge"]["stabilize"])
    assert "임의 점화하지 않는다" in text


def test_flare_evidence_enters_compact_prompt_only_when_linked():
    frame = {"time_s": 1.0, "header_pressure_mpa": 45.0}
    idle = build_evidence_manifest(frame, {}, [], False)
    idle_decision = prompt_decision_evidence(idle)
    assert "controlled_flare" not in idle_decision["response_guidance"]
    assert prompt_evidence_header(idle)["public_controlled_flare_evidence"][
        "runtime_use"
    ]["station_release_model_validation"] is False

    active = build_evidence_manifest(
        frame,
        {},
        [],
        False,
        active_conditions=[{
            "scenario": "안전밸브 개방·벤트 방출",
            "response_plan_id": "relief_discharge",
            "response_source_ids": ["HYDELTA_FLARE_2026"],
        }],
    )
    flare = prompt_decision_evidence(active)["response_guidance"]["controlled_flare"]
    assert flare["engineered_approved_system_only"] is True
    assert flare["ad_hoc_vent_ignition_authorized"] is False
    assert flare["tested_nitrogen_boundary_volpct"] == 34.0


def test_runtime_grounding_audit_passes():
    module = _load_script("audit_hydelta_flare_runtime_grounding.py")
    report = module.audit(ROOT)
    assert report["status"] == "PASS"
    assert all(report["checks"].values())


def test_local_source_pdf_still_matches_when_available():
    pdf = ROOT / "data/public_validation/raw/hydelta_20817291" / (
        "D5_E1_HyDelta_Vierde_Tranche_Experimental_Results_Of_The_"
        "Controlled_Hydrogen_Flaring_Installation_EN.pdf"
    )
    if not pdf.is_file():
        pytest.skip("publisher PDF is intentionally not committed")
    module = _load_script("audit_hydelta_controlled_flare.py")
    report = module.audit(pdf)
    assert report["status"] == "verified_report_level_controlled_flare_evidence"
    assert report["source"]["publisher_file_identity"]["identity_match"] is True
