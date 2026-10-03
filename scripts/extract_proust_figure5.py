"""Reproducibly digitize Proust et al. Figure 5 without model access.

Run with the bundled document/PDF Python environment.  The first pass reads
vector paths from the PDF.  The second renders the page and segments curve
colours.  Their mean is retained and their difference contributes to the
digitization uncertainty.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pdfplumber
import pypdfium2 as pdfium


PRESSURE_BAR = [100, 125, 150, 175, 200, 250, 300, 400, 500, 600, 700, 800, 900]
TEMPERATURE_C = {
    1.0: [-39, -38, -37, -34, -31, -25, -18, -2, 15, 27, 36, 40, 42],
    2.0: [-62, -58, -54, -47, -39, -20, -4, 15, 27, 34, 38, 40, 42],
    3.0: [-61, -47, -30, -20, -11, 4, 15, 28, 35, 39, 42, 44, 46],
}
COLOURS = {
    1.0: (0.0, 0.0, 0.50196),
    2.0: (1.0, 0.0, 0.0),
    3.0: (0.2, 0.60392, 0.39608),
}
AXIS = {
    "x_left_pdf": 132.6,
    "x_right_pdf": 515.82,
    "x_min_bar": 0.0,
    "x_max_bar": 1000.0,
    "y_top_pdf": 385.56,
    "y_bottom_pdf": 613.02,
    "y_min_g_s": 0.0,
    "y_max_g_s": 180.0,
}
RENDER_SCALE = 4


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _x_for_pressure(pressure_bar: float) -> float:
    return AXIS["x_left_pdf"] + (
        (pressure_bar - AXIS["x_min_bar"])
        / (AXIS["x_max_bar"] - AXIS["x_min_bar"])
        * (AXIS["x_right_pdf"] - AXIS["x_left_pdf"])
    )


def _flow_for_y(y_pdf: float) -> float:
    return AXIS["y_min_g_s"] + (
        (AXIS["y_bottom_pdf"] - y_pdf)
        / (AXIS["y_bottom_pdf"] - AXIS["y_top_pdf"])
        * (AXIS["y_max_g_s"] - AXIS["y_min_g_s"])
    )


def _vector_series(page, colour: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray]:
    points = []
    for obj in page.curves + page.lines:
        if obj.get("stroking_color") != colour:
            continue
        raw = obj.get("pts") or [(obj["x0"], obj["top"]), (obj["x1"], obj["bottom"])]
        for x, y in raw:
            if (
                max(165.0, AXIS["x_left_pdf"]) <= x <= AXIS["x_right_pdf"]
                and AXIS["y_top_pdf"] <= y <= AXIS["y_bottom_pdf"]
            ):
                points.append((float(x), float(y)))
    array = np.asarray(sorted(points), dtype=float)
    if not len(array):
        raise ValueError(f"no vector points for colour {colour}")
    unique_x, median_y = [], []
    for x in np.unique(array[:, 0]):
        unique_x.append(x)
        median_y.append(float(np.median(array[array[:, 0] == x, 1])))
    return np.asarray(unique_x), np.asarray(median_y)


def _raster_flow(image: np.ndarray, x_pdf: float, diameter_mm: float) -> float:
    x_pixel = int(round(x_pdf * RENDER_SCALE))
    y_top = int(round(AXIS["y_top_pdf"] * RENDER_SCALE))
    y_bottom = int(round(AXIS["y_bottom_pdf"] * RENDER_SCALE))
    strip = image[y_top:y_bottom + 1, x_pixel - 4:x_pixel + 5, :]
    red, green, blue = [strip[:, :, index].astype(float) for index in range(3)]
    if diameter_mm == 1.0:
        mask = (blue > 70) & (blue > 1.3 * red) & (blue > 1.3 * green)
    elif diameter_mm == 2.0:
        mask = (red > 130) & (red > 1.5 * green) & (red > 1.5 * blue)
    else:
        mask = (green > 70) & (green > 1.25 * red) & (green > 1.25 * blue)
    rows = np.where(mask)[0] + y_top
    if not len(rows):
        raise ValueError(f"no raster curve pixels at x={x_pdf}, d={diameter_mm}")
    return _flow_for_y(float(np.median(rows)) / RENDER_SCALE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf", type=Path,
        default=Path("data/public_validation/raw/proust_90mpa/Proust_Jamois_Studer_2009_ICHS.pdf"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/public_validation/derived/proust_90mpa_release.csv"),
    )
    parser.add_argument(
        "--metadata", type=Path,
        default=Path("data/public_validation/derived/proust_90mpa_extraction.json"),
    )
    args = parser.parse_args()

    document = pdfium.PdfDocument(str(args.pdf))
    raster = np.asarray(document[4].render(scale=RENDER_SCALE).to_pil().convert("RGB"))
    vector_page = pdfplumber.open(args.pdf).pages[4]
    half_pixel_g_s = (
        0.5 / RENDER_SCALE
        / (AXIS["y_bottom_pdf"] - AXIS["y_top_pdf"])
        * (AXIS["y_max_g_s"] - AXIS["y_min_g_s"])
    )
    rows, details = [], []
    for diameter_mm, colour in COLOURS.items():
        vector_x, vector_y = _vector_series(vector_page, colour)
        for index, (pressure_bar, temperature_c) in enumerate(
            zip(PRESSURE_BAR, TEMPERATURE_C[diameter_mm]), start=1
        ):
            x_pdf = _x_for_pressure(pressure_bar)
            vector_flow = _flow_for_y(float(np.interp(x_pdf, vector_x, vector_y)))
            raster_flow = _raster_flow(raster, x_pdf, diameter_mm)
            mean_flow = 0.5 * (vector_flow + raster_flow)
            uncertainty = 0.5 * abs(vector_flow - raster_flow) + half_pixel_g_s
            row = {
                "case_id": f"proust-{int(diameter_mm)}mm",
                "nozzle_diameter_mm": diameter_mm,
                "source_pressure_mpa_abs": pressure_bar / 10.0,
                "source_temperature_k": temperature_c + 273.15,
                "measured_mass_flow_g_s": mean_flow,
                "digitization_uncertainty_g_s": uncertainty,
                "source_figure": "Proust2009-Figure5-and-Table1",
                "point_index": index,
            }
            eligible_temperature = row["source_temperature_k"] >= 220.0
            if eligible_temperature:
                rows.append(row)
            details.append({
                "diameter_mm": diameter_mm,
                "pressure_bar": pressure_bar,
                "vector_pass_g_s": vector_flow,
                "raster_pass_g_s": raster_flow,
                "retained_mean_g_s": mean_flow,
                "uncertainty_g_s": uncertainty,
                "temperature_c_from_table1": temperature_c,
                "eligible_frozen_temperature_window": eligible_temperature,
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "schema_version": 1,
        "source_doi": "10.1016/j.ijhydene.2010.04.055",
        "source_pdf_sha256": _sha256(args.pdf),
        "source_pdf_committed": False,
        "protocol_committed_before_numerical_access": True,
        "protocol_commit": "3fb8b91",
        "page_one_based": 5,
        "mass_flow_source": "Figure 5",
        "temperature_source": "Table 1",
        "pressure_basis": "publisher reservoir-pressure axis treated as absolute; +101325 Pa sensitivity required because gauge/absolute wording is not explicit",
        "axis_calibration": AXIS,
        "render_scale": RENDER_SCALE,
        "half_pixel_y_resolution_g_s": half_pixel_g_s,
        "primary_pressure_points_bar": PRESSURE_BAR,
        "excluded_low_plot_points_reason": "20-80 bar vector paths overlap the in-plot legend x range; prospectively frozen minimums remain satisfied without them",
        "two_pass_details": details,
        "rights_note": "The public paper has no identified data-redistribution licence. These are independently digitized factual coordinates with citation; the PDF is not redistributed.",
    }
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(args.metadata)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
