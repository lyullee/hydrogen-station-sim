"""Run the post-outcome Schefer non-adiabatic sensitivity diagnostic.

This script deliberately writes a diagnostic artifact separate from the frozen
holdout result.  It must never be used to replace the primary validation JSON.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from h2station.schefer_2007_nonadiabatic_diagnostic import (
    evaluate_declared_sensitivity_envelope,
    write_diagnostic_json,
)
from h2station.schefer_2007_validation import load_schefer_2007_pressure_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(
            "data/public_validation/raw/hyram-v6.1/tests/hyram/validation/data/"
            "schefer-2007-fig4.csv"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/schefer_2007_nonadiabatic_diagnostic_2026_10_14.json"),
    )
    args = parser.parse_args()
    trace = load_schefer_2007_pressure_csv(args.data)
    metrics = evaluate_declared_sensitivity_envelope(trace)
    write_diagnostic_json(args.output, metrics)
    print(f"wrote {len(metrics)} declared sensitivity points to {args.output}")


if __name__ == "__main__":
    main()
