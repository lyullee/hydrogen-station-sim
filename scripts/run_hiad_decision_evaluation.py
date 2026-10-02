"""Collect blinded alarm-only/SAGA responses for independent expert review.

HIAD response, lesson, and corrective-action fields are withheld from SAGA and
retained only in the casebook supplied to the study coordinator.  Incident
narratives can contain hindsight information, so every vignette has an explicit
leakage-review field before it is admitted to a reported holdout set.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from time import perf_counter
from urllib.request import Request, urlopen


PROMPT = """Assess this historical hydrogen-refuelling-station observation using only the supplied facts.
Give one concise integrated response with: (1) situation and plausible scenario(s), clearly marking uncertainty; (2) immediately executable actions in priority order; (3) stabilization and restart criteria; and (4) prevention and follow-up controls. Do not invent measurements, distances, causes, or completed actions. Make the ordering clear enough for an operator to act without choosing among duplicate scenario lists."""


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _stratum(case: dict) -> str:
    value = str(case.get("consequence_nature") or "unknown").strip().lower()
    if "explosion" in value:
        return "explosion"
    if "fire" in value:
        return "fire"
    if "leak" in value or "release" in value:
        return "unignited-release"
    if "near miss" in value:
        return "near-miss"
    return "other"


def _split(cases: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for case in cases:
        if not any(case.get(name) for name in (
            "emergency_action", "lesson_learnt", "corrective_measures"
        )):
            continue
        groups.setdefault(_stratum(case), []).append(case)
    development, holdout = [], []
    for group in groups.values():
        ordered = sorted(
            group,
            key=lambda case: hashlib.sha256(
                f"HIAD-2601:{case['event_id']}".encode()
            ).hexdigest(),
        )
        count = max(1, round(len(ordered) * 0.25))
        development.extend(ordered[:count])
        holdout.extend(ordered[count:])
    return {
        "development": sorted(development, key=lambda case: int(case["event_id"])),
        "holdout": sorted(holdout, key=lambda case: int(case["event_id"])),
    }


def _context(case: dict) -> dict:
    return {
        "station_status": "HISTORICAL_INCIDENT",
        "historical_observation": {
            "title": case["title"],
            "description": case["description"],
            "initiating_system": case["initiating_system"],
            "physical_effect": case["physical_effect"],
            "consequence_nature": case["consequence_nature"],
            "sub_application": case["sub_application"],
            "supply_chain_stage": case["supply_chain_stage"],
            "operational_condition": case["operational_condition"],
        },
        "active_alerts": [],
        "impact_results": [],
        "known_limitations": [
            "Historical narrative; no live sensor values or calculated consequence distances supplied."
        ],
    }


def _baseline(case: dict) -> str:
    return (
        f"Incident reported: {case['title']}. Observed physical effect: "
        f"{case['physical_effect'] or 'not specified'}. Follow the station emergency "
        "procedure and have an authorized operator assess the equipment."
    )


def _post(url: str, payload: dict, timeout_s: float) -> tuple[dict, float]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = perf_counter()
    with urlopen(request, timeout=timeout_s) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result, (perf_counter() - started) * 1000.0


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=Path("data/public_validation/processed/hiad_hrs_cases.jsonl"))
    parser.add_argument("--saga-url")
    parser.add_argument("--provider", choices=("service_hub", "groq"), default="groq")
    parser.add_argument("--split", choices=("development", "holdout"), default="holdout")
    parser.add_argument("--repeats", type=int, default=3, choices=range(1, 11))
    parser.add_argument("--timeout-s", type=float, default=90.0)
    parser.add_argument("--output", type=Path, default=Path("data/public_validation/results/hiad_decision"))
    parser.add_argument("--prepare-casebook", action="store_true")
    parser.add_argument("--approved-casebook", type=Path)
    args = parser.parse_args()

    splits = _split(_read_jsonl(args.cases))
    cases = splits[args.split]
    args.output.mkdir(parents=True, exist_ok=True)
    casebook = [{
        "event_id": case["event_id"],
        "quality": case["quality"],
        "stratum": _stratum(case),
        "input_context": _context(case)["historical_observation"],
        "reference_emergency_action": case["emergency_action"],
        "reference_lesson_learnt": case["lesson_learnt"],
        "reference_corrective_measures": case["corrective_measures"],
        "references": case["references"],
        "narrative_action_leakage_review": "PENDING",
        "expert_vignette_approved": "NO",
    } for case in cases]
    prepared_casebook = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "HIAD 2.2", "split": args.split,
        "development_count": len(splits["development"]),
        "holdout_count": len(splits["holdout"]), "cases": casebook,
    }
    prepared_path = args.output / "casebook_for_approval.json"
    if args.prepare_casebook:
        prepared_path.write_text(
            json.dumps(prepared_casebook, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(prepared_path)
        return 0
    if args.approved_casebook is None:
        raise SystemExit(
            "Prepare and review the casebook first, then pass --approved-casebook PATH"
        )
    if not args.saga_url:
        raise SystemExit("--saga-url is required during response collection")
    approved = json.loads(args.approved_casebook.read_text(encoding="utf-8"))
    approved_by_id = {str(case["event_id"]): case for case in approved["cases"]}
    invalid = [
        event_id for event_id, case in approved_by_id.items()
        if str(case.get("expert_vignette_approved", "NO")).upper() != "YES"
        or str(case.get("narrative_action_leakage_review", "")).upper() != "PASS"
    ]
    if invalid:
        raise SystemExit(
            "Casebook approval/leakage review incomplete for event IDs: "
            + ", ".join(invalid)
        )
    split_by_id = {str(case["event_id"]): case for case in cases}
    unknown = sorted(set(approved_by_id) - set(split_by_id), key=int)
    if unknown:
        raise SystemExit("Approved casebook contains IDs outside the selected split: " + ", ".join(unknown))
    cases = [split_by_id[event_id] for event_id in approved_by_id]
    endpoint = args.saga_url.rstrip("/") + "/api/integrations/digital-twin/main"
    responses = []
    errors = []
    for case in cases:
        responses.append({
            "event_id": case["event_id"], "variant": "alarm-only", "repeat": 1,
            "answer": _baseline(case), "latency_ms": 0.0,
            "provider": "deterministic", "model": "alarm-only",
        })
        for repeat in range(1, args.repeats + 1):
            try:
                result, latency = _post(endpoint, {
                    "question": PROMPT,
                    "context": _context(case),
                    "history": [],
                    "request_kind": "user_query",
                    "provider": args.provider,
                    "language": "en",
                    "max_tokens": 1200,
                }, args.timeout_s)
                responses.append({
                    "event_id": case["event_id"], "variant": "saga-linked",
                    "repeat": repeat, "answer": str(result.get("answer") or ""),
                    "latency_ms": latency, "provider": str(result.get("provider") or args.provider),
                    "model": str(result.get("model") or ""),
                })
            except Exception as exc:  # collection must preserve per-case failures
                errors.append({
                    "event_id": case["event_id"], "repeat": repeat,
                    "error": f"{type(exc).__name__}: {exc}",
                })
        print(f"collected HIAD {case['event_id']}", flush=True)

    blinded = []
    allocation = []
    for response in responses:
        digest = hashlib.sha256(
            f"blind-2601:{response['event_id']}:{response['variant']}:{response['repeat']}".encode()
        ).hexdigest()[:12].upper()
        response_code = f"R-{digest}"
        allocation.append({"response_code": response_code, **response})
        blinded.append({
            "response_code": response_code,
            "event_id": response["event_id"],
            "response_text": response["answer"],
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
    blinded.sort(key=lambda row: row["response_code"])
    (args.output / "casebook_snapshot.json").write_text(
        json.dumps(approved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (args.output / "raw_responses.jsonl").open("w", encoding="utf-8") as handle:
        for row in responses:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    _write_csv(args.output / "allocation_key.csv", allocation, [
        "response_code", "event_id", "variant", "repeat", "provider", "model",
        "latency_ms", "answer",
    ])
    _write_csv(args.output / "blind_expert_review.csv", blinded, list(blinded[0]))
    (args.output / "collection_errors.json").write_text(
        json.dumps(errors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": 1,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "source": "HIAD 2.2",
        "split": args.split,
        "casebook_sha256": hashlib.sha256(
            args.approved_casebook.read_bytes()
        ).hexdigest(),
        "case_ids": [str(case["event_id"]) for case in cases],
        "prompt": PROMPT,
        "prompt_sha256": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
        "provider_requested": args.provider,
        "endpoint": endpoint,
        "language": "en",
        "max_tokens": 1200,
        "repeats": args.repeats,
        "timeout_s": args.timeout_s,
        "response_count": len(responses),
        "failed_call_count": len(errors),
    }
    (args.output / "collection_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output / "blind_expert_review.csv")
    if errors:
        raise SystemExit(f"Collection completed with {len(errors)} failed SAGA calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
