# 외부 원자료 custodian 실행 가이드

기준일: 2026-10-14
목적: 독립 검증 원자료가 확보되는 즉시, 원시 행을 공개 저장소에 복사하지 않고 고정된 모델·프로토콜로 재현 평가를 실행하는 절차를 제공한다.

이 문서는 데이터 요청을 발송했다는 증거가 아니며, 새로운 검증 결과를 만들지 않는다. 현재 열린 검증 게이트의 숫자는 원자료와 권리·역할 증명이 들어오기 전까지 바뀌지 않는다.

## 역할과 저장 경계

| 역할 | 수행 위치 | 저장 가능한 산출물 |
|---|---|---|
| 데이터 custodian | 접근 통제된 원자료 작업공간 | 원시 CSV/XLSX, 원래 태그, 시설·장비 식별자 |
| 검증 담당자 | 깨끗한 소스 커밋의 별도 실행환경 | 모델·평가 프로토콜 해시, 이벤트별 집계 지표, 실패 포함 결과 |
| 공개 저장소 | GitHub/Zenodo | 스키마, 실행 코드, 합의된 집계치와 불확도, 합성 재현자료 |

원시 행, 원래 파일명·경로, 회사·시설명, 제조사·시리얼, 절대 날짜·시각, API 키는 저장소와 공개 프롬프트에 들어갈 수 없다. 재사용 권리가 없으면 원자료를 전달하지 말고 custodian 실행형 결과만 받는다.

## 단계 0 — 요청과 권리 확인

`research/EXTERNAL_RAW_DATA_REQUEST_PACKAGE_2026_10_14.md`의 해당 기관 항목을 사용한다. custodian은 다음을 먼저 확인한다.

1. 최소 채널, 공학 단위, 샘플주기, 교정 상태와 불확도를 확인한다.
2. 이벤트 시작을 0초로 재기준하고, 시설·회사·제조사·정확한 날짜를 제거한다.
3. 파라미터 조정·사례 선택에 원자료를 사용하지 않는다는 점과, 실패 사례도 포함한다는 점을 서면으로 확인한다.
4. 파생 지표의 논문 사용·검토자 열람·해시 공개 권리를 확인한다.

권리·역할·단위가 확인되지 않으면 다음 단계로 넘어가지 않는다.

## 단계 1 — 스키마만 점검

원자료는 저장소 밖에 둔다. 행을 모델 결과에 사용하기 전에 단일 이벤트 또는 최소 pilot bundle을 점검한다.

```powershell
$env:PYTHONPATH = 'src'
python scripts/inspect_privacy_safe_event.py `
  --event <custodian-controlled-event.csv> `
  --require-vehicle-boundary `
  --output <outside-repository>\event_schema_preview.json
```

여러 이벤트의 station·vehicle 파일이 분리되어 있으면 다음 API를 사용한다.

```powershell
$env:PYTHONPATH = 'src'
python scripts/freeze_privacy_safe_full_loop.py `
  --station-events <outside-repository>\station_001.csv <outside-repository>\station_002.csv <outside-repository>\station_003.csv `
  --vehicle-events <outside-repository>\vehicle_001.csv <outside-repository>\vehicle_002.csv <outside-repository>\vehicle_003.csv `
  --protocol research/external_hrs_intake_protocol.json `
  --model <frozen-model-file> `
  --evaluator <frozen-evaluator-file> `
  --channel-roles <private-channel-roles.json> `
  --minimum-event-count 3 `
  --output <outside-repository>\preaccess_freeze_manifest.json
