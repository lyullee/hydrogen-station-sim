#!/usr/bin/env python3
"""Build a claim-bounded crosswalk of the remaining release-model failures.

The crosswalk is deliberately diagnostic.  It reads already-recorded frozen
results and post-outcome diagnostics, but never rewrites a validation result,
runtime parameter, or readiness gate.  Its purpose is to identify model-form
changes that can address more than one failed gate before a new prospective
holdout is frozen.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def pct(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def build() -> dict[str, Any]:
    schefer_line = load("research/schefer_2006_line_transient_diagnostic_2026_10_09.json")
    schefer_2007 = load("research/schefer_2007_nonadiabatic_diagnostic_2026_10_14.json")
    sensitivity = load("research/release_model_posthoc_sensitivity_latest.json")
    preslhy = load("research/preslhy_blowdown_external_validation.json")
    preslhy_freeze = load("research/preslhy_blowdown_freeze_integrity_audit_2026_10_13.json")
    part_b = load("research/preslhy_partb_nonadiabatic_diagnostic_2026_10_05.json")
    proust = load("research/proust_release_boundary_semantics_diagnostic_2026_10_12.json")

    sensitivity_by_case = {item["case_id"]: item for item in sensitivity["cases"]}
    proust_ranges = [item["effective_cd_range"] for item in proust["series"]]
    valve_grid = schefer_line["post_outcome_valve_time_constant_sensitivity"]
    best_valve = min(
        valve_grid,
        key=lambda item: item["outlet_flow"]["median_absolute_percentage_error_percent"],
    )
    part_b_cases = part_b["diagnostic_result"]["cases"]
    part_b_two_mm = [item for item in part_b_cases if "2mm" in item["case_id"]]

    findings = [
        {
            "id": "apparatus_boundary_and_line_inventory",
            "affected_gates": [
                "schefer_transient_release_validation",
                "proust_independent_release_validation",
                "preslhy_blowdown_external_validation",
            ],
            "evidence": [
                "The Schefer line diagnostic preserves separate source/outlet boundaries but still fails the frozen timing and error screens.",
                "Proust effective discharge coefficient varies by nominal diameter, so one global coefficient cannot reconcile all series.",
                "PRESLHY performance varies strongly by nozzle diameter and pressure group.",
            ],
            "interpretation": "The controlling boundary is likely a network of vessel, line, valve and terminal restriction rather than a single fixed aperture coefficient.",
            "next_evidence": "Freeze measured line length/diameter, valve opening law, upstream pressure-temperature boundary and terminal geometry before reading outcomes.",
        },
        {
            "id": "valve_and_transient_timing",
            "affected_gates": [
                "schefer_transient_release_validation",
                "schefer_2007_pressure_decay_validation",
            ],
            "evidence": [
                f"A post-outcome 4 s source-valve sensitivity reduces Schefer 2006 outlet median APE to {best_valve['outlet_flow']['median_absolute_percentage_error_percent']:.2f}%, but does not establish a pass.",
                "Schefer 2007 non-adiabatic wall sensitivity changes the pressure transient but leaves the joint screen failed.",
            ],
            "interpretation": "Opening/closing dynamics and instrument boundary timing may explain the remaining transient mismatch, but the available traces cannot identify a production time constant.",
            "next_evidence": "Obtain a new event with valve command, valve position or flow-meter timing on the same clock as vessel pressure.",
        },
        {
            "id": "diameter_and_discharge_regime",
            "affected_gates": [
                "preslhy_blowdown_external_validation",
                "preslhy_partb_ambient_external_validation",
                "preslhy_revised_holdout_validation",
                "proust_independent_release_validation",
            ],
            "evidence": [
                f"PRESLHY's controlling frozen result is {preslhy_freeze['primary_frozen_result']['aggregate']['joint_primary_pass_fraction']:.3f} (11/22); the later {preslhy['aggregate']['joint_primary_pass_fraction']:.3f} rerun is post-outcome and demoted. The 1.0 mm group is 0/4 while 4.0 mm is 7/7 in the retained stratification.",
                f"Part-B non-adiabatic sensitivity remains {part_b['diagnostic_result']['joint_primary_pass_fraction']:.3f}; both 2 mm cases retain approximately {max(item['half_time_error_percent'] for item in part_b_two_mm):.1f}% half-time error.",
                "Proust reports diameter-dependent effective discharge coefficients.",
            ],
            "interpretation": "A single choked-flow relation is insufficient across the observed diameter and pressure regimes; a declared regime transition or measured manifold loss is needed.",
            "next_evidence": "Use an untouched campaign spanning at least two diameters and pressure regimes with measured upstream conditions and aperture/manifold geometry.",
        },
        {
            "id": "thermal_boundary",
            "affected_gates": [
                "dickens_typeiii_prospective_validation",
                "schefer_2007_pressure_decay_validation",
                "preslhy_partb_ambient_external_validation",
            ],
            "evidence": [
                "Dickens passes pressure screens but fails gas-temperature screens.",
                "Adding consumed wall-thermal sensitivity to Schefer 2007 and PRESLHY Part-B does not close the joint screens.",
            ],
            "interpretation": "Thermal state is a real limitation, but a generic wall heat-transfer coefficient alone is not sufficient; inlet and wall geometry/temperature history are under-specified.",
            "next_evidence": "Freeze measured wall mass/heat capacity, inlet temperature history and geometry for a new independent charge or blowdown event.",
        },
    ]

    return {
        "schema_version": 1,
        "artifact_type": "release_failure_crosswalk",
        "generated_from": [
            "research/schefer_2006_line_transient_diagnostic_2026_10_09.json",
            "research/schefer_2007_nonadiabatic_diagnostic_2026_10_14.json",
            "research/release_model_posthoc_sensitivity_latest.json",
            "research/preslhy_blowdown_external_validation.json",
            "research/preslhy_blowdown_freeze_integrity_audit_2026_10_13.json",
            "research/preslhy_partb_nonadiabatic_diagnostic_2026_10_05.json",
            "research/proust_release_boundary_semantics_diagnostic_2026_10_12.json",
        ],
        "evidence_role": "post_outcome_diagnostic_only",
        "claim_boundary": "This crosswalk does not promote a failed result, select a runtime parameter, or establish an independent validation claim. A new untouched holdout is required after any model change.",
        "findings": findings,
        "model_change_order": [
            "Resolve apparatus boundary and line/valve inventory.",
            "Declare diameter/regime semantics and thermal boundary inputs.",
            "Freeze the revised model and protocol before inspecting outcomes.",
            "Evaluate a new independent holdout and retain the current negative controls.",
        ],
        "diagnostic_summary": {
            "schefer_2006_best_posthoc_valve_time_constant_s": best_valve["source_valve_time_constant_s"],
            "schefer_2006_best_posthoc_outlet_median_ape_percent": best_valve["outlet_flow"]["median_absolute_percentage_error_percent"],
            "preslhy_frozen_joint_pass_fraction": preslhy_freeze["primary_frozen_result"]["aggregate"]["joint_primary_pass_fraction"],
            "preslhy_post_outcome_joint_pass_fraction": preslhy["aggregate"]["joint_primary_pass_fraction"],
            "preslhy_part_b_diagnostic_joint_pass_fraction": part_b["diagnostic_result"]["joint_primary_pass_fraction"],
            "proust_effective_cd_range_min": min(proust_ranges),
            "proust_effective_cd_range_max": max(proust_ranges),
            "schefer_2007_diagnostic_points": len(schefer_2007["metrics"]),
        },
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 방출모델 실패 게이트 교차분석",
        "",
        "이 문서는 여러 독립 검증 실패에서 반복되는 모델 경계 원인을 묶은 개발 진단이다.",
        "기존 PASS/FAIL/PENDING 판정과 런타임 파라미터는 변경하지 않는다.",
        "",
        "## 공통 원인",
        "",
    ]
    for idx, finding in enumerate(result["findings"], 1):
        lines += [
            f"### {idx}. {finding['id']}",
            f"- 영향 게이트: {', '.join(finding['affected_gates'])}",
            f"- 해석: {finding['interpretation']}",
            f"- 다음 검증 입력: {finding['next_evidence']}",
            "- 근거:",
        ]
        lines += [f"  - {item}" for item in finding["evidence"]]
        lines.append("")
    lines += [
        "## 다음 모델 동결 순서",
        "",
    ]
    lines += [f"{idx}. {item}" for idx, item in enumerate(result["model_change_order"], 1)]
    lines += [
        "",
        "## 경계",
        "",
        result["claim_boundary"],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", default="research/release_failure_crosswalk_2026_10_14.json")
    parser.add_argument("--report-output", default="research/RELEASE_FAILURE_CROSSWALK_2026_10_14.md")
    args = parser.parse_args()
    result = build()
    (ROOT / args.json_output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / args.report_output).write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result["diagnostic_summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
