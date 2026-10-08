"""Generate compact protocol and SAGA-linkage tables for a research report.

The default run executes one real simulator fill and an alarm-only baseline.  If
SAGA-PY is running, add ``--saga-url http://127.0.0.1:8090`` to collect the live
LLM-assisted rows under exactly the same fixed cases.  No API key is read or
written by this script; SAGA owns its provider configuration.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import mean, pstdev
import subprocess
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from h2station.api import ProcessSettings
from h2station.operations import ProcessRuntime
from h2station.research_evaluation import (
    DecisionSupportRubric,
    audit_fueling_protocol,
    score_decision_support,
)
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


DECISION_CASES = (
    {
        "id": "DS-LEAK-01",
        "question": (
            "현재 사고를 종합해 관리자가 실행할 행동을 사고판단, 즉시조치, "
            "안정화확인, 예방관리 순서로 간결하게 작성해줘."
        ),
        "context": {
            "station_status": "CRITICAL",
            "active_alerts": [{
                "sensor_id": "GD-0901", "equipment": "고압 저장 뱅크",
                "value": 2.0, "unit": "vol%_H2", "hazard": "수소 누출",
            }],
            "impact_results": [{
                "equipment": "고압 저장 뱅크", "maximum_overpressure_kpa": 12.4,
                "maximum_heat_flux_kw_m2": 5.8, "effect_distance_m": 5.5,
                "calculation_status": "calculated",
            }],
            "recommended_actions": [
                "충전·공급 중지", "해당 뱅크 상류 차단", "영향구역 출입 통제 및 인원 대피",
                "가스 농도 감소 확인", "복구 전 기밀시험",
            ],
        },
        "baseline": "GD-0901 수소 누출 경보: 2.0 vol%_H2.",
        "rubric": DecisionSupportRubric(
            case_id="DS-LEAK-01",
            situation_concepts=(("수소 누출", "가스 농도"), ("고압 저장", "GD-0901")),
            ordered_action_concepts=(
                ("충전 중지", "공급 중지", "충전·공급 중지", "공급을 중지"),
                ("상류 차단", "뱅크 차단", "상류를 차단"),
                ("출입 통제", "인원 대피", "출입을 통제"),
                ("농도 감소", "안정화 확인", "농도가 기준 이하"),
            ),
            prevention_concepts=(("기밀시험", "누설시험"),),
            impact_concepts=(("5.5 m", "5.5m"), ("12.4 kPa", "12.4kPa")),
        ),
    },
    {
        "id": "DS-OVERHEAT-01",
        "question": (
            "차량 충전 중 과열 상황을 종합해 즉시조치, 재가동 조건, 예방관리 순서로 작성해줘."
        ),
        "context": {
            "station_status": "ALARM",
            "active_alerts": [{
                "sensor_id": "TT-1401", "equipment": "차량 1 탱크",
                "value": 85.0, "unit": "°C", "hazard": "충전 중 과열",
            }],
            "impact_results": [],
            "recommended_actions": [
                "차량 1 충전 정지", "충전밸브 차단 확인", "탱크 온도와 압력 안정화 확인",
                "프리쿨러 및 온도센서 기능시험 후 재가동 승인",
            ],
        },
        "baseline": "TT-1401 차량 온도 경보: 85.0 °C.",
        "rubric": DecisionSupportRubric(
            case_id="DS-OVERHEAT-01",
            situation_concepts=(("과열", "온도 경보", "탱크 온도"), ("차량 1", "TT-1401")),
            ordered_action_concepts=(
                ("충전 정지", "충전을 정지", "충전 중단"),
                ("밸브 차단", "밸브를 차단"),
                ("안정화 확인", "안정화되", "안정화된"),
                ("재가동 승인", "재가동이 승인", "재가동 전"),
            ),
            prevention_concepts=(("프리쿨러",), ("온도센서", "온도 센서")),
        ),
    },
)


def _post_json(url: str, payload: dict, timeout_s: float) -> tuple[dict, float]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = perf_counter()
    with urlopen(request, timeout=timeout_s) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body, (perf_counter() - started) * 1000.0


def run_protocol_case(duration_s: float, control_period_s: float) -> dict:
    config = ReferenceScenario(duration_s=duration_s, control_period_s=control_period_s)
    built = build_reference_scenario(config, UnavailableHyRAMBackend())
    built.simulator.process_runtime = ProcessRuntime(
        ProcessSettings(vehicle_1=True).model_dump()
    )
    trajectory = built.simulator.simulate(
        built.initial_state, duration_s, control_period_s, pace_idle=False
    )
    commands = trajectory.fueling_commands
    completion = next((
        command.stop_reason for command in commands
        if command.stop_reason in {"target-pressure", "target-soc", "gas-temperature-limit"}
    ), None)
    audit = audit_fueling_protocol(
        case_id="PT-03-DEFAULT-H70",
        schedule=built.station.partial_station.controller.schedule,
        time_s=trajectory.time_s,
        pressure_pa=trajectory.vehicle_pressure_pa,
        reference_pressure_pa=[command.reference_pressure_pa for command in commands],
        gas_temperature_k=trajectory.vehicle_temperature_k,
        mass_flow_kg_s=trajectory.nozzle_1_mass_flow_kg_s,
        soc=[command.state_of_charge for command in commands],
        completion_reason=completion,
    )
    return audit.to_dict()


def run_decision_cases(
    saga_url: str | None, provider: str, timeout_s: float, repeats: int,
) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    errors: list[str] = []
    endpoint = saga_url.rstrip("/") + "/api/integrations/digital-twin/main" if saga_url else None
    for case in DECISION_CASES:
        # The compact baseline verbalizes the same structured value/unit pair;
        # include it so JSON field separation is not mistaken for fabrication.
        evidence = (
            json.dumps(case["context"], ensure_ascii=False, sort_keys=True)
            + "\n" + case["baseline"] + "\n" + _verbalized_evidence(case["context"])
        )
        baseline = score_decision_support(
            answer=case["baseline"], allowed_evidence=evidence,
            rubric=case["rubric"], variant="alarm-only", latency_ms=0.0,
            provider="deterministic", model="alarm-only", repeat_index=1,
        )
        rows.append(baseline.to_dict())
        if endpoint is None:
            continue
        for repeat_index in range(1, repeats + 1):
            try:
                response, latency = _post_json(endpoint, {
                    "question": case["question"], "context": case["context"],
                    "history": [], "request_kind": "user_query", "provider": provider,
                    "language": "ko", "max_tokens": 1000,
                }, timeout_s)
                answer = str(response.get("answer") or "")
                rows.append(score_decision_support(
                    answer=answer,
                    allowed_evidence=evidence + "\n" + case["question"],
                    rubric=case["rubric"], variant="saga-linked", latency_ms=latency,
                    provider=str(response.get("provider") or provider),
                    model=str(response.get("model") or ""), repeat_index=repeat_index,
                ).to_dict())
            except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{case['id']} repeat {repeat_index}: {type(exc).__name__}: {exc}")
    return rows, errors


def _verbalized_evidence(context: dict) -> str:
    """Join structured value/unit pairs for numeric-claim comparison."""

    parts: list[str] = []
    for alert in context.get("active_alerts", []):
        if "value" in alert and alert.get("unit"):
            parts.append(f"{alert['value']} {alert['unit']}")
    for impact in context.get("impact_results", []):
        for key, unit in (
            ("maximum_overpressure_kpa", "kPa"),
            ("maximum_heat_flux_kw_m2", "kW/m2"),
            ("effect_distance_m", "m"),
        ):
            if key in impact:
                parts.append(f"{impact[key]} {unit}")
    return "; ".join(parts)


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _git_state(path: Path) -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=path, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "status", "--porcelain"], cwd=path, check=True,
            capture_output=True, text=True,
        ).stdout.strip())
        return {"repository": path.resolve().name, "commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"repository": path.resolve().name, "commit": "unavailable", "dirty": None}


def _case_manifest() -> dict:
    """Freeze the visible cases and keyword rubric used by a result file."""

    cases = [{
        "id": case["id"],
        "question": case["question"],
        "context": case["context"],
        "baseline": case["baseline"],
        "rubric": asdict(case["rubric"]),
    } for case in DECISION_CASES]
    canonical = json.dumps(cases, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "version": "2026-10-08.2",
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "cases": cases,
        "boundary": (
            "Transparent keyword-concept development rubric; not an expert rating, "
            "human-factors result, field-safety result, or regulatory compliance test."
        ),
    }


def _write_markdown(path: Path, report: dict) -> None:
    protocol = report["protocol"]
    lines = [
        "# Digital-twin paper evaluation",
        "",
        f"Generated: {report['generated_at']}",
        f"Digital twin commit: `{report['source']['digital_twin']['commit']}` (dirty={report['source']['digital_twin']['dirty']})  ",
        f"SAGA-PY commit: `{report['source']['saga_py']['commit']}` (dirty={report['source']['saga_py']['dirty']})  ",
        f"Provider: `{report['source']['provider']}`; requested repeats: {report['source']['requested_repeats']}",
        f"Case/rubric manifest: `{report['evaluation_protocol']['version']}` / "
        f"`{report['evaluation_protocol']['sha256']}`",
        "",
        "## Fueling schedule-boundary audit",
        "",
        "| Case | Boundary pass | APRR scheduled / observed | Tracking RMSE | Peak temperature | Peak flow | Final pressure / SOC | SOC target | Stop |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
        (f"| {protocol['case_id']} | {protocol['protocol_boundary_pass']} | "
         f"{protocol['scheduled_aprr_mpa_min']:.2f} / {protocol['observed_aprr_mpa_min']:.2f} MPa/min | "
         f"{protocol['pressure_tracking_rmse_mpa']:.3f} MPa | "
         f"{protocol['peak_gas_temperature_c']:.2f} °C | "
         f"{protocol['peak_mass_flow_g_s']:.2f} g/s | "
         f"{protocol['final_pressure_mpa']:.2f} MPa / {protocol['final_soc_percent']:.1f}% | "
         f"{protocol['soc_target_pass']} ({protocol['soc_shortfall_percent']:.1f}%p short) | "
         f"{protocol['completion_reason']} |"),
        "",
        f"> Scope: {protocol['scope']}",
        "",
        "## Decision-support A/B evaluation",
        "",
        "| Case | Variant | N | Score mean ± SD | Score range | Latency mean | Unsupported-number runs |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["decision_summary"]:
        lines.append(
            f"| {row['case_id']} | {row['variant']} | {row['n']} | "
            f"{row['score_mean']:.1f} ± {row['score_sd']:.1f} | "
            f"{row['score_min']:.1f}–{row['score_max']:.1f} | "
            f"{row['latency_mean_ms']:.0f} ms | {row['unsupported_run_count']} |"
        )
    lines.extend([
        "",
        "| Case | Variant | Model | Run | Score | Situation | Actions | Order | Prevention | Impact | Unsupported numbers | Latency |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ])
    for row in report["decision_support"]:
        unsupported = ", ".join(row["unsupported_numeric_claims"]) or "—"
        latency = "—" if row["latency_ms"] is None else f"{row['latency_ms']:.0f} ms"
        lines.append(
            f"| {row['case_id']} | {row['variant']} | {row['model'] or '—'} | {row['repeat_index']} | {row['score']:.1f} | "
            f"{row['situation_coverage']:.2f} | {row['action_coverage']:.2f} | "
            f"{row['action_order']:.2f} | {row['prevention_coverage']:.2f} | "
            f"{row['impact_coverage']:.2f} | {unsupported} | {latency} |"
        )
    if report["errors"]:
        lines.extend(["", "## Collection errors", ""] + [f"- {item}" for item in report["errors"]])
    lines.extend([
        "",
        "The rubric is deterministic and keyword-concept based. Report the model, provider, prompt, "
        "source commit and repeated-run distribution with any paper result. A unit-test pass or this "
        "table alone is not evidence of field safety or regulatory compliance.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _decision_summary(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        grouped.setdefault((row["case_id"], row["variant"]), []).append(row)
    summary = []
    for (case_id, variant), group in sorted(grouped.items()):
        scores = [float(row["score"]) for row in group]
        latencies = [float(row["latency_ms"]) for row in group if row["latency_ms"] is not None]
        summary.append({
            "case_id": case_id,
            "variant": variant,
            "n": len(group),
            "score_mean": mean(scores),
            "score_sd": pstdev(scores),
            "score_min": min(scores),
            "score_max": max(scores),
            "latency_mean_ms": mean(latencies) if latencies else 0.0,
            "unsupported_run_count": sum(bool(row["unsupported_numeric_claims"]) for row in group),
        })
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--saga-url", default=None, help="Running SAGA-PY base URL")
    parser.add_argument("--provider", choices=("service_hub", "groq"), default="groq")
    parser.add_argument("--timeout-s", type=float, default=90.0)
    parser.add_argument("--repeats", type=int, default=1, choices=range(1, 31))
    parser.add_argument("--duration-s", type=float, default=360.0)
    parser.add_argument("--control-period-s", type=float, default=1.0)
    parser.add_argument("--output-dir", type=Path, default=Path("data/paper_evaluation"))
    parser.add_argument("--saga-repo", type=Path, default=Path("../saga-system"))
    parser.add_argument("--require-saga", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    protocol = run_protocol_case(args.duration_s, args.control_period_s)
    decision_rows, errors = run_decision_cases(
        args.saga_url, args.provider, args.timeout_s, args.repeats
    )
    if args.require_saga and (errors or not any(row["variant"] == "saga-linked" for row in decision_rows)):
        raise SystemExit("SAGA-linked rows were required but could not be collected: " + "; ".join(errors))
    report = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "digital_twin": _git_state(Path.cwd()),
            "saga_py": _git_state(args.saga_repo),
            "provider": args.provider if args.saga_url else "not-run",
            "requested_repeats": args.repeats,
        },
        "evaluation_protocol": _case_manifest(),
        "protocol": protocol,
        "decision_support": decision_rows,
        "decision_summary": _decision_summary(decision_rows),
        "errors": errors,
    }
    (args.output_dir / "evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_csv(args.output_dir / "decision_support.csv", decision_rows)
    _write_markdown(args.output_dir / "report.md", report)
    print(args.output_dir / "report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
