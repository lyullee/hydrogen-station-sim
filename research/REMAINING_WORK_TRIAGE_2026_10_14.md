# IJHE 목표 잔여 작업표 — 2026-10-14

이 문서는 현재 저장소의 검증 상태를 빠르게 판단하기 위한 작업표다. 진행률은 코드 기능의 완성도가 아니라, 사전에 고정한 독립 검증 게이트가 닫힌 비율이다.

## 현재 상태

- 현재 readiness 게이트: **134 PASS / 11 FAIL / 7 PENDING = 88.2%**
- 이전 주 범위 보고서의 **133 PASS / 10 FAIL / 2 PENDING = 91.7%**는 별도 축약 분모이며 현재 제출판정과 혼용하지 않는다.
- 전체 회귀: **1,578 passed / 0 failed / 0 skipped / 222 warnings**
- 최근 회귀 기록: `research/full_regression_test_run_2026_10_14.json` (실행 당시 구현 커밋 `c2d9b2f`; 이후 원고 패키지 커밋 `b7357f9`)
- 런타임 승격이 금지된 후보: Type-III 열전달 수정안, H2SAFE 공간 검지기 후보, 사후 보정된 누출·영향 모델
- NREL H2FillS: `nrel_h2fills_2022_hdvs_typeiv.xlsx` 한 파일만 보유하며 이미 수치 결과를 확인했다. 따라서 새 독립 holdout으로 재사용하지 않는다.

## 이번 즉시 처리 완료
- 방출모델 실패 게이트 교차분석을 `research/RELEASE_FAILURE_CROSSWALK_2026_10_14.md`와 `research/release_failure_crosswalk_2026_10_14.json`에 고정했다. Schefer·PRESLHY·Proust 실패를 장치 경계/라인·밸브, 직경·유동영역, 열경계의 네 공통 원인으로 묶었으며, 이 진단은 기존 판정과 런타임 파라미터를 변경하지 않는다.
- SAGA 직접응답 경로 회귀를 별도 실행해 55 passed / 0 failed / 0 skipped를 확인했다. 직접 질의·피해영향평가 전달·가상 조치 명령·측정값 guard·응답 선택성 범위를 `research/direct_answer_llm_regression_2026_10_14.json`에 고정했다.

