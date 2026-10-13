"""Audit finite compressor-package line-pack and post-ESD leak behaviour."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from h2station.api import ProcessSettings  # noqa: E402
from h2station.operations import ProcessRuntime  # noqa: E402
from h2station.risk.runtime_backend import UnavailableHyRAMBackend  # noqa: E402
from h2station.scenario import ReferenceScenario, build_reference_scenario  # noqa: E402
from h2station.safety_runtime import FaultEvent, FaultKind  # noqa: E402


OUT_JSON = ROOT / "research/compressor_package_isolation_audit_2026_10_13.json"
OUT_MD = ROOT / "research/COMPRESSOR_PACKAGE_ISOLATION_AUDIT_2026_10_13.md"


def _digest(relative: str) -> str:
    return sha256((ROOT / relative).read_bytes()).hexdigest()


def build_audit() -> dict:
    leak = FaultEvent(
        event_id="compressor-package-leak",
        kind=FaultKind.HYDROGEN_LEAK,
        target="compressor",
        start_time_s=0.0,
        leak_diameter_m=0.0005,
    )
    built = build_reference_scenario(
        ReferenceScenario(
            duration_s=6.0,
            control_period_s=0.2,
            fault_events=(leak,),
        ),
        UnavailableHyRAMBackend(),
    )
    process = ProcessRuntime(
        ProcessSettings(
            trailer_supply=True,
            pressure_recharge=True,
            recharge_auto_stop=False,
        ).model_dump()
    )
    built.simulator.process_runtime = process
    built.station.compressor_suction = lambda _time: process.trailer_state()

    connected = built.simulator.simulate(built.initial_state, 0.6, 0.2)
    package_at_trip = connected.final_state.compressor_package
    package_gas_at_trip = built.station.compressor_package.gas_state(
        package_at_trip
    )
    high_bank_mass_at_trip = connected.final_state.banks[2].hydrogen_mass_kg

    process.safety.issue("esd.trip", "station", 0.6, process=process)
    isolated = built.simulator.simulate(
        connected.final_state,
        5.0,
        0.2,
        start_time_s=0.6,
        reset_runtime=False,
    )
    package_final = isolated.final_state.compressor_package
    package_gas_final = built.station.compressor_package.gas_state(package_final)
    release = isolated.leak_mass_flow_by_release[leak.event_id]
    integrated_release_kg = float(np.trapezoid(release, isolated.time_s))
    package_mass_loss_kg = float(
        package_at_trip.hydrogen_mass_kg - package_final.hydrogen_mass_kg
    )
    bank_mass_change_kg = float(
        isolated.final_state.banks[2].hydrogen_mass_kg - high_bank_mass_at_trip
    )
    mass_balance_residual_kg = package_mass_loss_kg - integrated_release_kg
    checks = {
        "esd_latched": bool(isolated.safety_commands[-1].esd_latched),
        "high_bank_isolated_mass_change_abs_le_1e_9_kg": (
            abs(bank_mass_change_kg) <= 1.0e-9
        ),
        "package_inventory_decreased": package_mass_loss_kg > 0.0,
        "package_pressure_decreased": (
            package_gas_final.pressure_pa < package_gas_at_trip.pressure_pa
        ),
        "residual_release_continued_after_esd": bool(np.all(release > 0.0)),
        "release_rate_decreased": bool(release[-1] < release[0]),
        "post_esd_mass_balance_abs_le_5e_6_kg": (
            abs(mass_balance_residual_kg) <= 5.0e-6
        ),
    }
    return {
        "schema_version": 1,
        "status": (
            "completed_development_physics_audit"
            if all(checks.values()) else "failed_development_physics_audit"
        ),
        "model_status": "DEVELOPMENT_PHYSICS_UNVALIDATED",
        "purpose": (
            "Verify that an active compressor-package leak continues from finite "
            "residual inventory after ESD while the isolated storage bank stops "
            "replenishing that release."
        ),
        "source_hashes": {
            relative: _digest(relative)
            for relative in (
                "src/h2station/full_station.py",
                "src/h2station/safe_operation.py",
                "src/h2station/scenario.py",
                "tests/test_process_operations.py",
            )
        },
        "declared_inputs": {
            "compressor_package_internal_volume_m3": (
                built.station.compressor_package.volume_m3
            ),
            "leak_diameter_mm": leak.leak_diameter_m * 1000.0,
            "connected_operation_duration_s": 0.6,
            "post_esd_duration_s": 5.0,
            "control_period_s": 0.2,
            "consequence_backend": "unavailable-by-design-for-process-audit",
        },
        "results": {
            "package_pressure_at_esd_mpa_abs": (
                package_gas_at_trip.pressure_pa / 1.0e6
            ),
            "package_pressure_final_mpa_abs": (
                package_gas_final.pressure_pa / 1.0e6
            ),
            "package_mass_at_esd_kg": package_at_trip.hydrogen_mass_kg,
            "package_mass_final_kg": package_final.hydrogen_mass_kg,
            "package_mass_loss_kg": package_mass_loss_kg,
            "integrated_post_esd_release_kg": integrated_release_kg,
            "mass_balance_residual_kg": mass_balance_residual_kg,
            "high_bank_mass_change_after_esd_kg": bank_mass_change_kg,
            "post_esd_initial_release_g_s": float(release[0] * 1000.0),
            "post_esd_final_release_g_s": float(release[-1] * 1000.0),
        },
        "checks": checks,
        "claim_boundary": (
            "This is a deterministic internal consistency and topology audit. "
            "The declared package volume, restriction area and thermal parameters "
            "have not been validated against a specific compressor or an independent "
            "hydrogen package-depressurization time series; the result cannot establish "
            "field isolation time, leak rate or safety distance."
        ),
    }


def _markdown(record: dict) -> str:
    r = record["results"]
    checks = record["checks"]
    rows = "\n".join(
        f"| {name} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in checks.items()
    )
    return f"""# Compressor package isolation audit — 2026-10-13

This audit checks the new finite compressor discharge-package inventory. It is
an internal physics and topology check, not external validation.

## Deterministic result

- Package pressure after ESD: **{r['package_pressure_at_esd_mpa_abs']:.3f} → {r['package_pressure_final_mpa_abs']:.3f} MPa(abs)**
- Residual release rate: **{r['post_esd_initial_release_g_s']:.3f} → {r['post_esd_final_release_g_s']:.3f} g/s**
- High-bank mass change after ESD: **{r['high_bank_mass_change_after_esd_kg']:.3e} kg**
- Package/release mass-balance residual: **{r['mass_balance_residual_kg']:.3e} kg**

| Check | Result |
|---|---|
{rows}

## Interpretation

The compressor leak no longer drains the high-pressure storage bank after ESD.
The isolated package retains a finite inventory, continues to release hydrogen,
and depressurizes progressively. This preserves the difference between a
successful isolation command and the later confirmation of zero residual flow.

## Claim boundary

{record['claim_boundary']}
"""


def main() -> None:
    record = build_audit()
    OUT_JSON.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    OUT_MD.write_text(_markdown(record), encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": record["status"],
        "checks_passed": sum(record["checks"].values()),
        "check_count": len(record["checks"]),
        "mass_balance_residual_kg": record["results"]["mass_balance_residual_kg"],
    }, indent=2))


if __name__ == "__main__":
    main()
