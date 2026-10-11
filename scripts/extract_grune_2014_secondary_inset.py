"""Extract the red 4 mm valve curve from the public ICHS 2011 inset.

This script retains only derived coordinates; the source PDF is never copied
into the repository.  PyMuPDF is used because the conference figure is a
vector drawing, which avoids introducing a second raster digitization path.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import statistics
from collections import defaultdict
from pathlib import Path


SOURCE_SHA256 = "1edb02f2038bd58dd27399b68cb6e0d169f058981ee9e46c4a8340be15210421"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(source: Path, output: Path) -> int:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - environment guidance
        raise SystemExit("Install PyMuPDF to extract vector figure paths") from exc

    actual = _sha256(source)
    if actual != SOURCE_SHA256:
        raise SystemExit(
            f"unexpected source SHA-256: {actual}; expected {SOURCE_SHA256}"
        )

    page = fitz.open(source)[2]  # printed page 3
    # Figure 2 inset vector frame, in PDF page coordinates.
    x0, x1 = 354.84, 450.24
    y0, y1 = 455.77, 522.25
    by_x: dict[float, list[float]] = defaultdict(list)
    for drawing in page.get_drawings():
        color = drawing.get("color")
        if not (color and color[0] > 0.8 and color[1] < 0.2 and color[2] < 0.2):
            continue
        for item in drawing.get("items", []):
            if item[0] != "l":
                continue
            p1, p2 = item[1], item[2]
            if not (
                x0 - 0.2 <= p1.x <= x1 + 0.2
                and x0 - 0.2 <= p2.x <= x1 + 0.2
                and y0 - 0.2 <= p1.y <= y1 + 0.2
                and y0 - 0.2 <= p2.y <= y1 + 0.2
            ):
                continue
            by_x[round(float(p1.x), 4)].append(float(p1.y))
            by_x[round(float(p2.x), 4)].append(float(p2.y))

    points = [(x, statistics.median(ys)) for x, ys in sorted(by_x.items()) if ys]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "time_s",
                "measured_pressure_bar_abs",
                "digitization_uncertainty_bar",
                "source_curve",
            ]
        )
        for x, y in points:
            time_s = (x - x0) / (x1 - x0) * 0.5
            pressure_bar = (y1 - y) / (y1 - y0) * 200.0
            if 0.0 <= time_s <= 0.5 and pressure_bar > 0.0:
                writer.writerow(
                    [f"{time_s:.9f}", f"{pressure_bar:.6f}", "0.50", "4 mm valve (vector inset)"]
                )
    return len(points)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "data/public_validation/derived/grune_2014_ichs2011_inset_vector.csv"
        ),
    )
    args = parser.parse_args()
    print(f"wrote {extract(args.source, args.output)} vector points to {args.output}")


if __name__ == "__main__":
    main()
