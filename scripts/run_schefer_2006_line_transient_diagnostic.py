"""Run a post-outcome line-inventory diagnostic for the Schefer 2006 trace.

This is deliberately not a replacement for the frozen holdout.  The published
apparatus geometry was already recorded in the frozen protocol, so the
downstream tube volume can be introduced without fitting an outcome.  The
result is retained as development evidence only; it cannot change the
prospective gate.
"""

from __future__ import annotations

from datetime import date
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np

from h2station.line_transient_development import (
    LineTransientParameters,
    simulate_line_transient,
)
from h2station.schefer_2006_validation import load_schefer_flow_csv


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/public_validation/raw/hyram-v6.1/tests/hyram/validation/data/schefer-2006-fig3b.csv"
PROTOCOL = ROOT / "research/schefer_2006_holdout_protocol.json"
OUTPUT = ROOT / "research/schefer_2006_line_transient_diagnostic_2026_10_09.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metrics(measured: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    peak = float(np.max(measured))
    relative = measured >= 0.1 * peak
    return {
        "predicted_peak_mass_flow_g_s": float(np.max(predicted)),
        "mass_flow_nrmse_percent_peak_measured": float(
            np.sqrt(np.mean((predicted - measured) ** 2)) / peak * 100.0
        ),
        "median_absolute_percentage_error_percent": float(
            np.median(np.abs(predicted[relative] - measured[relative]) / measured[relative])
            * 100.0
        ),
    }


def main() -> None:
    trace = load_schefer_flow_csv(DATA)
    parameters = LineTransientParameters(
        source_volume_m3=0.098,
        source_pressure_pa_abs=15.513e6,
        source_temperature_k=315.15,
        line_length_m=7.6,
        line_inner_diameter_m=0.00794,
        outlet_inner_diameter_m=0.003175,
        source_to_line_discharge_coefficient=1.0,
        outlet_discharge_coefficient=1.0,
    )
    result = simulate_line_transient(trace.time_s, parameters=parameters)
    measured = trace.measured_mass_flow_g_s
    valve_sensitivity = []
    # The two very short values are intentionally left for a future stiff
    # solver study; this bounded grid keeps the diagnostic reproducible on the
    # same EOS backend used by the development model.
    for time_constant_s in (0.0, 0.5, 1.0, 2.0, 4.0):
        candidate = replace(
            parameters,
            source_valve_time_constant_s=time_constant_s,
        )
        candidate_result = simulate_line_transient(
            trace.time_s, parameters=candidate
        )
        valve_sensitivity.append(
            {
                "source_valve_time_constant_s": time_constant_s,
                "source_flow": _metrics(
                    measured, candidate_result.source_flow_kg_s * 1000.0
                ),
                "outlet_flow": _metrics(
                    measured, candidate_result.outlet_flow_kg_s * 1000.0
                ),
            }
        )
    payload = {
        "schema_version": 1,
        "artifact_type": "post_outcome_line_inventory_diagnostic",
        "generated_at": date.today().isoformat(),
        "post_outcome_diagnostic": True,
        "protocol_sha256": _sha256(PROTOCOL),
        "data_sha256": _sha256(DATA),
        "model": {
            "module": "src/h2station/line_transient_development.py",
            "source_volume_m3": parameters.source_volume_m3,
            "line_length_m": parameters.line_length_m,
            "line_inner_diameter_m": parameters.line_inner_diameter_m,
            "outlet_inner_diameter_m": parameters.outlet_inner_diameter_m,
            "line_volume_m3": parameters.line_volume_m3,
            "discharge_coefficients": {
                "source_to_line": parameters.source_to_line_discharge_coefficient,
                "outlet": parameters.outlet_discharge_coefficient,
            },
            "default_valve_time_constants_s": {
                "source_to_line": parameters.source_valve_time_constant_s,
                "outlet": parameters.outlet_valve_time_constant_s,
            },
        },
        "instrument_boundary_views": {
            "source_flow": _metrics(measured, result.source_flow_kg_s * 1000.0),
            "outlet_flow": _metrics(measured, result.outlet_flow_kg_s * 1000.0),
        },
        "post_outcome_valve_time_constant_sensitivity": valve_sensitivity,
        "frozen_result_unchanged": True,
        "runtime_parameter_updated": False,
        "validation_gate_effect": "none",
        "claim_supported": False,
        "interpretation": [
            "The explicit downstream-line inventory is numerically stable and preserves separate source and outlet flow boundaries.",
            "The geometry-only line state does not remove the frozen median-error or timing failures. A post-outcome 0.5-4 s source-valve sensitivity approaches the median-error screen at the longest value, but it is not a fitted or validated setting and the timing endpoint remains unresolved.",
            "A new untouched campaign with a declared measurement boundary is required before this model can be frozen for validation.",
        ],
        "claim_boundary": "This post-outcome diagnostic does not alter or replace the Schefer 2006 prospective result and does not validate a station loop, consequence distance or safety control.",
    }
    OUTPUT.write_bytes((json.dumps(payload, indent=2) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
