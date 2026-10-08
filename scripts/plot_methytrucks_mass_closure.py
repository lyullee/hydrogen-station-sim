"""Create the claim-bounded MetHyTrucks flow/scale closure figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


GROUP_LABELS = {
    "20590842": "Group B · HySaM",
    "20590903": "Group C · ENGIE",
}
GROUP_COLORS = {
    "20590842": "#1261A0",
    "20590903": "#D97706",
}


def _comparable_sessions(record: dict) -> list[dict]:
    return [
        item
        for item in record.get("mass_closure_sessions", [])
        if item.get("flow_to_scale_mass_ratio") is not None
    ]


def create_figure(record: dict, output_dir: Path) -> tuple[Path, Path]:
    sessions = _comparable_sessions(record)
    if not sessions:
        raise ValueError("no comparable flow/scale closure sessions")

    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "legend.fontsize": 8,
            "figure.dpi": 120,
        }
    )
    figure, axes = plt.subplots(
        1, 2, figsize=(7.2, 3.25), constrained_layout=True,
        gridspec_kw={"width_ratios": (1.15, 1.0)},
    )

    maximum_mass = max(
        max(
            float(item["scale_delta_assuming_kg"]),
            float(item["integrated_flow_mass_assuming_g_per_s_kg"]),
        )
        for item in sessions
    )
    limit = max(0.5, maximum_mass * 1.08)
    mass_axis = np.linspace(0.0, limit, 200)
    axes[0].fill_between(
        mass_axis, 0.8 * mass_axis, 1.2 * mass_axis,
        color="#DCEFE5", alpha=0.9, label="0.8–1.2 screen",
    )
    axes[0].plot(mass_axis, mass_axis, color="#253746", linewidth=1.1)
    for record_id in GROUP_LABELS:
        group = [item for item in sessions if item["record_id"] == record_id]
        if not group:
            continue
        axes[0].scatter(
            [float(item["scale_delta_assuming_kg"]) for item in group],
            [float(item["integrated_flow_mass_assuming_g_per_s_kg"]) for item in group],
            s=42, color=GROUP_COLORS[record_id], edgecolors="white", linewidths=0.6,
            label=GROUP_LABELS[record_id], zorder=3,
        )
    axes[0].set(
        xlim=(0.0, limit), ylim=(0.0, limit),
        xlabel=r"Scale mass change, $\Delta m$ (kg; assumed unit)",
        ylabel="Flow-integrated mass (kg; flow assumed g s$^{-1}$)",
        title="(a) Flow integral versus scale change",
    )
    axes[0].grid(alpha=0.2)
    axes[0].set_aspect("equal", adjustable="box")
    axes[0].legend(frameon=False, loc="upper left")

    positions = np.arange(1, len(sessions) + 1)
    ratios = [float(item["flow_to_scale_mass_ratio"]) for item in sessions]
    colors = [GROUP_COLORS[item["record_id"]] for item in sessions]
    axes[1].axhspan(0.8, 1.2, color="#DCEFE5", alpha=0.9)
    axes[1].axhline(1.0, color="#253746", linewidth=1.1)
    axes[1].scatter(
        positions, ratios, s=42, color=colors,
        edgecolors="white", linewidths=0.6, zorder=3,
    )
    for position, ratio, item in zip(positions, ratios, sessions):
        if item.get("descriptive_closure_screen_pass") is not True:
            axes[1].annotate(
                "outside screen", (position, ratio), xytext=(0, 7),
                textcoords="offset points", ha="center", fontsize=7, color="#9F2D20",
            )
    axes[1].set(
        xlim=(0.4, len(sessions) + 0.6),
        ylim=(0.75, max(1.4, max(ratios) + 0.05)),
        xlabel="Comparable transfer session",
        ylabel="Integrated-flow / scale-mass ratio",
        title="(b) Session-level closure ratio",
        xticks=positions,
    )
    axes[1].grid(axis="y", alpha=0.2)

    aggregate = record.get("aggregate", {})
    figure.suptitle(
        "MetHyTrucks public HRS measurements: descriptive mass closure\n"
        f"{aggregate.get('mass_closure_screen_pass_count')}/"
        f"{aggregate.get('mass_closure_comparable_session_count')} comparable sessions pass; "
        f"median absolute difference "
        f"{aggregate.get('mass_closure_comparable_absolute_relative_difference_pct_median'):.2f}%",
        fontsize=10,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "methytrucks_mass_closure.pdf"
    png_path = output_dir / "methytrucks_mass_closure.png"
    figure.savefig(pdf_path, bbox_inches="tight")
    figure.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return pdf_path, png_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("research/methytrucks_2026_public_measurement_intake.json"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("manuscript/figures")
    )
    args = parser.parse_args()
    record = json.loads(args.input.read_text(encoding="utf-8"))
    pdf_path, png_path = create_figure(record, args.output_dir)
    print(pdf_path)
    print(png_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
