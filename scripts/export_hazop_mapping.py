"""Export the current executable mapping assessment without modifying the source workbook."""
import csv
import json
from pathlib import Path
from h2station.hazop.database import load_catalog
from h2station.hazop.mapping import coverage

catalog = load_catalog()
assessment = coverage(catalog)
directory = Path(__file__).resolve().parents[1] / "data" / "hazop-review"
directory.mkdir(parents=True, exist_ok=True)
(directory / "mapping.json").write_text(json.dumps(assessment, ensure_ascii=False, indent=2), encoding="utf-8")
for kind in ("sensors", "rules"):
    rows = assessment[kind]
    with (directory / f"{kind}_mapping.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "; ".join(v) if isinstance(v, list) else v for k, v in row.items()})
print(directory)
