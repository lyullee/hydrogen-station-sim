"""Audit qualitative HIAD event coverage by the current emergency playbook families.

This is a traceability/coverage audit, not an effectiveness or probability claim.
It intentionally excludes HIAD emergency-action text so that no response answer key
is reconstructed from the public evidence inventory.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "research/hiad_hrs_public_evidence.json"
PLAYBOOKS = ROOT / "src/h2station/data/emergency_playbooks.json"
OUT_JSON = ROOT / "research/hiad_playbook_coverage.json"
OUT_MD = ROOT / "research/HIAD_PLAYBOOK_COVERAGE.md"

# The rules are deliberately conservative and reviewable.  They identify a
# response-family candidate from public event metadata; they do not assert that
# the selected plan is sufficient for a real incident.
def candidate_plans(case: dict) -> list[str]:
    title = str(case.get("title", "")).lower()
    effect = str(case.get("physical_effect", "")).lower()
    consequence = str(case.get("consequence_nature", "")).lower()
    text = " ".join(str(case.get(k, "")) for k in (
        "title", "physical_effect", "consequence_nature", "sub_application", "supply_chain_stage"
    )).lower()
    plans: list[str] = []
    positive_ignition = (
        "release and ignition" in effect
        or consequence in {"fire", "explosion", "explosion followed by a fire"}
        or title.startswith("fire ")
        or title.startswith("explosion ")
    )
    if positive_ignition:
        plans.append("hydrogen_fire")
    positive_release = (
        effect.startswith("unignited hydrogen release")
        or "release and ignition" in effect
        or ("oil leak" not in title and any(token in title for token in ("release", "leak", "leakage")))
    )
    if positive_release:
        plans.append("gas_release")
    if any(token in text for token in ("hose", "nozzle", "filling hose", "threaded joint")):
        plans.append("hose_connection")
    if "freezing" in text or "precool" in text:
        plans.append("precooling_fault")
    if any(token in text for token in ("compressor", "cavitation", "oil leak")):
        plans.append("compressor_thermal")
    if "storage" in text or "vessel" in text or "cylinder" in text:
        plans.append("overpressure")
    if any(token in text for token in ("dispenser failure", "malfunctioning", "dispenser of")):
        plans.append("fueling_fault")
    if any(token in text for token in ("damage", "collision", "structural", "canopy")):
        plans.append("structural_damage")
    if "pressure" in text or "overpressure" in text:
        plans.append("overpressure")
    # Preserve catalog order and remove duplicates.
    return list(dict.fromkeys(plans))


def main() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    playbook = json.loads(PLAYBOOKS.read_text(encoding="utf-8"))
    valid = {str(item["id"]) for item in playbook.get("plans", [])}
    rows = []
    for case in evidence["cases"]:
        candidates = candidate_plans(case)
        invalid = [item for item in candidates if item not in valid]
        candidates = [item for item in candidates if item in valid]
        rows.append({
            "event_id": str(case["event_id"]),
            "title": case["title"],
            "physical_effect": case["physical_effect"],
            "consequence_nature": case["consequence_nature"],
            "stage": case["supply_chain_stage"],
            "candidate_plan_ids": candidates,
            "unregistered_candidate_plan_ids": invalid,
            "coverage_status": "mapped" if candidates else "unmapped",
        })
    mapped = [row for row in rows if row["coverage_status"] == "mapped"]
    unmapped = [row for row in rows if row["coverage_status"] == "unmapped"]
    result = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "qualitative_traceability_only",
        "source": {
            "inventory": "research/hiad_hrs_public_evidence.json",
            "inventory_sha256": hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(),
            "public_source": evidence["source"]["url"],
            "case_count": len(rows),
            "response_text_excluded": bool(evidence["selection"]["blinded_response_text_excluded"]),
        },
        "playbook_catalog": {
            "path": "src/h2station/data/emergency_playbooks.json",
            "catalog_sha256": hashlib.sha256(PLAYBOOKS.read_bytes()).hexdigest(),
            "plan_count": len(valid),
            "candidate_rule_version": "metadata-keyword-v2-positive-effect",
        },
        "aggregate": {
            "case_count": len(rows),
            "mapped_case_count": len(mapped),
            "unmapped_case_count": len(unmapped),
            "mapped_fraction": len(mapped) / len(rows) if rows else 0.0,
            "unmapped_event_ids": [row["event_id"] for row in unmapped],
        },
        "cases": rows,
        "limitations": [
            "Candidate mapping uses only public event metadata and does not inspect HIAD emergency-action or lesson text.",
            "Mapped means a response family exists in the catalog, not that the steps are correct, complete or effective.",
            "No accident probability, safety distance, physics validation or operator-effectiveness claim is made.",
            "Human coordinator review and independent expert rating remain required before a blinded HIAD effectiveness claim.",
        ],
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# HIAD-to-playbook qualitative coverage audit",
        "",
        "This audit links public HIAD event metadata to candidate response families in",
        "the current emergency-playbook catalog. It does **not** read the HIAD emergency",
        "action or lesson text, and it is not an effectiveness, probability or safety",
        "distance evaluation.",
        "",
        f"- Cases reviewed: **{len(rows)}**",
        f"- Cases with at least one registered response family: **{len(mapped)}**",
        f"- Cases without a registered response family: **{len(unmapped)}**",
        f"- Metadata-only mapping fraction: **{len(mapped) / len(rows):.1%}**",
        "",
        "## Unmapped cases",
        "",
    ]
    if unmapped:
        lines += [f"- `{row['event_id']}` — {row['title']} ({row['stage']})" for row in unmapped]
    else:
        lines.append("None under the current conservative mapping rules.")
    lines += [
        "",
        "## Interpretation",
        "",
        "A mapped case only shows that the interface can select a response family for",
        "the event metadata. It does not show that the advice is complete, safe or",
        "effective. The unmapped records should be reviewed before the next casebook",
        "freeze; the current audit does not authorize holdout collection or publication",
        "claims.",
        "",
        f"Source inventory: `{evidence['source']['url']}`",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["aggregate"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
