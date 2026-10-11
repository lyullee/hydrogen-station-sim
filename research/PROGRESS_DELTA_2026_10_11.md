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
- 최신 감사 갱신 커밋: `ff15067`
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
전체 회귀 기록은 1,443 passed, 0 failed, 20 warnings이며, 경고는 의존성·수치
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

## 2026-10-11 — paper-scope wording alignment

- Reworded the manuscript so a three-arm incident study is explicitly an optional future study, not a pending result or a current scientific gate.
- Reworded the limitation so independent expert review is required only before a facility-specific human-effectiveness claim.
- Recompiled the exact LaTeX source with Tectonic 0.17.0: 23/23 pages, no fatal errors, unresolved citations/references 0, overfull boxes 0.
- Re-ran IJHE format and readiness audits: format gate PASS; readiness remains blocked by the existing failed release/holdout validation gates and unconfirmed submission metadata, while ethics/expert review remains optional for this objective engineering paper.
- Targeted regression: 33 passed (`test_ijhe_readiness_audit.py`, `test_llm_grounding.py`, `test_local_full_loop_schema_inventory.py`).

- NREL H2FillS geometry sensitivity (post-access diagnostic): legacy geometry 0/7 screens; declared-capacity EOS without volume fit 7/7, pressure RMSE 0.496 MPa. This does not change the runtime default or any validation gate; an untouched trace is still required before promotion. See `research/nrel_h2fills_geometry_sensitivity_2026_10_12.json`.

- Geometry holdout protocol frozen before outcome access: `research/nrel_h2fills_geometry_prospective_protocol_2026_10_12.json`; it does not change the runtime default or validation gates.

## 2026-10-12 — Grüne public trace recheck

- Publisher, KIT and public conference sources were rechecked for a complete,
  rights-cleared pressure–time trace. No reusable machine-readable full trace
  was found; the existing 51-point figure digitisation still stops before the
  required half-pressure crossing.
- The Grüne gate remains `PENDING_INELIGIBLE_FOR_JOINT_SCREEN`. Runtime
  parameters, readiness counts and manuscript claims are unchanged. See
  `research/grune_2014_public_pressure_trace_recheck_2026_10_12.json` and
  `research/GRUNE_2014_PUBLIC_PRESSURE_TRACE_RECHECK_2026_10_12.md`.

- Final full regression after the provenance-grounding change and audit-hash
  refresh: **1,446 passed, 0 failed, 20 warnings**
  (`research/full_regression_test_run_2026_10_11.json`). The additional three
  tests cover the DataverseNO recheck and its LLM evidence projection.

- LLM·사고경로 회귀를 다시 실행해 **65 passed / 0 failed / 2 warnings**를
  확인했다. 근거 기반 LLM 계약, provider routing, 직접 SAGA 대화, HIAD
  사고 재생, 가상 조치 실행과 단계별 대응 플레이북을 함께 검증했으며,
  상세 기록은 `research/paper_llm_accident_path_regression_2026_10_12.json`에
  고정했다. 이는 소프트웨어 계약과 사고자료 연결 증거이며 독립 전문가의
  사람 대상 안전효과나 현장 배포 안전성을 의미하지 않는다.

## 2026-10-12 — 공개 분산자료 provenance 재검증

- 기존 Figshare intake와 동일한 USN 공개 실험 22개 ZIP을 DataverseNO
  원자료 API에서 다시 확인했다. 22/22 실험 archive의 Dataverse MD5가
  임시 로컬 사본과 일치하고, CSV 스키마는 22/22 파일에서 37열·수소농도
  센서 29개로 확인됐다.
- archive SHA-256과 파일별 checksum은
  `research/usn_open_channel_dataverseno_recheck_2026_10_12.json`에 고정하고
  원자료·원시 행은 저장소에 넣지 않았다. 이 작업은 재현성·권리 추적을
  강화하는 provenance 보완이며 기존 점수, 런타임 파라미터 또는 IJHE 게이트를
  변경하지 않는다.
- 이 자료는 실제 수소 개방 채널 분산·유량 구성요소 검증 후보로만 유지한다.
  station-to-vehicle full-loop, HRS 제어기/ESD, 시설별 안전거리와 SAGA의
  인간 안전효과 주장을 닫는 근거로 사용하지 않는다.
- 이 provenance 재검증 경로를 근거 기반 LLM envelope에도 연결했다. 따라서
  SAGA가 해당 공개 실험의 범위나 재현성을 설명할 때 DataverseNO 체크섬 기록을
  근거로 노출할 수 있지만, spatial holdout 준비 여부는 계속 `false`로 유지한다.

## 2026-10-12 — 전체 회귀 및 기록 해시 재검증

- 전체 `.venv` 회귀에서 처음 발견된 두 기록 불일치(public Type-IV 런타임
  calibration 해시, KHK 사고 선례 라우팅 manifest 해시)를 현재 코드로
  재생성했다. 관련 readiness·routing 테스트는 **5/5 통과**했다.
- 전체 회귀는 **1,446 passed / 0 failed / 20 warnings**로 종료됐다. 경고는
  기존 FastAPI/httpx 호환성, HyRAM physics warning, openpyxl workbook warning이며,
  검증 점수나 런타임 파라미터를 변경하지 않았다.
- 최신 readiness audit를 회귀·해시 기록 이후 다시 생성했다. 게이트 수는
  **128 PASS / 10 FAIL / 7 PENDING**으로 동일하고, 공개 탱크 런타임 보정과
  사고 선례 라우팅은 `PASS`로 확인됐다. `bounded_ijhe_submission_ready`와
  `full_user_objective_ready`는 기존 물리 holdout·full-loop·사람 효과성 조건
  때문에 계속 `false`다.

- 2026-10-12 01:24 KST에 readiness audit를 다시 실행해 현재 파일·해시와
  일치함을 확인했다. 게이트 수와 차단 목록은 변하지 않았으며, 이 재실행은
  진행률을 부풀리거나 실패한 물리 검증을 통과로 바꾸지 않는다.


- 2026-10-12 KST: Rechecked public station-to-vehicle sources (Kuroki/NREL HITRF, Genovese Cal State LA, OSTI/NREL model and MetHyTrucks). No new rights-cleared synchronized raw holdout was identified; recorded as availability evidence only in `research/public_station_vehicle_search_recheck_2026_10_12.json`.
