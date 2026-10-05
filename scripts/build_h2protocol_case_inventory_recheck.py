"""Freeze the consumed-case boundary for the public H2Protocol archives.

This is an intake/audit utility, not a model-fitting or validation runner.  It
prevents an already-inspected case from being presented as a new holdout.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _csv_ids(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sorted(row["case_id"] for row in csv.DictReader(handle))


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_ids(path: Path) -> list[str]:
    return sorted(
        str(row["case_id"])
        for row in (_json(path).get("cases") or [])
        if row.get("case_id")
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build() -> dict:
    tables_csv = ROOT / "data/public_validation/processed/h2protocol_cases.csv"
    mc_csv = ROOT / "data/public_validation/processed/mc_default_cases.csv"
    tables_cases = _csv_ids(tables_csv)
    mc_cases = _csv_ids(mc_csv)

    consumed_sources = {
        "tank_model_all_cases_prequality_screen": _case_ids(
            ROOT / "data/public_validation/results/tank_model_all_cases/validation.json"
        ),
        "tank_model_validation_v2": _case_ids(
            ROOT / "research/tank_model_validation_v2.json"
        ),
        "closed_loop_development_v2": _case_ids(
            ROOT / "data/public_validation/results/closed_loop_development_v2/validation.json"
        ),
        "closed_loop_internal_comparison_v2": _case_ids(
            ROOT / "data/public_validation/results/closed_loop_internal_comparison_v2/validation.json"
        ),
    }
    mc_consumed = {
        "closed_loop_external_holdout": _case_ids(
            ROOT / "data/public_validation/results/closed_loop_external_holdout/validation.json"
        )
    }

    tables_consumed = sorted(
        set().union(*[set(values) for values in consumed_sources.values()])
    )
    tables_unaccounted = sorted(set(tables_cases) - set(tables_consumed))
    mc_unaccounted = sorted(set(mc_cases) - set(mc_consumed["closed_loop_external_holdout"]))

    archive_paths = sorted(
        (ROOT / "data/public_validation/raw/h2protocol_j2601_tables").glob("*.zip")
    ) + sorted((ROOT / "data/public_validation/raw/h2protocol_mc_default").glob("*.zip"))

    return {
        "schema_version": 1,
        "recorded_at": "2026-10-05",
        "purpose": "Determine whether an uninspected public H2Protocol case remains for a fresh station-to-vehicle holdout.",
        "evidence_role": "DATA_INTAKE_BOUNDARY_ONLY",
        "source_rights_boundary": "The H2Protocol files are used locally for verification. No redistribution or broader publication right is inferred from the download page.",
        "tables_method": {
            "processed_case_count": len(tables_cases),
            "case_ids": tables_cases,
            "consumed_by": consumed_sources,
            "unaccounted_case_ids": tables_unaccounted,
            "fresh_holdout_eligible_case_ids": [],
            "interpretation": "All 36 Tables Method cases are present in an inspected tank or closed-loop protocol record; H2P-L10 is explicitly excluded by the current mass-closure quality screen but is not fresh because its outcome was already inspected."
        },
        "mc_default": {
            "processed_case_count": len(mc_cases),
            "case_ids": mc_cases,
            "consumed_by": mc_consumed,
            "unaccounted_case_ids": mc_unaccounted,
            "fresh_holdout_eligible_case_ids": [],
            "interpretation": "All eight MC Default cases are already in the frozen external holdout; none can be reopened as a fresh independent test."
        },
        "archive_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): _sha256(path)
            for path in archive_paths
        },
        "decision": "NO_UNUSED_PUBLIC_H2PROTOCOL_CASE_FOR_FRESH_FULL_LOOP_HOLDOUT",
        "gate_impact": "full_loop_external_validation_remains_open",
        "next_required_evidence": [
            "independent synchronized station-to-vehicle logger archive",
            "common time base plus vehicle pressure, temperature and transferred mass",
            "station source pressure, inlet temperature, controller/valve state and protocol metadata",
            "written reuse rights for derived metrics and journal publication",
            "pre-access frozen no-fitting scoring protocol"
        ],
        "claim_boundary": "This inventory proves only that the currently downloaded H2Protocol cases have already entered inspected protocols. It is not a validation result and does not permit IJHE or goal completion."
    }


def main() -> None:
    output = ROOT / "research/h2protocol_case_inventory_recheck_2026_10_05.json"
    output.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
