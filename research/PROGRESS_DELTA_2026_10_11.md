# 진행상태 델타 — 2026-10-11

이 기록은 현재 감사 결과와 이전 진행률을 혼동하지 않도록, 검증 범위가
어디까지 닫혔고 어떤 항목을 목표에서 제외했는지 고정한다. 수치 검증 실패를
재튜닝으로 지우거나, 동일 설비 holdout을 독립 외부검증으로 부르지 않는다.

## 현재 감사

- 전체 게이트: **128 PASS / 10 FAIL / 7 PENDING**
- 선언한 주 목표 범위: **128 PASS / 9 FAIL / 2 PENDING (92.1%)**
- `bounded_ijhe_submission_ready`: `false`
- `full_user_objective_ready`: `false`
- 최신 readiness audit: `manuscript/ijhe_readiness_audit.json`
- 최신 감사 갱신 커밋: `efd0406`
- 최신 전체 회귀 기록: `research/full_regression_test_run_2026_10_11.json`

주 목표 범위에서 제외한 것은 공개 동기화 station-to-vehicle full-loop 원자료와
사람 대상 SAGA 효과 연구다. 따라서 92.1%는 전체 사용자 목표가 완료됐다는 뜻이
아니라, 현재 확보·권리 확인된 station-side/component 범위의 진행률이다.

## 이번 범위 결정

1. 소유자 자료는 시간 순서로 calibration/holdout을 분리했다. 이는 동일 설비의
   **시간순 station-side holdout**이며 독립 외부검증으로 표시하지 않는다.
2. 공개 Type-IV 자료는 별도의 **독립 외부 구성요소 holdout**으로 유지한다.
3. 공개 검색에서 station/dispenser와 vehicle/receptacle의 공통 시간축, 압력·온도·
   질량유량, 프로토콜·단위·재사용권을 함께 제공하는 원자료는 확인하지 못했다.
   station-to-vehicle full-loop 외부검증은 기본 목표에서 제거하고 논문 한계에
   명시했다.
4. 윤리 결정과 독립 전문가 평가는 사람을 모집해 SAGA가 안전 판단을 개선한다고
   주장할 때만 필요한 선택 연구다. 현재 물리 검증 논문의 필수 게이트로 사용하지
   않으며, 완료 전에는 인간 안전효과를 주장하지 않는다.

## 현재 주장 가능한 범위

- 시간순 동일 사이트 자료를 이용한 station-side 압력 경계, cascade sequence,
  단기 재충전 압력 예측.
- 공개 Type-IV receiving-tank 열역학 구성요소 검증.
- 실제 수소 점화·사고 기록에 대한 제한된 consequence 및 대응 playbook 추적성.
- 센서·사고 상태를 deterministic 계산과 근거 manifest에 먼저 연결한 직답형 SAGA.

## 아직 닫히지 않은 핵심

P0 방출·감압 holdout(Dickens, PRESLHY, Proust, Schefer, Grüne) 중 일부는 선언한
오차·과도응답 screen을 통과하지 못했다. Schefer line-inventory와 HyTunnel
two-zone 모델은 원인 진단용 post-outcome 모델로 기록되어 있지만, 기존 결과나
런타임 파라미터를 바꾸지 않는다. 새 장치의 배관 체적·밸브 동특성·벽 열전달과
동기화된 원시 trace가 확보될 때만 새 pre-access protocol로 재검증한다.

## 검증

이번 문서 갱신 후 focused validation/grounding 테스트는 **9 passed**였다.
전체 회귀 기록은 1,436 passed, 0 failed, 20 warnings이며, 경고는 의존성·수치
환경 경고로 기록되어 있다.
## 최신 impact-first 실행 결과 (2026-10-11)

- 병렬 우선 검증: **PASS**
  - LLM 근거 경계: 3 passed
  - full-loop 입력 계약: 19 passed
  - 가상 안전조치·응답: 24 passed
  - 산출물: `research/priority_validation_run_2026_10_11_latest.json`
- 병렬 물리 진단 프로세스: **PASS**, 과학 스크린 상태: **BLOCKED**
  - MC SOC/EOS 경계: 8/8 진단 스크린 통과
  - Dickens 혼합대류 민감도: 3/3 통과했지만 사후 진단이므로 원래 holdout 승격 금지
  - MC 탱크 경계: 0/8
  - H2SAFE 공간응답: 0/1 진단 스크린
  - NREL HDVS 수용탱크: 0/7
  - 산출물: `research/priority_diagnostics_run_2026_10_11_latest.json`

이 실행은 코드 계약과 실패 원인을 갱신한 것이며, 사후 진단을 외부 검증 통과로 바꾸거나 런타임 파라미터를 자동 승격하지 않는다. 물리 실패를 해결하려면 결과를 본 뒤 재튜닝하는 대신, 경계조건·공간좌표·동기화 채널이 명시된 새 사전동결 holdout이 필요하다.
