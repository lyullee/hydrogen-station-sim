# 비식별 충전 이벤트 입력 안내

충전소 원시 로그를 저장소에 공개하지 않고도 station-to-receiving-vessel 검증을 준비하기 위한 입력 계약이다. 원자료 보관자는 원본 CSV를 계속 보관하고, 저장소에는 검증 결과의 해시와 집계값만 남긴다.

## 최소 파일 형식

이벤트마다 CSV 하나를 사용한다. 시간은 달력 시각이 아닌 이벤트 시작을 0초로 둔 경과 시간이다.
CSV와 같은 열 구조의 XLSX/XLSM 워크북도 사용할 수 있으며, 기본 active
worksheet 또는 `--xlsx-worksheet`로 지정한 시트를 행 단위로 읽는다. 원본
워크북의 셀과 행은 결과 JSON에 기록하지 않는다.

| 열 | 단위 | 필수 | 의미 |
| --- | --- | --- | --- |
| elapsed_time_s | s | 예 | 이벤트 시작 기준 단조 증가 시간 |
| station_pressure_mpa | MPa | 예 | 충전기 또는 공급 경계 압력 |
| delivered_gas_temperature_c | °C | 예 | 디스펜서 출구 또는 전달가스 온도 |
| mass_flow_g_s 또는 transferred_mass_kg | g/s 또는 kg | 예 | 질량유량 또는 누적 전달질량 |
| protocol_phase | 문자열 | 예 | start, fill, hold, stop 등 |
| vehicle_pressure_mpa | MPa | 권장 | 수용 용기 압력 |
| vehicle_temperature_c | °C | 권장 | 수용 용기 온도 |
| selected_cascade_bank | 문자열 | 선택 | 선택된 뱅크 |
| precooler_outlet_temperature_c | °C | 선택 | 프리쿨러 출구 온도 |
| esd_state / fault_state | 문자열 | 선택 | ESD·고장 상태 |

사이트명, 회사명, 제조사, 시리얼, 주소, 달력 날짜와 실제 타임스탬프 열은 포함하지 않는다. 이벤트 파일명도 결과에는 기록되지 않는다.

station과 차량 로그가 별도 export로 제공되는 경우에는 파일을 임의로 합치지
않고 `validate_privacy_safe_split_event_bundle`에 `(station, vehicle)`
쌍으로 전달한다. 검사기는 두 파일을 행 단위로 스트리밍하며 `elapsed_time_s`
축을 기본 1 µs 허용오차로 대조한다. 행 수가 다르거나 시간축이 어긋나면
`channel_row_count_mismatch` 또는 `channel_time_axis_mismatch`로 해당 이벤트를
실패 처리하고, 원시 행은 저장하지 않는다. 이 경로도 공통 샘플 간격과 공정단계
검사를 통과해야 full-loop 프로토콜 동결 후보가 된다.
역할 확인서와 프로토콜·모델·평가기 해시까지 준비된 경우에는 같은 쌍을
`build_privacy_safe_split_freeze_manifest`에 전달해 분리된 원자료를 합치지
않은 채 pre-access freeze manifest를 만들 수 있다.

CLI에서는 다음처럼 두 목록을 같은 순서로 전달한다.

~~~powershell
python scripts/freeze_privacy_safe_full_loop.py `
  --station-events station_events\*.csv `
  --vehicle-events vehicle_events\*.csv `
  --protocol protocol.json --model model.py --evaluator evaluator.py `
  --channel-roles roles.json --output freeze_manifest.json
~~~

결합형 워크북을 쓰는 경우에는 `--events event_*.xlsx --xlsx-worksheet trace`
처럼 지정한다. 분리형 입력은 CSV, XLSX, XLSM 또는 서로 다른 형식의 혼합
쌍을 지원하며, 워크북 시트가 고정되어 있으면 다음처럼 채널별로 지정한다.

~~~powershell
--station-xlsx-worksheet station --vehicle-xlsx-worksheet vehicle
~~~

CSV·XLSX 혼합 쌍도 같은 행 수, 시간축, 샘플 간격, `protocol_phase` 및 차량
경계 검사를 통과해야 한다. 시트 이름과 셀 값은 manifest에 저장되지 않는다.

두 목록의 위치가 서로 다른 이벤트를 가리키지 않도록 제출 전에 파일명·순서를
보관자 측에서 고정하고, 결과의 `event_###` ID와 digest만 평가 담당자에게
전달한다.

## 제출 전 자동 검사

