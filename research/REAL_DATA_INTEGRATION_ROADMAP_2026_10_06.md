# 실데이터 통합·검증 로드맵

이 문서는 공개 실험, 비공개 운전 로그, 공개 사고자료를 하나의 검증 주장으로 섞지 않기 위한 실행 기준이다. 현재 저장소의 기본 모델과 공개 holdout 결과를 다시 맞추거나 덮어쓰지 않는다.

## 현재 확보된 근거

| 근거 | 현재 사용 | 주장 가능한 범위 |
|---|---|---|
| 공개 release·저장용기 실험 | 고정 프로토콜로 component holdout 실행 | 압력감쇠·방출·열전달 모델의 케이스별 성능과 실패 범위 |
| 공개 충전 실험 | 별도 calibration/validation split | 차량 탱크 압력·온도·SOC의 실험 범위 성능 |
| 공개 사고·사고보고 자료 | 시나리오 분류와 단계별 playbook 근거 | 누출·화재·대피·차단·복구 절차의 근거 연결 |
| 비공개 station logger | 8개 집계 파일, 10,896개 샘플 | 저장뱅크 압력 경계와 재충전 재시작 여유 0.540 MPa |
| 비공개 시간순 holdout | 보정 접두부 998점·미사용 접미부 30점 | 0.490 MPa 보정으로 보호형 경계 리플레이 완료; full-loop 검증 아님 |
| 비공개 다중 station 압력 교차 점검 | 2개 압력 경계 집계, 12,896 샘플 | 관측 압력 교집합 56.295–63.360 MPa; 압력 plausibility 보조 근거; 차량·유량·온도 검증 아님 |
| 공개 HITRF 설비 설명 | 저장 tier·압축 단계·H70/H35·예냉 정격 | 실설비 규모와 운전범위의 face-validity 비교 및 LLM 설명 근거; 원시 시계열·full-loop 검증 아님 |

비공개 로그는 원시 행·태그명·위치·운영자·설비 식별정보를 저장소에 넣지 않는다. 현재 온도와 유량은 경계 역할·단위·교정 증명이 없으므로 진단값으로만 남긴다.

수명 카운터는 소유자 설명자료로 완충 횟수 의미와 중압 450 bar·고압 850 bar
단위를 확인했다. 이 attestation은 `lifecycle_evidence` 로더를 거쳐 LLM과
운영자에게 이력 맥락으로만 전달된다. 카운터를 용량 저하·누출률·안전밸브
설정·고장확률로 변환하는 열화 관계는 아직 검증되지 않았으므로 물리 모델에는
주입하지 않는다.

최근 privacy-bounded schema 재검사에서는 압축기 압력·온도, station 압력·온도,
유량/적산, 밸브·알람 상태와 lifecycle counter 계열이 확인됐지만 차량측
채널 family는 0건이었다. 따라서 이 자료로 가능한 보정은 station-side 경계와
설비 상태까지이며, 차량 충전 정확도나 full-loop 검증으로 확대하지 않는다.

2026-10-06에 소유자 제공 폴더를 다시 읽어 `scripts/audit_confidential_station_schema.py`
로 헤더·채널 family 집계를 재생했다. 33개 파일, 압력 136개·온도 64개·유량
64개·상태 216개·수명 카운터 34개의 집계가 커밋된 요약과 일치했으며, 차량측
family는 0건으로 유지됐다. 이 재검사는 집계 일치성만 확인하고 원시 행·태그명·날짜·
단위는 저장하지 않는다. 기록은
`research/private_owner_data_intake_recheck_2026_10_06.json`의
`schema_recheck`에 남겼고, full-loop 검증 상태는 계속 `false`다.

같은 날 승인된 압력 매핑으로 운전영역 보정 집계를 다시 계산해 동결 프로필과
대조했다. 8개 파일·10,896개 샘플, 61초 중앙 샘플주기, 64초 최대 공백,
56.295–63.360 MPa 경계, 0.540 MPa 재시작 여유가 모두 일치했다. 온도·유량·
이산 상태 매핑이 없는 호출에서는 해당 항목을 일치로 간주하지 않고 생략 목록으로
기록한다. 불일치 시 프로필은 자동 교체하지 않는다. 재검산 기록은
`research/confidential_operational_profile_recheck_2026_10_06.json`이며, 실행
도구는 `scripts/recheck_confidential_operational_profile.py`다.

