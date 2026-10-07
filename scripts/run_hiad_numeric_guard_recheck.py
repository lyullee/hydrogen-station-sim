"""Recheck direct-answer numeric grounding after the SAGA runtime guard change.

This is an explicitly post-outcome safety diagnostic.  It preserves the
frozen HIAD benchmark and reruns the same 34 public cases only to check whether
unsupported value/unit claims remain visible at the API boundary.  It is not a
new benchmark, holdout, or effectiveness result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

import run_hiad_machine_response_benchmark as benchmark


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/public_validation/processed/hiad_hrs_cases.jsonl"
DEFAULT_ACTIONS = ROOT / "research/hiad_action_evidence.json"
DEFAULT_BASELINE = ROOT / "research/hiad_machine_response_benchmark_2026_10_08.json"
NOTICE = "No precise value was supplied for this point"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(
    *, cases_path: Path, actions_path: Path, baseline_path: Path,
    saga_repo: Path, provider: str,
) -> dict[str, Any]:
    cases = benchmark._read_jsonl(cases_path)
    actions = json.loads(actions_path.read_text(encoding="utf-8"))
    expected_by_id = {
        str(case["event_id"]): list(case["action_categories"])
        for case in actions["cases"]
    }
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    before_rows = [
        row for row in baseline["responses"] if row["variant"] == "saga-linked"
    ]
    if len(cases) != len(before_rows):
        raise ValueError("case count differs from the retained benchmark")

    sys.path.insert(0, str((saga_repo / "python").resolve()))
    from fastapi.testclient import TestClient
    from saga.api import app

    rows: list[dict[str, Any]] = []
    with TestClient(app) as client:
        health = client.get("/api/health").json()
        if not health.get("groq_configured"):
            raise RuntimeError("Groq is not configured in the SAGA runtime")
        for index, case in enumerate(cases, start=1):
            event_id = str(case["event_id"])
            context = benchmark._context(case)
            allowed_input = benchmark.QUESTION + "\n" + json.dumps(
                context, ensure_ascii=False,
            )
            started = perf_counter()
            response = client.post(
                "/api/integrations/digital-twin/main",
                json={
                    "question": benchmark.QUESTION,
                    "context": context,
                    "history": [],
                    "request_kind": "user_query",
                    "provider": provider,
                    "language": "en",
                    "max_tokens": 900,
                },
            )
            latency_ms = (perf_counter() - started) * 1000.0
            call_failed = response.status_code != 200
            body = response.json()
            answer = str(body.get("answer") or "") if not call_failed else ""
            rows.append({
                "event_id": event_id,
                "provider": str(body.get("provider") or provider),
                "model": str(body.get("model") or ""),
                "latency_ms": latency_ms,
                "call_failed": call_failed,
                "http_status": response.status_code,
                "guard_notice_present": NOTICE in answer,
                "answer": answer,
                **benchmark.score_answer(
                    answer,
                    expected_categories=expected_by_id[event_id],
                    allowed_input_text=allowed_input,
                ),
            })
            print(f"HIAD numeric guard recheck {index}/{len(cases)}", flush=True)

    before_unsupported = sum(
        bool(row["unsupported_value_unit_claims"]) for row in before_rows
    )
    after_unsupported = sum(
        bool(row["unsupported_value_unit_claims"]) for row in rows
    )
    return {
        "schema_version": 1,
        "artifact_type": "hiad_post_outcome_numeric_guard_recheck",
        "status": "POST_OUTCOME_RUNTIME_SAFETY_RECHECK",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "retained_benchmark": baseline_path.relative_to(ROOT).as_posix(),
            "retained_benchmark_sha256": _sha256(baseline_path),
            "case_count": len(cases),
            "same_public_hiad_cohort": True,
            "same_question_and_context_builder": True,
        },
        "runtime": {
            "digital_twin_commit": benchmark._git_commit(ROOT),
            "saga_commit": benchmark._git_commit(saga_repo),
            "provider": provider,
            "execution_mode": "in_process_fastapi_test_client_no_server",
        },
        "outcome": {
            "before_unsupported_claim_response_count": before_unsupported,
            "after_unsupported_claim_response_count": after_unsupported,
            "after_provider_failure_count": sum(row["call_failed"] for row in rows),
            "guard_notice_response_count": sum(row["guard_notice_present"] for row in rows),
            "mean_latency_ms": sum(row["latency_ms"] for row in rows) / len(rows),
        },
        "responses": rows,
        "claim_boundary": (
            "Post-outcome runtime safety diagnostic on the already observed 34-case cohort. "
            "It checks only whether the API exposes unsupported value/unit claims after the "
            "guard change. It is not an independent holdout, expert review, action-correctness "
            "study, or evidence of field safety or SAGA effectiveness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--actions", type=Path, default=DEFAULT_ACTIONS)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--saga-repo", type=Path, default=ROOT.parent / "saga-system")
    parser.add_argument("--provider", choices=("groq",), default="groq")
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "research/hiad_machine_response_guard_recheck_2026_10_08.json",
    )
    args = parser.parse_args()
    result = run(
        cases_path=args.cases.resolve(), actions_path=args.actions.resolve(),
        baseline_path=args.baseline.resolve(), saga_repo=args.saga_repo.resolve(),
        provider=args.provider,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(result["outcome"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
