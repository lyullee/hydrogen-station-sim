"""Public experimental operating-range diagnostics.

The public H2IQ benchmark is an aggregate report rather than a row-level
validation trace. This module exposes a transparent comparison next to a
simulation result and never feeds the reported values back into the
controller, thermodynamic model, or safety limits.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping


ARTIFACT_RELATIVE_PATH = "research/public_experimental_benchmarks_2026_10_06.json"
BENCHMARK_ID = "NREL_HD_FAST_FLOW_2024_REPORT"
FCH2RAIL_BENCHMARK_ID = "FCH2RAIL_D61_350BAR_REPORT"


@dataclass(frozen=True)
class PublicBenchmark:
    """One citation-bounded public aggregate benchmark."""

    benchmark_id: str
    title: str
    url: str
    aggregate: Mapping[str, float | str]
    claim_boundary: str


def _artifact_path(root: Path | None = None) -> Path:
    return (root or Path(__file__).resolve().parents[2]) / ARTIFACT_RELATIVE_PATH


def load_public_benchmark(root: Path | None = None) -> PublicBenchmark | None:
    """Load the public high-flow benchmark after provenance checks.

    Missing or malformed research metadata returns ``None`` rather than
    changing a simulation result. The runtime has no hard-coded operating
    setpoint derived from this file.
    """

    try:
        record = json.loads(_artifact_path(root).read_text(encoding="utf-8"))
        if (
            record.get("artifact_type") != "public_experimental_operating_benchmarks"
            or record.get("status") != "citation_bounded_aggregate_benchmarks"
        ):
            return None
        source = next(
            item for item in record.get("sources", [])
            if item.get("id") == BENCHMARK_ID
        )
        aggregate = source.get("aggregate") or {}
        required = (
            "mass_transfer_kg", "total_fill_time_s", "average_mass_flow_g_s",
            "peak_mass_flow_g_s", "starting_pressure_mpa", "ending_pressure_mpa",
            "aprr_mpa_min",
        )
        if source.get("raw_rows_public") is not False or any(
            not isinstance(aggregate.get(key), (int, float))
            or not math.isfinite(float(aggregate[key]))
            for key in required
        ):
            return None
        return PublicBenchmark(
            benchmark_id=BENCHMARK_ID,
            title=str(source.get("title") or ""),
            url=str(source.get("url") or ""),
            aggregate={key: aggregate[key] for key in required},
            claim_boundary=str(record.get("claim_boundary") or ""),
        )
    except (OSError, ValueError, TypeError, KeyError, StopIteration, json.JSONDecodeError):
        return None


def load_public_fch2rail_benchmark(root: Path | None = None) -> PublicBenchmark | None:
    """Load the 35 MPa FCH2RAIL aggregate boundary after provenance checks."""

    try:
        record = json.loads(_artifact_path(root).read_text(encoding="utf-8"))
        if (
            record.get("artifact_type") != "public_experimental_operating_benchmarks"
            or record.get("status") != "citation_bounded_aggregate_benchmarks"
        ):
            return None
        source = next(
            item for item in record.get("sources", [])
            if item.get("id") == FCH2RAIL_BENCHMARK_ID
        )
        aggregate = source.get("aggregate") or {}
        required = (
            "average_flow_min_g_s", "average_flow_max_g_s",
            "average_refuelling_speed_min_kg_min",
            "average_refuelling_speed_max_kg_min",
            "supply_pressure_mpa",
        )
        if source.get("raw_rows_public") is not False or any(
            not isinstance(aggregate.get(key), (int, float))
            or not math.isfinite(float(aggregate[key]))
            for key in required
        ):
            return None
        return PublicBenchmark(
            benchmark_id=FCH2RAIL_BENCHMARK_ID,
            title=str(source.get("title") or ""),
            url=str(source.get("url") or ""),
            aggregate={key: aggregate[key] for key in required},
            claim_boundary=str(record.get("claim_boundary") or ""),
        )
    except (OSError, ValueError, TypeError, KeyError, StopIteration, json.JSONDecodeError):
        return None


PUBLIC_H2IQ_BENCHMARK = load_public_benchmark()
PUBLIC_FCH2RAIL_BENCHMARK = load_public_fch2rail_benchmark()


def _metric(value: float | None, reference: float) -> dict[str, Any]:
    if value is None or not math.isfinite(float(value)):
        return {"simulated": None, "reference": reference, "difference": None}
    numeric = float(value)
    return {
        "simulated": numeric,
        "reference": reference,
        "difference": numeric - reference,
    }


def compare_public_high_flow_benchmark(
    *,
    duration_s: float | None,
    start_pressure_mpa: float | None,
    end_pressure_mpa: float | None,
    maximum_flow_g_s: float | None,
    ambient_temperature_c: float | None = None,
    benchmark: PublicBenchmark | None = PUBLIC_H2IQ_BENCHMARK,
) -> dict[str, Any]:
    """Compare a simulated fill summary with the public H2IQ aggregate.

    The returned status is deliberately ``operating_range_context``. It is
    not a pass/fail validation result because the source does not publish
    synchronized row-level data or the controller state needed for a holdout.
    """

    if benchmark is None:
        return {
            "status": "unavailable",
            "artifact": ARTIFACT_RELATIVE_PATH,
            "runtime_parameter_application": False,
            "claim_boundary": "공개 집계 근거를 읽지 못해 운전범위 비교를 생략함",
        }
    ref = benchmark.aggregate
    duration = float(duration_s) if duration_s is not None and math.isfinite(float(duration_s)) else None
    start = float(start_pressure_mpa) if start_pressure_mpa is not None and math.isfinite(float(start_pressure_mpa)) else None
    end = float(end_pressure_mpa) if end_pressure_mpa is not None and math.isfinite(float(end_pressure_mpa)) else None
    aprr = None
    if duration is not None and duration > 0.0 and start is not None and end is not None:
        aprr = (end - start) / duration * 60.0
    metrics: dict[str, Any] = {
        "duration_s": _metric(duration, float(ref["total_fill_time_s"])),
        "maximum_flow_g_s": _metric(maximum_flow_g_s, float(ref["peak_mass_flow_g_s"])),
        "starting_pressure_mpa": _metric(start, float(ref["starting_pressure_mpa"])),
        "ending_pressure_mpa": _metric(end, float(ref["ending_pressure_mpa"])),
        "aprr_mpa_min": _metric(aprr, float(ref["aprr_mpa_min"])),
    }
    if ambient_temperature_c is not None and math.isfinite(float(ambient_temperature_c)):
        metrics["ambient_temperature_c"] = _metric(
            float(ambient_temperature_c), float(ref["ambient_temperature_c"])
        )
    return {
        "status": "operating_range_context",
        "benchmark_id": benchmark.benchmark_id,
        "title": benchmark.title,
        "source_url": benchmark.url,
        "artifact": ARTIFACT_RELATIVE_PATH,
        "raw_rows_public": False,
        "full_loop_holdout_eligible": False,
        "runtime_parameter_application": False,
        "metrics": metrics,
        "claim_boundary": benchmark.claim_boundary,
    }


def compare_public_operating_context(
    *,
    duration_s: float | None,
    start_pressure_mpa: float | None,
    end_pressure_mpa: float | None,
    average_flow_g_s: float | None,
    maximum_flow_g_s: float | None,
    ambient_temperature_c: float | None = None,
    high_flow_benchmark: PublicBenchmark | None = PUBLIC_H2IQ_BENCHMARK,
    fch2rail_benchmark: PublicBenchmark | None = PUBLIC_FCH2RAIL_BENCHMARK,
) -> dict[str, Any]:
    """Select a pressure-class-appropriate public operating context.

    FCH2RAIL is used only for low-pressure (35 MPa-class) runs. H2IQ is used
    for the high-flow 70 MPa-class path. The selection is a display and
    provenance decision; neither report is a row-level holdout.
    """

    try:
        end_pressure = float(end_pressure_mpa) if end_pressure_mpa is not None else float("nan")
    except (TypeError, ValueError):
        end_pressure = float("nan")
    if math.isfinite(end_pressure) and end_pressure <= 50.0:
        if fch2rail_benchmark is None:
            return {
                "status": "unavailable",
                "selection": "fch2rail_35mpa",
                "runtime_parameter_application": False,
                "claim_boundary": "35 MPa 공개 운전범위 근거를 읽지 못함",
            }
        ref = fch2rail_benchmark.aggregate
        average = None
        if average_flow_g_s is not None:
            try:
                value = float(average_flow_g_s)
                if math.isfinite(value):
                    average = value
            except (TypeError, ValueError):
                pass
        range_low = float(ref["average_flow_min_g_s"])
        range_high = float(ref["average_flow_max_g_s"])
        flow_metric: dict[str, Any] = {
            "simulated": average,
            "reference_range": {"min": range_low, "max": range_high},
            "comparison": (
                "within_reported_range" if average is not None and range_low <= average <= range_high
                else "outside_reported_range" if average is not None else "unavailable"
            ),
        }
        return {
            "status": "operating_range_context",
            "selection": "fch2rail_35mpa",
            "benchmark_id": fch2rail_benchmark.benchmark_id,
            "title": fch2rail_benchmark.title,
            "source_url": fch2rail_benchmark.url,
            "artifact": ARTIFACT_RELATIVE_PATH,
            "raw_rows_public": False,
            "full_loop_holdout_eligible": False,
            "runtime_parameter_application": False,
            "metrics": {
                "average_flow_g_s": flow_metric,
                "supply_pressure_mpa": {"reference": float(ref["supply_pressure_mpa"])},
                "duration_s": {"simulated": duration_s},
                "maximum_flow_g_s": {"simulated": maximum_flow_g_s},
            },
            "claim_boundary": fch2rail_benchmark.claim_boundary,
        }
    return {
        "status": "operating_range_context",
        "selection": "nrel_h2iq_70mpa",
        **compare_public_high_flow_benchmark(
            duration_s=duration_s,
            start_pressure_mpa=start_pressure_mpa,
            end_pressure_mpa=end_pressure_mpa,
            maximum_flow_g_s=maximum_flow_g_s,
            ambient_temperature_c=ambient_temperature_c,
            benchmark=high_flow_benchmark,
        ),
    }


__all__ = [
    "ARTIFACT_RELATIVE_PATH",
    "BENCHMARK_ID",
    "FCH2RAIL_BENCHMARK_ID",
    "PUBLIC_FCH2RAIL_BENCHMARK",
    "PUBLIC_H2IQ_BENCHMARK",
    "PublicBenchmark",
    "compare_public_high_flow_benchmark",
    "compare_public_operating_context",
    "load_public_benchmark",
    "load_public_fch2rail_benchmark",
]
