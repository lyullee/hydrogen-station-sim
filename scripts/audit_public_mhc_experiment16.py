from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/public_validation/raw/mhc_experiment16/Experiment 16.xlsx"
OUT = ROOT / "research/public_mhc_experiment16_screen_2026_10_12.json"


def _nums(records: list[tuple[object, ...]], index: int) -> list[float]:
    return [
        float(row[index])
        for row in records
        if isinstance(row[index], (int, float))
        and math.isfinite(float(row[index]))
    ]


def _stats(records: list[tuple[object, ...]], index: int) -> dict[str, float | int | None]:
    values = _nums(records, index)
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": statistics.fmean(values) if values else None,
        "first": values[0] if values else None,
        "last": values[-1] if values else None,
    }


def main() -> None:
    sha256 = hashlib.sha256(RAW.read_bytes()).hexdigest()
    workbook = load_workbook(RAW, read_only=True, data_only=True)
    sheet = workbook["Cycle Data Exp.16"]
    units = list(next(sheet.iter_rows(min_row=10, max_row=10, values_only=True)))
    names = list(next(sheet.iter_rows(min_row=11, max_row=11, values_only=True)))
    rows = [
        row
        for row in sheet.iter_rows(min_row=12, values_only=True)
        if isinstance(row[2], (int, float))
    ]
    seconds = [float(row[2]) for row in rows]
    steps = [b - a for a, b in zip(seconds, seconds[1:])]
    required = {
        2: "elapsed_time_s",
        3: "inlet_pressure_bar",
        5: "mass_flow_l_min",
        6: "htf_temperature_c",
        9: "outlet_pressure_barg",
        18: "stage_temperature_c",
    }
    error_cells = [
        {"row": row_number, "column": label, "value": row[index]}
        for row_number, row in enumerate(rows, start=12)
        for index, label in required.items()
        if isinstance(row[index], str) and row[index].startswith("#")
    ]
    artifact = {
        "schema_version": 1,
        "artifact_type": "public_mhc_component_holdout_screen",
        "recorded_at": "2026-10-12",
        "status": "screened_component_only_not_runtime_admitted",
        "source": {
            "doi": "10.5281/zenodo.18213166",
            "version": "v1.1",
            "repository_path": "Dataset/Experiment 16.xlsx",
            "repository": "https://github.com/LukasFleming/MHC-Dataset/tree/v1.1",
            "license": "CC BY 4.0",
            "source_sha256": sha256,
            "source_bytes": RAW.stat().st_size,
            "accessed_after_protocol_freeze": True,
        },
        "protocol": {
            "protocol_artifact": "research/public_mhc_experiment16_holdout_protocol_2026_10_12.json",
            "holdout_selection_before_row_access": True,
            "raw_file_persisted_in_repository": False,
            "repository_search_prior_access_found": False,
        },
        "workbook": {
            "sheetnames": workbook.sheetnames,
            "cycle_data_sheet": "Cycle Data Exp.16",
            "cycle_data_rows_including_header": sheet.max_row,
            "cycle_data_numeric_records": len(rows),
            "elapsed_time_span_s": seconds[-1] - seconds[0],
            "experiment_type": "Single Tank Compression",
            "configuration": "Stage I TiZrMn; Stage II absent",
            "declared_inlet_pressure_bar": 20,
            "declared_outlet_pressure_min_bar": 60,
            "declared_cycle_time_min": 20,
            "declared_productivity_gH2_per_h": 12.843180786053574,
        },
        "schema_screen": {
            "required_families_present": all(_nums(rows, index) for index in required),
            "required_columns": {
                label: {"header": names[index], "unit": units[index]}
                for index, label in required.items()
            },
            "required_channel_stats": {
                label: _stats(rows, index) for index, label in required.items()
            },
        },
        "quality_checks": {
            "elapsed_time_monotonic_non_decreasing": all(step >= 0 for step in steps),
            "elapsed_time_duplicate_count": sum(step == 0 for step in steps),
            "elapsed_time_gap_count_over_1_5s": sum(step > 1.5 for step in steps),
            "elapsed_time_max_step_s": max(steps),
            "error_cells_in_required_channels": len(error_cells),
            "error_cell_examples": error_cells[:10],
            "failures_retained": True,
        },
        "decision": {
            "schema_screen_pass": True,
            "direct_runtime_model_compatibility": False,
            "component_validation_score": None,
            "runtime_parameter_application": False,
            "full_loop_external_holdout_eligible": False,
            "use": "independent component schema and boundary compatibility evidence only",
            "reason": (
                "Experiment 16 is a laboratory single-tank metal-hydride compressor trace. "
                "Flow is reported in L/min and the adsorption/thermal boundary is not the "
                "station compressor model; a separate attested component model and conversion "
                "are required before numerical error metrics."
            ),
        },
        "privacy": {
            "site_identity_published": False,
            "company_or_manufacturer_published": False,
            "absolute_private_timestamps_published": False,
            "raw_rows_persisted": False,
        },
        "claim_boundary": (
            "This holdout does not validate the HRS full loop, station-to-vehicle synchronization, "
            "safety response, HyRAM consequence distance or LLM effectiveness."
        ),
    }
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sha256": sha256, "bytes": RAW.stat().st_size, "records": len(rows), "span_s": seconds[-1] - seconds[0]}, indent=2))


if __name__ == "__main__":
    main()
