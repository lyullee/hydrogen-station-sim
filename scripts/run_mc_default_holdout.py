"""Run the prospectively frozen Powertech MC Default external holdout.

The archive is acquired separately and is not redistributed.  The evaluator
refuses to run if production physics files differ from the pre-outcome commit.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.run_h2protocol_validation import (
    SCREENING_LIMITS,
    _aggregate,
    _read_csv,
    _run_case_file,
    _write_csv,
)


FROZEN_MODEL_FILES = (
    "src/h2station/dispenser.py",
    "src/h2station/full_station.py",
    "src/h2station/operations.py",
    "src/h2station/protocol.py",
    "src/h2station/safe_operation.py",
    "src/h2station/scenario.py",
    "src/h2station/vehicle.py",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
    ).stdout.strip()


def _worktree_dirty() -> bool:
    return bool(subprocess.run(
        ["git", "status", "--porcelain"], check=True, capture_output=True, text=True,
    ).stdout.strip())


def _assert_frozen_model(commit: str) -> None:
    result = subprocess.run(
        ["git", "diff", "--quiet", commit, "--", *FROZEN_MODEL_FILES],
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            "Production model files differ from the prospectively frozen commit; "
            "the holdout must not be run on this worktree."
        )


def _prepare_summary(row: dict[str, str], index: int) -> dict[str, str]:
    result = dict(row)
    result["lab_test_number"] = str(index)
    result["scheduled_aprr_mpa_min"] = row["protocol_effective_aprr_mpa_min"]
    result["target_vehicle_pressure_mpa"] = row["protocol_target_pressure_mpa"]
    return result


def _write_report(path: Path, report: dict) -> None:
    aggregate = report["aggregate"]
    lines = [
        "# Prospectively frozen MC Default external holdout",
        "",
        f"Generated: {report['generated_at']}",
        f"Evaluation commit: `{report['source_commit']}`",
        f"Frozen model commit: `{report['frozen_model_commit']}`",
        f"Archive SHA-256: `{report['archive_sha256']}`",
        "",
        "> The eight workbook outcomes were unopened when the protocol and case list "
        "were committed. No case-specific fitting, post-freeze parameter tuning, "
        "dynamic time warping or failed-case exclusion was permitted.",
        "",
        "## Decision",
        "",
        f"Joint engineering-screen pass: {aggregate['screening_pass_count']}/"
        f"{aggregate['case_count']} "
        f"({100.0 * aggregate['screening_pass_fraction']:.1f}%).",
        "",
        "The MC Default workbook schedule is represented by its endpoint-equivalent "
        "average pressure ramp because the frozen production controller accepts one "
        "constant APRR. This is a disclosed approximation and is not an implementation "
        "or certification of the proprietary MC Formula.",
        "",
        "## Per-case results",
        "",
        "| Case | Chamber | Effective APRR | P RMSE | T RMSE | Final SOC error | Screen |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["cases"]:
        lines.append(
            f"| {row['case_id']} | {row['chamber_temperature_c']:.1f} °C | "
            f"{row['scheduled_aprr_mpa_min']:.2f} MPa/min | "
            f"{row['pressure_rmse_mpa']:.2f} MPa | "
            f"{row['temperature_rmse_c']:.2f} °C | "
            f"{row['soc_final_error_percentage_points']:.2f} %p | "
            f"{'PASS' if row['screening_pass'] else 'FAIL'} |"
        )
    lines.extend([
        "",
        "## Scope",
        "",
        "The experiment observes vehicle pressure, tank temperature, SOC, mass flow, "
        "inlet temperature and high-pressure source channels. It independently tests "
        "the frozen vehicle-fueling control, precooling and tank-response chain. The "
        "bench data do not expose all internal three-bank valve commands, so a passing "
        "result would not alone validate every station dispatch state or field safety.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/mc_default_external_holdout_protocol.json"),
    )
    parser.add_argument(
        "--processed", type=Path,
        default=Path("data/public_validation/processed"),
    )
    parser.add_argument(
        "--raw-archive", type=Path,
        default=Path(
            "data/public_validation/raw/h2protocol_mc_default/"
            "SAE J2601 MC Default Bench Test Data.zip"
        ),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/public_validation/results/closed_loop_external_holdout"),
    )
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()

    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    frozen_commit = protocol["frozen_model"]["git_commit"]
    _assert_frozen_model(frozen_commit)
    archive_hash = _sha256(args.raw_archive)
    if archive_hash != protocol["source"]["archive_sha256"]:
        raise SystemExit("MC Default archive checksum does not match the frozen protocol")

    source_rows = _read_csv(args.processed / "mc_default_cases.csv")
    selected = protocol["selected_workbooks"]
    by_member = {row["source_member"]: row for row in source_rows}
    if set(by_member) != set(selected) or len(source_rows) != 8:
        raise SystemExit("Processed MC Default case set differs from the frozen selection")
    summaries = [
        _prepare_summary(by_member[member], index)
        for index, member in enumerate(selected, start=1)
    ]

    tank_fit = {
        "effective_volume_multiplier": float(
            protocol["frozen_model"]["effective_volume_multiplier"]
        ),
        "gas_liner_ua_multiplier": float(
            protocol["frozen_model"]["gas_liner_ua_multiplier"]
        ),
    }
    flow_multiplier = float(
        protocol["frozen_model"]["dispenser_flow_area_multiplier"]
    )
    rows = []
    if args.jobs <= 1:
        for summary in summaries:
            rows.append(_run_case_file(
                summary,
                args.processed / "mc_default_traces" / f"{summary['case_id']}.csv",
                tank_fit,
                flow_multiplier,
            ))
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = {
                pool.submit(
                    _run_case_file,
                    summary,
                    args.processed / "mc_default_traces" / f"{summary['case_id']}.csv",
                    tank_fit,
                    flow_multiplier,
                ): index
                for index, summary in enumerate(summaries)
            }
            ordered = {}
            for future in as_completed(futures):
                ordered[futures[future]] = future.result()
            rows = [ordered[index] for index in range(len(summaries))]

    source_dirty = _worktree_dirty()
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "source_worktree_dirty": source_dirty,
        "protocol_frozen_before_data_access": True,
        "protocol": str(args.protocol),
        "frozen_model_commit": frozen_commit,
        "frozen_model_files": list(FROZEN_MODEL_FILES),
        "archive_sha256": archive_hash,
        "screening_limits": SCREENING_LIMITS,
        "schedule_mapping": "publisher pressure-schedule endpoint-equivalent constant APRR",
        "post_freeze_parameter_tuning": False,
        "aggregate": _aggregate(rows),
        "cases": rows,
        "scope_limitations": [
            "No claim of SAE J2601 MC Formula implementation or certification.",
            "The bench files do not expose every internal three-bank valve command.",
            "Source pressure channels are retained for traceability but are not uniquely mappable to the demonstrator's low/medium/high bank topology.",
            "A passing vehicle-side result cannot by itself establish field-wide station safety.",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(args.output / "case_metrics.csv", rows)
    _write_report(args.output / "report.md", report)
    print(args.output / "report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