- Figshare 실제 수소 개방형 채널 22개 archive에 고정 공간순위 후보를 재현 실행했다.
- 결과: 중앙 Spearman ρ `0.658`, 평균 top-5 recall `0.727`; 최근접 센서 사분위 적중률은 `0.545`로 전체 joint screen은 실패했다.
- 자료를 과거 진단에서 이미 열어 보았으므로 이번 결과는 `POST_ACCESS_TRANSFER_DIAGNOSTIC`이며 독립 검증 게이트·runtime 라우팅·진행률을 변경하지 않는다. 재현 결과는 `research/figshare_h2_channel_spatial_holdout_result_2026_10_14.json`에 고정했다.
- NBSDC 액체수소 충전소 운영 데이터 후보도 공식 카탈로그 API로 재확인했다. 35 MPa 충전기, 70 MPa 충전기, 90 MPa 압축기, 고압 저장용기, 액체수소 펌프·저장탱크 파일 목록은 공개되어 있지만 원자료 다운로드는 데이터 신청으로 제한된다. 따라서 수치 검증·독립 holdout·runtime 승격에는 사용하지 않았고, 접근 경계는 `research/nbsdc_lh2_station_access_recheck_2026_10_14.json`에 고정했다.
- 사용자 로컬 FTPData와 통제된 HRS 내보내기를 다시 확인했다. FTPData에는 수치 시계열 파일이 없고 사진·영상·문서만 있어 물리 holdout을 만들 수 없었다. 별도 21개 테이블 스키마에서도 압력·온도·유량·제어상태 표는 존재하지만 시간 중첩 클러스터와 full-loop 후보가 모두 `0`이며 원시 행·태그·단위는 보존하지 않는다. 이 결과는 `research/local_data_access_boundary_2026_10_14.json`과 `research/local_hrs_schema_consistency_recheck_2026_10_14.json`에 고정했다.
- Schefer 2007 장치 경계의 누락 원인을 분리하기 위해 벽 열용량·외부 열전달계수 16개 조합의 비단열 민감도 진단을 실행했다. 최선 조합도 압력 NRMSE `10.98%`, 중앙 APE `24.92%`로 고정 화면을 통과하지 못했다. 이 결과는 `research/schefer_2007_nonadiabatic_diagnostic_2026_10_14.json`에 보존했으며, 기존 holdout·런타임·진행률은 변경하지 않았다.
- Grune 2014의 KIT 서지 기록과 공개 ICHS/HyTunnel 요약을 다시 확인했지만, 권리 정리된 원시 pressure-time 표나 전체 logger export는 찾지 못했다. 공개 자료는 0.37 dm³ 저장조, 최대 약 200 bar, 3/4/10 mm 노즐과 밸브 개방 조건을 설명하는 경계자료로만 사용하고, 검증 게이트는 계속 보류한다.
- PRESLHY E3.1 공개 워크북 6개 아카이브(33개 시험, 5개 실제 수소 농도 채널)를 사용해 농도 검지 수송지연의 사후 진단을 추가했다. 압력 기반 방출시점 대비 농도 검지 onset 중앙 지연은 보정 전 `4.40 s`, 문헌상 3.75 s 타임스탬프 보정 후 `0.65 s`였다. 이 결과는 시간표시·불확실성 문맥만 보완하며, 독립 검증 게이트·알람 임계값·런타임 검지기 배치는 변경하지 않는다. 결과는 `research/preslhy_e31_concentration_transport_diagnostic_2026_10_14.json`에 고정했다.
- 2026-10-14 공개자료 재검색에서 JRC/GasTeF 원시 시계열, 유럽 H2-Stations API, DTU Modelica 라이브러리, California in-use 보고서를 확인했다. 새 권리정리 원자료 holdout은 발견되지 않았고, 이미 개방한 H2SAFE·ELVHYS·USN 자료는 재사용하지 않았다. 상세 경계와 다음 수집 조건은 `research/public_data_search_recheck_2026_10_14.json`에 고정했다.
- 같은 검색 라운드에서 NHyRA H2 releases database 1차 공개 문서와 HyTunnel-CS 공개 저장소 목록도 재확인했다. NHyRA 문서는 case-level 원시 시계열을 제공하지 않고, HyTunnel 목록은 이미 확인한 저장소의 카탈로그이므로 새 독립 holdout으로 계상하지 않았다. 이 반복 검색을 종료 조건에 반영해 같은 자료를 다시 조사하지 않도록 `research/public_data_search_recheck_2026_10_14.json`에 기록했다.
- Grüne·Sempert의 Zenodo PS 데이터셋(DOI `10.5281/zenodo.4668554`)을 추가 확인했다. CC BY 4.0 공개자료이며 실제 수소 농도 공간표 41개, 환기 조건과 CAD 맥락을 포함하지만 현재 공간분석을 이미 본 뒤 접근했고 시간 동기화된 충전소 자료가 아니므로 H2SAFE 독립 게이트에는 승격하지 않았다. 무결성·구조는 `research/grune_ps_h2_dispersion_intake_2026_10_14.json`에 고정했다.
- 같은 자료의 실제 수소 농도 공간표 41개, 5,148개 측정점을 모두 재현 읽기해 0.2/0.4/4.0 vol% 기준의 공간 점유율과 좌표 범위를 요약했다. 중앙 4.0 vol% 이상 점유율은 27.8%였으며, 이는 개발·논문 문맥용 공간 스냅샷 진단일 뿐 안전거리·대피반경·검지기 설정값으로 승격하지 않았다. 결과는 `research/grune_ps_actual_h2_spatial_diagnostic_2026_10_14.json`에 고정했다.
- 추가로 Cal State LA의 1년 실충전 운영 연구(DOI `10.1016/j.jclepro.2021.129737`)와 MetHyTrucks HySam 공개 XLSX(DOI `10.5281/zenodo.20590842`)를 확인했다. 전자는 원시 station/vehicle logger export가 공개 접근 경로에 없고, 후자는 샘플링 시스템 조건자료라 station-to-vehicle 또는 station-side 방출 holdout이 아니다. 둘 다 경계자료로만 기록했다.
- 최신 IJHE Type III/IV 충전 연구(DOI `10.1016/j.ijhydene.2026.156406`)도 확인했지만, 공개 접근 경로에서 원시 압력·온도·시간 파일과 권리정리된 보충 아카이브를 찾지 못해 경계자료로만 기록했다.
- ICHS 2011 전면규모 차고 방출 실험은 실제 수소/혼합가스 센서 위치·응답시각 근거를 추가했지만, 원시 시계열과 재사용 조건이 없어 H2SAFE 공간 holdout을 닫지 못한다.
- 차량탱크 경계조건의 영향도를 수치로 분리했다. MC 8개 시험에서 입구 엔탈피 압력을 공개된 `source_pressure_1`로 둘 때 압력 RMSE 평균은 `2.19 MPa`로 줄지만 온도 RMSE는 `23.28 °C`, SOC RMSE는 `5.58 pp`로 남았다. `source_pressure_3`도 압력 `1.82 MPa`까지 낮추지만 온도 `25.88 °C`와 SOC `5.58 pp`를 동시에 개선하지 못했고, 차량 압력을 쓰는 기존 경계는 온도 `9.05 °C`만 낮출 뿐 압력 `4.38 MPa`가 남는다. 따라서 공개 자료만으로 하나의 입구 경계를 선택해 런타임에 승격할 수 없으며, 원자료가 제공하는 노즐 상류 압력·온도 계측이 다음 독립 검증의 필수 입력이다. 진단 원본은 `research/mc_enthalpy_pressure_sensitivity_2026_10_05.json`이다.

