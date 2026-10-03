"""Run a preregistration-free geometry sensitivity on the NREL HDVS sample.

This is an exploratory diagnostic, not a confirmatory validation runner.  It
compares the legacy volume scaling with a capacity/EOS-based volume calculated
from the declared 9.8 kg at 70 MPa and 15 C.  No result from this script may be
used to claim validation or to replace the frozen model without a new protocol,
split and independent re-evaluation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from h2station.tabulated import PropsSI  # noqa: E402
from h2station.vehicle import CompositeTankFitParameters  # noqa: E402
from run_nrel_h2fills_hdvs_validation import (  # noqa: E402
    DEFAULT_WORKBOOK,
    TANK_IDS,
    _git_commit,
    _git_dirty,
    _sha256,
    _simulate_tank,
    read_nrel_workbook,
)


DEFAULT_FIT = ROOT / "research/tank_model_validation_v2.json"
DEFAULT_OUTPUT = ROOT / (
    "data/public_validation/results/nrel_h2fills_hdvs_typeiv/"
    "geometry_sensitivity.json"
)
REFERENCE_PRESSURE_PA = 70.0e6
REFERENCE_TEMPERATURE_K = 288.15
CAPACITY_KG = 9.8


def capacity_eos_volume_m3(
    capacity_kg: float = CAPACITY_KG,
    *,
    pressure_pa: float = REFERENCE_PRESSURE_PA,
    temperature_k: float = REFERENCE_TEMPERATURE_K,
) -> float:
    """Return a declared-capacity volume without fitting to the NREL trace."""

    density = float(
        PropsSI("Dmass", "P", pressure_pa, "T", temperature_k, "Hydrogen")
    )
    if density <= 0.0:
        raise ValueError("Hydrogen EOS density must be positive")
    return float(capacity_kg / density)


def run(
    workbook_path: Path = DEFAULT_WORKBOOK,
    fit_path: Path = DEFAULT_FIT,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    dataset = read_nrel_workbook(workbook_path)
    fit_data = json.loads(fit_path.read_text(encoding="utf-8"))["fit"]
    frozen_fit = CompositeTankFitParameters(
        effective_volume_multiplier=float(fit_data["effective_volume_multiplier"]),
        gas_liner_ua_multiplier=float(fit_data["gas_liner_ua_multiplier"]),
    )
    capacity_volume = capacity_eos_volume_m3()
    variants = {
        "legacy_frozen": {
            "base_volume_m3": 0.122 * CAPACITY_KG / 4.7,
            "fit": frozen_fit,
            "basis": "legacy 0.122 m3 per 4.7 kg scaling",
        },
        "capacity_eos_with_frozen_fit": {
            "base_volume_m3": capacity_volume,
            "fit": frozen_fit,
            "basis": "9.8 kg divided by tabulated Hydrogen density at 70 MPa and 15 C; frozen H2Protocol fit retained",
        },
        "capacity_eos_no_volume_fit": {
            "base_volume_m3": capacity_volume,
            "fit": CompositeTankFitParameters(
                effective_volume_multiplier=1.0,
                gas_liner_ua_multiplier=frozen_fit.gas_liner_ua_multiplier,
            ),
            "basis": "9.8 kg divided by tabulated Hydrogen density at 70 MPa and 15 C; effective-volume multiplier fixed at one",
        },
    }
    results: dict[str, Any] = {}
    for name, variant in variants.items():
        rows = [
            _simulate_tank(
                trace,
                variant["fit"],
                capacity_kg=CAPACITY_KG,
                base_volume_m3=float(variant["base_volume_m3"]),
            )
            for trace in dataset.traces
        ]
        results[name] = {
            "basis": variant["basis"],
            "base_volume_m3": float(variant["base_volume_m3"]),
            "effective_volume_multiplier": variant["fit"].effective_volume_multiplier,
            "gas_liner_ua_multiplier": variant["fit"].gas_liner_ua_multiplier,
            "screening_limits": {
                "pressure_rmse_mpa_max": 5.0,
                "temperature_rmse_c_max": 10.0,
                "mass_final_abs_error_kg_max": 0.5,
            },
            "aggregate": {
                "screening_pass_count": sum(row["screening_pass"] for row in rows),
                "screening_pass_fraction": sum(row["screening_pass"] for row in rows) / len(rows),
                **{
                    key: sum(float(row[key]) for row in rows) / len(rows)
                    for key in (
                        "pressure_rmse_mpa",
                        "temperature_rmse_c",
                        "mass_final_error_kg",
                        "pressure_final_error_mpa",
                    )
                },
            },
            "tanks": rows,
        }
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "exploratory_geometry_sensitivity_only",
        "claim_limit": (
            "The variants were compared after access to the NREL workbook. No variant "
            "is an independent confirmatory pass, and no parameter or default model "
            "was changed by this script. A new frozen protocol is required before "
            "using a capacity-based geometry in a validation claim."
        ),
        "source": {
            "workbook": str(workbook_path),
            "workbook_sha256": _sha256(workbook_path),
            "fit_source": str(fit_path),
            "fit_source_sha256": _sha256(fit_path),
            "tank_ids": list(TANK_IDS),
            "capacity_kg": CAPACITY_KG,
            "reference_pressure_pa": REFERENCE_PRESSURE_PA,
            "reference_temperature_k": REFERENCE_TEMPERATURE_K,
            "capacity_eos_volume_m3": capacity_volume,
        },
        "variants": results,
        "source_commit": _git_commit(),
        "source_worktree_dirty": _git_dirty(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--fit", type=Path, default=DEFAULT_FIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.workbook, args.fit, args.output)
    print(json.dumps({name: value["aggregate"] for name, value in report["variants"].items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
