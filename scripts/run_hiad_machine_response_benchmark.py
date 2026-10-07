"""Run a bounded retrospective machine benchmark of the direct SAGA endpoint.

The public HIAD incident descriptions are provided to the model while HIAD
emergency-action, lesson and corrective-action prose remains withheld.  The
evaluator compares only coarse, previously derived action categories and
response-stage proxies.  This is a development benchmark, not expert evidence
or a safety/effectiveness validation.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from time import perf_counter
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = ROOT / "data/public_validation/processed/hiad_hrs_cases.jsonl"
DEFAULT_ACTIONS = ROOT / "research/hiad_action_evidence.json"
DEFAULT_PROTOCOL = ROOT / "research/hiad_machine_response_benchmark_protocol_2026_10_08.json"

QUESTION = (
    "Assess this historical hydrogen-refuelling-station observation using only "
    "the supplied facts. Give one integrated operator response with: (1) the "
    "observed situation and plausible scenario, marking uncertainty; (2) "
    "immediate actions in priority order; (3) stabilization and restart "
    "conditions; and (4) prevention and follow-up controls. Do not invent "
    "measurements, distances, causes, or completed actions."
)

CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "shutdown_isolation_depressurization": (
        "emergency shutdown", "shut down", "shutdown", "stop operation",
        "stop fueling", "stop fuelling", "isolate", "close the valve",
        "close valves", "depressur", "controlled vent",
    ),
    "detection_alarm_monitoring": (
        "gas detector", "hydrogen detector", "monitor", "alarm", "gas concentration",
    ),
    "fire_response_cooling": (
        "fire service", "fire brigade", "firefighting", "fire suppression",
        "cooling water", "water spray", "thermal exposure", "adjacent equipment",
    ),
    "evacuation_perimeter_access": (
        "evacuat", "exclusion zone", "perimeter", "access control", "keep personnel away",
    ),
    "emergency_communication_coordination": (
        "notify", "emergency services", "incident command", "communicat",
        "site emergency", "fire department",
    ),
    "inspection_leak_test_repair": (
        "leak test", "tightness test", "inspect", "repair", "integrity test",
        "root cause",
    ),
    "procedure_interlock_training_design": (
        "procedure", "interlock", "training", "design review", "maintenance",
        "management of change", "preventive",
    ),
    "ventilation_purge": (
        "ventilat", "purge", "gas-free", "gas free",
    ),
}

STAGE_PATTERNS: dict[str, tuple[str, ...]] = {
    "recognition": (
        "observed", "reported", "plausible", "uncertain", "indicat", "suggest",
        "release", "fire", "explosion", "near miss",
    ),
    "immediate": (
        "immediate", "first", "shut", "stop", "isolate", "evacuat", "notify",
        "access control", "perimeter",
    ),
    "stabilize": (
        "stabili", "monitor", "confirm", "verify", "gas concentration", "pressure",
        "temperature", "ventilat", "purge",
    ),
    "restart": (
        "restart", "recommission", "return to service", "resume operation",
        "authorization", "authorised", "authorized",
    ),
    "prevention": (
        "prevent", "follow-up", "root cause", "inspect", "maintenance", "training",
        "procedure", "interlock", "design review",
    ),
}

UNSUPPORTED_VALUE_UNIT = re.compile(
    r"(?<![\w.])[-+]?\d+(?:\.\d+)?\s*(?:m|kpa|mpa|bar|%|vol\s*%|°c|degc|"
    r"seconds?|secs?|minutes?|mins?)(?![\w])",
    re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit(path: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=path, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(pattern.casefold() in lowered for pattern in patterns)


def score_answer(
    answer: str,
    *,
    expected_categories: list[str],
    allowed_input_text: str,
) -> dict[str, Any]:
    mentioned = sorted(
        category for category, patterns in CATEGORY_PATTERNS.items()
        if _contains_any(answer, patterns)
    )
    expected = sorted(set(expected_categories))
    matched = sorted(set(mentioned).intersection(expected))
    required_stages = {"recognition", "immediate", "stabilize", "restart", "prevention"}
    stages = sorted(
        stage for stage, patterns in STAGE_PATTERNS.items()
        if _contains_any(answer, patterns)
    )
    allowed_values = {
        match.group(0).casefold().replace(" ", "")
        for match in UNSUPPORTED_VALUE_UNIT.finditer(allowed_input_text)
    }
    unsupported_values = sorted({
        match.group(0) for match in UNSUPPORTED_VALUE_UNIT.finditer(answer)
        if match.group(0).casefold().replace(" ", "") not in allowed_values
    })
    category_recall = len(matched) / len(expected) if expected else None
    stage_coverage = len(required_stages.intersection(stages)) / len(required_stages)
    components = [stage_coverage]
    if category_recall is not None:
        components.append(category_recall)
    return {
        "expected_categories": expected,
        "mentioned_categories": mentioned,
        "matched_expected_categories": matched,
        "category_recall": category_recall,
        "response_stages": stages,
        "stage_coverage": stage_coverage,
        "unsupported_value_unit_claims": unsupported_values,
        "machine_proxy_score": float(np.mean(components)),
    }


def paired_bootstrap(
    baseline: list[float], linked: list[float], *, seed: int, replicates: int,
) -> dict[str, Any]:
    differences = np.asarray(linked, dtype=float) - np.asarray(baseline, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(differences, size=(replicates, len(differences)), replace=True)
    means = samples.mean(axis=1)
    return {
        "case_count": len(differences),
        "mean_paired_difference": float(differences.mean()),
        "bootstrap_95_ci": [
            float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975)),
        ],
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
    }


def _context(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "station_status": "HISTORICAL_INCIDENT",
        "historical_observation": {
            key: case.get(key) for key in (
                "title", "description", "initiating_system", "physical_effect",
                "consequence_nature", "sub_application", "supply_chain_stage",
                "operational_condition",
            )
        },
        "active_alerts": [],
        "impact_results": [],
        "known_limitations": [
            "Historical narrative only; no live sensor values or calculated consequence distances supplied."
        ],
    }


def _baseline(case: dict[str, Any]) -> str:
    return (
        f"Incident reported: {case.get('title')}. Observed physical effect: "
        f"{case.get('physical_effect') or 'not specified'}. Follow the station "
        "emergency procedure and have an authorized operator assess the equipment."
    )


def _aggregate(rows: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["variant"])].append(row)
    variants = {}
    for variant, values in grouped.items():
        scores = [float(row["machine_proxy_score"]) for row in values]
        recalls = [
            float(row["category_recall"]) for row in values
            if row["category_recall"] is not None
        ]
        variants[variant] = {
            "response_count": len(values),
            "mean_machine_proxy_score": float(np.mean(scores)),
            "mean_category_recall": float(np.mean(recalls)) if recalls else None,
            "mean_stage_coverage": float(np.mean([row["stage_coverage"] for row in values])),
            "unsupported_claim_response_count": sum(
                bool(row["unsupported_value_unit_claims"]) for row in values
            ),
            "failed_call_count": sum(bool(row.get("call_failed")) for row in values),
            "latency_ms_mean": float(np.mean([
                row["latency_ms"] for row in values if row.get("latency_ms") is not None
            ])),
        }
    by_key = {(str(row["event_id"]), str(row["variant"])): row for row in rows}
    event_ids = sorted({str(row["event_id"]) for row in rows}, key=int)
    baseline = [by_key[(event_id, "alarm-only")]["machine_proxy_score"] for event_id in event_ids]
    linked = [by_key[(event_id, "saga-linked")]["machine_proxy_score"] for event_id in event_ids]
    return {
        "case_count": len(event_ids),
        "response_count": len(rows),
        "variant_summary": variants,
        "paired_machine_proxy_difference": paired_bootstrap(
            baseline, linked,
            seed=int(protocol["analysis"]["bootstrap_seed"]),
            replicates=int(protocol["analysis"]["bootstrap_replicates"]),
        ),
    }


def run(
    *, protocol_path: Path, cases_path: Path, actions_path: Path,
    saga_repo: Path, provider: str,
) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    expected_hashes = protocol["frozen_inputs"]
    for path, key in (
        (cases_path, "hiad_cases_sha256"),
        (actions_path, "action_evidence_sha256"),
        (Path(__file__), "runner_sha256"),
    ):
        if _sha256(path) != expected_hashes[key]:
            raise ValueError(f"frozen input mismatch: {path}")
    saga_api = saga_repo / "python/saga/api.py"
    if _sha256(saga_api) != expected_hashes["saga_api_sha256"]:
        raise ValueError("SAGA direct API differs from the frozen implementation")

    cases = _read_jsonl(cases_path)
    action_evidence = json.loads(actions_path.read_text(encoding="utf-8"))
    expected_by_id = {
        str(case["event_id"]): list(case["action_categories"])
        for case in action_evidence["cases"]
    }
    if len(cases) != int(protocol["cohort"]["case_count"]):
        raise ValueError("HIAD cohort size differs from the frozen protocol")

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
            context = _context(case)
            allowed_input = QUESTION + "\n" + json.dumps(context, ensure_ascii=False)
            baseline = _baseline(case)
            rows.append({
                "event_id": event_id,
                "variant": "alarm-only",
                "provider": "deterministic",
                "model": "alarm-only",
                "latency_ms": 0.0,
                "call_failed": False,
                "answer": baseline,
                **score_answer(
                    baseline, expected_categories=expected_by_id[event_id],
                    allowed_input_text=allowed_input,
                ),
            })
            started = perf_counter()
            response = client.post(
                "/api/integrations/digital-twin/main",
                json={
                    "question": QUESTION,
                    "context": context,
                    "history": [],
                    "request_kind": "user_query",
                    "provider": provider,
                    "language": "en",
                    "max_tokens": int(protocol["collection"]["max_tokens"]),
                },
            )
            latency_ms = (perf_counter() - started) * 1000.0
            call_failed = response.status_code != 200
            body = response.json()
            answer = str(body.get("answer") or "") if not call_failed else ""
            rows.append({
                "event_id": event_id,
                "variant": "saga-linked",
                "provider": str(body.get("provider") or provider),
                "model": str(body.get("model") or ""),
                "latency_ms": latency_ms,
                "call_failed": call_failed,
                "http_status": response.status_code,
                "answer": answer,
                **score_answer(
                    answer, expected_categories=expected_by_id[event_id],
                    allowed_input_text=allowed_input,
                ),
            })
            print(f"HIAD machine benchmark {index}/{len(cases)}", flush=True)

    return {
        "schema_version": 1,
        "artifact_type": "hiad_retrospective_machine_response_benchmark",
        "status": "COMPLETED_RETROSPECTIVE_MACHINE_BENCHMARK",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "path": protocol_path.resolve().relative_to(ROOT).as_posix(),
            "sha256": _sha256(protocol_path),
            "model_outputs_accessed_before_protocol_freeze": False,
            "reference_action_categories_accessed_before_protocol_freeze": True,
        },
        "runtime": {
            "digital_twin_commit": _git_commit(ROOT),
            "saga_commit": _git_commit(saga_repo),
            "provider": provider,
            "execution_mode": "in_process_fastapi_test_client_no_server",
        },
        "aggregate": _aggregate(rows, protocol),
        "responses": rows,
        "claim_boundary": protocol["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--actions", type=Path, default=DEFAULT_ACTIONS)
    parser.add_argument("--saga-repo", type=Path, default=ROOT.parent / "saga-system")
    parser.add_argument("--provider", choices=("groq",), default="groq")
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "research/hiad_machine_response_benchmark_2026_10_08.json",
    )
    args = parser.parse_args()
    result = run(
        protocol_path=args.protocol.resolve(), cases_path=args.cases.resolve(),
        actions_path=args.actions.resolve(), saga_repo=args.saga_repo.resolve(),
        provider=args.provider,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(json.dumps(result["aggregate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
