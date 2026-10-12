from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_validation_gap_report import build_report, _markdown


ROOT = Path(__file__).resolve().parents[1]


def test_gap_report_keeps_failed_gates_and_privacy_boundary() -> None:
    report = build_report(ROOT)

    assert report["target_journal"] == "International Journal of Hydrogen Energy"
    assert report["overall"]["full_user_objective_ready"] is False
    assert report["interpretation"]["data_volume_is_primary_blocker"] is False
    ids = {item["id"] for item in report["unresolved_gates"]}
    assert "full_loop_external_validation" not in ids
    assert "dickens_typeiii_prospective_validation" in ids
    assert "hiad_casebook_frozen" in ids
    assert report["scope_exclusions"][0]["id"] == "full_loop_external_validation"
    assert all("C:\\" not in item["claim_boundary"] for item in report["unresolved_gates"])


def test_gap_report_classifies_primary_buckets() -> None:
    report = build_report(ROOT)
    buckets = report["bucket_counts"]
    assert buckets["component_model"]["FAIL"] >= 8
    assert buckets["governance_review"]["PENDING"] >= 5


def test_gap_report_can_use_dated_readiness_snapshot() -> None:
    report = build_report(ROOT, audit_path="research/ijhe_readiness_audit_2026_10_11.json")
    canonical = build_report(ROOT)

    assert report["source_audit_generated_at"] != canonical["source_audit_generated_at"]
    assert report["overall"]["pass"] == 127
    assert report["overall"]["fail"] == 10
    assert report["overall"]["pending"] == 7


def test_gap_report_exposes_declared_primary_scope_metric() -> None:
    report = build_report(ROOT, audit_path="research/ijhe_readiness_audit_2026_10_11.json")
    scope = report["primary_scope"]

    assert (scope["pass"], scope["fail"], scope["pending"], scope["total"]) == (
        127,
        9,
        2,
        138,
    )
    assert scope["closure_percent"] == 92.0
    assert "full_loop_external_validation" in scope["excluded_gate_ids"]
    assert "institutional_ethics_determination" in scope["excluded_gate_ids"]


def test_gap_report_prioritizes_high_impact_work_without_serializing_tracks() -> None:
    report = build_report(ROOT)

    assert report["execution_tracks"][0]["priority"] == "P0"
    assert report["execution_tracks"][0]["parallel_track"] == "component_model_repairs"
    unresolved = report["unresolved_gates"]
    assert unresolved[0]["id"] == "dickens_typeiii_prospective_validation"
    assert unresolved[0]["priority"] == "P0"
    assert {item["parallel_track"] for item in unresolved} >= {
        "component_model_repairs",
        "review_and_publication",
    }


def test_gap_report_keeps_grune_secondary_figure_diagnostic_out_of_primary_gate() -> None:
    report = build_report(ROOT)

    diagnostics = report["secondary_diagnostics"]
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic["source_gate"] == "grune_2014_pressure_decay_validation"
    assert diagnostic["status"] == "DIAGNOSTIC_ONLY"
    assert diagnostic["points"] == 319
    assert diagnostic["joint_primary_screen_pass"] is False
    assert diagnostic["primary_gate_unchanged"] is True
    grune = next(
        item
        for item in report["unresolved_gates"]
        if item["id"] == "grune_2014_pressure_decay_validation"
    )
    assert grune["status"] == "PENDING"
    assert "figure-derived" in grune["next_action"]


def test_markdown_does_not_expose_evidence_paths() -> None:
    markdown = _markdown(build_report(ROOT))
    assert "evidence" not in markdown.lower()
    assert "\\research\\" not in markdown
    assert "원시 데이터" in markdown
