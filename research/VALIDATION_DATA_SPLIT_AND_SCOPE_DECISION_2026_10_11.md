# 검증 데이터 분리 및 목표 범위 결정 — 2026-10-11

## 1. 보유 자료의 분리 원칙

같은 사업장 계측을 무작위로 섞어 train/test로 나누지 않는다. 동일 충전 사이클의
인접 행이 양쪽에 들어가면 시간 누수로 성능이 부풀려지기 때문이다. 보유 자료는
운전 episode와 시간 순서를 기준으로 보정용과 holdout용을 분리한다.

### A. 비식별 소유자 station-side 자료

- 33개 CSV에서 중복을 제거한 56,854,143개 행을 보유하고 있다.
- 압력 경계: 보정 998점, 시간순 holdout 30점.
- 중·고압 cascade 순서: 보정 8,106쌍, holdout 3,664쌍.
- 재충전 압력 단기 예측: 보정 1,024건, holdout 394건.
- lifecycle counter 정렬은 음성 결과를 보존하며 검증 통과로 승격하지 않는다.

이 묶음은 **동일 사이트 station-side holdout**이다. 데이터 보유자가 외부 기관이
아니므로 `independent external validation`이라고 부르지 않는다. 논문에서는 압력
경계·cascade·재충전 자문 범위로만 보고하고 차량 측 정확도나 현장 안전한계로
확장하지 않는다. 세부 식별자, 경로, 날짜, 제조사와 원시 행은 저장소에 공개하지
않는다. 근거: `research/confidential_station_side_integrated_validation_2026_10_09.json`.
분할 규칙·참조 산출물 해시·누수 방지 조건은
`research/confidential_validation_split_manifest_2026_10_11.json`에 고정했다.

### B. 공개 외부 Type-IV 수용탱크 자료

- 사전 고정 규칙: `lab_test_number modulo 3 == 0`을 validation holdout으로 지정.
- 보정 23건, 외부 validation 12건, 질량 폐쇄 실패로 제외한 1건.
- 보정 후 holdout을 열어 새 파라미터를 맞추지 않았다.
- 평균 RMSE: 압력 3.841 MPa, 온도 4.833 °C, SOC 3.850 %p.

이 묶음은 공개된 외부 **구성요소** 검증으로 보고한다. 차량 제어기, 디스펜서,
ESD, cascade topology 또는 현장 안전거리까지 검증한 결과가 아니다. 근거:
`research/independent_component_holdout_reanalysis_2026_10_11.json`.

## 2. station-to-vehicle 원자료 검색 판정

현재 공개 접근 경로에서 다음 조건을 동시에 만족하는 파일은 확인되지 않았다.

1. station/dispenser와 vehicle/receptacle의 계측 채널이 함께 존재
2. 공통 경과시간축과 압력·온도·질량유량 또는 이송질량이 기계 판독 가능
3. 프로토콜·초기조건·단위·센서 역할이 확인됨
4. 파생 결과를 재사용·출판할 권리가 명시됨

확인한 자료의 범위는 다음과 같다.

- [FCH2RAIL D6.1](https://fch2rail.eu/wp-content/uploads/2025/01/FCH2RAIL_D6.1_Report-on-KPI-assessment.pdf): 실제 열차 충전 측정의 범위와 결과를 설명하지만 공개 원시 logger export가 없다.
- [DLR/FCH2RAIL 충전 연구](https://elib.dlr.de/213625/1/manuscript_final_published_version.pdf): 차량 탱크와 디스펜서 채널의 예시 trace를 보여주지만 재사용 가능한 전체 시계열 묶음이 없다.
- [Cal State LA back-to-back fueling 연구](https://doi.org/10.1016/j.jclepro.2021.129737): 실제 station·호스·차량 채널과 고해상도 운전 자료를 설명하는 유력한 custodian 요청 대상이지만, 공개 페이지와 OSTI 기록에서 재사용 가능한 공통시계 logger 원자료와 권리 조건을 찾지 못했다. [OSTI station report](https://www.osti.gov/servlets/purl/1799187)도 DAQ 및 압력·분배 집계/도표를 제공할 뿐 원시 full-loop export는 제공하지 않는다.
- [NREL H2FillS](https://www.nrel.gov/hydrogen/h2fills): 차량 충전 모델과 소프트웨어 설명이며, station-to-vehicle holdout 원자료 저장소가 아니다.
- [H2-Stations Europe API v2](https://docs.h2-stations.eu/for-data-users/api-v2/): station layout과 availability/usage/storage/pricing 신호를 제공하지만 차량 탱크 transient 및 공통 station-to-vehicle 시계가 없다.
- [ELVHYS 4.2](https://doi.org/10.18710/JXJP0H): CC0 공개 자료지만 1 m³ transfer-connection space의 극저온 누출·방출·점화 실험으로, 차량 충전 full-loop가 아니다.
- 공개 HRS 운영·가용성 자료는 위치·압력단·가용성 또는 집계 실적 위주라 동기화 충전 transient holdout이 아니다.

따라서 이번 논문 목표에서는 `full_loop_external_validation`을 필수 게이트에서
제거하고, **공개 재사용 가능한 동기화 station-to-vehicle 원자료 부재**를
Data availability / Limitations에 명시한다. 이후 custodian이 비식별 3개 이상
이벤트를 제공하면 별도 프로토콜로 동결한 뒤 선택적 확장 검증으로 재개한다.

## 3. 윤리·전문가 평가의 의미와 현재 결정

이 항목은 물리 모델의 윤리성이나 HAZOP 규칙의 정답을 평가하는 절차가 아니다.
SAGA가 사람의 안전 판단을 개선한다고 주장할 때 필요한 **사람 대상 의사결정
지원 평가**다.

- **윤리 검토**: 기관이 이 평가가 사람 대상 연구인지, IRB 승인·면제·비해당
  결정 중 무엇이 필요한지 공식적으로 판단하는 단계다.
- **전문가 평가**: 수소 안전·공정안전·HAZOP·비상대응 경력자가 같은 HIAD 사건에
  대한 alarm-only, 직접 SAGA, 근거문서 RAG SAGA 답변을 눈가림으로 점수화한다.
  정확성, 즉시조치, 우선순위, 안정화·재가동 조건, 예방관리, 근거성,
  운영자 이해도와 위험한 누락/위험 조언을 평가한다. LLM이 자기 답변을 채점하는
  방식은 사용하지 않는다.

현재는 사람을 모집하거나 답변을 수집하지 않았고 기관 결정도 없다. 따라서
물리·디지털트윈 검증 논문에서는 선택 항목 및 미실시 한계로 둔다. SAGA가 실제
운영자의 안전성을 향상한다고 주장할 때만 IRB/면제/비해당 결정 후 독립 전문가
평가를 재개한다. 관련 동결 프로토콜은
`research/HIAD_EXPERT_STUDY_PREREGISTRATION.md`와
`research/hiad_study_protocol_manifest.json`에 남겨 둔다.
현재 범위 결정은 `research/ETHICS_AND_EXPERT_REVIEW_SCOPE_2026_10_11.md`와
`research/ethics_and_expert_review_scope_decision_2026_10_11.json`에도 고정했다.

## 주장 범위

현재 결과로 주장 가능한 것은 station-side 동역학, 공개 구성요소 검증, 사고·방출
근거에 연결된 SAGA 응답이다. 완전한 station-to-vehicle 현장 정확도, 차량 제어기
인증, SAGA의 사람 대상 안전 효과는 주장하지 않는다.
