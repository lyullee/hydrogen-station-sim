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

공개 HITRF 기준선은 `research/nlr_hitrf_public_operational_reference_2026_10_06.json`에 정적 정격과 명시적 주장 경계를 기록하고, LLM 근거 envelope에만 연결한다. 이 기준선으로 기본 시뮬레이션 파라미터를 자동 변경하지 않는다. 공개 페이지에는 자동 로깅이 설명되어 있지만 동기화된 원시 logger archive가 제공되지 않으므로 full-loop 검증 gate의 증거로 세지 않는다.

차량 용기 형상은 `capacity_eos` 선택지로 선언 용량과 공칭 압력에서 표 형상방정식
밀도로 체적을 계산할 수 있게 했다. 2026-10-06에 이미 열어본 공개 개발 케이스
8건을 재생한 결과는 0/8 screening pass로, 기존 `capacity_scaled`의 1/8보다
좋아지지 않았다. 따라서 생산 기본값은 유지하며, 이 결과는 새 holdout이나
프로토콜 검증으로 승격하지 않는다. 세부값은
`research/h2protocol_capacity_eos_diagnostic_2026_10_06.json`에 고정한다.

LLM 근거 봉투에는 이제 `public_source_links`와 현재 모의 노즐 유량을
NREL 고유량 실험의 집계 평균·최대값과 비교하는
`public_operating_envelope_screen`이 포함된다. 이는 공개 출처를 운영자에게
추적 가능하게 하고 운전범위 맥락을 제공하지만, 모델 정확도·프로토콜 적합성·
안전 인증을 판정하지 않는다. 원시 시계열이 공개되지 않은 출처는 반드시 그
한계를 함께 표시한다.

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
