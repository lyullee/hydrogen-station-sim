"""Deterministic, source-linked emergency guidance for the station monitor.

The catalogue is operator decision support. It never actuates the station and
does not replace the site's approved emergency response plan.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any


PLAYBOOK_PATH = Path(__file__).resolve().parents[1] / "data" / "emergency_playbooks.json"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
KHK_PRECEDENT_MAP_PATH = REPOSITORY_ROOT / "research" / "khk_scenario_precedent_map_2026_10_04.json"
EQUIPMENT_LABELS = {
    "cascade.low": "저압 저장뱅크", "cascade.medium": "중압 저장뱅크",
    "cascade.high": "고압 저장뱅크", "low": "저압 저장뱅크",
    "medium": "중압 저장뱅크", "high": "고압 저장뱅크",
    "hose_1": "1번 충전호스", "hose_2": "2번 충전호스",
    "vehicle_1": "차량 1 탱크", "vehicle_2": "차량 2 탱크",
    "compressor": "압축기", "precooler": "예냉기",
    "header": "공통 헤더", "supply": "트레일러 공급부",
    "station": "충전소 전체",
}

RESPONSE_STAGES = ("recognition", "immediate", "stabilize", "restart", "prevention")


def response_guidance_contract_issues(guidance: dict[str, Any] | None) -> list[str]:
    """Return missing safety-response fields before guidance reaches the UI.

    This is a structural guard only.  It checks that the deterministic plan
    contains the five staged response sections and traceable source metadata;
    it does not judge whether an individual action is safe for a real site or
    prove SAGA/operator effectiveness.
    """

    if not isinstance(guidance, dict):
        return ["guidance must be an object"]
    issues: list[str] = []
    plans = guidance.get("plans")
    if not isinstance(plans, list) or not plans:
        issues.append("plans must be a non-empty list")
        return issues
    if guidance.get("actual_alert") and not guidance.get("common_steps"):
        issues.append("active alerts require common_steps")
    for index, plan in enumerate(plans):
        prefix = f"plans[{index}]"
        if not isinstance(plan, dict):
            issues.append(f"{prefix} must be an object")
            continue
        if not str(plan.get("title") or "").strip():
            issues.append(f"{prefix}.title is empty")
        for stage in RESPONSE_STAGES:
            values = plan.get(stage)
            if not isinstance(values, list) or not any(str(value).strip() for value in values):
                issues.append(f"{prefix}.{stage} is empty")
        sources = plan.get("sources")
        if not isinstance(sources, list) or not sources:
            issues.append(f"{prefix}.sources is empty")
        else:
            for source_index, source in enumerate(sources):
                if not isinstance(source, dict) or not str(source.get("url") or "").startswith("https://"):
                    issues.append(f"{prefix}.sources[{source_index}] is not traceable")
    return issues


def _equipment_label(target: Any) -> str:
    text = str(target or "위치 확인 중")
    return EQUIPMENT_LABELS.get(text, text)


@lru_cache(maxsize=1)
def load_playbooks() -> dict[str, Any]:
    data = json.loads(PLAYBOOK_PATH.read_text(encoding="utf-8"))
    required = {"recognition", "immediate", "stabilize", "restart", "prevention", "sources"}
    for plan in data["plans"]:
        if not required.issubset(plan) or not all(plan[key] for key in required):
            raise ValueError(f"Incomplete emergency playbook: {plan.get('id')}")
        if any(source not in data["sources"] for source in plan["sources"]):
            raise ValueError(f"Unknown emergency source: {plan['id']}")
    return data


@lru_cache(maxsize=1)
def _public_accident_precedent_catalog() -> dict[str, Any]:
    """Load the citation-only KHK map after checking its source digest.

    Titles, equipment classes and links are already public metadata.  Report
    prose is not loaded.  Returning an empty catalogue on any integrity error
    keeps emergency guidance available without silently citing stale evidence.
    """

    empty = {"by_plan": {}, "representative_by_plan": {}, "source_page": None}
    try:
        record = json.loads(KHK_PRECEDENT_MAP_PATH.read_text(encoding="utf-8"))
        source = record.get("source_inventory") or {}
        inventory_path = REPOSITORY_ROOT / str(source.get("path") or "")
        if (
            record.get("status") != "citation_only_khk_scenario_precedent_map"
            or not inventory_path.is_file()
            or sha256(inventory_path.read_bytes()).hexdigest() != source.get("sha256")
        ):
            return empty
        cases = record.get("cases") or []
        if not isinstance(cases, list) or len(cases) != source.get("incident_report_count"):
            return empty
        known_plans = {plan["id"] for plan in load_playbooks()["plans"]}
        by_plan: dict[str, list[dict[str, Any]]] = {}
        case_index: dict[tuple[tuple[str, ...], str], dict[str, Any]] = {}
        for raw in cases:
            if not isinstance(raw, dict):
                return empty
            plan_ids = raw.get("playbook_ids") or []
            codes = tuple(str(value) for value in raw.get("incident_codes") or [] if value)
            url = str(raw.get("url") or "")
            if not codes or not url.startswith("https://") or any(plan_id not in known_plans for plan_id in plan_ids):
                return empty
            item = {
                "incident_codes": list(codes),
                "title": str(raw.get("title") or ""),
                "equipment_class": str(raw.get("equipment_class") or ""),
                "url": url,
            }
            case_index[(codes, url)] = item
            for plan_id in plan_ids:
                by_plan.setdefault(str(plan_id), []).append(item)

        mapping = record.get("mapping") or {}
        representatives = mapping.get("representative_precedents") or {}
        representative_by_plan: dict[str, list[dict[str, Any]]] = {}
        for plan_id, rows in representatives.items():
            if plan_id not in known_plans or not isinstance(rows, list):
                return empty
            for row in rows:
                if not isinstance(row, dict):
                    return empty
                key = (
                    tuple(str(value) for value in row.get("incident_codes") or [] if value),
                    str(row.get("url") or ""),
                )
                item = case_index.get(key)
                if item is None or item not in by_plan.get(plan_id, []):
                    return empty
                representative_by_plan.setdefault(plan_id, []).append(item)
        return {
            "by_plan": by_plan,
            "representative_by_plan": representative_by_plan,
            "source_page": source.get("source_page"),
        }
    except (OSError, ValueError, TypeError):
        return empty


def public_accident_precedents(
    plan_id: str,
    limit: int | None = 2,
    *,
    representative: bool = True,
) -> list[dict[str, Any]]:
    """Return public KHK precedents relevant to one response family."""

    catalog = _public_accident_precedent_catalog()
    rows = (
        catalog["representative_by_plan"].get(plan_id)
        if representative else catalog["by_plan"].get(plan_id)
    ) or []
    selected = rows if limit is None else rows[:max(0, limit)]
    return [dict(row) for row in selected]


def classify_rule(rule: dict[str, Any]) -> str:
    """Map each sensor rule to a response family; specific signals win first."""
    name = str(rule.get("시나리오명") or "")
    node = str(rule.get("node_id") or "")
    sensor = str(rule.get("sensor_id") or "")
    if sensor.startswith("FD-"):
        return "external_fire"
    if "데이터 갱신 지연" in name or "센서" in name and "고착" in name:
        return "sensor_fault"
    if sensor.startswith("GD-") or any(term in name for term in
        ("등온보정 압력 감소", "유출 지속", "급감압", "질량손실", "대량 유량 불일치")):
        return "gas_release"
    if any(term in name for term in ("폐쇄 후 유량", "ESD 후 유량")):
        return "isolation_failure"
    if node == "N20":
        return "vent_fault"
    if "외부가열" in name:
        return "external_fire"
    if node in {"N14", "N18"}:
        return "fueling_fault"
    if "분리 전 잔압" in name or "압력 비정상 역전" in name:
        return "hose_connection"
    if node in {"N12", "N16", "N19"}:
        return "precooling_fault"
    if any(term in name for term in ("과압", "목표 초과", "운전상한 도달", "토출 압력 접근")):
        return "overpressure" if node not in {"N11", "N13", "N15", "N17"} else "fueling_fault"
    if node in {"N04", "N05", "N06"} and any(term in name for term in
        ("고온", "과열", "냉각 후 온도", "압력 상승 부족")):
        return "compressor_thermal"
    if node in {"N13", "N17"} and any(term in name for term in ("고온", "저온")):
        return "fueling_fault"
    if any(term in name for term in ("역류", "과유량", "유량 초과", "수지 잔차", "유량 불일치")):
        return "flow_anomaly"
    if any(term in name for term in ("무유량", "저압", "부족", "막힘", "차압 증가")):
        return "low_supply_or_blockage"
    if node in {"N01", "N02"}:
        return "supply_connection"
    if node in {"N03", "N04", "N05", "N06"}:
        return "compressor_thermal"
    if node in {"N11", "N13", "N15", "N17"}:
        return "fueling_fault"
    if node in {"N07", "N08", "N09", "N10"}:
        return "overpressure"
    return "gas_release" if node in {"N21", "N22", "N23"} else "sensor_fault"


def response_selection(frame: dict[str, Any], catalog: dict[str, Any],
                       question: str = "", trigger: str = "manual", limit: int | None = None) -> list[dict[str, Any]]:
    """Choose active-event playbooks, or explicit hypothetical user requests."""
    data = load_playbooks()
    plans = {plan["id"]: plan for plan in data["plans"]}
    hazop = frame.get("hazop") or {}
    active = hazop.get("active") or []
    rules = {str(rule["rule_id"]): rule for rule in catalog["rules"]}
    selected: dict[str, dict[str, Any]] = {}

    def add(plan_id: str, evidence: str, bonus: int = 0,
            rule: dict[str, Any] | None = None) -> None:
        if plan_id not in plans:
            return
        key = f"rule:{rule['rule_id']}" if rule else plan_id
        if key not in selected:
            plan = dict(plans[plan_id])
            if rule:
                plan["title"] = rule["시나리오명"]
                plan["rule_id"] = rule["rule_id"]
                plan["sensor_id"] = rule["sensor_id"]
                stages = rule.get("비상대응_단계") or {}
                for stage in ("recognition", "immediate", "stabilize", "restart", "prevention"):
                    if stages.get(stage):
                        plan[stage] = list(stages[stage])
                plan["sources"] = rule.get("대응근거_출처") or plan["sources"]
            selected[key] = {"plan": plan, "evidence": [], "score": plans[plan_id]["priority"]}
        entry = selected[key]
        entry["score"] = max(entry["score"], plans[plan_id]["priority"] + bonus)
        if evidence and evidence not in entry["evidence"] and len(entry["evidence"]) < 4:
            entry["evidence"].append(evidence)

    for item in active:
        if not isinstance(item, dict):
            continue
        rule = rules.get(str(item.get("rule_id")))
        if rule:
            value = item.get("value")
            measured = f"판정값 {value:g} {rule['단위']} · " if isinstance(value, (int, float)) else ""
            threshold = f"기준 {rule['연산자']} {rule['임계값']} {rule['단위']}"
            add(classify_rule(rule), f"{rule['node_id']} {rule['sensor_id']} · {measured}{threshold} · {rule['시나리오명']}",
                15 if rule.get("등급") == "TRIP" else 0, rule=rule)
    for release in hazop.get("releases") or []:
        if isinstance(release, dict):
            component = _equipment_label(release.get("component_id"))
            consequence = release.get("consequence") or {}
            # A hydrogen leak may be ignited without an external-fire fault.
            # The consequence engine is the authoritative runtime signal for
            # this distinction, so route the event to the dedicated fire plan
            # while retaining the underlying release plan as a separate
            # scenario.  This keeps the LLM/SAGA handoff faithful to the
            # physical event instead of describing a jet fire as an unignited
            # leak only.
            # ``visible_flame_length_m`` and the literature jet-flame fields
            # are calculated as delayed-ignition screening outputs for an
            # unignited release too.  They are therefore not ignition state.
            # Only an explicit ignition flag or the enclosure ignition result
            # may promote a release to the hydrogen-fire plan.
            ignited = (
                consequence.get("ignited") is True
                or consequence.get("ignited_enclosure_status") == "calculated"
            )
            if ignited:
                add("hydrogen_fire", f"점화된 수소 방출: {component}", 40)
            add("gas_release", f"현재 누출: {component}", 35)
    for valve in frame.get("relief_valves_open") or []:
        add("relief_discharge", f"안전밸브 개방: {_equipment_label(valve)}", 25)
    for fault in frame.get("active_faults") or []:
        fault = str(fault)
        kind = fault.split(":", 1)[0]
        plan_id = {"external-fire": "external_fire", "hydrogen-leak": "gas_release",
                   "hydrogen-fire": "hydrogen_fire", "ignited-hydrogen-leak": "hydrogen_fire",
                   "sensor-freeze": "sensor_fault",
                   "sensor-bias": "sensor_fault", "precooler-loss": "precooling_fault",
                   "check-valve-failure": "flow_anomaly",
                   "pipe-restriction": "low_supply_or_blockage", "pcv-stuck-open": "fueling_fault",
                   "pcv-seat-leak": "fueling_fault",
                   "pcv-stuck-closed": "low_supply_or_blockage",
                   "cascade-valve-stuck-open": "overpressure", "cascade-valve-stuck-closed": "low_supply_or_blockage",
                   }.get(kind)
        if plan_id:
            kind_labels = {"external-fire": "외부 화재", "hydrogen-leak": "수소 누출",
                           "sensor-freeze": "센서 고착", "sensor-bias": "센서 편차",
                           "precooler-loss": "예냉 성능 저하", "compressor-trip": "압축기 정지",
                           "emergency-stop": "비상 차단", "pressure-disturbance": "압력 이상",
                           "temperature-disturbance": "온도 이상"}
            target = fault.split(":", 1)[1] if ":" in fault else "위치 확인 중"
            add(plan_id, f"사고 입력: {_equipment_label(target)} · {kind_labels.get(kind, kind)}", 30)

    # Only an explicit manual question can ask for a hypothetical response while healthy.
    if trigger == "manual" and question:
        q = re.sub(r"\s+", "", question)
        questions = {
            "hydrogen_fire": ("수소화재", "제트화재", "분출화재", "화염"),
            "external_fire": ("외부화재", "인접화재", "외부가열"),
            "gas_release": ("누출", "가스검지", "가스감지"),
            "relief_discharge": ("안전밸브", "릴리프", "방출밸브"),
            "overpressure": ("과압", "과충전", "과대저장"),
            "fueling_fault": ("차량충전", "충전중단", "급가압"),
            "hose_connection": ("호스", "노즐", "커플러", "하역연결"),
            "compressor_thermal": ("압축기", "단간냉각"),
            "precooling_fault": ("예냉", "프리쿨", "HTF"),
            "flow_anomaly": ("역류", "유량불일치", "과유량"),
            "low_supply_or_blockage": ("무유량", "공급부족", "막힘"),
            "vent_fault": ("벤트", "배압"),
            "sensor_fault": ("센서장애", "계측장애", "신호고착"),
            "isolation_failure": ("차단실패", "ESD후유량", "밸브고착"),
            "supply_connection": ("트레일러", "수소공급", "하역"),
        }
        for plan_id, terms in questions.items():
            if any(term.lower() in q.lower() for term in terms):
                add(plan_id, "운전자 질의에 따른 가상 상황", 4)
    ordered = sorted(selected.values(), key=lambda item: item["score"], reverse=True)
    return ordered if limit is None else ordered[:limit]


def prompt_guidance(selection: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Send only the first decision steps to a provider prompt.

    The API appends the complete staged response plan after the LLM's focused
    explanation.  Duplicating all five stages for as many as six situations
    bloats a direct-answer prompt and makes the model repeat a generic
    procedure instead of answering the operator's question.  Keep the trusted
    evidence and the first immediate/stabilization actions here; retain the
    full plan in :func:`render_guidance` and :func:`structured_guidance`.
    """
    result = []
    for item in selection[:4]:
        plan = item["plan"]
        result.append({
            "situation": plan["title"],
            "evidence": item["evidence"][:2],
            "immediate": plan["immediate"][:2],
            "stabilize": plan["stabilize"][:1],
            "public_accident_precedents": public_accident_precedents(plan["id"]),
            "precedent_claim_limit": (
                "유사 실제사고의 정성적 선례이며 현재 사고의 원인·확률·결과를 확정하지 않음"
            ),
            "full_plan_delivered_separately": True,
        })
    return result


