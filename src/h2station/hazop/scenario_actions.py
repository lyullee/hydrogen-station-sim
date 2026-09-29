"""Build reviewed-for-simulation, rule-specific response rows for the HAZOP DB.

These are advisory checklists. They do not change sensor thresholds, actuate
equipment, specify a universal exclusion distance, or replace site procedures.
"""
from __future__ import annotations

from typing import Any


# Each family adds a concrete local action and a separate verification step to
# the source-linked common playbook. The rule's own signal and node are then
# bound into the final persisted row.
FOCUS: dict[str, dict[str, str]] = {
    "gas_release": {
        "immediate": "인접 충전·재충전 경로까지 압력·유량 변화를 확인해 공통 공급원이 남아 있는지 판단하고, 안전한 원격 차단점부터 격리한다.",
        "stabilize": "차단 전후 가스 농도, 상·하류 압력, 질량수지의 감소 방향을 각각 확인한다. 한 검지기만 정상화된 것을 누출 종료로 취급하지 않는다.",
        "restart": "수리 위치의 누설시험 결과와 해당 구역 가스검지·차단 인터록 시험 기록을 함께 승인한다.",
        "prevention": "검지기 배치의 사각지대와 캐비닛·캐노피 환기 경로를 정기 점검하고, 실제 검지기 교정 이력을 관리한다.",
    },
    "hydrogen_fire": {
        "immediate": "분출 방향과 노출 용기·차량·트레일러를 소방 지휘에 전달한다. 공급이 유지되는 화염은 독자적으로 진압하지 않는다.",
        "stabilize": "원격 차단 피드백과 압력 감소를 함께 보며 공급 차단 여부를 확인하고, 열화상·가스검지로 잔류 위험을 확인한다.",
        "restart": "열 노출 압력용기·호스·씰의 제작사 평가와 사고 원점 기밀시험이 끝나기 전에는 충전·재충전을 재개하지 않는다.",
        "prevention": "화염검지기 시야·차폐·오경보와 ESD 연동을 점검하고 소방 대응자와 설비 배치도를 공유한다.",
    },
    "external_fire": {
        "immediate": "외부 열원을 수소 누출·수소 화염과 구별하여 신고하고, 원격으로 열 노출 설비의 이송을 멈춘다.",
        "stabilize": "노출 설비의 온도·압력 상승률과 방출밸브 상태를 동시 추적한다. 모의 화염검지 신호를 현장 실측으로 오인하지 않는다.",
        "restart": "열에 노출된 용기·배관·계기의 손상 및 잔류 압력을 평가하고 제작사·현장 책임자 승인 후 복귀한다.",
        "prevention": "외부 화재하중·차량 동선·트레일러 주차 위치와 원격 차단 접근성을 합동 점검한다.",
    },
    "overpressure": {
        "immediate": "해당 저장·토출 경로의 추가 유입을 멈추고 압축기 운전, 재충전 선택 및 PCV 명령을 구분해 확인한다.",
        "stabilize": "독립 압력계와 온도 추세를 대조하고, 안전밸브 개방·채터링·벤트 배압을 동시에 감시한다.",
        "restart": "초과압력 원인을 제거한 뒤 관련 차단밸브와 안전밸브 설정·재폐쇄 시험 결과를 확인한다.",
        "prevention": "운전 목표, 독립 차단 상한 및 릴리프 설정 간 순서를 검토하고 상한 우회 운전을 기록·제한한다.",
    },
    "relief_discharge": {
        "immediate": "방출 방향의 출입과 차량 이동을 통제하고 개방 압력, 방출 유량, 원인 설비의 공급 상태를 확인한다.",
        "stabilize": "밸브 재폐쇄 여부와 반복 개폐 횟수, 벤트 배압 및 주변 가스·화염 신호를 추적한다.",
        "restart": "시트 누설, 설정압력, 방출 배관의 막힘·동결·역류를 검사하고 기록을 승인한다.",
        "prevention": "릴리프 사건 기록을 보존하고 개방·재폐쇄 설정의 검교정과 방출 동선·스택 상태를 정기 확인한다.",
    },
    "fueling_fault": {
        "immediate": "해당 차량 번호의 디스펜서만 즉시 중단하고 PCV 폐쇄·노즐 유량 0을 확인한다. 다른 차량 신호로 정상 판단하지 않는다.",
        "stabilize": "차량 탱크 압력·온도·SOC와 호스 압력, 예냉 출구 온도를 같은 시각 기준으로 대조한다.",
        "restart": "차량 통신·프로토콜·종료 로직과 PCV/차단밸브 기능을 검증하고 해당 차량의 재충전 허용을 별도 판단한다.",
        "prevention": "차량별 충전 한계, 상승률 및 예냉 성능을 독립 기록하며 자동 종료와 ESD 시험을 분리 수행한다.",
    },
    "hose_connection": {
        "immediate": "잔압이 남은 호스·커플러를 분리하지 말고 양단 차단 및 차량·트레일러 이동 통제를 확인한다.",
        "stabilize": "연결부·노즐·브레이크어웨이 주변의 가스검지와 호스 압력 감쇠를 추적한다.",
        "restart": "무압 확인 후 씰·커플러·브레이크어웨이·체크밸브를 검사하고 재연결 누설시험을 기록한다.",
        "prevention": "연결 전 접지·고정·호스 손상 점검과 분리 전 잔압 확인을 체크리스트로 관리한다.",
    },
    "compressor_thermal": {
        "immediate": "압축기 부하와 재충전을 정지하고 각 단 토출·중간냉각 신호와 캐비닛 가스검지를 함께 확인한다.",
        "stabilize": "정지 후 온도·압력 감소 추세와 팬·펌프·냉각수·윤활 상태를 단계별로 확인한다.",
        "restart": "이상 단의 씰·밸브·냉각기와 온도계 교정을 점검하고 저부하 시험 결과를 확인한다.",
        "prevention": "단별 토출온도·압력비·냉각 후 온도의 기준 추세를 기록하고 냉각 상실 연동 시험을 실시한다.",
    },
    "precooling_fault": {
        "immediate": "영향받는 충전 라인을 중지하고 출구 수소 온도, 차량 탱크 온도 및 HTF 순환 상태를 비교한다.",
        "stabilize": "펌프 유량, HTF 공급·환수 온도, 열교환기 차압과 냉매 상태를 확인한다.",
        "restart": "예냉 성능과 온도계 교정·차단 인터록을 시험한 뒤 제한된 시험 충전을 승인한다.",
        "prevention": "냉각 부족과 과냉각을 모두 감시하고 결빙·열교환기 막힘·공유 냉각 패키지 영향을 점검한다.",
    },
    "flow_anomaly": {
        "immediate": "유입·유출의 실제 흐름 방향을 확인하고 영향 경로를 정지한 뒤 체크밸브·PCV·차단밸브 피드백을 확인한다.",
        "stabilize": "저장량 변화와 상·하류 압력차로 역류·과유량·유량계 편향을 분리한다.",
        "restart": "밸브 누설·역류방지·유량계 교정을 확인하고 정상 방향의 시험 유량으로 복귀한다.",
        "prevention": "질량수지 경보와 체크밸브 기능시험을 계획하고 공유 헤더에서 다른 뱅크로 전달되는 경로를 검토한다.",
    },
    "low_supply_or_blockage": {
        "immediate": "운전 요청이 있는데 유량이 부족하면 공회전·반복 시동을 피하고 해당 압축·충전 경로를 정지한다.",
        "stabilize": "공급 잔량, 흡입 압력, 필터 차압, 밸브 개도와 계기 품질을 차례로 확인한다.",
        "restart": "막힘 제거 또는 공급 복구 후 상·하류 기밀과 제한 유량 시험을 확인한다.",
        "prevention": "트레일러 잔량 하한, 필터 교체주기와 공급 압력 저하 추세를 관리한다.",
    },
    "vent_fault": {
        "immediate": "방출 명령과 실제 벤트 유량이 다르면 연결 설비의 공급을 멈추고 방출구 접근을 통제한다.",
        "stabilize": "헤더 배압, 역류·동결·물 유입, 릴리프 개방 상태를 원격 신호로 확인한다.",
        "restart": "벤트 배관의 막힘·지지·역류방지와 방출밸브 기능시험을 승인한다.",
        "prevention": "벤트 출구 장애물, 응축·동결 및 배압 추세를 정기 점검한다.",
    },
    "sensor_fault": {
        "immediate": "계기 단독 이상으로 공정 사고를 단정하지 말고 대체 신호·현장 안전상태를 확인한다. 신호를 임의로 우회하지 않는다.",
        "stabilize": "갱신 시각, 품질 플래그, 전원·통신·교정 이력을 확인하고 동일 설비의 독립 계기와 비교한다.",
        "restart": "수리·교정 후 정상 신호 품질과 경보·차단 인터록의 기능시험 기록을 확인한다.",
        "prevention": "센서 고착·지연·편향 진단 시험과 결측 시 안전 상태 전환 로직을 주기적으로 검증한다.",
    },
    "isolation_failure": {
        "immediate": "차단 명령 후에도 유량이 남으면 해당 경로를 실제 격리 실패 가능성으로 취급하고 상위 원격 차단과 현장 접근 통제를 시행한다.",
        "stabilize": "명령·밸브 위치 피드백·유량·압력 감소를 각각 대조해 누설, 잔류 라인팩, 밸브 고착을 구분한다.",
        "restart": "차단밸브 시트 누설·구동부·피드백과 ESD 시험을 완료하기 전에는 해당 경로를 재가압하지 않는다.",
        "prevention": "차단 시간과 실제 유량 0 도달 시간을 분리 기록하고 안전기능 검증에 반영한다.",
    },
    "supply_connection": {
        "immediate": "트레일러 이송을 멈추고 양측 원격 차단, 차량 고정 및 하역구역 출입 통제를 확인한다.",
        "stabilize": "하역 호스·매니폴드 압력과 유량, 접지·연결 상태 및 가스검지기를 확인한다.",
        "restart": "트레일러·하역 호스의 무압·기밀·체크밸브·접지 상태를 확인한 뒤 재연결을 승인한다.",
        "prevention": "트레일러 진입·고정·출구 동선과 하역 전후 체크리스트 및 비상 차단 위치를 점검한다.",
    },
}


