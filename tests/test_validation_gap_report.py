from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_validation_gap_report import build_report, _markdown


ROOT = Path(__file__).resolve().parents[1]


def test_gap_report_keeps_failed_gates_and_privacy_boundary() -> None:
    report = build_report(ROOT)

    assert report["overall"]["full_user_objective_ready"] is False
    assert report["interpretation"]["data_volume_is_primary_blocker"] is False
    ids = {item["id"] for item in report["unresolved_gates"]}
    assert "full_loop_external_validation" in ids
    assert "dickens_typeiii_prospective_validation" in ids
    assert "hiad_casebook_frozen" in ids
    assert all("C:\\" not in item["claim_boundary"] for item in report["unresolved_gates"])


def test_gap_report_classifies_primary_buckets() -> None:
    report = build_report(ROOT)
    buckets = report["bucket_counts"]
    assert buckets["full_loop_data"]["FAIL"] == 1
    assert buckets["component_model"]["FAIL"] >= 8
    assert buckets["governance_review"]["PENDING"] >= 5


def test_gap_report_prioritizes_high_impact_work_without_serializing_tracks() -> None:
    report = build_report(ROOT)

    assert report["execution_tracks"][0]["priority"] == "P0"
    assert report["execution_tracks"][0]["parallel_track"] == "full_loop_intake_and_scoring"
    unresolved = report["unresolved_gates"]
    assert unresolved[0]["id"] == "full_loop_external_validation"
    assert unresolved[0]["priority"] == "P0"
    assert {item["parallel_track"] for item in unresolved} >= {
        "full_loop_intake_and_scoring",
        "component_model_repairs",
        "review_and_publication",
    }


def test_markdown_does_not_expose_evidence_paths() -> None:
    markdown = _markdown(build_report(ROOT))
    assert "evidence" not in markdown.lower()
    assert "\\research\\" not in markdown
    assert "원시 데이터" in markdown
