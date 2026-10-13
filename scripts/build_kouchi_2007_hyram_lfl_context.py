"""Reproduce a claim-bounded HyRAM comparison to one Kouchi 2007 point.

The paper was opened before this endpoint was defined, so the output is a
post-access plausibility diagnostic rather than validation evidence.  It does
not fit or modify any runtime parameter.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from h2station.risk.hyram_adapter import (  # noqa: E402
    AmbientCondition,
    HyRAMRiskMonitor,
    LeakScenario,
)
from h2station.thermo import HydrogenEOS  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(root: Path) -> dict[str, object]:
    pressure_pa = 40.0e6
    temperature_k = 298.15
    aperture_m = 0.2e-3
    published_distance_m = 0.9
    published_concentration_volpct = 4.1
    target_contour_fraction = 0.04

    state = HydrogenEOS().state_pt(pressure_pa, temperature_k)
    monitor = HyRAMRiskMonitor(evaluation_period=1.0e-9)
    snapshot = monitor.evaluate(
        simulation_time=0.0,
        release_state=state,
        scenario=LeakScenario(
            orifice_diameter=aperture_m,
            locations=(),
            discharge_coefficient=1.0,
            release_angle=0.0,
            calculate_flame=False,
            calculate_overpressure=False,
            calculate_dispersion=True,
            dispersion_contour_fraction=target_contour_fraction,
        ),
        ambient=AmbientCondition(
            temperature=298.15,
            pressure=101_325.0,
            relative_humidity=0.50,
        ),
    )
    modeled_distance_m = float(snapshot.flammable_streamline_distance or 0.0)
    absolute_difference_m = abs(modeled_distance_m - published_distance_m)
    relative_difference = absolute_difference_m / published_distance_m
    adapter_path = root / "src/h2station/risk/hyram_adapter.py"

    return {
        "schema_version": 1,
        "artifact_type": "kouchi_2007_hyram_lfl_context_diagnostic",
        "evaluated_at": "2026-10-14",
        "status": "POST_ACCESS_SINGLE_POINT_PLAUSIBILITY_CONTEXT_NOT_VALIDATION",
        "source": {
            "title": "Dispersion Tests on Concentration and its Fluctuations for 40MPa Pressurized Hydrogen",
            "paper_id": "ICHS 2007 1.1.54",
            "official_pdf_url": "https://conference.ing.unipi.it/ichs2007/fileadmin/user_upload/CD/PAPERS/12SEPT/1.1.54.pdf",
            "pdf_sha256": "a80ab4303b8f5f167fe1cb1fac7d38e6e46c92199be669b46f2914607aa5b4ec",
            "test_gas": "hydrogen",
            "reported_pressure_mpa": 40.0,
            "reported_aperture_mm": 0.2,
            "reported_release_direction": "horizontal",
            "reported_point_distance_m": published_distance_m,
            "reported_time_averaged_concentration_volpct": published_concentration_volpct,
            "source_location": "section 3.2 and Figures 8-10",
        },
        "model": {
            "engine": "HyRAM+",
            "version": importlib.metadata.version("hyram"),
            "adapter": "src/h2station/risk/hyram_adapter.py",
            "adapter_sha256": _sha256(adapter_path),
            "source_pressure_pa": pressure_pa,
            "assumed_source_temperature_k": temperature_k,
            "orifice_diameter_m": aperture_m,
            "discharge_coefficient": 1.0,
            "release_angle_rad": 0.0,
            "ambient_temperature_k": 298.15,
            "ambient_pressure_pa": 101_325.0,
            "nozzle_model": "yuce",
            "target_centerline_mole_fraction": target_contour_fraction,
            "parameter_fitting_executed": False,
        },
        "result": {
            "modeled_mass_flow_kg_s": float(snapshot.mass_flow_rate),
            "modeled_4volpct_streamline_distance_m": modeled_distance_m,
            "published_near_lfl_point_distance_m": published_distance_m,
            "published_point_concentration_volpct": published_concentration_volpct,
            "absolute_distance_difference_m": absolute_difference_m,
            "relative_distance_difference_fraction": relative_difference,
            "relative_distance_difference_percent": relative_difference * 100.0,
        },
        "interpretation": {
            "published_point_is_exact_4volpct_contour": False,
            "published_point_is_near_4volpct": True,
            "source_temperature_reported": False,
            "meteorology_matched": False,
            "single_point_only": True,
            "post_access_endpoint": True,
            "independent_validation": False,
            "runtime_parameter_application": False,
            "spatial_detector_gate_changed": False,
            "consequence_validation_gate_changed": False,
        },
        "claim_boundary": "The current HyRAM+ 6.1 4 vol% centreline distance is compared with one published actual-hydrogen point at 4.1 vol% and nearly the same distance. The endpoint was defined after the paper was opened, source temperature and meteorology were not matched, and the published point is not an exact 4 vol% contour crossing. This is a single-point physical-plausibility context only, not model validation, parameter calibration, an emergency separation distance, or evidence of field safety.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/kouchi_2007_hyram_lfl_context_2026_10_14.json"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output
    if not output.is_absolute():
        output = root / output
    result = build(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "output": str(output),
        "status": result["status"],
        "modeled_4volpct_streamline_distance_m": result["result"][
            "modeled_4volpct_streamline_distance_m"
        ],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
