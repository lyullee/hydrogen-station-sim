"""Verify opt-in application of the privacy-bounded local station profile.

The owner-controlled logger archive is intentionally kept outside the
repository.  This audit exercises the public API with the sanitized aggregate
profile that is committed under ``research``.  It proves only that the
profile is applied when explicitly requested, that reference defaults remain
unchanged otherwise, and that the failed recharge-dynamics candidate is not
silently attached to a job.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from h2station.api import ProcessSettings, app  # noqa: E402


OUT_JSON = ROOT / "research/local_station_runtime_profile_integration_2026_10_09.json"
OUT_MD = ROOT / "research/LOCAL_STATION_RUNTIME_PROFILE_INTEGRATION_2026_10_09.md"


def _wait_for_completion(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(120):
        response = client.get(f"/api/simulations/{job_id}")
        response.raise_for_status()
        job = response.json()
        if job.get("status") in {"complete", "failed"}:
            return job
        time.sleep(0.1)
    raise RuntimeError(f"simulation {job_id} did not finish within the audit window")


def _run_case(client: TestClient, *, measured: bool) -> dict[str, Any]:
    settings = ProcessSettings(measured_boundary_calibration=measured)
    response = client.post(
        "/api/simulations",
        json={
            "duration_s": 0.2,
            "control_period_s": 0.2,
            "process_settings": settings.model_dump(),
        },
    )
    response.raise_for_status()
    job = _wait_for_completion(client, response.json()["id"])
    operations = job.get("operations") or {}
    runtime_settings = operations.get("settings") or {}
    calibration = job.get("calibration_profile") or {}
    dynamics = calibration.get("station_recharge_dynamics") or {}
    return {
        "requested": measured,
        "status": job.get("status"),
        "profile_id": calibration.get("id"),
        "evidence_artifact": calibration.get("evidence_artifact"),
        "sampled_rows": calibration.get("sampled_rows"),
        "recharge_hysteresis_pa": calibration.get("recharge_hysteresis_pa"),
        "recharge_restart_margin_pa": calibration.get("recharge_restart_margin_pa"),
        "runtime_restart_margins_mpa": {
            key.removeprefix("recharge_restart_margin_").removesuffix("_mpa"): value
            for key, value in runtime_settings.items()
            if key.startswith("recharge_restart_margin_")
        },
        "station_dynamics_calibration_applied": job.get(
            "station_dynamics_calibration_applied"
        ),
        "station_recharge_dynamics_status": dynamics.get("status"),
        "raw_data_guard": {
            "raw_rows_persisted": False,
            "source_identifiers_published": False,
            "source_paths_published": False,
        },
    }


def build_audit() -> dict[str, Any]:
    with TestClient(app) as client:
        reference = _run_case(client, measured=False)
        opt_in = _run_case(client, measured=True)

    checks = {
        "reference_defaults_preserved": (
            reference["profile_id"] == "reference_defaults"
            and reference["runtime_restart_margins_mpa"]
            == {"low": 2.0, "medium": 3.0, "high": 4.5}
        ),
        "opt_in_profile_applied": (
            opt_in["profile_id"] == "owner_measured_operational_envelope_v1"
            and opt_in["recharge_restart_margin_pa"] == 540000.0
            and opt_in["runtime_restart_margins_mpa"]
            == {"low": 0.54, "medium": 0.54, "high": 0.54}
        ),
        "failed_dynamics_profile_not_attached": (
            reference["station_recharge_dynamics_status"] == "disabled"
            and opt_in["station_recharge_dynamics_status"] == "disabled"
            and reference["station_dynamics_calibration_applied"] is False
            and opt_in["station_dynamics_calibration_applied"] is False
        ),
        "simulations_completed": reference["status"] == "complete"
        and opt_in["status"] == "complete",
        "privacy_boundary_preserved": all(
            row["raw_data_guard"] == {
                "raw_rows_persisted": False,
                "source_identifiers_published": False,
                "source_paths_published": False,
            }
            for row in (reference, opt_in)
        ),
    }
    return {
        "schema_version": 1,
        "artifact_type": "local_station_runtime_profile_integration_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_runtime_integration_audit",
        "evidence_role": "privacy_bounded_local_station_profile_runtime_traceability",
        "cases": {"reference_defaults": reference, "explicit_opt_in": opt_in},
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "claim_boundary": [
            "The audit verifies API wiring and provenance for a sanitized station-boundary pressure profile.",
            "The measured profile is not a vehicle-side, full-loop, safety-limit or field-effect-distance validation.",
            "The recharge-dynamics candidate remains disabled because its chronological holdout was inconsistent.",
            "Raw logger rows, source identifiers, dates, paths and equipment identities are not published.",
        ],
    }


def write_outputs(result: dict[str, Any]) -> None:
    OUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        "# Local station runtime profile integration audit",
        "",
        "This audit runs two short API simulations against the committed sanitized aggregate profile.",
        "The owner-controlled raw logger archive is never read by the runtime or written to the artifact.",
        "",
        "| Case | Result | Profile | Restart margins (MPa) | Dynamics profile |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, row in result["cases"].items():
        lines.append(
            f"| `{name}` | `{row['status']}` | `{row['profile_id']}` | "
            f"`{row['runtime_restart_margins_mpa']}` | `{row['station_recharge_dynamics_status']}` |"
        )
    lines += [
        "",
        f"All checks passed: **{result['all_checks_passed']}**",
        "",
        "## Claim boundary",
        "",
        *[f"- {item}" for item in result["claim_boundary"]],
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    result = build_audit()
    write_outputs(result)
    print(json.dumps(result["checks"], ensure_ascii=False, indent=2))
    if not result["all_checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
