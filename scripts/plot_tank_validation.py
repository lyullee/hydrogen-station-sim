"""Create publication-ready parity and per-case error figures."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _save(figure, root: Path, name: str) -> None:
    figure.savefig(root / f"{name}.pdf", bbox_inches="tight")
    figure.savefig(root / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("data/public_validation/results/tank_model"))
    args = parser.parse_args()
    report = json.loads((args.results / "validation.json").read_text(encoding="utf-8"))
    metrics = _rows(args.results / "case_metrics.csv")
    by_id = {row["case_id"]: row for row in metrics}

    plt.rcParams.update({
        "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 10,
        "legend.fontsize": 8, "figure.dpi": 120,
    })
    colors = {"calibration": "#3178A8", "validation": "#C44E52"}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.25), constrained_layout=True)
    limits = ((0, 90), (-25, 100))
    fields = (
        ("experimental_pressure_mpa", "predicted_pressure_mpa", "Pressure (MPa)"),
        ("experimental_temperature_c", "predicted_temperature_c", "Gas temperature (°C)"),
    )
    for axis, (actual_name, predicted_name, label), (low, high) in zip(axes, fields, limits):
        for split in ("calibration", "validation"):
            actual_values, predicted_values = [], []
            for case_id, metadata in by_id.items():
                if metadata["split"] != split:
                    continue
                trace = _rows(args.results / "traces" / f"{case_id}.csv")
                stride = max(1, len(trace) // 80)
                actual_values.extend(float(row[actual_name]) for row in trace[::stride])
                predicted_values.extend(float(row[predicted_name]) for row in trace[::stride])
            axis.scatter(
                actual_values, predicted_values, s=8, alpha=0.28,
                color=colors[split], edgecolors="none", label=split.capitalize(),
            )
        axis.plot([low, high], [low, high], color="#222222", linewidth=1, linestyle="--")
        axis.set(xlim=(low, high), ylim=(low, high), xlabel=f"Measured {label}", ylabel=f"Predicted {label}")
        axis.grid(alpha=0.2); axis.set_aspect("equal", adjustable="box")
    axes[0].legend(frameon=False, loc="upper left")
    _save(fig, args.results, "parity")

    ordered = sorted(metrics, key=lambda row: int(row["lab_test_number"]))
    positions = np.arange(len(ordered))
    fig, axes = plt.subplots(2, 1, figsize=(9.0, 5.0), sharex=True, constrained_layout=True)
    for axis, field, ylabel in (
        (axes[0], "pressure_rmse_mpa", "Pressure RMSE (MPa)"),
        (axes[1], "temperature_rmse_c", "Temperature RMSE (°C)"),
    ):
        axis.bar(
            positions, [float(row[field]) for row in ordered], width=0.78,
            color=[colors[row["split"]] for row in ordered], alpha=0.9,
        )
        axis.set_ylabel(ylabel); axis.grid(axis="y", alpha=0.2)
    axes[1].set_xticks(positions, [row["case_id"].removeprefix("H2P-") for row in ordered], rotation=90)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[name]) for name in ("calibration", "validation")]
    axes[0].legend(handles, ["Calibration", "Validation"], frameon=False)
    _save(fig, args.results, "case_rmse")

    validation = [row for row in ordered if row["split"] == "validation"]
    capacities = sorted({float(row["tank_capacity_kg"]) for row in validation})
    capacity_colors = {
        value: plt.cm.viridis(index / max(len(capacities) - 1, 1))
        for index, value in enumerate(capacities)
    }
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.25), constrained_layout=True)
    for axis, field, ylabel in (
        (axes[0], "pressure_rmse_mpa", "Pressure RMSE (MPa)"),
        (axes[1], "temperature_rmse_c", "Temperature RMSE (°C)"),
    ):
        for capacity in capacities:
            selected = [row for row in validation if float(row["tank_capacity_kg"]) == capacity]
            axis.scatter(
                [float(row["chamber_temperature_c"]) for row in selected],
                [float(row[field]) for row in selected],
                s=32, color=capacity_colors[capacity], label=f"{capacity:g} kg",
                edgecolors="white", linewidths=0.4,
            )
        axis.set(xlabel="Chamber temperature (°C)", ylabel=ylabel)
        axis.grid(alpha=0.2)
    axes[0].legend(frameon=False, title="Nominal capacity")
    _save(fig, args.results, "validation_conditions")

    print(args.results / "parity.pdf")
    print(args.results / "case_rmse.pdf")
    print(args.results / "validation_conditions.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
