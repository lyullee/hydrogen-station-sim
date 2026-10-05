from __future__ import annotations
import hashlib, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/public_validation/raw/hiad_2_2.xlsx"
OUT_JSON = ROOT / "research/hiad_2_2_access_recheck_2026_10_05.json"
OUT_MD = ROOT / "research/HIAD_2_2_ACCESS_RECHECK_2026_10_05.md"
CASEBOOK = ROOT / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json"

def clean(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_x000D_", " ").replace("\\n", " ")).strip()

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def rows(wb, sheet):
    ws = wb[sheet]
    it = ws.iter_rows(values_only=True)
    header = [clean(v) for v in next(it)]
    for vals in it:
        yield {header[i]: vals[i] if i < len(vals) else None for i in range(len(header))}

wb = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
events = {str(r.get("Event ID")): r for r in rows(wb, "EVENTS") if r.get("Event ID") is not None}
facility = {str(r.get("Event ID")): r for r in rows(wb, "FACILITY") if r.get("Event ID") is not None}
consequences = {str(r.get("Event ID")): r for r in rows(wb, "CONSEQUENCES") if r.get("Event ID") is not None}
nature = {str(r.get("Event ID")): r for r in rows(wb, "EVENT NATURE") if r.get("Event ID") is not None}
lessons = {str(r.get("Event ID")): r for r in rows(wb, "LESSONS LEARNT") if r.get("Event ID") is not None}
refs = {str(r.get("Event ID")): r for r in rows(wb, "REFERENCES") if r.get("Event ID") is not None}

station_ids = [
    eid for eid, row in facility.items()
    if clean(row.get("Application")).lower() == "hydrogen refuelling station"
]
station_ids.sort(key=lambda x: int(x) if x.isdigit() else x)
station_rows = []
for eid in station_ids:
    f = facility[eid]
    e = events.get(eid, {})
    c = consequences.get(eid, {})
    n = nature.get(eid, {})
    l = lessons.get(eid, {})
    r = refs.get(eid, {})
    station_rows.append({
        "event_id": eid,
        "quality": clean(e.get("Q")),
        "title": clean(e.get("Event Title")),
        "sub_application": clean(f.get("Sub-application")),
        "supply_chain_stage": clean(f.get("Hydrogen supply chain stage")),
        "storage_process_medium": clean(f.get("Storage/process medium")),
        "location_type": clean(f.get("Location type")),
        "location_description": clean(f.get("Location description")),
        "operational_condition": clean(f.get("Operational condition")),
        "physical_effect": clean(e.get("Classification of the physical effects")),
        "consequence_nature": clean(e.get("Nature of the consequences")),
        "release_type": clean(n.get("Release type")),
        "emergency_action": clean(n.get("Emergency action")),
        "injured_persons": clean(c.get("Number of injured persons")),
        "fatalities": clean(c.get("Number of fatalities")),
        "lesson_present": bool(clean(l.get("Lesson Learnt")) or clean(l.get("Corrective Measures"))),
        "primary_reference": clean(r.get("1st Reference & weblink")),
    })

subapps = Counter(row["sub_application"] for row in station_rows)
effects = Counter(row["physical_effect"] for row in station_rows)
consequences_count = Counter(row["consequence_nature"] for row in station_rows)
quality = Counter(row["quality"] for row in station_rows)
release = Counter(row["release_type"] for row in station_rows)
report = {
    "schema_version": 1,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "completed_public_accident_dataset_provenance_recheck",
    "source": {
        "title": "European Hydrogen Incidents and Accidents Database HIAD 2.2",
        "publisher": "European Commission Joint Research Centre / Clean Hydrogen Joint Undertaking",
        "official_page": "https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt",
        "download_url": "https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiad_22_export_for_users_2026_01_01xlsx",
        "version": "HIAD 2.2",
        "coverage_end": "2025-12-31",
        "download_date": "2026-10-05",
        "local_file": "data/public_validation/raw/hiad_2_2.xlsx",
        "sha256": sha256(RAW),
        "bytes": RAW.stat().st_size,
        "license_or_terms": "JRC states use is free of charge with required acknowledgement; users accept the HIAD 2.2 conditions of use on download. Preserve source attribution and original-source uncertainty.",
        "required_acknowledgement": "European Hydrogen Incidents and Accidents Database HIAD 2.2, European Commission, Joint Research Centre, Petten, The Netherlands.",
    },
    "workbook_observation": {
        "events_rows": len(events),
        "facility_rows": len(facility),
        "consequence_rows": len(consequences),
        "nature_rows": len(nature),
        "lessons_rows": len(lessons),
        "reference_rows": len(refs),
        "hydrogen_refuelling_station_records": len(station_rows),
        "station_record_quality_counts": dict(sorted(quality.items())),
        "station_sub_application_counts": dict(sorted(subapps.items())),
        "station_physical_effect_counts": dict(sorted(effects.items())),
        "station_consequence_counts": dict(sorted(consequences_count.items())),
        "station_release_type_counts": dict(sorted(release.items())),
        "station_records_with_lesson_or_corrective_measure": sum(row["lesson_present"] for row in station_rows),
    },
    "station_case_index": station_rows,
    "casebook_candidate": None,
    "evidence_role": "public_actual_accident_casebook_candidate_for_SAGA_response_grounding",
    "claim_boundary": "HIAD 2.2 is a reviewed incident/accident case repository with traceable source links. It supports scenario taxonomy, response grounding and future blinded expert casebook construction. It does not provide synchronized station-to-vehicle pressure/temperature/mass-flow logs and therefore does not close the numerical full-loop validation gate or prove SAGA effectiveness.",
    "next_action": "Use the indexed records to prepare a coordinator-reviewed, hindsight-masked casebook. Do not freeze the casebook or collect expert responses until the existing ethics determination and independent reviewer protocol are completed.",
}
if CASEBOOK.is_file():
    candidate = json.loads(CASEBOOK.read_text(encoding="utf-8"))
    station_id_set = {row["event_id"] for row in station_rows}
    case_ids = [str(case.get("event_id")) for case in candidate.get("cases", [])]
    report["casebook_candidate"] = {
        "local_file": "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json",
        "sha256": sha256(CASEBOOK),
        "source_label": candidate.get("source"),
        "case_count": len(case_ids),
        "all_case_ids_in_station_index": all(case_id in station_id_set for case_id in case_ids),
        "coordinator_review_pending": any(
            str(case.get("narrative_action_leakage_review", "")).upper() != "PASS"
            or str(case.get("expert_vignette_approved", "")).upper() != "YES"
            for case in candidate.get("cases", [])
        ),
        "claim_boundary": "Candidate only; it is not a frozen casebook and cannot support expert effectiveness claims until coordinator, ethics and reviewer gates pass.",
    }
OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
lines = [
    "# HIAD 2.2 access and station-incident recheck",
    "",
    f"- Generated: {report['generated_at_utc']}",
    "- Source: [European Hydrogen Incidents and Accidents Database HIAD 2.2](https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt)",
    f"- Local acquisition SHA-256: {report['source']['sha256']}",
    f"- Workbook rows: EVENTS {len(events)}, FACILITY {len(facility)}, CONSEQUENCES {len(consequences)}, EVENT NATURE {len(nature)}, LESSONS LEARNT {len(lessons)}",
    f"- Hydrogen refuelling station records: **{len(station_rows)}**",
    f"- Existing HIAD casebook candidate: **{report['casebook_candidate']['case_count'] if report['casebook_candidate'] else 0}** cases; coordinator review remains pending",
    "",
    "## Evidence use",
    "",
    "HIAD 2.2 is used here as public actual-incident evidence for scenario taxonomy, response grounding and a future blinded SAGA casebook. The JRC page requires the specified acknowledgement and preserves uncertainty inherited from each original source.",
    "",
    "The workbook does not contain a synchronized station-to-vehicle pressure/temperature/mass-flow logger archive. These records therefore do not close the numerical full-loop validation gate and are not represented as such.",
    "",
    "## Reproducible acquisition",
    "",
    "1. Download the official workbook from the source page/download URL.",
    "2. Compute SHA-256 and compare it with the JSON artifact.",
    "3. Run scripts/build_hiad_2_2_access_recheck.py.",
    "4. Retain the source workbook locally; do not alter the indexed event fields.",
    "",
    "## Next controlled step",
    "",
    "A non-rating coordinator must review and mask hindsight response/lesson leakage before any casebook freeze. Ethics determination and independent expert review remain prerequisites for the SAGA effectiveness gate.",
]
OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({
    "station_records": len(station_rows),
    "sha256": report["source"]["sha256"],
    "json": str(OUT_JSON),
    "markdown": str(OUT_MD),
}, ensure_ascii=False))
