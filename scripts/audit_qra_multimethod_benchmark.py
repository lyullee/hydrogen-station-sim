"""Audit a claim-bounded subset of the DATA3632 seven-method HRS QRA set.

This is a post-access descriptive inter-model comparison.  It is not an
experimental validation and deliberately has no pass/fail threshold.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Any
from urllib.request import Request, urlopen


DOI = "10.34810/DATA3632"
VERSION = "2.0"
BASE_URL = "https://dataverse.csuc.cat/api/access/datafile/{file_id}?format=original"

# Immutable selection frozen in the companion protocol.  Only the common HRS
# equipment classes are retained; pipe segments and proprietary simulation
# projects are outside this compact comparison.
QRA_FILES: tuple[tuple[int, str, str, str, str], ...] = (
    # file_id, method, country, equipment, category
    (515912, "M1", "Canada", "Compressor", "explosion"),
    (515952, "M1", "Canada", "Supply", "explosion"),
    (516070, "M2", "China", "Buffer", "explosion"),
    (515968, "M2", "China", "Compressor", "explosion"),
    (516055, "M2", "China", "Supply", "explosion"),
    (515972, "M3", "Japan", "Buffer", "explosion"),
    (515923, "M3", "Japan", "Compressor", "explosion"),
    (515932, "M3", "Japan", "Dispenser", "explosion"),
    (515937, "M3", "Japan", "Supply", "explosion"),
    (516071, "M4", "Korea", "Buffer", "explosion"),
    (515934, "M4", "Korea", "Supply", "explosion"),
    (515892, "M5", "Netherlands", "Buffer", "explosion"),
    (516009, "M5", "Netherlands", "Compressor", "explosion"),
    (516038, "M5", "Netherlands", "Supply", "explosion"),
    (516064, "M6", "Spain", "Buffer", "explosion"),
    (516130, "M6", "Spain", "Compressor", "explosion"),
    (515917, "M6", "Spain", "Supply", "explosion"),
    (515920, "M7", "USA", "Buffer", "explosion"),
    (515902, "M7", "USA", "Compressor", "explosion"),
    (515927, "M7", "USA", "Dispenser", "explosion"),
    (515930, "M7", "USA", "Supply", "explosion"),
    (515976, "M1", "Canada", "Compressor", "jet_fire"),
    (516139, "M1", "Canada", "Dispenser", "jet_fire"),
    (515985, "M1", "Canada", "Supply", "jet_fire"),
    (515983, "M2", "China", "Buffer", "jet_fire"),
    (516021, "M2", "China", "Compressor", "jet_fire"),
    (516113, "M2", "China", "Dispenser", "jet_fire"),
    (515995, "M2", "China", "Supply", "jet_fire"),
    (516062, "M3", "Japan", "Buffer", "jet_fire"),
    (515990, "M3", "Japan", "Compressor", "jet_fire"),
    (516015, "M3", "Japan", "Dispenser", "jet_fire"),
    (515973, "M3", "Japan", "Supply", "jet_fire"),
    (515987, "M4", "Korea", "Buffer", "jet_fire"),
    (516041, "M4", "Korea", "Supply", "jet_fire"),
    (516014, "M5", "Netherlands", "Buffer", "jet_fire"),
    (516149, "M5", "Netherlands", "Compressor", "jet_fire"),
    (516120, "M5", "Netherlands", "Dispenser", "jet_fire"),
    (516102, "M5", "Netherlands", "Supply", "jet_fire"),
    (515994, "M6", "Spain", "Buffer", "jet_fire"),
    (515906, "M6", "Spain", "Compressor", "jet_fire"),
    (516087, "M6", "Spain", "Dispenser", "jet_fire"),
    (516077, "M6", "Spain", "Supply", "jet_fire"),
    (515888, "M7", "USA", "Buffer", "jet_fire"),
    (516123, "M7", "USA", "Compressor", "jet_fire"),
    (515941, "M7", "USA", "Dispenser", "jet_fire"),
    (516142, "M7", "USA", "Supply", "jet_fire"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def number(value: str | None) -> float | None:
    text = (value or "").strip().replace("\u00a0", "")
    if not text or text.lower().startswith("not reached"):
        return None
    try:
        result = float(text.replace(",", "."))
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def normalized_weather(value: str) -> str:
    text = value.upper().replace("CATEGORY", "")
    return "".join(character for character in text if character.isalnum() or character == ".")


def endpoint(row: dict[str, str], prefix: str) -> float | None:
    key = next((name for name in row if name.startswith(prefix)), None)
    return number(row.get(key)) if key else None


def log_interpolate_distance(
    lower_effect: float,
    lower_distance: float | None,
    upper_effect: float,
    upper_distance: float | None,
    target_effect: float,
) -> float | None:
    if not (lower_effect < target_effect < upper_effect):
        raise ValueError("target must be bounded by source effects")
    if lower_distance is None or upper_distance is None:
        return None
    if lower_distance <= 0.0 or upper_distance <= 0.0:
        return None
    fraction = math.log(target_effect / lower_effect) / math.log(upper_effect / lower_effect)
    return math.exp(math.log(lower_distance) + fraction * math.log(upper_distance / lower_distance))


def summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "minimum": None, "median": None, "maximum": None}
    return {
        "count": len(values),
        "minimum": min(values),
        "median": median(values),
        "maximum": max(values),
    }


def download(path: Path, file_id: int) -> None:
    request = Request(
        BASE_URL.format(file_id=file_id),
        headers={"User-Agent": "hydrogen-station-sim evidence audit/1.0"},
    )
    with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed public host
        payload = response.read()
    if not payload.startswith(b'"Path"'):
        raise ValueError(f"unexpected DATA3632 payload for file {file_id}")
    path.write_bytes(payload)


def build(root: Path, raw_dir: Path, *, allow_download: bool) -> dict[str, Any]:
    protocol_path = root / "research/qra_multimethod_comparison_protocol_2026_10_08.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol["source"]["dataset_doi"] != DOI:
        raise ValueError("protocol DOI mismatch")
    raw_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for file_id, method, country, equipment, category in QRA_FILES:
        filename = f"{method}_{country}_{equipment}_{category}_{file_id}.csv".replace(" ", "_")
        path = raw_dir / filename
        if not path.is_file():
            if not allow_download:
                raise FileNotFoundError(f"missing {path}; rerun with --download")
            download(path, file_id)
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        files.append({
            "file_id": file_id,
            "method": method,
            "country": country,
            "equipment": equipment,
            "category": category,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "row_count": len(rows),
        })
        for row_index, row in enumerate(rows, start=1):
            pressure = endpoint(row, "Pressure (input)")
            temperature = endpoint(row, "Temperature (input)")
            hole = endpoint(row, "Hole size")
            common = {
                "file_id": file_id,
                "row_index": row_index,
                "method": method,
                "country": country,
                "equipment": equipment,
                "category": category,
                "scenario": row.get("Scenario", ""),
                "weather": row.get("Weather", ""),
                "weather_normalized": normalized_weather(row.get("Weather", "")),
                "pressure_bar": pressure,
                "temperature_c": temperature,
                "hole_size_mm": hole,
            }
            if category == "explosion":
                d_low = endpoint(row, "Distance downwind to overpressure 1")
                d_high = endpoint(row, "Distance downwind to overpressure 2")
                common.update({
                    "distance_2_068_kpa_m": d_low,
                    "distance_13_79_kpa_m": d_high,
                    "interpolated_distance_5_kpa_m": log_interpolate_distance(
                        2.068, d_low, 13.79, d_high, 5.0
                    ),
                })
            else:
                d_low = endpoint(row, "Distance downwind to intensity level 1")
                d_high = endpoint(row, "Distance downwind to intensity level 2")
                common.update({
                    "jet_fire_mass_rate_kg_s": endpoint(row, "Jet fire mass rate"),
                    "distance_4_kw_m2_m": d_low,
                    "distance_12_5_kw_m2_m": d_high,
                    "interpolated_distance_5_kw_m2_m": log_interpolate_distance(
                        4.0, d_low, 12.5, d_high, 5.0
                    ),
                })
            observations.append(common)

    endpoint_names = (
        "distance_2_068_kpa_m",
        "distance_13_79_kpa_m",
        "interpolated_distance_5_kpa_m",
        "distance_4_kw_m2_m",
        "distance_12_5_kw_m2_m",
        "interpolated_distance_5_kw_m2_m",
        "jet_fire_mass_rate_kg_s",
    )
    aggregate = {
        name: summary([
            float(item[name]) for item in observations if item.get(name) is not None
        ])
        for name in endpoint_names
    }
    by_method: dict[str, Any] = {}
    for method in sorted({item["method"] for item in observations}):
        selected = [item for item in observations if item["method"] == method]
        by_method[method] = {
            "row_count": len(selected),
            "equipment": sorted({item["equipment"] for item in selected}),
            "endpoints": {
                name: summary([
                    float(item[name]) for item in selected if item.get(name) is not None
                ])
                for name in endpoint_names
            },
        }

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for item in observations:
        required = (item["pressure_bar"], item["temperature_c"], item["hole_size_mm"])
        if any(value is None for value in required):
            continue
        signature = (
            item["category"], item["equipment"], round(float(item["pressure_bar"]), 3),
            round(float(item["temperature_c"]), 3), round(float(item["hole_size_mm"]), 3),
            item["weather_normalized"],
        )
        groups.setdefault(signature, []).append(item)
    matched: list[dict[str, Any]] = []
    for signature, items in groups.items():
        methods = sorted({item["method"] for item in items})
        if len(methods) < 2:
            continue
        value_name = (
            "interpolated_distance_5_kpa_m"
            if signature[0] == "explosion"
            else "interpolated_distance_5_kw_m2_m"
        )
        values = [float(item[value_name]) for item in items if item.get(value_name) is not None]
        value_summary = summary(values)
        spread_ratio = None
        if values and min(values) > 0.0:
            spread_ratio = max(values) / min(values)
        matched.append({
            "signature": {
                "category": signature[0], "equipment": signature[1],
                "pressure_bar": signature[2], "temperature_c": signature[3],
                "hole_size_mm": signature[4], "weather": signature[5],
            },
            "methods": methods,
            "method_count": len(methods),
            "runtime_aligned_endpoint": value_name,
            "distance_summary_m": value_summary,
            "jet_fire_mass_rate_summary_kg_s": (
                summary([
                    float(item["jet_fire_mass_rate_kg_s"])
                    for item in items
                    if item.get("jet_fire_mass_rate_kg_s") is not None
                ])
                if signature[0] == "jet_fire" else None
            ),
            "max_min_ratio": spread_ratio,
        })
    matched.sort(key=lambda item: (
        -item["method_count"], item["signature"]["category"],
        item["signature"]["equipment"], item["signature"]["hole_size_mm"],
    ))
    ratios = [float(item["max_min_ratio"]) for item in matched if item["max_min_ratio"] is not None]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_postaccess_descriptive_multimethod_comparison",
        "source": {"doi": DOI, "version": VERSION, "license": "CC BY 4.0"},
        "protocol": "research/qra_multimethod_comparison_protocol_2026_10_08.json",
        "selection": {
            "file_count": len(files),
            "method_count": len({item["method"] for item in files}),
            "equipment": sorted({item["equipment"] for item in files}),
            "categories": sorted({item["category"] for item in files}),
        },
        "files": files,
        "aggregate": {
            "observation_count": len(observations),
            "endpoint_summaries": aggregate,
            "matched_input_group_count": len(matched),
            "matched_input_spread_ratio": summary(ratios),
        },
        "by_method": by_method,
        "matched_input_groups": matched,
        "integrity": {
            "all_selected_files_present": len(files) == len(QRA_FILES),
            "all_seven_methods_present": len({item["method"] for item in files}) == 7,
            "value_based_exclusions": 0,
            "model_tuning_performed": False,
            "runtime_parameters_changed": False,
            "experimental_validation": False,
            "actual_incident_validation": False,
        },
        "claim_boundary": protocol["claim_boundary"],
    }


def markdown(result: dict[str, Any]) -> str:
    aggregate = result["aggregate"]
    endpoint = aggregate["endpoint_summaries"]
    lines = [
        "# DATA3632 seven-method HRS QRA comparison",
        "",
        "This is a post-access descriptive inter-model comparison, not experimental validation.",
        "",
        f"- Files: **{result['selection']['file_count']}**",
        f"- Methods: **{result['selection']['method_count']}**",
        f"- Source rows retained: **{aggregate['observation_count']}**",
        f"- Matched physical-input groups: **{aggregate['matched_input_group_count']}**",
        "",
        "## Overall consequence-distance envelopes",
        "",
        "| Endpoint | n | Minimum | Median | Maximum |",
        "|---|---:|---:|---:|---:|",
    ]
    labels = {
        "distance_2_068_kpa_m": "Direct 2.068 kPa overpressure distance",
        "distance_13_79_kpa_m": "Direct 13.79 kPa overpressure distance",
        "interpolated_distance_5_kpa_m": "Interpolated 5 kPa overpressure distance",
        "distance_4_kw_m2_m": "Direct 4 kW/m2 jet-fire distance",
        "distance_12_5_kw_m2_m": "Direct 12.5 kW/m2 jet-fire distance",
        "interpolated_distance_5_kw_m2_m": "Interpolated 5 kW/m2 jet-fire distance",
        "jet_fire_mass_rate_kg_s": "Direct exported jet-fire mass rate (kg/s)",
    }
    for name, label in labels.items():
        item = endpoint[name]
        lines.append(
            f"| {label} | {item['count']} | {item['minimum']:.3f} | "
            f"{item['median']:.3f} | {item['maximum']:.3f} |"
        )
    spread = aggregate["matched_input_spread_ratio"]
    lines += [
        "",
        "## Interpretation boundary",
        "",
        f"Across matched input groups, the method max/min distance ratio has median "
        f"**{spread['median']:.3f}** and maximum **{spread['maximum']:.3f}**.",
        "",
        "The range represents differences among implemented QRA methodologies. It is not an uncertainty interval, a safety factor, measured truth or a site-specific separation distance. Direct source endpoints remain distinguishable from the 5 kPa/5 kW/m2 log-log interpolations.",
        "",
        f"Claim boundary: {result['claim_boundary']}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/public_validation/raw/qra_multimethod_2026"))
    parser.add_argument("--output", type=Path, default=Path("research/qra_multimethod_comparison_2026_10_08.json"))
    parser.add_argument("--report", type=Path, default=Path("research/QRA_MULTIMETHOD_COMPARISON_2026_10_08.md"))
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    raw_dir = args.raw_dir if args.raw_dir.is_absolute() else root / args.raw_dir
    output = args.output if args.output.is_absolute() else root / args.output
    report = args.report if args.report.is_absolute() else root / args.report
    result = build(root, raw_dir, allow_download=args.download)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    with report.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown(result))
    print(json.dumps({"output": str(output), "report": str(report)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
