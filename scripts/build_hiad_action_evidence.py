"""Build a non-evaluative action taxonomy from the public HIAD HRS subset.

Only controlled categories and field-presence flags are retained.  The source
descriptions, emergency prose and lessons are deliberately not copied into the
artifact, so this summary cannot silently become the blinded SAGA holdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from h2station.public_validation import read_hiad_hrs_cases


CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "shutdown_isolation_depressurization": (
        r"shut.?down", r"shutdown", r"stop", r"closed? the valve", r"valve was closed",
        r"isolat", r"depressur", r"vented", r"venting", r"safe mode",
    ),
    "detection_alarm_monitoring": (
        r"detector", r"alarm", r"monitoring", r"trend", r"sensor", r"hissing",
        r"pressure drop", r"detected",
    ),
    "fire_response_cooling": (
        r"fire brigade", r"fire department", r"extinguish", r"cooled", r"cooling",
        r"fire under control", r"firefighting",
    ),
    "evacuation_perimeter_access": (
        r"perimeter", r"road .*closed", r"traffic", r"security zone", r"evacuat",
        r"access", r"hot zone",
    ),
    "emergency_communication_coordination": (
        r"notified", r"notification", r"contact", r"communicat", r"operator",
        r"emergency services", r"rescue service", r"fire brigade",
    ),
    "inspection_leak_test_repair": (
        r"inspect", r"investigat", r"leak test", r"repair", r"replaced?", r"replacement",
        r"o-ring", r"fitting", r"hose", r"tightening torque", r"maintenance",
    ),
    "procedure_interlock_training_design": (
        r"interlock", r"procedure", r"manual", r"checklist", r"standard", r"training",
        r"design", r"logic", r"protocol",
    ),
    "ventilation_purge": (r"vent", r"purge", r"air line", r"nitrogen"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _categories(text: str) -> list[str]:
    lowered = text.casefold()
    return [
        name for name, patterns in CATEGORY_PATTERNS.items()
        if any(re.search(pattern, lowered) for pattern in patterns)
    ]


def build(source: Path) -> dict[str, Any]:
    cases = read_hiad_hrs_cases(source)
    rows = []
    category_counts = {name: 0 for name in CATEGORY_PATTERNS}
    field_counts = {name: 0 for name in ("emergency_action", "lesson_learnt", "corrective_measures")}
    for case in cases:
        fields = {
            "emergency_action": case.emergency_action,
            "lesson_learnt": case.lesson_learnt,
            "corrective_measures": case.corrective_measures,
        }
        present = {name: bool(value.strip()) for name, value in fields.items()}
        for name, value in present.items():
            field_counts[name] += int(value)
        combined = " ".join(value for value in fields.values() if value)
        categories = _categories(combined)
        for category in categories:
            category_counts[category] += 1
        rows.append({
            "event_id": case.event_id,
            "title": case.title,
            "physical_effect": case.physical_effect,
            "consequence_nature": case.consequence_nature,
            "supply_chain_stage": case.supply_chain_stage,
            "operational_condition": case.operational_condition,
            "source_quality": case.quality,
            "source_fields_present": present,
            "action_categories": categories,
        })
    rows.sort(key=lambda row: (0, int(row["event_id"])) if row["event_id"].isdigit() else (1, row["event_id"]))
    return {
        "schema_version": 1,
        "status": "derived_non_evaluative_action_taxonomy",
        "evidence_role": "public_incident_grounding_summary",
        "source": {
            "path": str(source).replace("/", "\\"),
            "sha256": _sha256(source),
            "public_use_note": "HIAD 2.2 workbook states that the database is intended for public use; verify permission before redistributing raw prose.",
            "raw_text_retained": False,
            "holdout_use": False,
        },
        "claim_boundary": "This artifact counts controlled action categories derived from HIAD HRS records. It does not judge whether an action was correct or safe, estimate incident probability, validate physics, or evaluate SAGA effectiveness.",
        "taxonomy": {
            "category_patterns_version": "hiad-action-taxonomy-v1",
            "category_counts": category_counts,
            "field_presence_counts": field_counts,
        },
        "case_count": len(rows),
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/public_validation/raw/hiad_2_2/HIAD 2.2.xlsx"))
    parser.add_argument("--output", type=Path, default=Path("research/hiad_action_evidence.json"))
    args = parser.parse_args()
    result = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
