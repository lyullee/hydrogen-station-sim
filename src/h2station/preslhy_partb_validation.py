"""PRESLHY Cryostat Part-B ambient holdout reader.

The Part-B archive is a separate public experiment series from the older
DisCha archive.  This module only reads the five ambient-temperature gas
blow-down workbooks and supplies the measured Cryostat volume to the frozen
release model.  No case-specific fitting, time warping, or post-outcome
parameter selection is performed here.
"""

from __future__ import annotations

from io import BytesIO
import math
from pathlib import Path, PurePosixPath
import re
from typing import Iterable

import numpy as np
from openpyxl import load_workbook
from scipy.integrate import solve_ivp

from .full_station import CascadeBank, CascadeBankParameters, CascadeBankState
from .preslhy_validation import (
    PreslhyCaseResult,
    PreslhyTrace,
    _crossing_time,
    eligible_pressure_window,
)
from .risk.live import DynamicLeakModel, LeakScenario, LeakSourceState
from .tabulated import PropsSI


CRYOSTAT_VOLUME_M3 = 0.225
STANDARD_AMBIENT_PRESSURE_PA = 101_325.0
RELEASE_DETECTION_THRESHOLD_BAR_G = 0.1


def _numeric(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _release_columns(sheet) -> tuple[int, int, int, int]:
    """Return header row, relative-time column and vessel-pressure column."""
    header_row = None
    time_column = None
    pressure_column = None
    for row_index in range(1, min(sheet.max_row, 20) + 1):
        values = [str(value or "").strip().lower() for value in next(
            sheet.iter_rows(
                min_row=row_index,
                max_row=row_index,
                max_col=min(sheet.max_column, 40),
                values_only=True,
            )
        )]
        for column, value in enumerate(values):
            normal = re.sub(r"[^a-z0-9]", "", value)
            if normal in {"timenews", "times"} and time_column is None:
                header_row, time_column = row_index, column
            if normal in {"pinnen", "pvessel"}:
                pressure_column = column
    if header_row is None or time_column is None or pressure_column is None:
        raise ValueError("Part-B release sheet lacks Time new [s] or P-Innen")
    nozzle_column = None
    for column, value in enumerate(
        next(
            sheet.iter_rows(
                min_row=header_row,
                max_row=header_row,
                max_col=min(sheet.max_column, 40),
                values_only=True,
            )
        )
    ):
        normal = re.sub(r"[^a-z0-9]", "", str(value or "").lower())
        if normal in {"pduese", "pnozzle"}:
            nozzle_column = column
    if nozzle_column is None:
        raise ValueError("Part-B release sheet lacks P-Duese")
    return header_row, time_column, pressure_column, nozzle_column


def _release_samples(sheet, header_row: int, time_column: int, pressure_column: int,
                     nozzle_column: int) -> np.ndarray:
    rows: list[tuple[float, float, float]] = []
    for row in sheet.iter_rows(
        min_row=header_row + 2,
        max_col=max(time_column, pressure_column, nozzle_column) + 1,
        values_only=True,
    ):
        time_s = _numeric(row[time_column] if time_column < len(row) else None)
        pressure = _numeric(row[pressure_column] if pressure_column < len(row) else None)
        nozzle = _numeric(row[nozzle_column] if nozzle_column < len(row) else None)
        if time_s is None or pressure is None or nozzle is None:
            continue
        rows.append((time_s, pressure, nozzle))
    if len(rows) < 20:
        raise ValueError("fewer than 20 finite Part-B release samples")
    values = np.asarray(rows, dtype=float)
    order = np.argsort(values[:, 0], kind="stable")
    values = values[order]
    unique = np.concatenate(([True], np.diff(values[:, 0]) > 0.0))
    return values[unique]


def _initial_temperature_k(workbook) -> float:
    candidates = [sheet for sheet in workbook.worksheets if "-te" in sheet.title.lower()]
    if not candidates:
        raise ValueError("Part-B temperature sheet not found")
    sheet = candidates[0]
    header_row = None
    time_column = None
    temperature_columns: list[int] = []
    for row_index in range(1, min(sheet.max_row, 20) + 1):
        row = next(
            sheet.iter_rows(
                min_row=row_index,
                max_row=row_index,
                max_col=min(sheet.max_column, 40),
                values_only=True,
            )
        )
        for column, value in enumerate(row):
            normal = re.sub(r"[^a-z0-9]", "", str(value or "").lower())
            if normal in {"timenews", "times"} and time_column is None:
                header_row, time_column = row_index, column
            if re.fullmatch(r"cryo[1-5]", normal):
                temperature_columns.append(column)
    if header_row is None or time_column is None or len(temperature_columns) < 3:
        raise ValueError("Part-B temperature channels not found")
    samples: list[float] = []
    for row in sheet.iter_rows(
        min_row=header_row + 2,
        max_col=max([time_column, *temperature_columns]) + 1,
        values_only=True,
    ):
        time_s = _numeric(row[time_column] if time_column < len(row) else None)
        if time_s is None or not -1.0 <= time_s < 0.0:
            continue
        values = [
            _numeric(row[column] if column < len(row) else None)
            for column in temperature_columns
        ]
        samples.extend(value for value in values if value is not None)
    if len(samples) < 3:
        raise ValueError("fewer than 3 pre-release Part-B temperature samples")
    return float(np.median(samples))


def read_preslhy_partb_workbook(
    payload: bytes,
    *,
    source_package: str,
    source_member: str,
) -> PreslhyTrace:
    """Read one published ambient Cryostat workbook without model fitting."""
    match = re.search(r"-(?P<diameter>[0-9]+(?:\.[0-9]+)?)mm-", PurePosixPath(source_member).name)
    if not match:
        raise ValueError("no nozzle diameter in Part-B filename")
    nozzle_diameter_mm = float(match.group("diameter"))
    workbook = load_workbook(BytesIO(payload), read_only=True, data_only=True)
    try:
        release_sheet = next(
            (
                sheet
                for sheet in workbook.worksheets
                if "-vd" in sheet.title.lower() or "-v10" in sheet.title.lower()
            ),
            None,
        )
        if release_sheet is None:
            raise ValueError("Part-B release worksheet not found")
        header_row, time_column, pressure_column, nozzle_column = _release_columns(
            release_sheet
        )
        values = _release_samples(
            release_sheet, header_row, time_column, pressure_column, nozzle_column
        )
        # The event is defined prospectively from the published nozzle pressure
        # channel, not from a fitted shift.  The sensor is gauge pressure.
        opened = np.flatnonzero(values[:, 2] >= RELEASE_DETECTION_THRESHOLD_BAR_G)
        if not opened.size:
            raise ValueError("no identifiable release start in P-Duese")
        release_index = int(opened[0])
        release_time = float(values[release_index, 0])
        time_s = values[:, 0] - release_time
        pressure_bar_abs = values[:, 1] + STANDARD_AMBIENT_PRESSURE_PA / 1.0e5
        if np.count_nonzero(time_s >= 0.0) < 20:
            raise ValueError("fewer than 20 samples after release start")
        initial_pressure = float(
            np.median(values[(time_s >= -1.0) & (time_s < 0.0), 1])
        )
        if not math.isfinite(initial_pressure) or initial_pressure <= 0.0:
            raise ValueError("non-positive initial gauge pressure")
        return PreslhyTrace(
            case_id=PurePosixPath(source_member).stem,
            source_package=source_package,
            source_member=source_member,
            nozzle_diameter_mm=nozzle_diameter_mm,
            time_s=time_s,
            pressure_bar_abs=pressure_bar_abs,
            initial_temperature_k=_initial_temperature_k(workbook),
            ambient_pressure_pa=STANDARD_AMBIENT_PRESSURE_PA,
            pressure_unit_interpretation="header_gauge_plus_standard_ambient",
            temperature_substituted=False,
            ambient_pressure_substituted=False,
        )
    finally:
        workbook.close()


def iter_preslhy_partb_traces(root: Path) -> Iterable[PreslhyTrace]:
    """Yield only the five ambient Final workbooks in the extracted archive."""
    for path in sorted(root.glob("*_290K-*mm-*.xlsx")):
        if not path.stem.lower().endswith("-final"):
            continue
        yield read_preslhy_partb_workbook(
            path.read_bytes(),
            source_package=path.parent.name,
            source_member=path.name,
        )


def simulate_preslhy_partb_blowdown(
    trace: PreslhyTrace,
    evaluation_time_s: np.ndarray,
    *,
    discharge_coefficient: float = 0.8,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run the unchanged release equations with the reported 225 dm³ volume."""
    initial_pressure = trace.initial_pressure_pa
    bank = CascadeBank(
        CascadeBankParameters(
            name="preslhy-cryostat-part-b",
            internal_volume_m3=CRYOSTAT_VOLUME_M3,
            target_pressure_pa=initial_pressure,
            wall_mass_kg=1.0,
            wall_specific_heat_j_kg_k=1.0,
            gas_wall_ua_w_k=0.0,
            wall_ambient_ua_w_k=0.0,
        )
    )
    initial = bank.initial_state(initial_pressure, trace.initial_temperature_k)
    leak = DynamicLeakModel()
    scenario = LeakScenario(
        release_id=trace.case_id,
        component_id="PRESLHY-Cryostat",
        location="direct circular aperture",
        start_time_s=0.0,
        orifice_diameter_m=trace.nozzle_diameter_mm / 1000.0,
        discharge_coefficient=discharge_coefficient,
    )
    ambient = trace.ambient_pressure_pa

    def derivative(_time, vector):
        state = CascadeBankState.from_vector(vector)
        gas = bank.gas_state(state)
        if gas.pressure_pa <= ambient * 1.000001:
            return np.zeros(3)
        flow = leak.mass_flow_kg_s(
            scenario,
            LeakSourceState(gas.pressure_pa, gas.temperature_k, ambient),
        )
        flow = min(flow, state.hydrogen_mass_kg / 1.0e-3)
        return np.asarray([-flow, -flow * gas.specific_enthalpy_j_kg, 0.0])

    end_time = float(evaluation_time_s[-1])
    solution = solve_ivp(
        derivative,
        (0.0, end_time),
        initial.as_vector(),
        method="LSODA",
        rtol=1.0e-7,
        atol=(1.0e-10, 1.0e-2, 1.0e-8),
        max_step=max(0.001, min(0.1, end_time / 500.0)),
    )
    if not solution.success:
        raise RuntimeError(f"PRESLHY Part-B integration failed: {solution.message}")
    node_states = [
        bank.gas_state(CascadeBankState.from_vector(solution.y[:, index]))
        for index in range(solution.y.shape[1])
    ]
    pressure_nodes = np.asarray([state.pressure_pa for state in node_states])
    node_flows = [
        leak.mass_flow_kg_s(
            scenario,
            LeakSourceState(state.pressure_pa, state.temperature_k, ambient),
        )
        if state.pressure_pa > ambient * 1.000001
        else 0.0
        for state in node_states
    ]
    requested = np.asarray(evaluation_time_s, dtype=float)
    predicted = np.interp(requested, solution.t, pressure_nodes)
    mass = np.interp(requested, solution.t, solution.y[0])
    return predicted, mass, np.asarray([max(node_flows, default=0.0)])


def evaluate_preslhy_partb_trace(trace: PreslhyTrace) -> PreslhyCaseResult:
    """Apply the frozen primary screens to one Part-B ambient trace."""
    time_s, measured_bar = eligible_pressure_window(trace)
    measured_pa = measured_bar * 1.0e5
    predicted_pa, mass, peak_flow = simulate_preslhy_partb_blowdown(trace, time_s)
    errors_bar = (predicted_pa - measured_pa) / 1.0e5
    initial_pressure = trace.initial_pressure_pa
    target = trace.ambient_pressure_pa + 0.5 * (
        initial_pressure - trace.ambient_pressure_pa
    )
    experimental_half = _crossing_time(time_s, measured_pa, target)
    predicted_half = _crossing_time(time_s, predicted_pa, target)
    if not math.isfinite(experimental_half) or experimental_half <= 0.0:
        half_error = math.inf
    elif not math.isfinite(predicted_half):
        half_error = math.inf
    else:
        half_error = abs(predicted_half - experimental_half) / experimental_half * 100.0
    nrmse = float(np.sqrt(np.mean(errors_bar**2)) * 1.0e5 / initial_pressure * 100.0)
    pressure_pass = nrmse <= 10.0
    half_pass = half_error <= 20.0
    return PreslhyCaseResult(
        case_id=trace.case_id,
        nozzle_diameter_mm=trace.nozzle_diameter_mm,
        initial_pressure_bar_abs=initial_pressure / 1.0e5,
        samples=len(time_s),
        pressure_rmse_bar=float(np.sqrt(np.mean(errors_bar**2))),
        pressure_mae_bar=float(np.mean(np.abs(errors_bar))),
        pressure_nrmse_percent_initial_absolute_pressure=nrmse,
        experimental_time_to_50_percent_gauge_s=experimental_half,
        predicted_time_to_50_percent_gauge_s=predicted_half,
        time_to_50_percent_gauge_relative_error_percent=half_error,
        pressure_screen_pass=pressure_pass,
        half_time_screen_pass=half_pass,
        joint_primary_screen_pass=pressure_pass and half_pass,
        peak_mass_flow_kg_s=float(peak_flow[0]),
        cumulative_released_mass_kg=float(
            PropsSI(
                "Dmass", "P", initial_pressure, "T", trace.initial_temperature_k,
                "Hydrogen",
            )
            * CRYOSTAT_VOLUME_M3
            - mass[-1]
        ),
    )


__all__ = [
    "CRYOSTAT_VOLUME_M3",
    "RELEASE_DETECTION_THRESHOLD_BAR_G",
    "iter_preslhy_partb_traces",
    "evaluate_preslhy_partb_trace",
    "read_preslhy_partb_workbook",
    "simulate_preslhy_partb_blowdown",
]
