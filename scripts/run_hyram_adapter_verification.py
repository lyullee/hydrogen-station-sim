"""Verify the production consequence adapter against HyRAM+ 6.1.

Sandia's tests establish the upstream model's published validation evidence.
Local parity cases separately establish that this repository preserves the
upstream API's units, coordinates, contours, and output indexing.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import hyram
import numpy as np
from hyram.phys import api

from h2station.risk.hyram_adapter import AmbientCondition, HyRAMRiskMonitor, LeakScenario
from h2station.thermo_types import ThermoState


UPSTREAM_COMMIT = "b45abf9a6d995951311be6aad836f1874e4d420b"
UPSTREAM_TAG = "v6.1"
UPSTREAM_REPOSITORY = "https://github.com/sandialabs/hyram.git"
VALIDATION_MODULES = (
    "tests/hyram/validation/test_jetplume.py",
    "tests/hyram/validation/test_heatflux.py",
    "tests/hyram/validation/test_unconfined_overpressure.py",
)


@dataclass(frozen=True)
class VerificationCase:
    case_id: str
    pressure_pa: float
    temperature_k: float
    orifice_diameter_m: float
    discharge_coefficient: float
    release_angle_rad: float
    relative_humidity: float
    mass_flow_override_kg_s: float | None = None


CASES = (
    VerificationCase("low-bank-1mm", 45.0e6, 298.15, 0.001, 0.8, 0.0, 0.50),
    VerificationCase("mid-bank-2mm-cold", 70.0e6, 253.15, 0.002, 0.8, 0.0, 0.50),
    VerificationCase(
        "high-bank-3mm-override", 100.0e6, 333.15, 0.003, 0.8, 0.0, 0.50,
        mass_flow_override_kg_s=0.025,
    ),
)
LOCATIONS = (
    (1.0, 0.0, 1.0),
    (2.0, 0.0, 1.0),
    (5.0, 0.0, 1.0),
    (10.0, 0.0, 1.0),
)


def _git_state(root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip())
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "unavailable", "dirty": None}


def _python_tree_digest(root: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    files = sorted(root.rglob("*.py"), key=lambda path: path.relative_to(root).as_posix())
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {"python_file_count": len(files), "sha256": digest.hexdigest()}


def _state(case: VerificationCase) -> ThermoState:
    # The adapter consumes pressure and temperature only. NaN makes accidental
    # use of unrelated fields visible instead of introducing a second EOS.
    return ThermoState(
        pressure=case.pressure_pa, temperature=case.temperature_k,
        density=float("nan"), internal_energy=float("nan"), enthalpy=float("nan"),
        entropy=float("nan"), cp=float("nan"), cv=float("nan"),
        viscosity=float("nan"), conductivity=float("nan"),
        compressibility=float("nan"), speed_of_sound=float("nan"),
    )


def _direct_hyram(case: VerificationCase) -> dict[str, Any]:
    ambient = api.create_fluid("air", temp=298.15, pres=101_325.0)
    release = api.create_fluid("H2", temp=case.temperature_k, pres=case.pressure_pa)
    requested = case.mass_flow_override_kg_s
    if requested is None:
        mass_flow = float(np.asarray(api.compute_mass_flow(
            release, case.orifice_diameter_m, amb_pres=101_325.0, is_steady=True,
            dis_coeff=case.discharge_coefficient, create_plot=False,
        )["rates"]).reshape(-1)[0])
    else:
        mass_flow = requested

    plume = api.analyze_jet_plume(
        ambient, release, case.orifice_diameter_m, mass_flow=mass_flow,
        rel_angle=case.release_angle_rad, dis_coeff=case.discharge_coefficient,
        nozzle_model="yuce", create_plot=False, contours=[0.04],
    )
    modeled_mass_flow = float(plume["mass_flow_rate"])
    flame = api.jet_flame_analysis(
        ambient, release, case.orifice_diameter_m, mass_flow=modeled_mass_flow,
        dis_coeff=case.discharge_coefficient, rel_angle=case.release_angle_rad,
        nozzle_key="yuce", rel_humid=case.relative_humidity,
        create_temp_plot=False, analyze_flux=True, create_flux_plot=False,
        flux_coordinates=list(LOCATIONS),
    )
    modeled_mass_flow = float(flame[3])
    blast = api.compute_overpressure(
        "bst", list(LOCATIONS), ambient, release, case.orifice_diameter_m,
        mass_flow=modeled_mass_flow, release_angle=case.release_angle_rad,
        discharge_coefficient=case.discharge_coefficient, nozzle_model="yuce",
        bst_flame_speed=0.35, tnt_factor=0.03,
        create_overpressure_plot=False, create_impulse_plot=False,
    )
    contour = plume["mole_frac_dists"][0.04]
    return {
        "modeled_mass_flow_kg_s": modeled_mass_flow,
        "heat_flux_w_m2": [float(value) for value in np.asarray(flame[2]).reshape(-1)],
        "overpressure_pa": [float(value) for value in np.asarray(blast["overpressures"]).reshape(-1)],
        "impulse_pa_s": [float(value) for value in np.asarray(blast["impulses"]).reshape(-1)],
        "visible_flame_length_m": float(flame[5]),
        "radiant_fraction": float(flame[6]),
        "plume_4vol_streamline_distance_m": float(np.asarray(plume["streamline_dists"]).reshape(-1)[0]),
        "plume_4vol_x_extent_m": [float(value) for value in contour[0]],
        "plume_4vol_y_extent_m": [float(value) for value in contour[1]],
    }


def _adapter(case: VerificationCase) -> dict[str, Any]:
    result = HyRAMRiskMonitor().evaluate(
        0.0, _state(case),
        LeakScenario(
            orifice_diameter=case.orifice_diameter_m, locations=LOCATIONS,
            discharge_coefficient=case.discharge_coefficient,
            release_angle=case.release_angle_rad, nozzle_model="yuce",
            overpressure_method="bst", bst_flame_speed=0.35, tnt_factor=0.03,
            calculate_flame=True, calculate_overpressure=True,
            calculate_dispersion=True, dispersion_contour_fraction=0.04,
        ),
        AmbientCondition(298.15, 101_325.0, case.relative_humidity),
        mass_flow_override=case.mass_flow_override_kg_s,
    )
    return {
        "modeled_mass_flow_kg_s": result.mass_flow_rate,
        "heat_flux_w_m2": list(result.heat_fluxes),
        "overpressure_pa": list(result.overpressures),
        "impulse_pa_s": list(result.impulses),
        "visible_flame_length_m": result.visible_flame_length,
        "radiant_fraction": result.radiant_fraction,
        "plume_4vol_streamline_distance_m": result.flammable_streamline_distance,
        "plume_4vol_x_extent_m": list(result.flammable_x_extent or ()),
        "plume_4vol_y_extent_m": list(result.flammable_y_extent or ()),
    }


def compare_outputs(direct: dict[str, Any], adapter: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    passed = True
    for name, expected in direct.items():
        actual = adapter[name]
        expected_array = np.asarray(expected, dtype=float)
        actual_array = np.asarray(actual, dtype=float)
        shape_match = expected_array.shape == actual_array.shape
        if shape_match and expected_array.size:
            absolute = np.abs(actual_array - expected_array)
            denominator = np.maximum(np.abs(expected_array), 1.0e-30)
            max_absolute = float(np.max(absolute))
            max_relative = float(np.max(absolute / denominator))
            match = bool(np.allclose(actual_array, expected_array, rtol=1.0e-12, atol=1.0e-9))
        else:
            max_absolute = None
            max_relative = None
            match = shape_match and expected_array.size == 0
        fields[name] = {
            "match": match, "shape_match": shape_match,
            "max_absolute_error": max_absolute, "max_relative_error": max_relative,
        }
        passed = passed and match
    return {"passed": passed, "fields": fields}


def _run_upstream_validation(upstream_root: Path) -> dict[str, Any]:
    if not upstream_root.exists():
        return {"status": "not_run", "reason": f"missing upstream checkout: {upstream_root}"}
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=upstream_root,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    command = [sys.executable, "-m", "pytest", *VALIDATION_MODULES, "-q"]
    environment = os.environ.copy()
    environment.update({"PYTHONUTF8": "1", "MPLBACKEND": "Agg"})
    completed = subprocess.run(
        command, cwd=upstream_root, env=environment,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    passed_match = re.search(r"(\d+) passed", output)
    subtests_match = re.search(r"(\d+) subtests passed", output)
    warnings_match = re.search(r"(\d+) warnings?", output)
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "return_code": completed.returncode,
        "upstream_commit": commit,
        "expected_commit": UPSTREAM_COMMIT,
        "commit_match": commit == UPSTREAM_COMMIT,
        "test_modules": list(VALIDATION_MODULES),
        "passed_test_count": int(passed_match.group(1)) if passed_match else None,
        "passed_subtest_count": int(subtests_match.group(1)) if subtests_match else None,
        "warning_count": int(warnings_match.group(1)) if warnings_match else 0,
        "output_tail": "\n".join(output.splitlines()[-20:]),
    }


def _markdown(report: dict[str, Any]) -> str:
    upstream = report["upstream_validation"]
    rows = []
    for case in report["adapter_parity_cases"]:
        adapter = case["adapter_output"]
        rows.append(
            f"| {case['case']['case_id']} | {case['status']} | "
            f"{adapter['modeled_mass_flow_kg_s']:.6f} | "
            f"{adapter['plume_4vol_streamline_distance_m']:.3f} | "
            f"{adapter['visible_flame_length_m']:.3f} |"
        )
    return "\n".join([
        "# HyRAM+ 6.1 production-adapter verification",
        "",
        f"Generated: `{report['generated_at']}`  ",
        f"Digital-twin source: `{report['source']['commit']}` (dirty={report['source']['dirty']})  ",
        f"Installed HyRAM: `{report['hyram']['installed_version']}`  ",
        f"Upstream reference: `{UPSTREAM_TAG}` / `{UPSTREAM_COMMIT}`",
        "",
        "## Result",
        "",
        f"- Sandia validation suite: **{upstream['status'].upper()}** "
        f"({upstream.get('passed_test_count')} tests, {upstream.get('passed_subtest_count')} subtests).",
        f"- Installed/upstream Python source identity: **{'MATCH' if report['hyram']['source_identity_match'] else 'MISMATCH'}**.",
        f"- Production-adapter API parity: **{'PASS' if report['adapter_parity_passed'] else 'FAIL'}**.",
        "",
        "| Case | Parity | modeled flow (kg/s) | 4 vol% plume distance (m) | visible flame length (m) |",
        "|---|---:|---:|---:|---:|",
        *rows,
        "",
        "## What this establishes",
        "",
        "Sandia's tests exercise HyRAM against published plume, flame-radiation and unconfined-overpressure experiments. "
        "The local parity cases separately establish that the production adapter preserves SI units, coordinates, contour selection and output indexing for the exact installed package.",
        "",
        "## Claim boundary",
        "",
        "This verification does not independently revalidate HyRAM physics, establish a regulatory separation distance, or validate the station geometry. "
        "The 4 vol% result is a directional centerline distance. Radiation and overpressure values apply only at the listed observation coordinates. "
        "The upstream validation acceptance limits belong to HyRAM's maintainers; they are not new acceptance criteria created by this project.",
        "",
        "## Reproduction",
        "",
        "```powershell",
        "git clone --depth 1 --branch v6.1 https://github.com/sandialabs/hyram.git data\\public_validation\\raw\\hyram-v6.1",
        "$env:PYTHONPATH = \"src\"",
        ".venv\\Scripts\\python.exe scripts\\run_hyram_adapter_verification.py",
        "```",
        "",
        "Machine-readable details, per-field errors and captured upstream test output are written beside this report as `verification.json`.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--upstream-root", type=Path,
        default=Path("data/public_validation/raw/hyram-v6.1"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/public_validation/results/hyram_adapter_verification"),
    )
    parser.add_argument("--skip-upstream", action="store_true")
    args = parser.parse_args()

    repository_root = Path(__file__).resolve().parents[1]
    upstream_root = args.upstream_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    installed_root = Path(inspect.getfile(hyram)).resolve().parent
    upstream_source = upstream_root / "src" / "hyram"
    installed_digest = _python_tree_digest(installed_root)
    upstream_digest = _python_tree_digest(upstream_source) if upstream_source.exists() else None

    cases = []
    for case in CASES:
        direct = _direct_hyram(case)
        adapter = _adapter(case)
        comparison = compare_outputs(direct, adapter)
        cases.append({
            "case": asdict(case),
            "locations_m": [list(location) for location in LOCATIONS],
            "direct_hyram_output": direct,
            "adapter_output": adapter,
            "comparison": comparison,
            "status": "PASS" if comparison["passed"] else "FAIL",
        })

    upstream_validation = (
        {"status": "not_run", "reason": "--skip-upstream"}
        if args.skip_upstream else _run_upstream_validation(upstream_root)
    )
    source_identity = upstream_digest is not None and installed_digest == upstream_digest
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": _git_state(repository_root),
        "hyram": {
            "installed_version": importlib.metadata.version("hyram"),
            "installed_package_root": str(installed_root),
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_tag": UPSTREAM_TAG,
            "upstream_commit": UPSTREAM_COMMIT,
            "installed_source_digest": installed_digest,
            "upstream_source_digest": upstream_digest,
            "source_identity_match": source_identity,
        },
        "unit_mapping": {
            "pressure": "Pa", "temperature": "K", "orifice_diameter": "m",
            "release_angle": "rad", "locations": "m", "heat_flux": "W/m2",
            "overpressure": "Pa", "impulse": "Pa s", "plume_contour": "mole fraction",
        },
        "upstream_validation": upstream_validation,
        "adapter_parity_passed": all(case["comparison"]["passed"] for case in cases),
        "adapter_parity_cases": cases,
    }
    (output / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(_markdown(report), encoding="utf-8")
    print(_markdown(report))
    return 0 if (
        report["adapter_parity_passed"]
        and source_identity
        and upstream_validation["status"] in {"passed", "not_run"}
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
