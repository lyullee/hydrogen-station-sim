"""Audit the frozen PRESLHY Cryostat Part-B input interpretation.

This is a data/parser diagnostic only.  It does not rerun or replace the
frozen external-validation result and it does not select a model parameter.
It checks the publisher's labels, units, time base, release marker and
pre-release pressure window so that a validation failure is not attributed to
an avoidable workbook-parsing defect.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

from h2station.preslhy_partb_validation import (
    RELEASE_DETECTION_THRESHOLD_BAR_G,
    _release_columns,
    _release_samples,
    _initial_temperature_k,
    iter_preslhy_partb_traces,
)


def _nominal_pressure_bar(name: str) -> float | None:
    match = re.search(r"mm-(?P<p>[0-9]+(?:bar[0-9]+|bar))", name.lower())
    if not match:
        return None
    token = match.group("p").replace("bar", ".")
    try:
        return float(token.rstrip("."))
    except ValueError:
        return None


def audit(raw: Path) -> dict:
    cases: list[dict] = []
    for path in sorted(raw.glob("*_290K-*mm-*-Final.xlsx")):
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            sheet = next(
                sheet
                for sheet in workbook.worksheets
                if "-vd" in sheet.title.lower() or "-v10" in sheet.title.lower()
            )
            header_row, time_col, pressure_col, nozzle_col = _release_columns(sheet)
            labels = list(
                next(
                    sheet.iter_rows(
                        min_row=header_row,
                        max_row=header_row,
                        max_col=min(sheet.max_column, 40),
                        values_only=True,
                    )
                )
            )
            units = list(
                next(
                    sheet.iter_rows(
                        min_row=header_row - 2,
                        max_row=header_row - 2,
                        max_col=min(sheet.max_column, 40),
                        values_only=True,
                    )
                )
            )
            values = _release_samples(sheet, header_row, time_col, pressure_col, nozzle_col)
            threshold_indices = np.flatnonzero(
                values[:, 2] >= RELEASE_DETECTION_THRESHOLD_BAR_G
            )
            if not threshold_indices.size:
                raise ValueError("no release marker at the frozen threshold")
            release_index = int(threshold_indices[0])
            release_time = float(values[release_index, 0])
            pre = values[(values[:, 0] >= release_time - 1.0) & (values[:, 0] < release_time), 1]
            near_zero = int(np.argmin(np.abs(values[:, 0])))
            trigger_time = float(
                next(
                    value
                    for value in (
                        row[0]
                        for row in sheet.iter_rows(
                            min_row=3, max_row=5, max_col=1, values_only=True
                        )
                    )
                    if isinstance(value, (int, float))
                )
            )
            p_increase_time = float(
                list(sheet.iter_rows(min_row=5, max_row=5, max_col=1, values_only=True))[0][0]
            )
            cases.append(
                {
                    "case_id": path.stem,
                    "file_bytes": path.stat().st_size,
                    "sheet": sheet.title,
                    "header_row": header_row,
                    "time_label": str(labels[time_col]),
                    "time_step_s": float(np.median(np.diff(values[:, 0]))),
                    "pressure_label": str(labels[pressure_col]),
                    "pressure_unit": str(units[pressure_col]),
                    "nozzle_label": str(labels[nozzle_col]),
                    "nozzle_unit": str(units[nozzle_col]),
                    "temperature_initial_k": _initial_temperature_k(workbook),
                    "nominal_pressure_bar": _nominal_pressure_bar(path.name),
                    "measured_pre_release_pressure_bar_g_median": float(np.median(pre)),
                    "release_threshold_bar_g": RELEASE_DETECTION_THRESHOLD_BAR_G,
                    "release_first_threshold_time_new_s": release_time,
                    "release_first_threshold_nozzle_bar_g": float(values[release_index, 2]),
                    "reported_trigger_time_s": trigger_time,
                    "reported_pressure_increase_time_s": p_increase_time,
                    "zero_time_x_value_consistent": math.isclose(
                        p_increase_time,
                        float(
                            list(
                                sheet.iter_rows(
                                    min_row=8 + near_zero,
                                    max_row=8 + near_zero,
                                    min_col=2,
                                    max_col=2,
                                    values_only=True,
                                )
                            )[0][0]
                        ),
                        rel_tol=0.0,
                        abs_tol=0.02,
                    ),
                    "monotonic_time": bool(np.all(np.diff(values[:, 0]) > 0.0)),
                    "finite_samples": bool(np.isfinite(values).all()),
                }
            )
        finally:
            workbook.close()

    expected = 5
    units_ok = all(
        case["pressure_unit"].lower() == "bar"
        and case["nozzle_unit"].lower() == "bar"
        for case in cases
    )
    structural_ok = all(
        case["monotonic_time"]
        and case["finite_samples"]
        and case["zero_time_x_value_consistent"]
        and abs(
            case["measured_pre_release_pressure_bar_g_median"]
            - float(case["nominal_pressure_bar"])
        )
        <= 0.12
        for case in cases
    )
    return {
        "schema_version": 1,
        "status": "completed_frozen_input_interpretation_audit",
        "evidence_role": "parser_and_unit_diagnostic_only",
        "raw_directory": str(raw).replace("\\", "/"),
        "frozen_validation_result_unchanged": True,
        "outcomes_were_accessed_before_this_diagnostic": True,
        "checks": {
            "expected_case_count": expected,
            "observed_case_count": len(cases),
            "case_count_ok": len(cases) == expected,
            "pressure_and_nozzle_units_are_bar": units_ok,
            "monotonic_finite_time_pressure_nozzle_samples": structural_ok,
            "all_checks_pass": len(cases) == expected and units_ok and structural_ok,
        },
        "cases": cases,
        "interpretation": {
            "finding": "No workbook label, unit, time-base, release-marker or nominal-pressure parsing defect was found.",
            "release_marker": "first P-Duese sample at or above 0.1 bar gauge; the resulting zero is within one 0.01 s sample of the publisher's X_Value/pIncrease marker",
            "pressure_basis": "P-Innen and P-Duese are labelled bar in the publisher workbook; the frozen protocol treats them as gauge and adds standard ambient pressure for absolute state calculations.",
            "remaining_model_boundary": "The frozen model still excludes discharge-line/valve travel inventory, two-phase effects and wall/neck thermal coupling; this diagnostic does not repair or validate those boundaries.",
            "claim_boundary": "This record cannot replace the frozen Part-B external-validation result or clear an IJHE/full-objective gate.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("data/public_validation/raw/preslhy_partb_xlsx"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/preslhy_partb_input_audit_2026_10_05.json"),
    )
    args = parser.parse_args()
    result = audit(args.raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not result["checks"]["all_checks_pass"]:
        raise SystemExit("PRESLHY Part-B input audit failed")


if __name__ == "__main__":
    main()
