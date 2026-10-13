"""Evaluate the frozen spatial-rank candidate on a disjoint ELVHYS cohort.

The raw CC0 dataset is intentionally kept outside the repository.  This runner
stores only aggregate case metrics and file hashes.  The pressure-derived
release-window rule is fixed before concentration responses are scored and is
not a fitted model parameter.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from h2station.prospective_spatial_rank import prospective_spatial_rank_score
from h2station.spatial_detector import Point3D


PROTOCOL = Path("research/elvhys_wp42_spatial_holdout_protocol_2026_10_14.json")
AMENDMENT = Path("research/elvhys_wp42_release_window_amendment_2026_10_14.json")
EXCLUDED_CASES = {29, 30, 31, 45}
INVALID_CASES = {27, 28}
HORIZONTAL_CASES = set(range(3, 27))
VERTICAL_CASES = {43, 44, 46, 47, 48}
ELIGIBLE_CASES = (HORIZONTAL_CASES | VERTICAL_CASES) - EXCLUDED_CASES

# Coordinates are from the public README.  The frozen candidate uses y as the
# elevation axis; the source data use X/Y/Z with Z as elevation.
SENSOR_COORD_MM: dict[str, tuple[float, float, float]] = {
    "Bottom1": (100, 500, 200),
    "Bottom3": (300, 500, 200),
    "Bottom5": (500, 500, 200),
    "Bottom7": (700, 500, 200),
    "Bottom9": (900, 500, 200),
    "ChimneyBottom": (500, 500, 1150),
    "ChimneyTop": (500, 500, 1850),
    "Side1": (500, 500, 900),
    "Side3": (500, 500, 700),
    "Side5": (500, 500, 500),
    "Side6": (500, 500, 400),
    "Side7": (500, 500, 300),
    "Side8": (500, 500, 100),
    "VentBottom": (850, 250, 125),
    "VentTop": (850, 250, 875),
}


def _case_id(name: str) -> int | None:
    match = re.search(r"HSE0*(\d+)", name.upper())
    return int(match.group(1)) if match else None


def _files(raw_dir: Path, family: str) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for path in raw_dir.glob(f"*{family}*.csv"):
        case = _case_id(path.name)
        if case is not None:
            result[case] = path
    return result


def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def _finite(value: str | None) -> float | None:
    try:
        number = float(value or "")
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _quantile(values: list[float], fraction: float) -> float:
    values = sorted(values)
    if not values:
        raise ValueError("quantile requires values")
    index = fraction * (len(values) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values[lower]
    weight = index - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _rank(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = rank
        i = j
    return ranks


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    ml = sum(left) / len(left)
    mr = sum(right) / len(right)
    dl = [v - ml for v in left]
    dr = [v - mr for v in right]
    den = math.sqrt(sum(v * v for v in dl) * sum(v * v for v in dr))
    return sum(a * b for a, b in zip(dl, dr)) / den if den else None


def _release_window(pressure_rows: list[dict[str, str]]) -> tuple[float, float] | None:
    points = [(_finite(row.get("Time")), _finite(row.get("PT1ReleaseRig"))) for row in pressure_rows]
    points = [(t, p) for t, p in points if t is not None and p is not None]
    if len(points) < 20:
        return None
    pressures = [p for _, p in points]
    q90 = _quantile(pressures, 0.90)
    q99 = _quantile(pressures, 0.99)
    hold = (q90 + q99) / 2.0
    start_level = 0.90 * hold
    stop_level = 0.10 * hold
    starts = [t for t, p in points if p >= start_level]
    if not starts:
        return None
    start = starts[0]
    sustained = [t for t, p in points if t >= start and p >= stop_level]
    if not sustained:
        return None
    stop = sustained[-1]
    return (start, stop) if stop > start else None


def _response(rows: list[dict[str, str]], fields: Iterable[str], window: tuple[float, float]) -> dict[str, float]:
    start, stop = window
    values: dict[str, list[float]] = {field: [] for field in fields}
    for row in rows:
        time = _finite(row.get("Time"))
        if time is None or not start <= time <= stop:
            continue
        for field in values:
            value = _finite(row.get(field))
            if value is not None:
                values[field].append(value)
    return {
        field: _quantile(series, 0.99) - _quantile(series, 0.10)
        for field, series in values.items()
        if len(series) >= 8
    }


def _point(name: str, *, source: bool = False, vertical: bool = False) -> Point3D:
    if source:
        x, y, z = (93, 500, 250) if vertical else (20, 500, 250)
    else:
        x, y, z = SENSOR_COORD_MM[name]
    return Point3D(x=x / 1000.0, y=z / 1000.0, z=y / 1000.0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate(raw_dir: Path) -> dict[str, object]:
    protocol_path = Path(__file__).resolve().parents[1] / PROTOCOL
    amendment_path = Path(__file__).resolve().parents[1] / AMENDMENT
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    amendment = json.loads(amendment_path.read_text(encoding="utf-8"))
    concentration = _files(raw_dir, "CONC")
    pressure = _files(raw_dir, "PRES")
    cases: list[dict[str, object]] = []
    ineligible: list[dict[str, object]] = []
    source_files: list[dict[str, object]] = []
    for case in sorted(ELIGIBLE_CASES):
        conc_path = concentration.get(case)
        pres_path = pressure.get(case)
        if conc_path is None or pres_path is None:
            ineligible.append({"case_id": case, "reason": "missing concentration or pressure file"})
            continue
        fields, rows = _rows(conc_path)
        pressure_fields, pressure_rows = _rows(pres_path)
        channels = [field for field in fields if field.startswith("H2")]
        window = _release_window(pressure_rows)
        if "Time" not in fields or "PT1ReleaseRig" not in pressure_fields or len(channels) < 8 or window is None:
            ineligible.append({"case_id": case, "reason": "required channel or fixed release-window rule unavailable"})
            continue
        response = _response(rows, channels, window)
        if len(response) < 8:
            ineligible.append({"case_id": case, "reason": "fewer than eight finite concentration responses in window", "response_count": len(response)})
            continue
        source = _point("source", source=True, vertical=case in VERTICAL_CASES)
        scores = {channel: prospective_spatial_rank_score(source, _point(channel[2:])) for channel in response if channel[2:] in SENSOR_COORD_MM}
        paired = [(channel, scores[channel], response[channel]) for channel in response if channel in scores]
        if len(paired) < 8:
            ineligible.append({"case_id": case, "reason": "fewer than eight coordinate-mapped channels", "mapped_count": len(paired)})
            continue
        names = [item[0] for item in paired]
        score_values = [item[1] for item in paired]
        response_values = [item[2] for item in paired]
        score_rank = _rank(score_values)
        response_rank = _rank(response_values)
        rho = _correlation(score_rank, response_rank)
        observed_order = sorted(range(len(paired)), key=lambda i: (-response_values[i], names[i]))
        predicted_order = sorted(range(len(paired)), key=lambda i: (-score_values[i], names[i]))
        quartile_count = max(1, math.ceil(len(paired) / 4))
        observed_top = set(observed_order[:quartile_count])
        predicted_top5 = set(predicted_order[: min(5, len(paired))])
        cases.append({
            "case_id": case,
            "orientation": "vertical" if case in VERTICAL_CASES else "horizontal",
            "sensor_count": len(paired),
            "release_window_s": {"start": window[0], "stop": window[1], "duration": window[1] - window[0]},
            "response_definition": "q99_minus_q10_during_pressure_crosswalk_window",
            "spearman_rho": rho,
            "top5_recall": len(predicted_top5 & observed_top) / len(predicted_top5),
            "nearest_success": predicted_order[0] in observed_top,
            "screen": {
                "rho_at_least_0_4": rho is not None and rho >= 0.4,
                "top5_recall_at_least_0_6": len(predicted_top5 & observed_top) / len(predicted_top5) >= 0.6,
                "nearest_success": predicted_order[0] in observed_top,
            },
        })
        for path in (conc_path, pres_path):
            source_files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path), "case_id": case})
    rho_values = [case["spearman_rho"] for case in cases if case["spearman_rho"] is not None]
    top5_values = [case["top5_recall"] for case in cases]
    nearest = [case["nearest_success"] for case in cases]
    aggregate = {
        "eligible_case_count": len(cases),
        "ineligible_case_count": len(ineligible),
        "median_spearman": sorted(rho_values)[len(rho_values) // 2] if rho_values else None,
        "fraction_spearman_at_least_0_4": sum(value >= 0.4 for value in rho_values) / len(rho_values) if rho_values else 0.0,
        "mean_top5_recall": sum(top5_values) / len(top5_values) if top5_values else 0.0,
        "nearest_success_fraction": sum(nearest) / len(nearest) if nearest else 0.0,
    }
    screens = {
        "all_declared_cases_eligible": not ineligible and len(cases) >= 10,
        "median_spearman_at_least_0_5": aggregate["median_spearman"] is not None and aggregate["median_spearman"] >= 0.5,
        "fraction_cases_spearman_at_least_0_4_at_least_0_6": aggregate["fraction_spearman_at_least_0_4"] >= 0.6,
        "mean_top5_recall_at_least_0_6": aggregate["mean_top5_recall"] >= 0.6,
        "nearest_success_fraction_at_least_0_7": aggregate["nearest_success_fraction"] >= 0.7,
    }
    return {
        "schema_version": 1,
        "artifact_type": "elvhys_wp42_actual_hydrogen_spatial_holdout_result",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "PASS" if all(screens.values()) else "FAIL",
        "protocol": {"path": str(PROTOCOL), "sha256": _sha256(protocol_path), "protocol_id": protocol["protocol_id"]},
        "amendment": {"path": str(AMENDMENT), "sha256": _sha256(amendment_path), "status": amendment["status"]},
        "source": {"doi": "10.18710/JXJP0H", "license": "CC0 1.0", "existing_overlap_case_ids_excluded": sorted(EXCLUDED_CASES)},
        "candidate": "pooled_spatial_rank_v1",
        "selection": {"eligible_case_ids": sorted(ELIGIBLE_CASES), "invalid_case_ids_excluded": sorted(INVALID_CASES), "parameter_tuning_after_access": False},
        "aggregate": aggregate,
        "screens": screens,
        "cases": cases,
        "ineligible_cases": ineligible,
        "source_file_manifest": source_files,
        "runtime_promotion": False,
        "claim_boundary": "This result tests only within-case spatial response ordering in the disjoint ELVHYS cryogenic indoor geometry. It does not validate concentration magnitude, detector timing, outdoor HRS placement, consequence distance, ESD, field safety or station-to-vehicle behavior.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("research/elvhys_wp42_spatial_holdout_result_2026_10_14.json"))
    args = parser.parse_args()
    result = evaluate(args.raw_dir.resolve())
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "aggregate": result["aggregate"], "screens": result["screens"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
