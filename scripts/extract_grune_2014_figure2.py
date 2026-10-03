"""Extract the separable red valve trace from the official Figure 2 raster.

The publisher image is fetched for analysis but is not redistributed.  The
small inset contains overlapping traces and is intentionally not inferred.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path
from urllib.request import urlopen

import numpy as np
from PIL import Image


SOURCE_URL = "https://ars.els-cdn.com/content/image/1-s2.0-S0360319913020521-gr2.jpg"
SOURCE_SHA256 = "0c3d4ad6173749df7bec5b16f5f16041f940a93e969034597e2617efdDA3855c".lower()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(
        "data/public_validation/derived/grune_2014_figure2.csv"
    ))
    parser.add_argument("--image-cache", type=Path, default=Path(
        "tmp/grune_2014_gr2.jpg"
    ))
    args = parser.parse_args()
    args.image_cache.parent.mkdir(parents=True, exist_ok=True)
    if not args.image_cache.is_file():
        args.image_cache.write_bytes(urlopen(SOURCE_URL, timeout=30).read())
    digest = hashlib.sha256(args.image_cache.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise SystemExit(f"publisher image hash changed: {digest}")

    pixels = np.asarray(Image.open(args.image_cache).convert("RGB"), dtype=float)
    red, green, blue = (pixels[:, :, index] for index in range(3))
    red_mask = (red > 140.0) & ((red - green) > 25.0) & ((red - blue) > 20.0)
    y_pixel, x_pixel = np.where(red_mask)
    # Exclude the legend and the full-duration inset using the monotonic startup
    # corridor.  Coordinates are fixed to the hashed 369 x 213 publisher raster.
    keep = (
        (x_pixel >= 33) & (x_pixel <= 338)
        & (y_pixel >= 30) & (y_pixel <= 185)
        & (y_pixel >= 37.0 + 0.38 * (x_pixel - 33.0))
        & (y_pixel <= 60.0 + 0.48 * (x_pixel - 33.0))
    )
    x_pixel, y_pixel = x_pixel[keep], y_pixel[keep]
    unique_x = np.unique(x_pixel)
    median_y = np.asarray([np.median(y_pixel[x_pixel == x]) for x in unique_x])
    if unique_x.size < 250 or np.max(np.diff(unique_x)) > 8:
        raise SystemExit("red startup trace could not be separated reproducibly")

    sample_x = np.arange(35.0, 337.0, 6.0)
    sample_y = np.interp(sample_x, unique_x, median_y)
    # Axis calibration from tick intersections: x=34 -> 0 s, x=359 -> 0.01 s;
    # y=31 -> 202 bar and y=184 -> 180 bar.
    time_s = (sample_x - 34.0) / (359.0 - 34.0) * 0.01
    pressure_bar = 202.0 - (sample_y - 31.0) / (184.0 - 31.0) * 22.0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([
            "time_s", "measured_pressure_bar_abs", "digitization_uncertainty_bar",
            "source_curve",
        ])
        for time, pressure in zip(time_s, pressure_bar, strict=True):
            writer.writerow([f"{time:.9f}", f"{pressure:.6f}", "0.30", "4 mm valve"])


if __name__ == "__main__":
    main()
