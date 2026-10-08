"""Run the frozen confidential recharge pressure forecast holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.confidential_recharge_forecast import (
    RechargeForecastRules,
    validate_recharge_pressure_forecast,
)

try:
    from calibrate_confidential_station_data import _mapping
except ModuleNotFoundError:
    from scripts.calibrate_confidential_station_data import _mapping


PROTOCOL_ID = "CONFIDENTIAL-STATION-RECHARGE-PRESSURE-FORECAST-001"


def _bank_role(value: str) -> tuple[str, str]:
    try:
        role, bank = value.split("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use PRESSURE_ROLE=medium|high") from exc
    role, bank = role.strip(), bank.strip().lower()
    if not role or bank not in {"medium", "high"}:
        raise argparse.ArgumentTypeError("use PRESSURE_ROLE=medium|high")
    return role, bank


def _git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compressor-state-role", required=True)
    parser.add_argument("--active-state", action="append", required=True)
    parser.add_argument("--bank-role", type=_bank_role, action="append", required=True)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-rows-per-file", type=int)
    parser.add_argument("--pressure-semantics-attested", action="store_true")
    parser.add_argument("--state-semantics-attested", action="store_true")
    args = parser.parse_args()
    if not args.pressure_semantics_attested or not args.state_semantics_attested:
        parser.error("both pressure and state semantics attestations are required")
    protocol_bytes = args.protocol.read_bytes()
    protocol = json.loads(protocol_bytes.decode("utf-8"))
    if protocol.get("protocol_id") != PROTOCOL_ID:
        parser.error("unexpected protocol_id")
    if protocol.get("joint_holdout_outcomes_seen_before_freeze") is not False:
        parser.error("protocol is not prospective")
    bank_roles = dict(args.bank_role)
    if set(bank_roles.values()) != {"medium", "high"} or len(bank_roles) != 2:
        parser.error("exactly one medium and one high --bank-role are required")

    result = validate_recharge_pressure_forecast(
        args.input,
        _mapping(args.mapping),
        compressor_state_role=args.compressor_state_role,
        active_state_values=args.active_state,
        bank_by_pressure_role=bank_roles,
        pressure_semantics_attested=True,
        state_semantics_attested=True,
        rules=RechargeForecastRules(),
        stride=args.stride,
        max_rows_per_file=args.max_rows_per_file,
    )
    result["protocol"] = {
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        "frozen_before_joint_holdout_outcome_access": True,
    }
    result["runner_git_commit"] = _git_head()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
