"""Run the privacy-bounded confidential recharge-flow screen."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from h2station.confidential_recharge_flow import audit_confidential_recharge_flow


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
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-rows-per-file", type=int, default=200_000)
    arguments = parser.parse_args()
    source = _outside_repository(arguments.input, label="input")
    mapping_path = _outside_repository(arguments.mapping, label="mapping")
    output = _outside_repository(arguments.output, label="output")
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    result = audit_confidential_recharge_flow(
        source,
        mapping,
        max_rows_per_file=arguments.max_rows_per_file,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
