from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_methytrucks_group_d_prospective import evaluate  # noqa: E402


RESULT = ROOT / "research/methytrucks_group_d_prospective_result_2026_10_08.json"


def test_committed_group_d_result_retains_prospective_metadata_failure() -> None:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))

    assert payload["status"] == "completed_prospective_intake_ineligible"
    assert payload["decision"] == "MODEL_SCREEN_NOT_RUN_INELIGIBLE_METADATA"
    assert payload["protocol"]["selected_file_replaced"] is False
    assert payload["protocol"]["thresholds_changed_after_access"] is False
    assert payload["file_integrity"]["zenodo_md5_match"] is True
    assert payload["file_integrity"]["raw_rows_committed"] is False
    assert payload["workbook_structure"]["sample_count"] == 720
    assert payload["workbook_structure"]["sampling_interval_s_median"] == 0.5
    unresolved = set(payload["channel_screen"]["unresolved_required"])
    assert {"vehicle_pressure", "vehicle_temperature", "engineering_units", "independent_tank_geometry"}.issubset(unresolved)
    assert payload["model_evaluation"]["executed"] is False
    assert payload["model_evaluation"]["case_specific_fitting_performed"] is False
    assert payload["full_loop_gate_impact"]["full_loop_external_validation_supported"] is False


def test_evaluator_reproduces_committed_structural_decision_from_quarantined_file() -> None:
    source = ROOT / "data/public_validation/raw/methytrucks_group_d/20241024_Test_5_SINTEF_CESAME.xlsx"
    if not source.is_file():
        return

    replay = evaluate(source)
    committed = json.loads(RESULT.read_text(encoding="utf-8"))
    assert replay["decision"] == committed["decision"]
    assert replay["file_integrity"]["sha256"] == committed["file_integrity"]["sha256"]
    assert replay["workbook_structure"] == committed["workbook_structure"]
    assert replay["channel_screen"] == committed["channel_screen"]
