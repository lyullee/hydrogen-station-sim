"""Idempotently extend the packaged HAZOP catalog with virtual flame heads.

The reference XLSX predates these heads. Keep this migration as the explicit
source of the extension rather than silently rewriting the source workbook.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date

from h2station.hazop.database import DEFAULT_DB
from h2station.hazop.flame import FLAME_DETECTORS
from h2station.hazop.mapping import mapping_catalog
from h2station.hazop.response import classify_rule, load_playbooks
from h2station.hazop.scenario_actions import build_rule_guidance


def put(db: sqlite3.Connection, table: str, key: str, payload: dict) -> None:
    db.execute(f"INSERT OR REPLACE INTO {table} VALUES (?, ?)",
               (key, json.dumps(payload, ensure_ascii=False)))


def get(db: sqlite3.Connection, table: str, key: str) -> dict:
    row = db.execute(f"SELECT payload FROM {table} WHERE id=?", (key,)).fetchone()
    if row is None:
        raise KeyError(f"{table}: {key}")
    return json.loads(row[0])


def main() -> None:
    plans = {plan["id"]: plan for plan in load_playbooks()["plans"]}
    with sqlite3.connect(DEFAULT_DB, timeout=20) as db:
        has_response_table = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='response_actions'").fetchone() is not None
        source = get(db, "sources", "SRC14")
        source.update({
            "source_id": "SRC_FLAME",
            "기준명": "H2Tools 수소 화염검지 권고 · 시뮬레이션 확장",
            "출처": "https://h2tools.org/bestpractices/hydrogen-properties-and-leak-detection-considerations/flame-detection; "
                  "https://h2tools.org/bestpractices/gaseous-gh2-and-liquid-hydrogen-lh2-fueling-stations",
            "적용범위": "트레일러·압축기·저장뱅크·디스펜서 등 구역별 가상 광학 화염검지. "
                       "현재 값은 주입 화재 위치와 모의 응답시간에서 계산하며 실제 검지기 실측 또는 시야 검증이 아님.",
            "확인일": str(date.today()),
        })
        put(db, "sources", "SRC_FLAME", source)
        template_rule = get(db, "rules", "HZ-153")
        for number, (tag, node, zone, targets) in enumerate(FLAME_DETECTORS, 206):
            sensor = get(db, "sensors", "GD-" + tag[3:])
            sensor.update({
                "sensor_id": tag, "node_id": node, "종류": "FD",
                "설치_측정위치": zone + " 화염검지 헤드", "단위": "bool",
                "SI_단위": "boolean", "SI_배율": 1.0, "SI_오프셋": 0.0,
                "계측상태": "시나리오 연동 가상 검지기 · 실물 센서 미연결",
                "제안_자동채널": None, "제안_DT_key": "hrs.fd." + tag[3:],
                "표본주기_s": 0.5, "최대데이터나이_s": 2.0,
                "품질조건": "GOOD + 유효 시각 + 구역 매핑",
                "source_id": "SRC_FLAME;ASM01",
                "비고": "주입 화재 대상과 모의 응답지연으로 계산. 화재 독립 검증이나 실제 광학 시야 범위를 뜻하지 않음. "
                        + ", ".join(targets),
            })
            put(db, "sensors", tag, sensor)
            rule = dict(template_rule)
            rule.update({
                "rule_id": f"HZ-{number:03d}", "node_id": node, "sensor_id": tag,
                "시나리오명": zone + " 화염검지 신호", "신호식": tag,
                "연산자": ">=", "임계값": 0.5, "단위": "bool",
                "지속_s": 0.0, "window_s": 0.0, "gate_id": "G_ANY",
                "복귀연산자": "<", "복귀값": 0.1, "복귀지속_s": 1.0,
                "등급": "TRIP", "래치": False, "분류": "화염검지",
                "원인후보": "해당 구역 화재 또는 광학 검지기 오동작",
                "사고_진전조건": "현장 화염 확인, 압력·온도 변화 및 가스검지와 교차 검증",
                "판단한계": "현재는 주입한 화재 사건으로부터 생성한 가상 신호. 독립적인 화염 실측이 아님.",
                "권고조치": "해당 구역 접근 제한과 현장 CCTV·온도·압력 확인, ESD 및 비상대응 절차 검토.",
                "HyRAM_case_id": None,
                "프롬프트_힌트": "화염검지 신호가 가상 시뮬레이션인지 실측인지 명시하고 주입 시나리오와 구분.",
                "추가데이터_요구": "실제 검지기 설치 시 광학 시야, 자기진단, 통신 품질",
                "기준구분": "REFERENCE_PLUS_PROPOSED", "source_id": "SRC_FLAME;ASM01",
                "설계해설": "모의 화염검지 임계값 0.5 bool. 응답지연은 런타임에서 별도 계산.",
                "현장활성화": False, "검토상태": "REVIEW_REQUIRED", "rule_version": "1.0",
            })
            guidance = build_rule_guidance(rule, zone, plans[classify_rule(rule)])
            rule["대응유형"] = guidance["plan_id"]
            rule["비상대응_단계"] = guidance["stages"]
            rule["안전관리_방안"] = guidance["stages"]["prevention"]
            rule["대응근거_출처"] = guidance["source_ids"]
            rule["대응검토상태"] = guidance["scope"]
            put(db, "rules", rule["rule_id"], rule)
            if has_response_table:
                db.execute("INSERT OR REPLACE INTO response_actions VALUES (?, ?)",
                           (rule["rule_id"], json.dumps(guidance, ensure_ascii=False)))
            mapping = mapping_catalog([sensor])[0]
            db.execute("INSERT OR REPLACE INTO mappings VALUES (?, ?)",
                       (tag, json.dumps(mapping, ensure_ascii=False)))
        db.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)",
                   ("flame_detector_extension", json.dumps("virtual-v1", ensure_ascii=False)))
    print(f"Added {len(FLAME_DETECTORS)} virtual flame detectors to {DEFAULT_DB}")


if __name__ == "__main__":
    main()
