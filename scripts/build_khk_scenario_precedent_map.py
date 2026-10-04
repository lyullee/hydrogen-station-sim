"""Build a compact, citation-only map from KHK accident records to playbooks."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "research/khk_hydrogen_station_public_reports_inventory_2026_10_04.json"
DEFAULT_OUTPUT = ROOT / "research/khk_scenario_precedent_map_2026_10_04.json"

# The mapping is intentionally conservative.  It uses only the public inventory's
# equipment class and title; it does not infer causes, frequencies, or outcomes
# from report PDFs that are not mirrored in this repository.
PLAYBOOKS_BY_CLASS = {
    "hydrogen_generation": ("gas_release",),
    "dehumidifier_ignition": ("hydrogen_fire", "external_fire"),
    "explosion": ("hydrogen_fire", "overpressure"),
    "filling_equipment_explosion": ("fueling_fault", "overpressure"),
    "vehicle_fire": ("hydrogen_fire", "external_fire"),
    "storage_fitting_leak": ("gas_release",),
    "fitting_leak": ("gas_release", "hose_connection"),
    "leak_static_ignition": ("gas_release", "hydrogen_fire"),
    "hydrogen_leak": ("gas_release",),
    "filling_hose_damage": ("hose_connection", "fueling_fault"),
    "compressor_leak": ("gas_release", "compressor_thermal"),
    "hose_leak_detector_alarm": ("hose_connection", "gas_release"),
    "filling_hose_rupture": ("hose_connection", "gas_release"),
    "dispenser_leak": ("gas_release", "fueling_fault"),
    "isolation_valve_leak": ("isolation_failure", "gas_release"),
    "breakaway_coupling_leak": ("hose_connection", "gas_release"),
    "station_hydrogen_leak": ("gas_release",),
    "mobile_breakaway_leak": ("hose_connection", "gas_release"),
    "dispenser_isolation_valve_leak": ("isolation_failure", "gas_release"),
    "dispenser_fitting_leak": ("gas_release", "hose_connection"),
    "accumulator_fire": ("hydrogen_fire", "external_fire"),
    "filling_hose_leak": ("hose_connection", "gas_release"),
    "station_explosion": ("hydrogen_fire", "overpressure"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source_path: Path) -> dict[str, object]:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    reports = source.get("accident_reports") or []
    if not isinstance(reports, list) or not reports:
        raise ValueError("KHK inventory has no accident_reports list")
    cases: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    unmapped: list[str] = []
    for report in reports:
        equipment_class = str(report.get("equipment_class") or "").strip()
        playbooks = PLAYBOOKS_BY_CLASS.get(equipment_class, ())
        if not playbooks:
            unmapped.append(equipment_class or "<missing>")
        counts.update(playbooks)
        cases.append({
            "incident_codes": [str(code) for code in report.get("incident_codes") or []],
            "title": str(report.get("title") or ""),
            "equipment_class": equipment_class,
            "playbook_ids": list(playbooks),
            "url": str(report.get("url") or ""),
        })
    if unmapped:
        raise ValueError(f"KHK inventory classes need an explicit mapping: {unmapped}")

    representatives: dict[str, list[dict[str, object]]] = defaultdict(list)
    for case in cases:
        for playbook_id in case["playbook_ids"]:
            if len(representatives[playbook_id]) < 2:
                representatives[playbook_id].append({
                    "incident_codes": case["incident_codes"],
                    "title": case["title"],
                    "equipment_class": case["equipment_class"],
                    "url": case["url"],
                })

    return {
        "schema_version": 1,
        "recorded_at": source.get("recorded_at") or date.today().isoformat(),
        "status": "citation_only_khk_scenario_precedent_map",
        "source_inventory": {
            "path": source_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(source_path),
            "source_page": (source.get("source_page") or {}).get("url"),
            "incident_report_count": len(cases),
            "incident_code_count": sum(len(case["incident_codes"]) for case in cases),
        },
        "mapping": {
            "mapped_report_count": len(cases),
            "unmapped_report_count": len(unmapped),
            "playbook_case_counts": dict(sorted(counts.items())),
            "representative_precedents": dict(sorted(representatives.items())),
        },
        "cases": cases,
        "claim_boundary": (
            "Citation-only qualitative scenario coverage. The equipment class and title "
            "are not a causal inference, frequency estimate, numerical-model validation, "
            "or proof that a recommended action is effective."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": args.output.as_posix(),
        "mapped_report_count": result["mapping"]["mapped_report_count"],
        "unmapped_report_count": result["mapping"]["unmapped_report_count"],
        "playbook_case_counts": result["mapping"]["playbook_case_counts"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
