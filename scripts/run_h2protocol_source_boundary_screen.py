"""Screen the published H2Protocol upstream-pressure boundary channels.

The regular J2601 comparison intentionally uses a declared constant upstream
pressure because the normalized vehicle traces are the frozen comparison
interface.  The source workbooks also contain pressure channels (for example
``Psupply``), so this script checks whether the large baseline residual is
consistent with a missing boundary condition.

This is a post-outcome diagnostic, not an independent holdout.  It must not be
used to change the frozen validation result or to claim SAE/J2601 compliance.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

from h2station.public_validation import _active_fill_bounds, _select_numeric_column
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_partial_station_validation import _load_fit, run_case


DEFAULT_CASES = ("H2P-L01", "H2P-L06", "H2P-L10")
DATA_LANDING_PAGE = "http://www.h2protocol.com/h2-fueling-data/"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _archive_path(raw_root: Path, summary: dict[str, str]) -> Path:
    name = Path(summary["source_archive"]).name
    path = raw_root / name
    if not path.is_file():
        raise FileNotFoundError(f"Missing source archive: {path}")
    return path


def _source_profile(
    archive: Path, member: str, column: str,
) -> tuple[tuple[float, float], ...]:
    """Read one source pressure channel on the normalized active-fill clock."""

    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - research extra guard
        raise RuntimeError("Install the research extra to read H2Protocol workbooks") from exc

    with zipfile.ZipFile(archive) as bundle:
        content = bundle.read(member)
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    worksheet = workbook.worksheets[0]
    header_values = next(worksheet.iter_rows(values_only=True))
    headers = {str(value).strip(): index for index, value in enumerate(header_values) if value is not None}
    if "Time (s)" not in headers or column not in headers:
        raise ValueError(f"{member} has no complete {column} source channel")
    rows = [
        row for row in worksheet.iter_rows(min_row=2, values_only=True)
        if isinstance(row[headers["Time (s)"]], (int, float))
    ]
    _, time_all = _select_numeric_column(rows, headers, ("Time (s)",))
    _, flow_all = _select_numeric_column(rows, headers, ("FM(R)", "FM"), min_finite_fraction=0.01)
    first, last = _active_fill_bounds(time_all, flow_all, flow_threshold_g_s=1.0)
    active_rows = rows[first:last + 1]
    _, time = _select_numeric_column(active_rows, headers, ("Time (s)",))
    _, pressure = _select_numeric_column(active_rows, headers, (column,))
    finite = np.isfinite(time) & np.isfinite(pressure)
    time = time[finite]
    pressure = pressure[finite]
    if len(time) < 3 or np.any(np.diff(time) <= 0.0):
        raise ValueError(f"{member} has invalid {column} timestamps")
    t0 = float(time[0])
    return tuple((float(t - t0), float(p)) for t, p in zip(time, pressure))


def _profile_for_case(raw_root: Path, summary: dict[str, str]) -> tuple[str, tuple[tuple[float, float], ...]]:
    # Psupply is the preferred upstream boundary.  Pinlet is retained as a
    # declared fallback for workbooks where the supply channel is incomplete.
    for column in ("Psupply", "Pinlet"):
        try:
            return column, _source_profile(
                _archive_path(raw_root, summary), summary["source_member"], column
            )
        except ValueError:
            continue
    raise ValueError(f"No usable upstream pressure channel for {summary['case_id']}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/public_validation/processed"))
    parser.add_argument("--raw", type=Path, default=Path("data/public_validation/raw/h2protocol_j2601_tables"))
    parser.add_argument("--fit", type=Path, default=Path("research/closed_loop_development_v2.json"))
    parser.add_argument("--output", type=Path, default=Path("research/h2protocol_source_boundary_screen_2026_10_04.json"))
    parser.add_argument("--case-ids", nargs="*", default=list(DEFAULT_CASES))
    parser.add_argument("--physics-only-temperature-stop-c", type=float, default=2000.0)
    args = parser.parse_args()

    summaries = {
        row["case_id"]: row
        for row in _read_csv(args.processed / "h2protocol_cases.csv")
    }
    fit = _load_fit(args.fit)
    cases: list[dict] = []
    archive_hashes: dict[str, str] = {}
    for case_id in args.case_ids:
        if case_id not in summaries:
            raise SystemExit(f"Unknown case id: {case_id}")
        summary = summaries[case_id]
        trace = _read_csv(args.processed / "h2protocol_traces" / f"{case_id}.csv")
        source_column, profile = _profile_for_case(args.raw, summary)
        archive = _archive_path(args.raw, summary)
        archive_hashes[archive.name] = _sha256(archive)
        constant, _ = run_case(summary, trace, fit, maximum_gas_temperature_k=args.physics_only_temperature_stop_c)
        forced, _ = run_case(
            summary,
            trace,
            fit,
            supply_pressure_profile_mpa=profile,
            maximum_gas_temperature_k=args.physics_only_temperature_stop_c,
        )
        cases.append({
            "case_id": case_id,
            "source_archive": archive.name,
            "source_member": summary["source_member"],
            "source_pressure_column": source_column,
            "source_pressure_initial_mpa": profile[0][1],
            "source_pressure_final_mpa": profile[-1][1],
            "constant_boundary": {
                "supply_pressure_mpa": 90.0,
                "pressure_rmse_mpa": constant["pressure_rmse_mpa"],
                "temperature_rmse_c": constant["temperature_rmse_c"],
                "soc_final_error_percentage_points": constant["soc_final_error_percentage_points"],
                "screening_pass": constant["screening_pass"],
            },
            "measured_boundary_profile": {
                "pressure_rmse_mpa": forced["pressure_rmse_mpa"],
                "temperature_rmse_c": forced["temperature_rmse_c"],
                "soc_final_error_percentage_points": forced["soc_final_error_percentage_points"],
                "screening_pass": forced["screening_pass"],
            },
            "improvement": {
                "pressure_rmse_mpa": constant["pressure_rmse_mpa"] - forced["pressure_rmse_mpa"],
                "temperature_rmse_c": constant["temperature_rmse_c"] - forced["temperature_rmse_c"],
                "abs_soc_final_error_percentage_points": abs(constant["soc_final_error_percentage_points"]) - abs(forced["soc_final_error_percentage_points"]),
            },
        })

    output = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "post_outcome_boundary_diagnostic",
        "claim_boundary": (
            "The H2Protocol archive is already used by the frozen development and MC evaluations. "
            "This screen diagnoses a missing upstream boundary condition and is not an independent "
            "holdout, field validation, SAE certification, or safety claim."
        ),
        "source": {
            "landing_page": DATA_LANDING_PAGE,
            "publisher": "H2Protocol.com / Powertech Labs",
            "archive_sha256": archive_hashes,
            "source_channels": {
                "preferred": "Psupply",
                "fallback": "Pinlet",
                "units": "MPa gauge-equivalent as recorded by the workbook",
            },
        },
        "model": {
            "fit_source": str(args.fit),
            "fit": fit,
            "constant_boundary_mpa": 90.0,
            "temperature_stop_c": args.physics_only_temperature_stop_c,
            "temperature_stop_mode": "declared_physics_only_sensitivity",
        },
        "cases": cases,
        "aggregate": {
            "case_count": len(cases),
            "constant_boundary_pressure_rmse_mean_mpa": float(np.mean([c["constant_boundary"]["pressure_rmse_mpa"] for c in cases])),
            "measured_boundary_pressure_rmse_mean_mpa": float(np.mean([c["measured_boundary_profile"]["pressure_rmse_mpa"] for c in cases])),
            "measured_boundary_screening_pass_count": sum(bool(c["measured_boundary_profile"]["screening_pass"]) for c in cases),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
