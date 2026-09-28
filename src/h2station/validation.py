"""Traceable validation utilities for dynamic hydrogen-station models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

import numpy as np
from scipy.interpolate import PchipInterpolator


class OutputChannel(str, Enum):
    DISPENSED_MASS_FLOW = "dispenser.mass_flow"
    BANK_PRESSURE = "storage.bank.pressure"
    BANK_TEMPERATURE = "storage.bank.temperature"
    PCV_INLET_PRESSURE = "dispenser.pcv.inlet_pressure"
    PCV_INLET_TEMPERATURE = "dispenser.pcv.inlet_temperature"
    PCV_OUTLET_PRESSURE = "dispenser.pcv.outlet_pressure"
    PCV_OUTLET_TEMPERATURE = "dispenser.pcv.outlet_temperature"
    PRESSURE_REFERENCE = "controller.pressure_reference"
    PRECOOLER_OUTLET_TEMPERATURE = "precooler.outlet_temperature"
    PRECOOLER_HEAT_RATE = "precooler.heat_rate"
    HOSE_PRESSURE = "dispenser.hose.pressure"
    HOSE_TEMPERATURE = "dispenser.hose.temperature"
    RECEPTACLE_PRESSURE = "vehicle.receptacle.pressure"
    RECEPTACLE_TEMPERATURE = "vehicle.receptacle.temperature"
    VEHICLE_INLET_PRESSURE = "vehicle.tank.inlet_pressure"
    VEHICLE_INLET_TEMPERATURE = "vehicle.tank.inlet_temperature"
    VEHICLE_GAS_PRESSURE = "vehicle.tank.gas_pressure"
    VEHICLE_GAS_TEMPERATURE = "vehicle.tank.gas_temperature"
    LINER_INNER_TEMPERATURE = "vehicle.tank.liner_inner_temperature"
    LINER_CFRP_TEMPERATURE = "vehicle.tank.liner_cfrp_temperature"
    CFRP_OUTER_TEMPERATURE = "vehicle.tank.cfrp_outer_temperature"
    VEHICLE_SOC = "vehicle.tank.soc"
    INJECTOR_VELOCITY = "vehicle.tank.injector_velocity"


@dataclass(frozen=True)
class ValidationTrace:
    channel: OutputChannel
    time_s: np.ndarray
    values: np.ndarray
    unit: str
    source: str
    case_id: str

    def __post_init__(self) -> None:
        time = np.asarray(self.time_s, dtype=float)
        values = np.asarray(self.values, dtype=float)
        if time.ndim != 1 or values.ndim != 1 or len(time) != len(values):
            raise ValueError("time_s and values must be equal-length one-dimensional arrays")
        if len(time) < 2 or np.any(np.diff(time) <= 0.0):
            raise ValueError("time_s must contain at least two strictly increasing points")
        if not np.all(np.isfinite(time)) or not np.all(np.isfinite(values)):
            raise ValueError("Validation traces cannot contain non-finite values")
        if not self.unit or not self.source or not self.case_id:
            raise ValueError("unit, source, and case_id are required for traceability")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "values", values)


@dataclass(frozen=True)
class ValidationCriterion:
    maximum_nrmse: float | None = None
    maximum_absolute_error: float | None = None
    maximum_final_error: float | None = None
    normalization: float | None = None

    def __post_init__(self) -> None:
        supplied = (
            self.maximum_nrmse,
            self.maximum_absolute_error,
            self.maximum_final_error,
        )
        if all(value is None for value in supplied):
            raise ValueError("At least one acceptance limit must be supplied")
        if any(value is not None and value < 0.0 for value in supplied):
            raise ValueError("Acceptance limits cannot be negative")
        if self.normalization is not None and self.normalization <= 0.0:
            raise ValueError("normalization must be positive")


@dataclass(frozen=True)
class ChannelValidationResult:
    channel: OutputChannel
    case_id: str
    sample_count: int
    nrmse: float
    mean_error: float
    maximum_absolute_error: float
    final_error: float
    passed: bool
    failures: tuple[str, ...]


@dataclass(frozen=True)
class ValidationReport:
    case_id: str
    results: tuple[ChannelValidationResult, ...]

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(result.passed for result in self.results)


class DynamicModelValidator:
    """Compare simulation traces with measurements on their overlapping time range."""

    def compare(
        self,
        simulation: ValidationTrace,
        reference: ValidationTrace,
        criterion: ValidationCriterion,
    ) -> ChannelValidationResult:
        if simulation.channel is not reference.channel:
            raise ValueError("Simulation and reference channels must match")
        if simulation.unit != reference.unit:
            raise ValueError("Convert traces to the same unit before validation")
        if simulation.case_id != reference.case_id:
            raise ValueError("Simulation and reference case IDs must match")

        start_s = max(simulation.time_s[0], reference.time_s[0])
        end_s = min(simulation.time_s[-1], reference.time_s[-1])
        reference_mask = (reference.time_s >= start_s) & (reference.time_s <= end_s)
        comparison_time_s = reference.time_s[reference_mask]
        if len(comparison_time_s) < 2:
            raise ValueError("Traces need at least two overlapping reference samples")

        interpolator = PchipInterpolator(
            simulation.time_s,
            simulation.values,
            extrapolate=False,
        )
        predicted = np.asarray(interpolator(comparison_time_s), dtype=float)
        observed = reference.values[reference_mask]
        error = predicted - observed

        scale = criterion.normalization
        if scale is None:
            scale = float(np.max(observed) - np.min(observed))
        if scale <= np.finfo(float).eps:
            scale = max(float(np.max(np.abs(observed))), 1.0)

        nrmse = float(np.sqrt(np.mean(error * error)) / scale)
        maximum_absolute_error = float(np.max(np.abs(error)))
        final_error = float(error[-1])
        failures: list[str] = []
        if criterion.maximum_nrmse is not None and nrmse > criterion.maximum_nrmse:
            failures.append("nrmse")
        if (
            criterion.maximum_absolute_error is not None
            and maximum_absolute_error > criterion.maximum_absolute_error
        ):
            failures.append("maximum_absolute_error")
        if (
            criterion.maximum_final_error is not None
            and abs(final_error) > criterion.maximum_final_error
        ):
            failures.append("final_error")

        return ChannelValidationResult(
            channel=simulation.channel,
            case_id=simulation.case_id,
            sample_count=len(comparison_time_s),
            nrmse=nrmse,
            mean_error=float(np.mean(error)),
            maximum_absolute_error=maximum_absolute_error,
            final_error=final_error,
            passed=not failures,
            failures=tuple(failures),
        )

    def validate_case(
        self,
        simulations: Mapping[OutputChannel, ValidationTrace],
        references: Mapping[OutputChannel, ValidationTrace],
        criteria: Mapping[OutputChannel, ValidationCriterion],
    ) -> ValidationReport:
        channels = set(references) & set(criteria)
        missing = channels - set(simulations)
        if missing:
            names = ", ".join(sorted(channel.value for channel in missing))
            raise ValueError(f"Missing simulation channels: {names}")
        if not channels:
            raise ValueError("No reference channels have validation criteria")

        case_ids = {references[channel].case_id for channel in channels}
        if len(case_ids) != 1:
            raise ValueError("All reference traces must belong to one case")
        results = tuple(
            self.compare(simulations[channel], references[channel], criteria[channel])
            for channel in sorted(channels, key=lambda item: item.value)
        )
        return ValidationReport(case_id=case_ids.pop(), results=results)


def mass_balance_residual_kg(
    time_s: np.ndarray,
    inlet_mass_flow_kg_s: np.ndarray,
    outlet_mass_flow_kg_s: np.ndarray,
    initial_inventory_kg: float,
    final_inventory_kg: float,
) -> float:
    """Return final minus expected inventory using trapezoidal flow integration."""

    time = np.asarray(time_s, dtype=float)
    inlet = np.asarray(inlet_mass_flow_kg_s, dtype=float)
    outlet = np.asarray(outlet_mass_flow_kg_s, dtype=float)
    if time.ndim != 1 or inlet.shape != time.shape or outlet.shape != time.shape:
        raise ValueError("Mass-balance arrays must have matching one-dimensional shapes")
    if len(time) < 2 or np.any(np.diff(time) <= 0.0):
        raise ValueError("time_s must be strictly increasing")
    net_flow = inlet - outlet
    transferred_mass = float(
        np.sum(0.5 * (net_flow[1:] + net_flow[:-1]) * np.diff(time))
    )
    expected_final = initial_inventory_kg + transferred_mass
    return final_inventory_kg - expected_final

