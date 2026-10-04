"""Audit local KHK candidate incidents against the staged response catalogue.

The KHK/METI workbook and the generated casebook are restricted local inputs.
This command never copies either into a tracked or published output.  The
result is written below ``data/`` (which is gitignored) and is intended to
prove interface traceability only; it is not an expert, probability, safety,
or response-effectiveness validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASEBOOK = ROOT / "data/public_validation/results/khk_local_casebook/casebook.json"
DEFAULT_OUTPUT = ROOT / "data/public_validation/results/khk_local_casebook/playbook_coverage.json"
DEFAULT_REPORT = ROOT / "data/public_validation/results/khk_local_casebook/playbook_coverage.md"
PLAYBOOKS = ROOT / "src/h2station/data/emergency_playbooks.json"
STAGES = ("recognition", "immediate", "stabilize", "restart", "prevention")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(casebook: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic catalogue/stage contract result."""

    plans = {str(item.get("id")): item for item in catalog.get("plans", [])}
    rows: list[dict[str, Any]] = []
    for index, case in enumerate(casebook.get("cases", []), start=1):
        plan_ids = [str(item) for item in case.get("response_plan_candidates", [])]
        unknown = [item for item in plan_ids if item not in plans]
        missing: list[dict[str, str]] = []
        for plan_id in plan_ids:
            plan = plans.get(plan_id)
            if plan is None:
                continue
            for stage in STAGES:
                value = plan.get(stage)
                if not isinstance(value, list) or not value or not all(str(step).strip() for step in value):
                    missing.append({"plan_id": plan_id, "stage": stage})
        rows.append({
            "case_index": index,
            "candidate_plan_count": len(plan_ids),
            "unknown_plan_ids": unknown,
            "missing_stage_count": len(missing),
            "stage_contract": "pass" if plan_ids and not unknown and not missing else "fail",
        })

    aggregate = {
        "case_count": len(rows),
        "mapped_case_count": sum(row["candidate_plan_count"] > 0 for row in rows),
        "unmapped_case_count": sum(row["candidate_plan_count"] == 0 for row in rows),
        "unknown_plan_reference_count": sum(len(row["unknown_plan_ids"]) for row in rows),
        "case_with_missing_stage_count": sum(row["missing_stage_count"] > 0 for row in rows),
        "stage_contract_pass": all(row["stage_contract"] == "pass" for row in rows),
    }
    # An empty casebook is not a successful audit; it is an input failure.
    aggregate["contract_pass"] = bool(
        aggregate["case_count"] > 0
        and aggregate["mapped_case_count"] == aggregate["case_count"]
        and aggregate["unknown_plan_reference_count"] == 0
        and aggregate["case_with_missing_stage_count"] == 0
        and aggregate["stage_contract_pass"]
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "local_only_metadata_stage_contract",
        "catalog": {"path": "src/h2station/data/emergency_playbooks.json", "plan_count": len(plans), "required_stages": list(STAGES)},
        "aggregate": aggregate,
        "cases": rows,
        "limitations": [
            "The KHK workbook and casebook are local restricted inputs and are not included in this output or repository.",
            "A mapped case means only that a candidate response family and five non-empty stages exist.",
            "No incident probability, consequence distance, physics validity, expert approval or operator-effectiveness claim is made.",
            "Written source permission, coordinator approval and blinded expert scoring remain required before public validation.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--casebook", type=Path, default=DEFAULT_CASEBOOK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    if not args.casebook.exists():
        raise SystemExit(f"local KHK casebook not found: {args.casebook}")
    casebook = json.loads(args.casebook.read_text(encoding="utf-8"))
    catalog = json.loads(PLAYBOOKS.read_text(encoding="utf-8"))
    result = audit(casebook, catalog)
    result["inputs"] = {
        "casebook_sha256": _sha256(args.casebook),
        "casebook_not_committed": True,
        "catalog_sha256": _sha256(PLAYBOOKS),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    aggregate = result["aggregate"]
    args.report.write_text(
        "\n".join([
            "# Local KHK candidate-to-playbook coverage",
            "",
            "This local-only audit checks catalogue traceability. It is not an expert or safety-effectiveness validation.",
            "",
            f"- Contract: **{'PASS' if aggregate['contract_pass'] else 'FAIL'}**",
            f"- Cases mapped: **{aggregate['mapped_case_count']}/{aggregate['case_count']}**",
            f"- Cases with missing stages: **{aggregate['case_with_missing_stage_count']}**",
            f"- Unknown plan references: **{aggregate['unknown_plan_reference_count']}**",
            "",
            "The casebook and all incident descriptions remain local because KHK/METI terms restrict transfer and public posting.",
            "",
        ]),
        encoding="utf-8",
    )
    print(json.dumps(aggregate, ensure_ascii=False))
    return 0 if aggregate["contract_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