## 먼저 처리할 수 있는 작업

### 1. 투고 메타데이터 잠금 — 즉시 가능

실제 저자·소속·기여·이해상충·연구비·AI 사용 공개만 확인하면 `submission_metadata.json`을 잠글 수 있다. 이름이나 소속을 추정해서 채우지 않는다. 이 작업은 수치 검증과 독립적으로 진행된다.

### 2. 논문 주장 범위 정리 — 즉시 가능

현재 통과한 구성요소 결과만 본문 주장에 사용하고, 다음은 명시적 한계로 유지한다.

- station-to-vehicle 공통 시계열 전체 루프
- 야외 수소 제트화재·폭발 영향거리
- 운영자 대응 효과와 안전성 개선
- 실제 시설의 법정 안전거리·규제 적합성

### 3. 실패 게이트의 재현성 보존 — 즉시 가능

실패한 결과는 재튜닝으로 PASS로 바꾸지 않고, 실패 물리량·경계조건·필요한 새 입력을 그대로 기록한다. 현재 전체 회귀와 비밀값 감사는 통과 상태다.

## 새 원자료가 있어야 닫히는 작업

### P0 — Type-III 탱크 열전달

기존 Dickens 시험은 압력은 통과했지만 온도는 실패했다. 원문과 보관본의 탱크 길이 차이, 5 mm/82 mm 입구 형상, 시간별 입구 온도 경계를 먼저 확정한 뒤 새 미개봉 충전·방출 trace가 필요하다.

### P0 — 누출·영향 모델

현재 통과한 것은 제한된 방출·밀폐공간 압력 피크 구성요소다. 야외 제트화재·복사열·과압 거리는 실험 holdout이 없어 닫을 수 없다. 시뮬레이션 앙상블은 불확실성 문맥으로만 사용한다.

### P0 — 공간 검지기 배치

실제 수소 독립 holdout 18건에서 평균 top-5 recall이 0.578로 동결 기준 0.600에 미달했다. HVAC 벡터·하향 제트·장애물 정보를 포함한 후보를 개발용으로 만든 뒤, 별도의 미개봉 실제 수소 cohort에서 다시 평가해야 한다.

### P0 — Grüne 압력 감쇠 원자료

현재 공개 도표를 디지털화한 진단은 1차 화면을 통과하지 못했고, 권리 정리된 원시 pressure-time 표가 없다. 원자료와 재사용 조건을 받은 뒤에만 새 프로토콜을 동결한다.

### P0 — 제출 메타데이터

저자·소속·기관 이메일·CRediT·이해상충·연구비·AI 사용 공개를 실제 저자 확인으로 잠가야 한다. 현재는 추정 입력을 하지 않고 대기한다.

## 반복하면 안 되는 작업

- 이미 열어 본 NREL·MetHyTrucks·H2SAFE 파일을 새 독립 holdout으로 재계상
- 실패 결과를 맞추기 위한 사후 파라미터 선택
- 시뮬레이션 앙상블을 실험 검증으로 표현
- 회사·시설·제조사·정확한 날짜가 식별되는 원시 행을 저장소나 논문에 복사

## 목표 종료 조건

주 범위의 FAIL 게이트를 새 독립 자료로 재평가하고, 투고 메타데이터를 잠근 뒤에야 “목표 달성”으로 표시한다. 현재는 코드·재현성·근거 추적은 정리되어 있지만, 독립 물리 검증 세 축이 남아 있어 종료 상태가 아니다.


- 최신 critical 우선순위 재실행(`research/priority_focus_run_2026_10_14.json`): 소프트웨어 검사는 PASS(LLM 근거 경계 24건, full-loop 입력 경계 19건, 가상 안전·대응 25건)였고 약 5.0초에 완료됐다. 과학적 화면은 `mc_tank_boundary`(8건 중 0건), `h2safe_spatial_response`(1개 화면 실패), `nrel_h2fills_hdvs_tank`(7건 중 0건)에서 실패했다. 이 결과는 개발 진단으로만 보존하며 런타임 파라미터·독립 검증 게이트·논문 주장을 변경하지 않는다.
