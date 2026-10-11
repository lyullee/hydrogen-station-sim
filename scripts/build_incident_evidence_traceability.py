"""Build a claim-bounded summary of public hydrogen-incident evidence.

The summary is deliberately metadata-only.  It records how public incident
records traverse the canonical safety/runtime recipes; it never presents a
replay as an accident reconstruction or as evidence of response effectiveness.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root: Path) -> dict[str, Any]:
    hiad_path = root / "research/hiad_digital_twin_replay_coverage_2026_10_08.json"
    khk_path = root / "research/khk_digital_twin_replay_coverage_2026_10_08.json"
    response_path = root / "research/hiad_accident_response_coverage_evaluation_2026_10_05.json"
    hiad = _load(hiad_path)
    khk = _load(khk_path)
    response = _load(response_path)
    return {
        "schema_version": 1,
        "artifact_type": "public_incident_evidence_traceability_summary",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": [
            {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": _sha256(path)}
            for path in (hiad_path, khk_path, response_path)
        ],
        "hiad": {
            "case_count": hiad["aggregate"]["case_count"],
            "trace_pass_count": hiad["aggregate"]["integration_trace_pass_count"],
            "direct_physical_replay_cases": hiad["aggregate"]["representation_case_counts"]["direct_physical_replay"],
            "proxy_partial_replay_cases": hiad["aggregate"]["representation_case_counts"]["proxy_partial_replay"],
            "response_only_cases": hiad["aggregate"]["representation_case_counts"]["response_only_no_physical_model"],
            "mapped_family_count": hiad["aggregate"]["mapped_family_count"],
            "executable_family_recipes": hiad["runtime"]["unique_family_recipes_run"],
            "passed_family_recipes": hiad["runtime"]["family_recipe_pass_count"],
        },
        "khk": {
            "public_report_count": khk["aggregate"]["public_report_count"],
            "incident_code_count": khk["aggregate"]["incident_code_count"],
            "in_scope_report_count": khk["aggregate"]["in_scope_report_count"],
            "in_scope_incident_code_count": khk["aggregate"]["in_scope_incident_code_count"],
            "trace_pass_report_count": khk["aggregate"]["integration_trace_pass_report_count"],
            "trace_pass_incident_code_count": khk["aggregate"]["integration_trace_pass_incident_code_count"],
            "direct_canonical_replay_reports": khk["aggregate"]["representation_report_counts"]["direct_canonical_family_replay"],
            "proxy_partial_replay_reports": khk["aggregate"]["representation_report_counts"]["proxy_partial_replay"],
            "executable_family_recipes": khk["runtime"]["family_recipe_count"],
            "passed_family_recipes": khk["runtime"]["family_recipe_pass_count"],
        },
        "response_grounding": {
            "case_count": response["aggregate"]["case_count"],
            "cases_with_public_action_categories": response["aggregate"]["public_action_category_case_count"],
            "action_category_count": response["aggregate"]["category_count"],
            "covered_action_category_count": response["aggregate"]["covered_category_count"],
            "contract_pass": response["aggregate"]["contract_pass"],
        },
        "supported_claim": "Public incident metadata can be mapped to registered staged response families and used as traceability evidence for grounded decision-support prompts.",
        "excluded_claims": [
            "accident reconstruction",
            "accident frequency or calibrated risk",
            "site separation distance or consequence validation",
            "operator effectiveness or improved human safety",
        ],
    }


def markdown(summary: dict[str, Any]) -> str:
    h, k, r = summary["hiad"], summary["khk"], summary["response_grounding"]
    source_lines = "\n".join(f"- `{s['path']}` — SHA-256 `{s['sha256']}`" for s in summary["sources"])
    return f"""# Public incident evidence traceability (2026-10-12)

This companion records how public incident metadata traverses the canonical
runtime and staged response plans. It is not accident reconstruction or a
human-effectiveness study.

## Coverage

| Source | Records/codes | Trace result | Representation |
|---|---:|---:|---|
| HIAD 2.2 HRS subset | {h['case_count']} cases | {h['trace_pass_count']}/{h['case_count']} traces | {h['direct_physical_replay_cases']} direct, {h['proxy_partial_replay_cases']} proxy, {h['response_only_cases']} response-only |
| KHK public reports | {k['public_report_count']} reports / {k['incident_code_count']} codes | {k['trace_pass_report_count']} reports / {k['trace_pass_incident_code_count']} codes | {k['direct_canonical_replay_reports']} direct, {k['proxy_partial_replay_reports']} proxy; one out-of-scope chemical case |

HIAD executed {h['passed_family_recipes']}/{h['executable_family_recipes']} family recipes.
KHK executed {k['passed_family_recipes']}/{k['executable_family_recipes']} family recipes.
The HIAD response contract covered {r['covered_action_category_count']}/{r['action_category_count']} action categories across {r['cases_with_public_action_categories']} cases; contract pass: `{r['contract_pass']}`.

## Interpretation boundary

The evidence supports metadata-to-runtime traceability and grounding of staged
response prompts. Incident narratives do not set pressure, temperature, leak
size, enclosure geometry, heat flux or event timing in the canonical recipes.
The summary therefore does not support accident reconstruction, calibrated
frequency/risk, site separation distance, or operator/human-safety effectiveness.

## Source hashes

{source_lines}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path, default=Path("research/incident_evidence_traceability_2026_10_12.json"))
    parser.add_argument("--md-output", type=Path, default=Path("research/INCIDENT_EVIDENCE_TRACEABILITY_2026_10_12.md"))
    args = parser.parse_args()
    root = args.root.resolve()
    result = build(root)
    for path, content in ((args.json_output, json.dumps(result, ensure_ascii=False, indent=2) + "\n"), (args.md_output, markdown(result))):
        target = path if path.is_absolute() else root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    print(json.dumps({"case_count": result["hiad"]["case_count"], "khk_codes": result["khk"]["incident_code_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
