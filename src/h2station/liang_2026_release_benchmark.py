"""Post-access benchmark against Liang et al. (2026) Table 2.

The published outcomes were visible before this evaluator was written.  The
module therefore measures zero-fit transfer of the existing runtime model; it
does not create a prospective validation claim or tune production parameters.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .risk.live import DynamicLeakModel, LeakScenario, LeakSourceState


SOURCE_DOI = "10.19912/j.0254-0096.tynxb.2024-2238"
SOURCE_URL = "https://www.tynxb.org.cn/CN/10.19912/j.0254-0096.tynxb.2024-2238"
NOZZLE_DIAMETER_M = 0.001
TEMPERATURE_K = 300.15
AMBIENT_PRESSURE_PA = 101_325.0
RUNTIME_DISCHARGE_COEFFICIENT = 0.8
DIAGNOSTIC_DISCHARGE_COEFFICIENT = 0.6


@dataclass(frozen=True)
class LiangReleasePoint:
    case_id: str
    nozzle_pressure_mpa: float
    measured_mass_flow_kg_min: float
    paper_ideal_mass_flow_kg_min: float
    paper_real_gas_mass_flow_kg_min: float
    paper_abel_noble_mass_flow_kg_min: float
    paper_ideal_cd: float
    paper_real_cd: float


def load_points(path: str | Path) -> tuple[LiangReleasePoint, ...]:
    rows: list[LiangReleasePoint] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                LiangReleasePoint(
                    case_id=str(raw["case_id"]),
                    nozzle_pressure_mpa=float(raw["nozzle_pressure_mpa"]),
                    measured_mass_flow_kg_min=float(
                        raw["measured_mass_flow_kg_min"]
                    ),
                    paper_ideal_mass_flow_kg_min=float(
                        raw["paper_ideal_mass_flow_kg_min"]
                    ),
                    paper_real_gas_mass_flow_kg_min=float(
                        raw["paper_real_gas_mass_flow_kg_min"]
                    ),
                    paper_abel_noble_mass_flow_kg_min=float(
                        raw["paper_abel_noble_mass_flow_kg_min"]
                    ),
                    paper_ideal_cd=float(raw["paper_ideal_cd"]),
                    paper_real_cd=float(raw["paper_real_cd"]),
                )
            )
    if len(rows) != 7:
        raise ValueError("Liang Table 2 benchmark requires all seven rows")
    pressures = np.asarray([item.nozzle_pressure_mpa for item in rows])
    if not np.all(np.diff(pressures) > 0.0):
        raise ValueError("Liang Table 2 nozzle pressures must be strictly increasing")
    return tuple(rows)


def predict_mass_flow_kg_min(
    points: tuple[LiangReleasePoint, ...],
    discharge_coefficient: float,
) -> np.ndarray:
    model = DynamicLeakModel()
    predicted: list[float] = []
    for item in points:
        scenario = LeakScenario(
            release_id=f"liang-2026-{item.case_id}",
            component_id="published-round-nozzle",
            location="outdoor-horizontal-release",
            start_time_s=0.0,
            orifice_diameter_m=NOZZLE_DIAMETER_M,
            discharge_coefficient=discharge_coefficient,
        )
        source = LeakSourceState(
            pressure_pa=item.nozzle_pressure_mpa * 1.0e6,
            temperature_k=TEMPERATURE_K,
            ambient_pressure_pa=AMBIENT_PRESSURE_PA,
        )
        predicted.append(model.mass_flow_kg_s(scenario, source) * 60.0)
    return np.asarray(predicted, dtype=float)


def _metrics(predicted: np.ndarray, observed: np.ndarray) -> dict[str, float]:
    residual = predicted - observed
    return {
        "nrmse_percent_of_observed_peak": float(
            np.sqrt(np.mean(residual**2)) / np.max(observed) * 100.0
        ),
        "median_absolute_percentage_error": float(
            np.median(np.abs(residual) / observed) * 100.0
        ),
        "mean_percentage_bias": float(np.mean(residual / observed) * 100.0),
        "maximum_absolute_percentage_error": float(
            np.max(np.abs(residual) / observed) * 100.0
        ),
    }


def evaluate(path: str | Path) -> dict[str, object]:
    points = load_points(path)
    measured = np.asarray(
        [item.measured_mass_flow_kg_min for item in points], dtype=float
    )
    paper_theory = np.asarray(
        [item.paper_abel_noble_mass_flow_kg_min for item in points], dtype=float
    )
    runtime = predict_mass_flow_kg_min(points, RUNTIME_DISCHARGE_COEFFICIENT)
    unit_coefficient = predict_mass_flow_kg_min(points, 1.0)
    diagnostic = predict_mass_flow_kg_min(
        points, DIAGNOSTIC_DISCHARGE_COEFFICIENT
    )
    implied_cd = measured / unit_coefficient

    runtime_metrics = _metrics(runtime, measured)
    theory_metrics = _metrics(unit_coefficient, paper_theory)
    diagnostic_metrics = _metrics(diagnostic, measured)
    runtime_screens = {
        "nrmse_le_15_percent": (
            runtime_metrics["nrmse_percent_of_observed_peak"] <= 15.0
        ),
        "median_ape_le_20_percent": (
            runtime_metrics["median_absolute_percentage_error"] <= 20.0
        ),
    }
    theory_screens = {
        "nrmse_le_2_percent": (
            theory_metrics["nrmse_percent_of_observed_peak"] <= 2.0
        ),
        "median_ape_le_2_percent": (
            theory_metrics["median_absolute_percentage_error"] <= 2.0
        ),
    }
    return {
        "source": {
            "doi": SOURCE_DOI,
            "url": SOURCE_URL,
            "table": "Table 2",
            "medium": "hydrogen",
            "geometry": "1 mm circular nozzle; p2 pressure near nozzle",
            "temperature_k": TEMPERATURE_K,
            "ambient_pressure_pa": AMBIENT_PRESSURE_PA,
        },
        "evidence_role": "POST_ACCESS_ZERO_FIT_BENCHMARK_NOT_PROSPECTIVE",
        "outcomes_accessed_before_protocol": True,
        "parameter_fitting": False,
        "production_model_parameter_changed": False,
        "runtime_model": {
            "discharge_coefficient": RUNTIME_DISCHARGE_COEFFICIENT,
            "metrics": runtime_metrics,
            "screens": runtime_screens,
            "joint_screen_pass": all(runtime_screens.values()),
        },
        "real_gas_equation_parity": {
            "comparison": "runtime Cd=1 prediction versus paper Abel-Noble theory",
            "metrics": theory_metrics,
            "screens": theory_screens,
            "joint_screen_pass": all(theory_screens.values()),
        },
        "diagnostic_only_cd_0_6": {
            "discharge_coefficient": DIAGNOSTIC_DISCHARGE_COEFFICIENT,
            "metrics": diagnostic_metrics,
            "not_promoted_to_runtime": True,
        },
        "effective_discharge_coefficient": {
            "minimum": float(np.min(implied_cd)),
            "median": float(np.median(implied_cd)),
            "maximum": float(np.max(implied_cd)),
        },
        "rows": [
            {
                **asdict(item),
                "runtime_predicted_mass_flow_kg_min": float(runtime[index]),
                "unit_cd_predicted_mass_flow_kg_min": float(
                    unit_coefficient[index]
                ),
                "diagnostic_cd_0_6_mass_flow_kg_min": float(diagnostic[index]),
                "implied_discharge_coefficient": float(implied_cd[index]),
            }
            for index, item in enumerate(points)
        ],
        "decision": {
            "runtime_mass_flow_screen": "PASS" if all(runtime_screens.values()) else "FAIL",
            "real_gas_equation_parity_screen": "PASS" if all(theory_screens.values()) else "FAIL",
            "runtime_action": "UNCHANGED_PENDING_GEOMETRY_SPECIFIC_EXTERNAL_VALIDATION",
            "interpretation": (
                "The real-gas isentropic equation reproduces the paper's Abel-Noble "
                "theory, while the generic runtime Cd=0.8 overpredicts this round-nozzle "
                "experiment. Geometry-specific discharge behavior, not the EOS layer, "
                "controls the remaining discrepancy."
            ),
        },
        "claim_boundary": (
            "The seven numerical outcomes were inspected before this protocol was "
            "written. This is a post-access zero-fit benchmark, not a prospective "
            "holdout or independent validation. The Cd=0.6 comparison is diagnostic "
            "only and is not promoted to runtime. One 1 mm round-nozzle campaign "
            "cannot define coefficients for cracks, valves, long lines, or other "
            "station release geometries."
        ),
    }
