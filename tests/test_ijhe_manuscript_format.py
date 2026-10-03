from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_ijhe_manuscript import check  # noqa: E402


def test_current_ijhe_manuscript_passes_static_submission_checks():
    result = check(
        ROOT / "manuscript/ijhe_manuscript_draft.tex",
        ROOT / "manuscript/Highlights.txt",
    )
    assert result["format_gate_passed"] is True
    assert result["counts"]["unresolved_citations"] == []
    assert result["counts"]["missing_figure_assets"] == []