```

단일 파일 이벤트 묶음은 `--events`를 사용한다. 이 단계의 출력은 채널 존재, 시간축 품질, 행 수 집계, SHA-256뿐이다. 출력의 `full_loop_validation_scored`가 `false`인 것은 정상이며, 스키마 통과를 검증 통과로 해석하지 않는다.

## 단계 2 — 결과 열기 전에 평가를 고정

custodian과 검증 담당자는 다음 네 해시를 기록한다.

- 모델 소스 커밋 또는 모델 파일 SHA-256
- 평가 프로토콜 SHA-256
- 평가 코드/실행기 SHA-256
- 비식별 이벤트 파일 SHA-256

`preaccess_freeze_manifest.json`의 `outcomes_accessed_before_freeze`는 `false`, `parameter_fitting_performed`는 `false`, `post_freeze_parameter_tuning_prohibited`는 `true`여야 한다. 수치 결과를 확인한 뒤 모델·임계값·이벤트 분할을 바꾸면 해당 실행은 독립 검증으로 사용할 수 없다.

station-to-vehicle 전체 루프를 주장하려면 모든 이벤트에 차량/리셉터 압력·온도, 공통 상대시간축, 프로토콜 시작·종료 상태가 있어야 한다. 선택된 cascade bank만 있는 자료는 station-to-dispenser 또는 selected-bank 경계로만 분류한다.

## 단계 3 — custodian 환경에서 제한 실행

원자료가 공개될 수 있으면 비식별 export를 사용하되 저장소 밖에서 실행한다. 공개가 불가능하면 custodian이 동일한 커밋과 동결된 프로토콜을 실행하고 다음만 반환한다.

```json
{
  "event_id": "opaque_event_001",
  "source_sha256": "<64-hex>",
  "pressure_rmse_mpa": 0.0,
  "temperature_rmse_c": 0.0,
  "mass_flow_rmse_g_s": 0.0,
  "time_to_half_pressure_error_s": 0.0,
  "bootstrap_interval": {"lower": 0.0, "upper": 0.0},
  "pass_fail_by_frozen_rule": {"pressure": false, "temperature": false},
  "failure_reason": "<if any>"
}
```

위 JSON은 형식 예시다. 실제 값은 결과를 본 뒤 파라미터를 조정하지 않고, 모든 이벤트와 실패 원인을 포함해야 한다. 원자료가 파일로 제공되는 경우에도 `scripts/export_confidential_full_loop_bundle.py`의 저장소 외부 출력 경계를 유지한다.

## 단계 4 — 재현 결과 판정

결과를 받으면 다음 순서로 확인한다.

1. 반환된 `source_sha256`가 pre-access manifest와 일치하는지 확인한다.
2. 모델·프로토콜·평가 코드 해시가 동결 manifest와 일치하는지 확인한다.
3. 이벤트 누락, 선택적 성공 보고, 단위·시간축 변경, 사후 파라미터 튜닝이 없는지 확인한다.
4. 사전 선언된 압력 NRMSE, 온도 RMSE, 질량유량 오차, half-pressure 시간 오차와 bootstrap 불확도를 이벤트별로 보고한다.
5. 고정 화면을 모두 통과한 경우에만 해당 구성요소 게이트를 PASS로 올린다. 하나라도 실패하면 FAIL을 유지하고 실패 원인을 기록한다.

스키마 점검 또는 custodian 실행형 집계만으로는 안전거리, 화재·폭발, 규제 적합성, 운영자 대응 효과, 완전 station-to-vehicle 정확도를 주장하지 않는다.

## 열린 게이트별 최소 추가자료

| 게이트 | 필요한 독립 자료 | 현재 허용되는 주장 |
|---|---|---|
| Dickens Type-III | 충전 압력과 가스 온도 원시 시계열, 경계조건 | 압력 결과만 유지; 온도·공동 검증은 보류 |
| Grüne/KIT | 권리 정리된 pressure-time 원자료와 노즐 조건 | 공개 도표 진단은 참고 전용 |
| Schefer/Sandia | 압력감쇠·질량유량 시계열과 용기/제한부 정보 | 기존 실패 결과 유지 |
| PRESLHY | 시험별 압력·유량·온도, 밸브/배관 재고와 열경계 | 공개 캠페인 결과는 고정 프로토콜 범위로만 해석 |
| H2SAFE/공간 검증 | 실제 수소, 방출 좌표·방향·센서 응답 | 좌표 기반 개발 진단만 허용 |
| station-to-vehicle | 공통 시계열의 station·dispenser·vehicle 채널과 권리 증명 | 현재 논문 주 범위에서는 full-loop 주장 제외 |

## 종료 조건과 기록

각 실행은 `raw_rows_persisted=false`, `source_paths_published=false`, `model_scoring_performed`의 실제 상태, `claim_boundary`, 실패 포함 이벤트 수를 남긴다. 독립 원자료가 없으면 상태를 PASS로 바꾸지 않고 `PENDING` 또는 기존 `FAIL`을 유지한다. 이 가이드는 검증 작업의 반복 비용을 줄이지만, 데이터 접근 자체를 대신하지 않는다.
