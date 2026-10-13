import importlib.util
import json
from pathlib import Path

import pytest

from h2station.hazop.response import load_playbooks
from h2station.llm_grounding import (
    build_evidence_manifest,
    prompt_decision_evidence,
    prompt_evidence_header,
)


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_committed_hydelta_ventilation_evidence_is_bounded_and_grounded():
    evidence = json.loads((
        ROOT / "research/hydelta_natural_ventilation_evidence_2026_10_13.json"
    ).read_text(encoding="utf-8"))
    assert evidence["status"] == "verified_report_level_natural_ventilation_evidence"
    assert evidence["source"]["doi"] == "10.5281/zenodo.8164602"
    assert evidence["source"]["license"] == "CC BY 4.0"
    assert evidence["source"]["publisher_file_identity"]["identity_match"] is True
    assert evidence["experiment_scope"]["actual_hydrogen"] is True
    assert evidence["experiment_scope"]["measured_case_count"] == 10
    assert all(evidence["claim_checks"].values())
    assert evidence["runtime_use"] == {
        "emergency_response_grounding": True,
        "ventilation_as_single_safe_state_proof_authorized": False,
        "measured_gas_clearance_required": True,
        "dispersion_proxy_calibration": False,
        "alarm_setpoint_calibration": False,
        "station_release_model_validation": False,
        "site_safety_distance_validation": False,
        "raw_machine_readable_time_series_available": False,
    }

    playbooks = load_playbooks()
    source = playbooks["sources"]["HYDELTA_VENTILATION_2023"]
    assert source["license"] == "CC BY 4.0"
    gas_release = next(
        plan for plan in playbooks["plans"] if plan["id"] == "gas_release"
    )
    assert "HYDELTA_VENTILATION_2023" in gas_release["sources"]
    stabilize = " ".join(gas_release["stabilize"])
    assert "환기가 작동한다는 표시만으로 안전을 선언하지 않는다" in stabilize
    assert "독립 계측" in stabilize


def test_ventilation_evidence_enters_decision_only_for_linked_response():
    frame = {"time_s": 1.0, "header_pressure_mpa": 45.0}
    idle = build_evidence_manifest(frame, {}, [], False)
    idle_decision = prompt_decision_evidence(idle)
    assert "natural_ventilation" not in idle_decision["response_guidance"]
    header = prompt_evidence_header(idle)["public_natural_ventilation_evidence"]
    runtime_use = header["runtime_use"]
    assert runtime_use["ventilation_as_single_safe_state_proof_authorized"] is False
    assert runtime_use["measured_gas_clearance_required"] is True
    assert runtime_use["dispersion_proxy_calibration"] is False

    active = build_evidence_manifest(
        frame,
        {},
        [],
        False,
        active_conditions=[{
            "scenario": "수소 누출·가스검지 상승",
            "response_plan_id": "gas_release",
            "response_source_ids": ["HYDELTA_VENTILATION_2023"],
        }],
    )
    guidance = prompt_decision_evidence(active)["response_guidance"][
        "natural_ventilation"
    ]
    assert guidance["hydrogen_accumulates_as_upper_blanket"] is True
    assert guidance["ventilation_mitigates_but_does_not_guarantee_below_lfl"] is True
    assert guidance["ventilation_as_single_safe_state_proof_authorized"] is False
    assert guidance["measured_gas_clearance_required"] is True
    assert guidance["measure_before_opening_recommended"] is True
    assert any(
        item["id"] == "HYDELTA_VENTILATION_2023"
        and item["url"] == "https://doi.org/10.5281/zenodo.8164602"
        for item in prompt_evidence_header(active)["public_source_links"]
    )


def test_local_source_pdf_still_matches_when_available():
    pdf = ROOT / "data/public_validation/raw/hydelta_8164602" / (
        "D6B_1_2_HyDelta_Tweede_Tranche_Ventilation_in_Gas_Stations_EN.pdf"
    )
    if not pdf.is_file():
        pytest.skip("publisher PDF is intentionally not committed")
    module = _load_script("audit_hydelta_natural_ventilation.py")
    report = module.audit(pdf)
    assert report["status"] == "verified_report_level_natural_ventilation_evidence"
    assert report["source"]["publisher_file_identity"]["identity_match"] is True
    assert report["reported_findings"][
        "ventilation_mitigates_but_does_not_guarantee_below_lfl"
    ] is True


def test_runtime_grounding_audit_passes():
    module = _load_script("audit_hydelta_ventilation_runtime_grounding.py")
    report = module.audit(ROOT)
    assert report["status"] == "PASS"
    assert all(report["checks"].values())
