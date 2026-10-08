"""Run the privacy-bounded confidential pressure/flow consistency screen."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from h2station.confidential_signal_consistency import audit_confidential_signal_consistency


ROOT = Path(__file__).resolve().parents[1]


def _outside_repository(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{label} must be outside the repository worktree")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-rows-per-file", type=int, default=200_000)
    parser.add_argument("--stride", type=int, default=1)
    arguments = parser.parse_args()
    source = _outside_repository(arguments.input, label="input")
    output = _outside_repository(arguments.output, label="output")
    result = audit_confidential_signal_consistency(
        source,
        max_rows_per_file=arguments.max_rows_per_file,
        stride=arguments.stride,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
