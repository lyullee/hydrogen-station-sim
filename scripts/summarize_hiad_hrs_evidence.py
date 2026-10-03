"""Create a reproducible public-evidence summary from JRC HIAD 2.2.

This is an evidence inventory, not an expert-approved holdout casebook.  It
keeps incident identifiers and provenance while deliberately omitting the
response/lesson text that would leak a blinded SAGA evaluation.
"""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from h2station.public_validation import read_hiad_hrs_cases


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build_summary(source: Path) -> dict:
    cases = read_hiad_hrs_cases(source)
    compact = []
    for case in cases:
        compact.append({
            "event_id": case.event_id,
            "quality": case.quality,
            "title": case.title.strip(),
            "physical_effect": case.physical_effect,
            "consequence_nature": case.consequence_nature,
            "sub_application": case.sub_application,
            "supply_chain_stage": case.supply_chain_stage,
            "operational_condition": case.operational_condition,
            "has_emergency_action": bool(case.emergency_action.strip()),
            "has_lesson_learnt": bool(case.lesson_learnt.strip()),
            "has_corrective_measures": bool(case.corrective_measures.strip()),
            "reference_count": len(case.references),
            "references": list(case.references),
        })
    return {
        "schema_version": 1,
        "source": {
            "title": "European Hydrogen Incidents and Accidents Database HIAD 2.2",
            "publisher": "European Commission Joint Research Centre",
            "url": "https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt",
            "file": source.as_posix(),
            "sha256": _sha256(source),
            "scope": "Public HRS application rows from the EVENTS/FACILITY/LESSONS/EVENT NATURE/REFERENCES sheets",
            "reuse_note": "Free public use with required acknowledgement; source validity remains the responsibility of the original source.",
        },
        "selection": {
            "rule": "FACILITY.Application exactly equals 'Hydrogen refuelling station'",
            "related_rows_not_included": True,
            "blinded_response_text_excluded": True,
            "coordinator_approval": False,
        },
        "aggregate": {
            "case_count": len(compact),
            "with_emergency_action": sum(item["has_emergency_action"] for item in compact),
            "with_lesson_learnt": sum(item["has_lesson_learnt"] for item in compact),
            "with_corrective_measures": sum(item["has_corrective_measures"] for item in compact),
            "physical_effect_counts": dict(Counter(item["physical_effect"] for item in compact)),
            "consequence_counts": dict(Counter(item["consequence_nature"] for item in compact)),
            "sub_application_counts": dict(Counter(item["sub_application"] for item in compact)),
            "stage_counts": dict(Counter(item["supply_chain_stage"] for item in compact)),
        },
        "cases": compact,
        "claim_boundary": (
            "HIAD is a public incident and near-miss evidence source. It does not provide synchronized station sensor traces, "
            "exposure denominators, or a calibrated probability model. This summary supports scenario coverage and traceable "
            "qualitative evidence only; it does not close the full-loop physics or expert-effectiveness gates."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/public_validation/raw/hiad_2_2/HIAD 2.2.xlsx"))
    parser.add_argument("--output", type=Path, default=Path("research/hiad_hrs_public_evidence.json"))
    args = parser.parse_args()
    summary = build_summary(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["aggregate"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