def render_guidance(selection: list[dict[str, Any]], *, actual_alert: bool) -> str:
    if not selection:
        return ""
    data = load_playbooks()
    sections = ["### 상황별 긴급대응·안전관리", "현장 승인 비상계획과 현장 지휘를 우선하세요. 아래는 시뮬레이션 신호에 기반한 의사결정 지원입니다."]
    if actual_alert:
        sections.append("**공통 초기 대응**\n" + "\n".join(f"- {step}" for step in data["common_response"]))
    for item in selection:
        plan = item["plan"]
        parts = [f"#### {plan['title']}"]
        if item["evidence"]:
            parts.append("근거: " + "; ".join(item["evidence"]))
        for label, key in (("확인할 신호", "recognition"), ("즉시 조치", "immediate"),
                           ("안정화 확인", "stabilize"), ("재가동 전 조건", "restart"),
                           ("예방·안전관리", "prevention")):
            parts.append(f"**{label}**\n" + "\n".join(f"- {step}" for step in plan[key]))
        sources = [data["sources"][key] for key in plan["sources"]]
        parts.append("근거 자료: " + ", ".join(f"[{source['title']}]({source['url']})" for source in sources))
        precedents = public_accident_precedents(plan["id"])
        if precedents:
            parts.append(
                "공개 실제사고 선례(정성 근거): "
                + ", ".join(
                    f"[{row['title']} ({'/'.join(row['incident_codes'])})]({row['url']})"
                    for row in precedents
                )
                + ". 현재 사고의 원인·확률·결과를 확정하는 근거는 아닙니다."
            )
        sections.append("\n\n".join(parts))
    return "\n\n".join(sections)


