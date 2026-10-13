"""Run the bounded PRESLHY E3.1 concentration-delay diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.preslhy_e31_concentration_transport import run_archive_diagnostic


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=ROOT / "data/public_validation/raw/preslhy",
        help="directory containing the PRESLHY E3.1 PRE*.zip archives",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/preslhy_e31_concentration_transport_diagnostic_2026_10_14.json",
    )
    args = parser.parse_args()
    result = run_archive_diagnostic(args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "archive_count", "trace_count", "error_count", "raw_onset_lag",
        "corrected_onset_lag", "raw_peak_lag", "corrected_peak_lag",
    )}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
