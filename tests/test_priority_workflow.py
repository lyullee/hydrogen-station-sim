from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_priority_workflow_keeps_science_blockers_separate_from_ci_regressions() -> None:
    workflow = (ROOT / ".github/workflows/priority-validation.yml").read_text(
        encoding="utf-8"
    )

    # External-science screens are intentionally blocked today.  They must be
    # retained in the uploaded report without turning every push into a noisy
    # red build when the reproducible software checks still pass.
    assert "continue-on-error: true" in workflow
    assert "Fail only on software or process regression" in workflow
    assert "software_checks" in workflow
    assert "s == 'PASS'" in workflow