def structured_guidance(selection: list[dict[str, Any]], *, actual_alert: bool) -> dict[str, Any] | None:
    """Machine-readable stages for the SAGA chat timeline."""
    if not selection:
        return None
    data = load_playbooks()
    from ..virtual_safety import suggested_actions
    def _node_id(sensor_id: str | None) -> str | None:
        match = re.search(r"-(\d\d)\d\d$", sensor_id or "")
        return f"N{match.group(1)}" if match else None
    guidance = {
        "actual_alert": actual_alert,
        "intro": "현장 승인 비상계획과 현장 지휘를 우선하세요. 시뮬레이션 기반 의사결정 지원입니다.",
        "common_steps": list(data["common_response"]) if actual_alert else [],
        "plans": [{
            "id": item["plan"]["id"], "title": item["plan"]["title"],
            "rule_id": item["plan"].get("rule_id"), "sensor_id": item["plan"].get("sensor_id"),
            "evidence": list(item["evidence"]),
            "executable_actions": suggested_actions(item["plan"]["id"],
                                                    _node_id(item["plan"].get("sensor_id"))) if actual_alert else [],
            **{stage: list(item["plan"][stage]) for stage in
               ("recognition", "immediate", "stabilize", "restart", "prevention")},
            "sources": [data["sources"][key] for key in item["plan"]["sources"]],
            "public_accident_precedents": public_accident_precedents(item["plan"]["id"]),
            "precedent_claim_limit": (
                "유사 실제사고의 정성적 선례이며 현재 사고의 원인·확률·결과를 확정하지 않음"
            ),
        } for item in selection],
    }
    issues = response_guidance_contract_issues(guidance)
    if issues:
        # A missing stage is a software defect, not a reason to silently show
        # an incomplete emergency plan.  Keep the failure explicit so tests
        # and operators can identify the broken plan/source mapping.
        raise RuntimeError("response guidance contract violation: " + "; ".join(issues))
    return guidance