보관자에게는 [빈 이벤트 템플릿](privacy_safe_full_loop_event_template.csv)과 [채널 역할 예시](privacy_safe_full_loop_channel_roles.example.json)를 함께 전달한다. 템플릿은 헤더만 포함하며 실제 행·시설명·파일명 규칙을 저장소에 추가하지 않는다. 이벤트별 원본은 보관자가 보관하고, 평가 담당자에게는 아래 사전검사 결과와 해시만 전달한다.

~~~powershell
python -c "from h2station.privacy_safe_full_loop_intake import validate_privacy_safe_pilot_bundle; import pathlib, json; p=sorted(pathlib.Path('pilot_events').glob('*.csv')); print(json.dumps(validate_privacy_safe_pilot_bundle(p), ensure_ascii=False, indent=2))"
~~~

`READY_FOR_FULL_LOOP_PROTOCOL_FREEZE`가 나오더라도 이는 수용부 채널까지 갖춘 입력 후보라는 뜻이다. `FROZEN_BEFORE_OUTCOME_ACCESS` manifest를 만든 뒤에야 모델 결과를 열어야 하며, 원시 CSV·경로·시설 식별자는 결과 JSON에 남기지 않는다.

기본 검사는 비식별 이벤트 3건, **각 이벤트가 0초에서 시작하는 공통 경과시간 축**, 단조 증가 시간축, 유한한 수치, 음수 질량유량, 누적질량 역전, 필수 열 누락을 검사한다. 이벤트가 서로 다른 기준 시각에서 시작하면 `elapsed_time_does_not_start_at_zero`로 거부한다. 각 파일의 샘플 간격 평균·최소·최대와 변동률도 계산하고, 기본 변동률 5%를 넘거나 이벤트 간 공통 샘플 간격을 만들 수 없으면 full-loop 프로토콜 동결 후보에서 제외한다. `protocol_phase`가 빈 행도 거부한다. 결과에는 event_001 형식의 가상 ID, 행 수, 시간 범위, 채널 존재 여부, SHA-256만 남고 `full_loop_readiness.common_elapsed_time_axis`와 `common_sample_period_s`에 동기화 검사 결과가 기록된다.

`READY_FOR_PROTOCOL_FREEZE`는 station 경계 입력의 형식과 품질이 준비되었다는 뜻이다. 차량 압력·온도 두 열이 모든 이벤트에 있지 않으면 이 상태만 부여되며, station-to-vehicle full-loop 후보가 아니다. 이 경우에도 모델 점수나 안전성 검증 결과를 의미하지 않는다.

세 이벤트 모두에 `vehicle_pressure_mpa`와 `vehicle_temperature_c`가 있고, 동기화 축과 공통 샘플 간격 검사를 통과하면 상태가 `READY_FOR_FULL_LOOP_PROTOCOL_FREEZE`로 표시된다. 차량 채널만 있고 시간축 품질이 맞지 않으면 `READY_FOR_PROTOCOL_FREEZE`에 머물러 full-loop 후보로 승격되지 않는다. 이것은 full-loop 평가를 시작할 수 있는 **자료 계약 후보**라는 의미일 뿐이다. 실제 freeze manifest가 full-loop 후보로 표시되려면 두 차량 채널의 역할 확인서도 있어야 한다. 프로토콜·모델·평가기를 결과를 보기 전에 해시 고정하고, 사전 선언된 독립 평가를 통과하기 전에는 full-loop 검증이나 안전성 주장을 하지 않는다. 보고서의 `full_loop_readiness.claim_supported`는 항상 `false`로 남는다.

사전 동결 manifest 생성 절차는 [PRIVACY_SAFE_FULL_LOOP_FREEZE_2026_10_10.md](PRIVACY_SAFE_FULL_LOOP_FREEZE_2026_10_10.md)에 있다. 이 단계는 코드·프로토콜·이벤트 해시와 채널 역할만 잠그며, 결과를 보거나 모델을 조정하지 않는다.

## 최소 묶음과 전체 평가

비식별 3건은 수용부 채널의 동기화와 역할을 확인하는 파일럿 묶음이다. 차량 압력·온도까지 **세 이벤트 모두**에 포함되면 station-to-receiving-vessel 경계를 재생할 수 있는 full-loop 프로토콜 동결 후보가 된다. 하나라도 빠지면 station 경계 자료로만 기록하고 수용부 관련 주장을 열지 않는다. 완전한 외부 검증과 일반화 주장은 사전 동결된 disjoint 이벤트 묶음으로 별도 평가한다.

원시 행은 보관자가 관리하고, 저장소에는 원시 데이터 대신 파일 해시·행 수·집계 지표·채널 역할 확인서만 전달한다. 이 절차는 실데이터의 비공개 조건을 유지하면서 재현 가능한 검증 기록을 남기기 위한 것이다.
