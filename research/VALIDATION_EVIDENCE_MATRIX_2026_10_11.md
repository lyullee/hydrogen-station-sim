# 검증 증거 매트릭스 — 2026-10-11

이 매트릭스는 논문, readiness audit, SAGA 근거 요약이 동일한 검증 용어를 사용하도록 고정한 기록이다. `independent external validation`은 동일 사이트 보류자료에 붙이지 않는다.

## 현재 주장 가능한 검증

| 증거 레인 | 현재 상태 | 주장 가능한 범위 | 주장하면 안 되는 범위 |
|---|---|---|---|
| 소유자 station-side 자료 | **지원됨: 시간순 동일 사이트 holdout** | 압력 경계, cascade sequence, 단기 재충전 압력 예측 | 독립 외부검증, 차량 충전, 현장 안전거리, 인증, SAGA 효과 |
| 공개 Type-IV 탱크 | **고정 분할 준비됨: 독립 외부 구성요소** | receiving-tank 열역학 구성요소 | station controller, dispenser, 차량, ESD, 현장 안전 |
| 실제 수소 점화 압력 peak | **확증 구성요소 통과** (27/27) | 점화된 압력 peak consequence 구성요소 | H70 옥외 충전소 전체, 방사열 거리, 비상제어, SAGA 효과 |
| 실제 수소 비점화 압력 peak | **탐색 결과** (7/10) | 제한된 밀폐·벤트 공간의 탐색 근거 | 확증 검증, full-loop, 현장 안전 |

수치와 원본 기록은 JSON 매트릭스 및 각 `source_artifact`에 있다. 동일 사이트 자료의 56,854,143행은 보유자료의 크기이지 독립 표본 수를 의미하지 않는다.

## 목표에서 제외하고 논문 한계로 남긴 범위

공개된 **동기화 station-to-vehicle 원자료**는 다음을 동시에 만족하는 재사용 가능 데이터로 확인되지 않았다.

- station/dispenser와 vehicle/receptacle 신호
- 공통 경과시간축
- 압력·온도·질량유량 또는 이송질량
- 단위·초기조건·프로토콜 메타데이터
- 원자료 또는 파생자료의 재사용 권리

따라서 full-loop 외부검증은 기본 목표에서 제거했다. 논문에는 “공개 재사용 가능한 동기화 원자료를 찾지 못해 차량 측 제어·ESD와 완전한 station-to-vehicle 현장 검증은 연구 범위 밖”이라고 명시한다. 향후 관리자가 비식별화한 원자료를 제공하고, 결과를 보기 전에 프로토콜·해시·권리를 동결하면 별도 확장 검증으로 다시 열 수 있다.

## 윤리 검토와 전문가 평가의 의미

**윤리 검토**는 HAZOP 표의 정답을 심사하는 절차가 아니다. 사람에게 SAGA 답변을 보여 주고 응답을 수집하는 후속 연구라면 기관 IRB/연구윤리 담당자가 승인·면제·심의 불필요 중 하나를 공식 결정하는 절차다. 현재 연구는 공개 기록과 비식별 station-side 자료를 분석하므로 사람 대상 연구라고 단정하지 않는다.

**전문가 평가**는 LLM이 자기 답변을 채점하는 기능이 아니다. 수소안전·공정안전·HAZOP·비상대응 자격을 확인한 독립 평가자 3명이 동일 holdout 사건 24개를 `alarm_only`, `direct_saga`, `standards_rag_saga` 조건으로 눈가림 평가한다. 핵심 평가지표는 critical omission과 unsafe advice이며, 조치 정확성·우선순위·안정화·예방관리·근거성도 함께 기록한다.

현재 두 상태는 `PENDING`이다. 따라서 물리·station-side 논문은 진행할 수 있지만, **SAGA가 운영자 안전성·대응시간·판단 정확도를 개선한다**는 주장은 두 절차가 끝날 때까지 하지 않는다.

## 참조 파일

- `research/validation_evidence_matrix_2026_10_11.json`
- `research/validation_data_split_and_scope_decision_2026_10_11.json`
- `research/external_full_loop_data_recheck_2026_10_11.json`
- `research/ethics_and_expert_review_scope_decision_2026_10_11.json`