추가로 온도·유량·이산 상태 채널을 임의로 물리 보정에 사용하지 않도록 generic
매핑으로 품질만 재검산했다. 8개 파일에서 1,092개 샘플의 시간값은 모두
파싱됐고, 압력·유량·상태 관측은 유한값 비율 1.0이었다. 온도는 한정된 결측이
확인됐으며, 이산 상태 전이는 1,283건으로 집계됐다. 이 결과는 채널 품질과
동기화 가능성의 intake 근거일 뿐 단위·교정·태그 의미를 대신하지 않는다.
따라서 온도·유량 parameter fit과 full-loop 검증은 계속 보류하고, 결과는
`research/confidential_station_channel_quality_recheck_2026_10_06.json` 및
`scripts/recheck_confidential_station_channel_quality.py`에 보존한다.

## 수용용기 측 전 구간 추적을 확보했을 때의 안전한 반입

원본 CSV, 원래 태그명, 절대시각은 저장소에 넣지 않는다. 권한 있는 데이터
관리자가 로컬의 별도 제어 구역에서
`scripts/export_confidential_full_loop_bundle.py`를 실행해 상대시간과 일반화된
공학 채널만 포함한 `full_loop_event.csv`를 생성한다. 이 도구는 다음을 모두
요구한다.

- 수용용기 압력, 가스·탱크 온도, 질량유량, 충전소·캐스케이드 압력,
  압축기·프리쿨러·누설검사·벤트·고장·ESD 상태의 명시적 매핑
- 압력·온도·유량 단위와 모든 이산 상태의 의미에 대한 관리자의 확인
- 동결한 평가 프로토콜 이전에 결과를 보지 않았다는 확인과 제어된 연구 이용 권한

출력 디렉터리가 이 저장소 안에 있으면 도구가 즉시 거절한다. 이후에도
`validate_external_hrs_manifest.py`, `validate_external_hrs_trace.py`,
`validate_external_hrs_full_loop.py`를 모두 통과해야만 **평가 입력 후보**가
된다. 이 절차의 통과는 검증, 안전성 인증, 현장 안전거리 확인을 뜻하지 않는다.

공개 HITRF 기준선은 `research/nlr_hitrf_public_operational_reference_2026_10_06.json`에 정적 정격과 명시적 주장 경계를 기록하고, LLM 근거 envelope에만 연결한다. 이 기준선으로 기본 시뮬레이션 파라미터를 자동 변경하지 않는다. 공개 페이지에는 자동 로깅이 설명되어 있지만 동기화된 원시 logger archive가 제공되지 않으므로 full-loop 검증 gate의 증거로 세지 않는다.

추가로 비공개 설비 logger에서 식별정보를 제거한 압력·온도·상태 envelope를
`research/confidential_station_equipment_operational_envelope_2026_10_06.json`으로
LLM 근거에 연결했다. 1,426개 샘플의 station-side 압력 범위와 상태 전이 횟수는
운전 맥락을 설명하는 데 사용하지만, 온도 역할과 상태 의미는 custodian attestation
전까지 보정값으로 승격하지 않는다. 차량측 채널이 없으므로 full-loop 또는 안전거리
검증을 주장하지 않으며, 기본 모델 파라미터도 변경하지 않는다.

같은 압력 bundle은 generic 채널별로도 집계했다. 채널 1·2의 중앙값은 각각
43.2896 MPa와 82.8211 MPa로 서로 다른 경계를 보였고, 이 값은 LLM이 관측
범위를 설명하는 데만 사용한다. 채널과 저·중·고압 뱅크의 대응은 공개하지 않았고
attestation도 받지 않았으므로 controller에 자동 주입하지 않는다. 결과는
`research/confidential_station_boundary_channel_envelopes_2026_10_06.json`에
보존한다.

추가로 새로운 장비 로그 구간을 기존 운전 경계 프로필과 비교하는 드리프트
재점검을 수행했다. 새 구간은 1,426개 표본에서 기존 8개 파일 집계와 표본 수,
관측 기간, 압력 중앙값·잡음, 상태 전이 수가 달랐다. 이 차이는 보정 프로필을
자동 교체하지 않고 custodian 검토 대상으로 격리했다. 기록은
`research/confidential_station_equipment_drift_recheck_2026_10_06.json`과
`scripts/recheck_confidential_equipment_drift.py`에 남겼으며, 온도·유량 보정과
full-loop 검증은 계속 보류한다.

