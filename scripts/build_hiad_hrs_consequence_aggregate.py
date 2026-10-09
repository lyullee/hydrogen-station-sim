"""Build a privacy-bounded human-impact aggregate from the HIAD HRS index.

The HIAD workbook contains optional consequence fields.  Empty cells are not
zeroes, so this artifact keeps reported totals and missing-report counts
separate.  It contains no event identifiers, titles, or narrative text and is
not a frequency, severity, or effectiveness estimate.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/hiad_2_2_access_recheck_2026_10_05.json"
OUTPUT = ROOT / "research/hiad_hrs_consequence_aggregate_2026_10_10.json"


def _reported_integer(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def build(source: Path = SOURCE) -> dict:
    record = json.loads(source.read_text(encoding="utf-8"))
    rows = record.get("station_case_index") or []
    injury_values = [_reported_integer(row.get("injured_persons")) for row in rows]
    fatality_values = [_reported_integer(row.get("fatalities")) for row in rows]
    injury_reported = [value for value in injury_values if value is not None]
    fatality_reported = [value for value in fatality_values if value is not None]
    return {
        "schema_version": 1,
        "status": "derived_privacy_bounded_hiad_human_impact_aggregate",
        "source": {
            "artifact": "research/hiad_2_2_access_recheck_2026_10_05.json",
            "sha256": sha256(source.read_bytes()).hexdigest(),
            "source_version": str((record.get("source") or {}).get("version") or ""),
            "case_count": len(rows),
            "raw_case_rows_included": False,
            "narrative_text_included": False,
        },
        "aggregate": {
            "case_count": len(rows),
            "reported_injured_persons_total": sum(injury_reported),
            "reported_fatalities_total": sum(fatality_reported),
            "records_with_reported_injury_count": len(injury_reported),
            "records_with_reported_fatality_count": len(fatality_reported),
            "records_without_reported_injury_count": len(rows) - len(injury_reported),
            "records_without_reported_fatality_count": len(rows) - len(fatality_reported),
            "reported_fields_are_not_exposure_denominators": True,
        },
        "claim_boundary": (
            "Reported consequence fields are an aggregate historical context only. "
            "Blank fields are unreported, not zero; the aggregate cannot estimate "
            "frequency, severity, response effectiveness, or station safety distance."
        ),
    }


def main() -> int:
    OUTPUT.write_text(
        json.dumps(build(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(build()["aggregate"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
