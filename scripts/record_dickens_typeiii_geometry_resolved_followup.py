"""Record a source-grounded Dickens Type-III follow-up candidate.

The original Type-III result is a prospective negative validation and remains
unchanged.  This script only joins the source geometry mapping to the already
computed 5 mm post-outcome sensitivity so a future protocol can be prepared
without silently treating a tuned result as validation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "research/dickens_typeiii_source_geometry_mapping_2026_10_09.json"
DIAGNOSTIC_PATH = ROOT / "research/dickens_typeiii_mixed_convection_diagnostic_2026_10_08.json"
OUTPUT_PATH = ROOT / "research/dickens_typeiii_geometry_resolved_followup_2026_10_10.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def build() -> dict[str, Any]:
    mapping = _load(MAPPING_PATH)
    diagnostic = _load(DIAGNOSTIC_PATH)
    runs = diagnostic.get("runs") or []
    five_mm = next(
        (run for run in runs if run.get("nozzle_diameter_mm") == 5.0), None
    )
    if five_mm is None:
        raise ValueError("5 mm diagnostic run is required")
    geometry = mapping["geometry_mapping"]
    boundary = mapping["boundary_mapping"]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_type": "source_geometry_resolved_followup_candidate",
        "case_id": "dickens_typeIII",
        "status": "candidate_protocol_input_not_validation",
        "evidence_role": "post_outcome_model_development_diagnostic",
        "source_geometry": {
            "inlet_pipe_internal_diameter_m": geometry[
                "inlet_pipe_internal_diameter_m"
            ]["source_value"],
            "inlet_pipe_extension_m": geometry["inlet_pipe_extension_m"][
                "source_value"
            ],
            "tank_internal_diameter_m": geometry["tank_internal_diameter_m"][
                "source_value"
            ],
            "tank_internal_length_source_m": geometry["tank_internal_length_m"][
                "source_value"
            ],
            "tank_internal_length_archived_case_m": geometry[
                "tank_internal_length_m"
            ]["archived_case_value"],
        },
        "source_geometry_mapping_artifact": str(MAPPING_PATH.relative_to(ROOT)),
        "selected_diagnostic": {
            "nozzle_diameter_mm": five_mm["nozzle_diameter_mm"],
            "metrics": five_mm["metrics"],
            "screen_results": five_mm["screen_results"],
            "joint_primary_screen_pass": five_mm["joint_primary_screen_pass"],
        },
        "diagnostic_interpretation": {
            "all_four_frozen_screens_pass_for_candidate": bool(
                five_mm["joint_primary_screen_pass"]
            ),
            "source_geometry_confirmed_after_original_outcome": True,
            "tank_length_mapping_resolved": False,
            "time_resolved_inlet_temperature_available": boundary[
                "time_resolved_inlet_temperature_available_in_archived_case"
            ],
            "original_frozen_validation_result_changed": False,
            "runtime_parameter_updated": False,
            "validation_gate_effect": "none",
        },
        "next_protocol_requirements": [
            "Resolve whether the source 0.893 m tank length or archived 0.7451 m case length is the intended physical geometry before freezing a new run.",
            "Obtain and freeze the source time-resolved inlet hydrogen-temperature trace.",
            "Declare the 5 mm inlet diameter and 82 mm insertion before accessing any new outcome values.",
            "Evaluate an untouched filling or discharge trace and retain the result regardless of outcome.",
        ],
        "claim_boundary": (
            "The source-confirmed 5 mm geometry makes the existing mixed-convection "
            "run a physically grounded follow-up candidate. It does not promote the "
            "post-outcome sensitivity to validation, revise the original Type-III "
            "failure, change runtime parameters, or validate the HRS full loop, "
            "consequence distances, safety logic or SAGA effectiveness."
        ),
    }


def main() -> int:
    report = build()
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"output": str(OUTPUT_PATH), "joint_pass": report["selected_diagnostic"]["joint_primary_screen_pass"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
