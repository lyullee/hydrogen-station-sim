"""Render the manuscript's shared-state safety workflow from native geometry."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "manuscript/figures"
    root.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(6.6, 3.45))
    ax.set(xlim=(0, 12.4), ylim=(0, 5.15))
    ax.axis("off")
    navy = "#17364D"
    teal = "#117F80"
    boxes = [
        (0.05, "Process model", "Mass / energy\nPressure / T\nInventory / flow"),
        (2.58, "Virtual signals", "Value / units / time\nOrigin / quality\nAlarms / history"),
        (5.11, "Safety analysis", "HAZOP scenarios\nRelease boundary\nImpact / uncertainty"),
        (7.64, "Response plan", "Five stages\nTarget / conditions\nCompletion checks"),
        (10.17, "SAGA interface", "Focused answer\nEvidence checks\nFull plan separate"),
    ]
    for x, title, content in boxes:
        ax.add_patch(FancyBboxPatch((x, 2.95), 2.18, 1.64,
            boxstyle="round,pad=0.02,rounding_size=0.08", linewidth=1.1,
            edgecolor=navy, facecolor="#F3F7FA"))
        ax.text(x + 1.09, 4.26, title, ha="center", va="center",
                color=navy, fontsize=8.6, weight="bold")
        ax.text(x + 1.09, 3.59, content, ha="center", va="center",
                linespacing=1.5, fontsize=8.0, color=navy)
    for start in (2.23, 4.76, 7.29, 9.82):
        ax.add_patch(FancyArrowPatch((start + .025, 3.78), (start + .32, 3.78),
            arrowstyle="-|>", mutation_scale=13, color=navy, linewidth=1.5))

    ax.text(6.2, 4.98, "Shared simulation state and traceable safety evidence",
            ha="center", color=navy, weight="bold", fontsize=10)
    ax.text(4.9, 2.55,
            "Generated text is advisory",
            ha="center", va="center", fontsize=8, color="#526773")
    ax.add_patch(FancyBboxPatch((2.58, .66), 7.24, 1.15,
        boxstyle="round,pad=0.02,rounding_size=0.08", linewidth=1.1,
        edgecolor=teal, facecolor="#EDF6F3"))
    ax.text(6.2, 1.51, "Virtual action and feedback", ha="center",
            weight="bold", color=teal, fontsize=9)
    ax.text(6.2, 1.08,
            "Command → motion → feedback → flow confirmation",
            ha="center", color=navy, fontsize=8)
    ax.annotate("", xy=(8.73, 1.84), xytext=(8.73, 2.91),
                arrowprops={"arrowstyle": "-|>", "color": teal, "lw": 1.4})
    ax.text(8.88, 2.13, "Operator / schedule", ha="left", va="center",
            color=teal, fontsize=7.4)
    ax.plot([2.54, 1.14, 1.14], [1.24, 1.24, 2.68], color=teal, linewidth=1.5)
    ax.annotate("", xy=(1.14, 2.91), xytext=(1.14, 2.67),
                arrowprops={"arrowstyle": "-|>", "color": teal, "lw": 1.5})
    ax.text(1.31, 2.0, "Recalculate\nphysical state", va="center",
            color=teal, fontsize=8)
    ax.text(6.2, .16,
            "Evaluation: public experiments | private temporal holdouts | incidents | software checks",
            ha="center", va="center", color="#526773", fontsize=7.5)
    fig.subplots_adjust(left=.01, right=.99, top=.99, bottom=.01)
    for extension in ("pdf", "png"):
        fig.savefig(root / f"integrated_safety_workflow.{extension}", dpi=240,
                    bbox_inches="tight", pad_inches=.05)
    plt.close(fig)
    print(root / "integrated_safety_workflow.pdf")


if __name__ == "__main__":
    main()
