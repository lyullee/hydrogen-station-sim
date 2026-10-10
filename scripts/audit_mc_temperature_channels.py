"""Inventory individual MC Default tank-temperature channels.

The MC Default reader historically exposed only a mean and a maximum tank
temperature.  This audit records whether the source workbooks also contain
complete individual thermocouple channels (and, where present, a publisher
reported average).  It deliberately stores no workbook rows or temperature
values and does not alter the frozen holdout result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.public_validation import iter_mc_default_traces


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_inventory(
    archive: Path,
    selected_members: Sequence[str],
    *,
    expected_archive_sha256: str | None = None,
) -> dict[str, Any]:
    traces = list(iter_mc_default_traces(archive, selected_members))
    cases: list[dict[str, Any]] = []
    for trace in traces:
        names = [name for name, _ in trace.tank_temperature_channels_c]
        independent = [name for name in names if "_Ave" not in name and "_Avg" not in name]
        aggregate = [name for name in names if name not in independent]
        cases.append({
            "case_id": trace.case_id,
            "tank_capacity_kg": trace.metadata.tank_capacity_kg,
            "active_sample_count": int(len(trace.time_s)),
            "individual_temperature_channels": independent,
            "reported_average_channels": aggregate,
            "complete_channel_count": len(names),
            "channel_contract_pass": len(independent) >= 1,
        })

    archive_sha256 = _sha256(archive)
    return {
        "schema_version": 1,
        "artifact_type": "mc_default_temperature_channel_inventory",
        "recorded_at": "2026-10-11",
        "status": "post_access_schema_diagnostic",
        "source": {
            "archive_alias": "public_mc_default_bench_archive",
            "archive_sha256": archive_sha256,
            "expected_archive_sha256": expected_archive_sha256,
            "selected_case_count": len(selected_members),
        },
        "inventory": {
            "parsed_case_count": len(cases),
            "cases_with_individual_channels": sum(
                case["channel_contract_pass"] for case in cases
            ),
            "cases_with_reported_average": sum(
                bool(case["reported_average_channels"]) for case in cases
            ),
            "cases": cases,
        },
        "privacy": {
            "raw_archive_committed": False,
            "raw_rows_persisted": False,
            "temperature_values_persisted": False,
            "source_paths_persisted": False,
            "source_member_names_persisted": False,
            "site_company_manufacturer_published": False,
        },
        "interpretation": {
            "model_use": (
                "The reader now preserves complete individual channels for future "
                "thermal-stratification diagnostics; frozen mean/max validation "
                "projections are unchanged."
            ),
            "runtime_parameter_change": False,
            "holdout_gate_change": False,
            "claim_boundary": (
                "Channel presence is schema evidence only. It does not validate "
                "sensor calibration, spatial coordinates, station control, or a "
                "full-loop refuelling model."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive", type=Path,
        default=ROOT / "data/public_validation/raw/h2protocol_mc_default/SAE J2601 MC Default Bench Test Data.zip",
    )
    parser.add_argument(
        "--protocol", type=Path,
        default=ROOT / "research/mc_default_external_holdout_protocol.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "research/mc_temperature_channel_inventory_2026_10_11.json",
    )
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    result = build_inventory(
        args.archive.resolve(),
        protocol["selected_workbooks"],
        expected_archive_sha256=protocol["source"].get("archive_sha256"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "output": str(args.output),
        "parsed_case_count": result["inventory"]["parsed_case_count"],
        "cases_with_individual_channels": result["inventory"]["cases_with_individual_channels"],
        "status": result["status"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
