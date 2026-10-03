from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SCRIPT = ROOT / "scripts" / "package_hiad_expert_review.py"
ANALYZE_SCRIPT = ROOT / "scripts" / "analyze_hiad_expert_review.py"


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _collection(tmp_path: Path) -> Path:
    collection = tmp_path / "collection"
    collection.mkdir()
    cases = [
        {
            "event_id": str(event_id),
            "expert_vignette_approved": "YES",
            "narrative_action_leakage_review": "PASS",
        }
        for event_id in (1, 2)
    ]
    (collection / "casebook_snapshot.json").write_text(
        json.dumps({"cases": cases}), encoding="utf-8"
    )
    allocation = []
    blind = []
    for event_id in ("1", "2"):
        for variant in ("alarm-only", "saga-linked"):
            code = f"{event_id}-{variant}"
            answer = f"response {code}"
            allocation.append({
                "response_code": code,
                "event_id": event_id,
                "variant": variant,
                "repeat": "1",
                "provider": "deterministic" if variant == "alarm-only" else "groq",
                "model": variant,
                "answer_mode": "direct",
                "citation_count": "0",
                "latency_ms": "0" if variant == "alarm-only" else "125",
                "call_failed": "False",
                "error": "",
                "answer": answer,
            })
            blind.append({
                "response_code": code,
                "event_id": event_id,
                "response_text": answer,
                "rater_id": "",
                "situation_accuracy_1_5": "",
                "immediate_action_correctness_1_5": "",
                "priority_order_1_5": "",
                "stabilization_restart_1_5": "",
                "prevention_quality_1_5": "",
                "evidence_grounding_1_5": "",
                "operator_usability_1_5": "",
                "critical_omission_0_1": "",
                "unsafe_advice_0_1": "",
                "comments": "",
            })
    _write_csv(collection / "allocation_key.csv", allocation)
    _write_csv(collection / "blind_expert_review.csv", blind)
    _write_csv(collection / "reviewer_case_reference.csv", [
        {"event_id": "1", "historical_observation_json": "{}"},
        {"event_id": "2", "historical_observation_json": "{}"},
    ])
    (collection / "raw_responses.jsonl").write_text("{}\n", encoding="utf-8")
    (collection / "collection_errors.json").write_text("[]\n", encoding="utf-8")
    hashes = {
        name: _sha(collection / name)
        for name in (
            "casebook_snapshot.json", "raw_responses.jsonl", "allocation_key.csv",
            "blind_expert_review.csv", "reviewer_case_reference.csv",
            "collection_errors.json",
        )
    }
    (collection / "collection_manifest.json").write_text(json.dumps({
        "source_commit": "abc123",
        "response_count": 4,
        "expected_response_count": 4,
        "failed_call_count": 0,
        "failed_calls_retained_for_blinded_scoring": True,
        "file_sha256": hashes,
    }), encoding="utf-8")
    return collection


def _complete(path: Path) -> None:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0])
    for row in rows:
        score = "3" if row["response_code"].endswith("alarm-only") else "4"
        for field in (
            "situation_accuracy_1_5", "immediate_action_correctness_1_5",
            "priority_order_1_5", "stabilization_restart_1_5",
            "prevention_quality_1_5", "evidence_grounding_1_5",
            "operator_usability_1_5",
        ):
            row[field] = score
        row["critical_omission_0_1"] = "0"
        row["unsafe_advice_0_1"] = "0"
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_reviewer_packets_are_blinded_locked_and_analyzable(tmp_path: Path):
    collection = _collection(tmp_path)
    package = tmp_path / "package"
    completed = subprocess.run([
        sys.executable, str(PACKAGE_SCRIPT),
        "--collection", str(collection), "--output", str(package),
        "--reviewer-codes", "R1", "R2", "--ethics-status", "exempt",
    ], check=True, capture_output=True, text=True)
    assert "coordinator_lock_manifest.json" in completed.stdout
    for code in ("R1", "R2"):
        folder = package / "reviewers" / code
        assert not (folder / "allocation_key.csv").exists()
        ratings = folder / f"ratings_{code}.csv"
        _complete(ratings)

    output = tmp_path / "analysis"
    subprocess.run([
        sys.executable, str(ANALYZE_SCRIPT),
        "--allocation", str(collection / "allocation_key.csv"),
        "--casebook", str(collection / "casebook_snapshot.json"),
        "--ratings", str(package / "reviewers/R1/ratings_R1.csv"),
        str(package / "reviewers/R2/ratings_R2.csv"),
        "--output", str(output),
    ], check=True, capture_output=True, text=True)
    report = json.loads((output / "expert_review_analysis.json").read_text())
    assert report["event_count"] == 2
    assert report["rater_count"] == 2
    assert report["paired_composite_differences_vs_alarm"]["saga-linked"]["mean"] == 1.0
    assert report["variant_summary"]["saga-linked"]["latency_ms_mean"] == 125.0


def test_analyzer_rejects_modified_locked_response_text(tmp_path: Path):
    collection = _collection(tmp_path)
    package = tmp_path / "package"
    subprocess.run([
        sys.executable, str(PACKAGE_SCRIPT),
        "--collection", str(collection), "--output", str(package),
        "--reviewer-codes", "R1", "R2", "--ethics-status", "exempt",
    ], check=True, capture_output=True, text=True)
    paths = [package / f"reviewers/{code}/ratings_{code}.csv" for code in ("R1", "R2")]
    for path in paths:
        _complete(path)
    text = paths[0].read_text(encoding="utf-8-sig")
    paths[0].write_text(text.replace("response 1-alarm-only", "tampered"), encoding="utf-8-sig")
    result = subprocess.run([
        sys.executable, str(ANALYZE_SCRIPT),
        "--allocation", str(collection / "allocation_key.csv"),
        "--casebook", str(collection / "casebook_snapshot.json"),
        "--ratings", *(str(path) for path in paths),
        "--output", str(tmp_path / "analysis"),
    ], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Locked response_text was changed" in result.stderr
