"""Create a metadata-bounded descriptive summary of reachable KIT LH2 workbooks.

The input files are public but the repository does not redistribute them.  This
runner deliberately produces aggregate ranges and channel coverage only; it
does not fit a consequence model or change any runtime parameter.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, time
from pathlib import Path
from statistics import median
from typing import Any

from openpyxl import load_workbook


DEFAULT_INPUT = Path("data/public_validation/raw/kit_lh2_consequence_1483/selective")
DEFAULT_OUTPUT = Path("research/kit_lh2_exploratory_summary_2026_10_11.json")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _time_seconds(value: Any) -> float | None:
    if isinstance(value, datetime):
        return (value.hour * 3600 + value.minute * 60 + value.second
                + value.microsecond / 1_000_000)
    if isinstance(value, time):
        return value.hour * 3600 + value.minute * 60 + value.second + value.microsecond / 1_000_000
    if isinstance(value, str):
        text = value.strip()
        parts = text.split(":")
        try:
            if len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        except ValueError:
            return None
    return None


def _sheet_summary(ws: Any, *, scan_limit_rows: int = 20_000) -> dict[str, Any]:
    # Blastlogger and BlastloggerClip contain 100k–500k high-rate rows per
    # workbook.  Keep their dimensions and headers in the inventory, while
    # scanning smaller engineering channels for bounded descriptive ranges.
    if ws.max_row and ws.max_row > scan_limit_rows:
        header = []
        for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
            header = [str(value) if value is not None else "" for value in row]
        return {
            "rows": max(0, int(ws.max_row) - 1),
            "columns": header,
            "numeric_ranges": {},
            "values_scanned": False,
            "scan_limit_rows": scan_limit_rows,
        }
    rows = ws.iter_rows(values_only=True)
    try:
        header = [str(value) if value is not None else "" for value in next(rows)]
    except StopIteration:
        return {"rows": 0, "columns": [], "numeric_ranges": {}}

    values: list[list[float]] = [[] for _ in header]
    times: list[float] = []
    row_count = 0
    for row in rows:
        row_count += 1
        for index, value in enumerate(row[: len(header)]):
            numeric = _number(value)
            if numeric is not None:
                values[index].append(numeric)
            elif index == 0:
                timestamp = _time_seconds(value)
                if timestamp is not None:
                    times.append(timestamp)
    ranges: dict[str, Any] = {}
    for name, series in zip(header, values, strict=True):
        if not name or not series:
            continue
        ranges[name] = {
            "finite_count": len(series),
            "min": min(series),
            "max": max(series),
        }
    result: dict[str, Any] = {
        "rows": row_count,
        "columns": header,
        "numeric_ranges": ranges,
        "values_scanned": True,
    }
    if len(times) >= 2:
        deltas = [b - a for a, b in zip(times, times[1:]) if b > a]
        if deltas:
            result["timebase"] = {
                "finite_time_samples": len(times),
                "median_positive_interval_s": median(deltas),
                "duration_s": max(times) - min(times),
            }
    return result


def summarize(input_dir: Path, output: Path) -> dict[str, Any]:
    paths = sorted(input_dir.glob("ignited_trial_*_28-10-2019alldata.xlsx"))
    if not paths:
        raise FileNotFoundError(f"no frozen KIT members in {input_dir}")
    trials: list[dict[str, Any]] = []
    for path in paths:
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            sheets = {ws.title: _sheet_summary(ws) for ws in workbook.worksheets}
        finally:
            workbook.close()
        trials.append({"file": path.name, "sheets": sheets})
    result = {
        "schema_version": 1,
        "artifact_type": "kit_lh2_exploratory_component_summary",
        "generated_at": date.today().isoformat(),
        "protocol": "research/kit_lh2_stage2_exploratory_protocol_2026_10_11.json",
        "case_count": len(trials),
        "trials": trials,
        "numeric_values_opened_after_protocol_freeze": True,
        "parameter_fitting_performed": False,
        "runtime_parameter_changes": False,
        "validation_gate_effect": "none",
        "claim_boundary": (
            "Descriptive aggregate replay of four complete workbooks in an incomplete archive prefix. "
            "No quantitative validation, station safety-distance, HyRAM, full-loop or SAGA effectiveness claim."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = summarize(args.input, args.output)
    print(json.dumps({"status": "PASS", "case_count": result["case_count"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
