import argparse
import json
from pathlib import Path
from .database import DEFAULT_DB, import_workbook, load_catalog

parser = argparse.ArgumentParser(description="Import and inspect the HAZOP SQLite catalogue")
parser.add_argument("command", choices=["import", "inspect"])
parser.add_argument("workbook", nargs="?", type=Path)
parser.add_argument("--database", type=Path, default=DEFAULT_DB)
args = parser.parse_args()
if args.command == "import":
    if args.workbook is None: parser.error("workbook is required for import")
    result = import_workbook(args.workbook, args.database)
else:
    data = load_catalog(args.database)
    result = {"metadata": data["metadata"], "counts": {k:len(v) for k,v in data.items() if isinstance(v,list)}}
print(json.dumps(result, ensure_ascii=False, indent=2))
