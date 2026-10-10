# 검증 진행 브리프 (privacy-safe, 2026-10-11)

이 문서는 현재 저장소에 있는 근거의 주장 범위를 기록한다. 원자료 행, 사업장·제조사 식별정보, 절대 경로와 원자료 측정값은 포함하지 않는다.

## 현재 판정

- IJHE 내부 게이트: **PASS 127 / FAIL 10 / PENDING 7**.
- 게이트 충족률: **127 / 144 = 88.2%**. 이는 게재 확률이나 논문 수락 예측이 아니다.
- 제한된 IJHE 투고 준비: **아직 불가**.
- 사용자 목표(독립적인 station-to-vehicle full-loop와 SAGA 효과 근거 포함): **아직 미달**.

## 이번 점검에서 확인한 것

- 우선순위 검증 묶음은 **45/45 통과**, 병렬 실행 시간은 **4.511초**였다. 이는 intake·LLM 근거 경계·가상 안전조치 계약을 검증한 결과이며 과학적 외부 검증을 대신하지 않는다.
- 전체 회귀 테스트는 **1,363 passed, 20 warnings**였다. 경고는 기존 물성 라이브러리와 테스트 의존성 경고이며 검증 게이트 승격 근거로 사용하지 않는다.
- NREL H2FillS HDVS 공개 탱크 자료의 사후 기하 진단에서는 기존 체적 규칙이 **0/7**, 선언 용량을 수소 EOS로 한 번만 환산한 규칙이 **7/7** 탱크 화면을 통과했다. 이 자료는 이미 수치 결과를 연 뒤 비교했으므로 **탐색 진단**이며 공식 게이트나 기본값을 변경하지 않는다.
- MC Default 탱크 경계의 동결 모델은 **0/8** 공동 화면 통과다. 용량-EOS 사후 비교는 **4/8**이지만, 체적 규칙을 결과를 본 뒤 선택할 수 없으므로 공식 결과를 대체하지 않는다.
- Dickens Type-III의 고정 결과는 온도 화면 실패를 유지한다. 5 mm 유입관과 온도 관측 연산자에 대한 후속 진단은 원인 후보를 좁혔지만 사후 선택이므로 검증 게이트를 닫지 않는다.
- 비식별 private station-side 재검은 CSV 8개를 모두 읽었고 수치·행·헤더·경로는 보존하지 않았다. 공통시각·제어상태·질량/유량·압력·온도 후보는 있었지만 cascade/storage, 수용용기 식별·압력·온도, delivered-temperature와 단위·역할 attestation이 없어 full-loop holdout으로 승격하지 않았다. 상세 판정은 `research/local_private_full_loop_schema_recheck_2026_10_11.json`에 기록했다.
- HRS 작업영역과 controlled export를 CSV/XLSX 스키마 인벤토리로 다시 훑어 13개 파일·25개 테이블을 확인했다. 압력·온도·유량·제어상태 후보는 있었지만 full-loop, station-recharge, vehicle-fill 후보가 모두 0건이었다. 이 결과는 행·헤더·경로를 저장하지 않는 [비식별 인벤토리](local_full_loop_schema_inventory_2026_10_11.json)에 기록했다.

## 현재 사용할 수 있는 주장 범위

1. 비식별 station-side 자료는 압력·cascade·재충전 동역학과 시간순 holdout에 사용할 수 있다.
2. 공개 탱크·방출·검지·사고 자료는 구성요소 물리 진단, 사고 시나리오, 단계별 가상 안전조치와 LLM 근거 연결에 사용할 수 있다.
3. capacity-EOS는 명시적으로 선택한 런타임 옵션으로 구현되어 있으며, 용량·정격압력·기준온도를 입력으로 물리 체적을 계산한다. 외부 검증 결과를 본 뒤 기본값으로 자동 전환하지 않는다.
4. SAGA/LLM은 센서·시나리오·피해영향 계산 결과를 근거로 답하도록 경계가 구현되어 있지만, 안전 효과와 운영 성능은 독립 평가가 끝나지 않았다.

## 남은 가장 큰 병목

- 공개 MC·NREL·Type-III 자료는 각각 탱크 또는 경계 구성요소 중심이다. 동기화된 station pressure/temperature/mass-flow, vehicle/receptacle pressure/temperature, protocol state, cascade/controller state, ESD/fault transition을 함께 가진 **새로운 outcome-unseen full-loop 코호트**가 없다.
- 독립적인 HAZOP/SAGA 효과 평가, 전문가 검토, 사고 casebook freeze와 holdout collection이 아직 남아 있다.
- 따라서 현재 88.2%는 구현·근거 게이트의 폐쇄율이며, “검증된 전체 수소충전소 디지털 트윈” 달성률이나 IJHE 게재 가능성을 의미하지 않는다.

## 다음 고효율 작업

1. capacity-EOS·혼합대류 규칙을 사전 동결한 새 external holdout 요청/수집.
2. 공개 사고·검지 데이터에 대해 원인-센서-피해영향-대응 단계의 매핑을 고정하고 SAGA 효과 평가 설계를 완료.
3. 위 자료가 들어오기 전까지는 현재 실패 결과를 유지한 채 논문 방법·한계·재현 패키지를 정리.