동기화된 수용용기 측 trace가 확보되면, 입력 통과만으로 모델 성능을 주장하지
않는다. `scripts/prepare_controlled_full_loop_evaluation.py`가 receipt의 hash와
evidence scope만으로 저장소 밖의 동결 평가 프로토콜 초안을 만들고,
`scripts/evaluate_controlled_full_loop.py`가 동일 trace hash·동일 Git commit·깨끗한
worktree·사전 선언한 오차 한계를 확인한 뒤 집계 RMSE/MAE와 상태 일치도만
출력한다. 선택 뱅크 압력만 있을 때는 차량–공급원 경계로 범위를 제한하며,
저·중·고압 뱅크 압력 3개가 모두 있어야 cascade dispatch/recharge 결과를
평가한다. 전체 절차와 공개 한계는
`research/CONTROLLED_FROZEN_FULL_LOOP_EVALUATION.md`에 고정했다.

차량 용기 형상은 `capacity_eos` 선택지로 선언 용량과 공칭 압력에서 표 형상방정식
밀도로 체적을 계산할 수 있게 했다. 2026-10-06에 이미 열어본 공개 개발 케이스
8건을 재생한 결과는 0/8 screening pass로, 기존 `capacity_scaled`의 1/8보다
좋아지지 않았다. 따라서 생산 기본값은 유지하며, 이 결과는 새 holdout이나
프로토콜 검증으로 승격하지 않는다. 세부값은
`research/h2protocol_capacity_eos_diagnostic_2026_10_06.json`에 고정한다.

이번 보완에서는 공개 NREL 탱크 민감도 결과를 LLM 근거 봉투에도 연결했다.
`public_geometry_sensitivity`는 legacy/reference와 capacity/EOS 선택 경로의
집계 성능을 구분해 전달하고, 사후 접근 진단이라는 한계를 함께 표시한다.
각 실행 프레임에는 실제 선택된 `vehicle_geometry_basis`와 선언 용량도 남겨
reference 기본 실행과 capacity/EOS 민감도 실행이 혼동되지 않게 했다. 이
연결은 모델 기본값을 바꾸지 않으며, 미사용 외부 holdout이 확보되기 전에는
검증 완료나 논문 성능 주장으로 승격하지 않는다.

Proust 독립 방출 holdout에서는 고정된 전역 방출계수 `Cd=0.8`이 1·2·3 mm
구경을 동시에 설명하지 못했다. 사후 진단에서 구경별 measured-to-unit 계수가
서로 다른 범위를 보였고, 1 mm 계열은 유효계수가 1보다 크게 추정되었다. 이는
상류 밸브·배관 제한, 라인 체적 또는 계측·디지타이징의 영향을 분리해야 한다는
신호이며, holdout 결과에 맞춰 계수를 조정하거나 생산 모델을 변경할 근거가
아니다. 세부 민감도 표는
`research/proust_discharge_coefficient_sensitivity_2026_10_06.json`에 기록했고,
해당 파일은 `post_outcome_diagnostic_only`로 고정했다. 새 apparatus-resolved
release 모델은 미사용 캠페인에서 밸브 개방법과 라인 저항을 함께 동결한 뒤
독립 검증해야 한다.

LLM 근거 봉투에는 이제 `public_source_links`와 현재 모의 노즐 유량을
NREL 고유량 실험의 집계 평균·최대값과 비교하는
`public_operating_envelope_screen`이 포함된다. 이는 공개 출처를 운영자에게
추적 가능하게 하고 운전범위 맥락을 제공하지만, 모델 정확도·프로토콜 적합성·
안전 인증을 판정하지 않는다. 원시 시계열이 공개되지 않은 출처는 반드시 그
한계를 함께 표시한다.

공개 CC BY HySaM/NPL sampling workbook 13개도 계측 맥락으로 LLM 근거 봉투에
연결했다. 파일 수준 검사에서 공통 0.5 s 시간 간격은 확인되지만 공개 채널
사전·차량/리셉터클 의미·완전한 충전 프로토콜은 제공되지 않는다. 따라서 이
근거는 계측 시간축과 provenance 설명에만 사용하며 station-to-vehicle
full-loop 검증이나 수치 파라미터 보정에는 사용하지 않는다.

