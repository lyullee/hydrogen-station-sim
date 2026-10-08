from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from record_ijhe_compile_status import _sha256, build_status  # noqa: E402


def test_current_compiled_working_manuscript_is_exact_and_inspected():
    status_path = ROOT / "manuscript/ijhe_compile_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    source = ROOT / status["source"]["path"]
    pdf = ROOT / status["pdf"]["path"]
    log = ROOT / status["compile_log"]["path"]

    assert status["schema_version"] == 2
    assert status["success"] is True
    assert status["source"]["sha256"] == _sha256(source)
    assert status["pdf"]["sha256"] == _sha256(pdf)
    assert status["compile_log"]["sha256"] == _sha256(log)
    assert status["compile_log"]["unresolved_citations"] == 0
    assert status["compile_log"]["unresolved_references"] == 0
    assert status["compile_log"]["fatal_errors"] == []
    assert status["visual_qa"]["pages_inspected"] == status["pdf"]["page_count"]
    assert status["visual_qa"]["all_pages_rendered_and_inspected"] is True


def test_verifier_reproduces_success_from_committed_artifacts():
    stored = json.loads(
        (ROOT / "manuscript/ijhe_compile_status.json").read_text(encoding="utf-8")
    )
    rebuilt = build_status(
        source=ROOT / stored["source"]["path"],
        pdf=ROOT / stored["pdf"]["path"],
        log=ROOT / stored["compile_log"]["path"],
        compiler=stored["compiler"]["name"],
        compiler_version=stored["compiler"]["version"],
        compiler_url=stored["compiler"]["official_release_url"],
        compiler_archive_sha256=stored["compiler"]["archive_sha256"],
        visual_pages_inspected=stored["visual_qa"]["pages_inspected"],
    )
    assert rebuilt["success"] is True
    assert rebuilt["source"]["sha256"] == stored["source"]["sha256"]
    assert rebuilt["pdf"]["sha256"] == stored["pdf"]["sha256"]
    assert rebuilt["compile_log"]["sha256"] == stored["compile_log"]["sha256"]