def build_rule_guidance(rule: dict[str, Any], node_name: str,
                        plan: dict[str, Any]) -> dict[str, Any]:
    """Return complete stages bound to one sensor threshold and one node."""
    tag = str(rule["sensor_id"])
    location = node_name or str(rule["node_id"])
    focus = FOCUS[plan["id"]]
    threshold = f"{rule['신호식']} {rule['연산자']} {rule['임계값']:g} {rule['단위']}"
    detection = ("가상 화염검지 신호이므로 실제 광학 검지·열화상·온도·압력으로 확인한다."
                 if tag.startswith("FD-") else
                 "가상 가스농도는 누출량 기반 대리 신호이므로 위치·현장 검지를 별도로 확인한다."
                 if tag.startswith("GD-") else
                 "단일 센서 임계 초과만으로 누출·화재·파손을 확정하지 않는다.")
    conditions = [
        f"{location}의 {tag} 신호가 {threshold} 기준에 {rule['지속_s']:g}초 이상 해당하는지 품질·시각과 함께 확인한다.",
        f"원인 후보: {rule['원인후보']}. {detection}",
    ]
    actions = {
        "recognition": conditions + list(plan["recognition"]),
        "immediate": [focus["immediate"]] + list(plan["immediate"]),
        "stabilize": [focus["stabilize"],
                      f"{tag}가 복귀 기준 {rule['복귀연산자']} {rule['복귀값']:g} {rule['단위']}에 이르고 관련 신호도 안정되는지 확인한다."]
                     + list(plan["stabilize"]),
        "restart": [focus["restart"],
                    f"{location}의 원인 시정 기록, 관련 경보·차단·검지 기능시험과 담당자 재가동 승인을 확인한다."]
                   + list(plan["restart"]),
        "prevention": [focus["prevention"],
                       f"{tag}의 경보·복귀 설정과 표본 주기, 데이터 품질 및 해당 설비 운전 절차를 정기 검토한다."]
                      + list(plan["prevention"]),
    }
    return {"rule_id": rule["rule_id"], "node_id": rule["node_id"],
            "sensor_id": tag, "scenario": rule["시나리오명"],
            "plan_id": plan["id"], "severity": rule["등급"],
            "trigger": {"expression": rule["신호식"], "operator": rule["연산자"],
                        "threshold": rule["임계값"], "unit": rule["단위"],
                        "persistence_s": rule["지속_s"]},
            "source_ids": list(plan["sources"]), "stages": actions,
            "scope": "SIMULATION_ADVISORY_SITE_REVIEW_REQUIRED"}