PRESLHY source-depletion 결과도 LLM 근거에 개발/독립 holdout으로 분리해
연결했다. 개발 자료는 22건 중 20건 통과였지만 외부검증 주장은 금지되고,
E5.1 독립 ambient holdout은 3건 중 2건 통과로 최소 케이스 조건과 70% 주장
조건을 충족하지 못한다. 이 결과는 실패 경계를 설명하는 데만 사용하며
런타임 방출계수는 변경하지 않는다.

## 다음 단계의 승인 조건

### 1. 온도·유량 경계 채널 attestation

데이터 관리자가 각 generic 채널에 대해 역할, 단위 변환, 교정 상태, 절대시간 동기화, 결측·최대 간격을 확인해야 한다. 특히 장비 온도는 공급가스 경계로 사용할지 별도 승인해야 한다. 승인 전에는 모델 경계에 자동 주입하지 않는다.

### 2. 비공개 full-loop holdout

차량 또는 디스펜서 식별정보를 공개하지 않아도 된다. 다만 검토자에게는 원자료를 제공할 수 있어야 하며, 다음 채널이 같은 시간축으로 있어야 한다.

- 저장뱅크·공급부 압력과 온도
- 디스펜서·노즐 질량유량과 압력
- 차량 탱크 압력·온도·SOC 또는 질량수지
- 충전 프로토콜 상태, 차단·밸브 피드백, ESD 상태

모델·파라미터·전처리·점수 기준은 원자료를 열기 전에 고정한다. 최소 8개 이상의 독립 실행과 사전 정의된 합격률을 사용하며, 실패 케이스도 모두 보존한다.

입수 후에는 `scripts/validate_external_hrs_full_loop.py`로 동일 시간축,
유한값·결측률·최대 간격, 차량/디스펜서/캐스케이드 압력, 공급가스 온도,
압축기·프리쿨러·누출·벤트·고장·ESD 상태를 먼저 검사한다. 이 결과는
`FULL_LOOP_TRACE_READY_FOR_EVALUATION`인 경우에만 별도 동결 평가기에 넘기며,
보간·재표본화·누락값 대체를 하지 않는다. 입력 화면을 통과해도 모델 검증이나
안전성 입증으로 승격하지 않는다.

캐스케이드 전환·재충전까지 평가하려면 저압·중압·고압 뱅크 압력 3개와 선택
뱅크 상태가 같은 시간축에 있어야 한다. 선택 뱅크 압력만 있는 경우는
`STATION_TO_VEHICLE_TRACE_READY_PARTIAL_CASCADE`로 따로 기록하며, 차량–디스펜서
경계의 부분 검증에만 사용할 수 있다. 누락된 뱅크 압력을 추정하거나 보간해
full-loop 결과로 승격하지 않는다.

### 3. 피해영향 모델의 component 범위 확장

현재 실패한 PRESLHY·Proust·Schefer holdout은 재튜닝하지 않는다. 새 장치의 line volume, valve law, terminal restriction, wall heat transfer가 공개되거나 검토 가능한 데이터로 확보될 때만 apparatus-resolved 모델을 새 프로토콜로 동결한다.

### 4. SAGA 효과성 평가

공개 사고자료는 대응 근거와 시나리오 분류에만 사용한다. 효과성 주장을 하려면 hindsight를 제거한 24개 사례, 168개 맹검 응답, 독립 전문가 3인의 고정 평가와 윤리·누출 검토가 필요하다. 이 조건 전에는 LLM의 안전성·효과성을 주장하지 않는다.

## 승격 규칙

실측 보정 프로필은 `measured_boundary_calibration`을 켠 실행에서만 적용한다. 공개 holdout 합격 결과가 없는 파라미터를 production 기본값으로 승격하지 않는다. full-loop 검증과 SAGA 독립 평가가 모두 통과하기 전에는 목표 상태를 완료로 표시하지 않는다.

관련 근거:

- `research/CONFIDENTIAL_OPERATIONAL_ENVELOPE_CALIBRATION_SUMMARY_2026_10_06.md`
- `research/CONFIDENTIAL_AUTHORIZED_CHANNEL_CONTRACT_2026_10_06.md`
- `research/IJHE_SUBMISSION_BLOCKER_MATRIX_2026_10_05.md`
- `research/ijhe_readiness_audit.json`
