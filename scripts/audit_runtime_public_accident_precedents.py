"""Audit KHK public-accident precedent routing into live LLM evidence.

The audit compares the complete citation-only map with the runtime resolver and
then builds one synthetic evidence envelope per mapped response family.  It
checks traceability and prompt delivery only; it does not score the historical
response, infer accident frequency, or establish decision-support efficacy.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from h2station.hazop.response import public_accident_precedents
from h2station.llm_grounding import build_evidence_manifest, prompt_decision_evidence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = ROOT / "research/khk_scenario_precedent_map_2026_10_04.json"
DEFAULT_OUTPUT = ROOT / "research/runtime_public_accident_precedent_routing_2026_10_07.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(map_path: Path = DEFAULT_MAP) -> dict[str, Any]:
    record = json.loads(map_path.read_text(encoding="utf-8"))
    source = record.get("source_inventory") or {}
    inventory_path = ROOT / str(source.get("path") or "")
    mapping = record.get("mapping") or {}
    expected_counts = mapping.get("playbook_case_counts") or {}
    mapped_families = sorted(expected_counts)
    rows = []
    for plan_id in mapped_families:
        all_cases = public_accident_precedents(
            plan_id, limit=None, representative=False,
        )
        representatives = public_accident_precedents(plan_id, limit=None)
        manifest = build_evidence_manifest(
            {"time_s": 0.0}, {}, [], False,
            active_conditions=[{
                "scenario": f"audit:{plan_id}",
                "sensor_id": "AUDIT",
                "state": "TRIGGER",
                "response_plan_id": plan_id,
                "response_source_ids": ["KHK_PUBLIC"],
            }],
        )
        routed = (
            manifest.get("response_evidence", {})
            .get("relevant_public_accident_precedents", {})
            .get("by_response_plan", {})
            .get(plan_id, [])
        )
        prompt_routed = (
            prompt_decision_evidence(manifest)
            .get("response_guidance", {})
            .get("relevant_public_accident_precedents", {})
            .get(plan_id, [])
        )
        rows.append({
            "response_plan_id": plan_id,
            "expected_case_count": expected_counts.get(plan_id),
            "runtime_case_count": len(all_cases),
            "representative_count": len(representatives),
            "manifest_representative_count": len(routed),
            "prompt_representative_count": len(prompt_routed),
            "case_count_matches": len(all_cases) == expected_counts.get(plan_id),
            "runtime_manifest_matches": routed == representatives,
            "prompt_projection_matches": prompt_routed == representatives,
        })
    source_integrity = bool(
        record.get("status") == "citation_only_khk_scenario_precedent_map"
        and inventory_path.is_file()
        and _sha256(inventory_path) == source.get("sha256")
        and len(record.get("cases") or []) == source.get("incident_report_count")
    )
    contract_pass = bool(
        source_integrity
        and mapped_families
        and all(
            row["case_count_matches"]
            and row["representative_count"] > 0
            and row["runtime_manifest_matches"]
            and row["prompt_projection_matches"]
            for row in rows
        )
    )
    return {
        "schema_version": 1,
        "artifact_type": "runtime_public_accident_precedent_routing_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if contract_pass else "FAIL",
        "source": {
            "precedent_map": str(map_path.relative_to(ROOT)).replace("/", "\\"),
            "precedent_map_sha256": _sha256(map_path),
            "inventory": str(inventory_path.relative_to(ROOT)).replace("/", "\\"),
            "inventory_sha256": _sha256(inventory_path) if inventory_path.is_file() else None,
            "source_digest_matches": source_integrity,
            "runtime_resolver": "src\\h2station\\hazop\\response.py",
            "runtime_resolver_sha256": _sha256(
                ROOT / "src/h2station/hazop/response.py"
            ),
            "runtime_manifest": "src\\h2station\\llm_grounding.py",
            "runtime_manifest_sha256": _sha256(
                ROOT / "src/h2station/llm_grounding.py"
            ),
        },
        "aggregate": {
            "public_report_count": len(record.get("cases") or []),
            "mapped_response_family_count": len(mapped_families),
            "runtime_routed_case_references": sum(row["runtime_case_count"] for row in rows),
            "runtime_representative_references": sum(row["representative_count"] for row in rows),
            "unmatched_response_family_count": sum(not row["case_count_matches"] for row in rows),
            "manifest_routing_failure_count": sum(not row["runtime_manifest_matches"] for row in rows),
            "prompt_projection_failure_count": sum(not row["prompt_projection_matches"] for row in rows),
            "contract_pass": contract_pass,
        },
        "response_families": rows,
        "raw_report_text_loaded": False,
        "effectiveness_claimed": False,
        "frequency_claimed": False,
        "claim_boundary": (
            "This audit verifies citation integrity and scenario-specific runtime routing "
            "of public accident precedents. It does not establish historical action "
            "correctness, response effectiveness, accident frequency, causality or safety."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = audit(args.map)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "status": result["status"],
        "public_report_count": result["aggregate"]["public_report_count"],
        "mapped_response_family_count": result["aggregate"]["mapped_response_family_count"],
    }, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
