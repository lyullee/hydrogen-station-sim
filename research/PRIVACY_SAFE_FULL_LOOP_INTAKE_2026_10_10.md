# 비식별 충전 이벤트 입력 안내

충전소 원시 로그를 저장소에 공개하지 않고도 station-to-receiving-vessel 검증을 준비하기 위한 입력 계약이다. 원자료 보관자는 원본 CSV를 계속 보관하고, 저장소에는 검증 결과의 해시와 집계값만 남긴다.

## 최소 파일 형식

이벤트마다 CSV 하나를 사용한다. 시간은 달력 시각이 아닌 이벤트 시작을 0초로 둔 경과 시간이다.

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

## 제출 전 자동 검사

~~~powershell
python -c "from h2station.privacy_safe_full_loop_intake import validate_privacy_safe_pilot_bundle; import pathlib, json; p=sorted(pathlib.Path('pilot_events').glob('*.csv')); print(json.dumps(validate_privacy_safe_pilot_bundle(p), ensure_ascii=False, indent=2))"
~~~

기본 검사는 비식별 이벤트 3건, 단조 증가 시간축, 유한한 수치, 음수 질량유량, 누적질량 역전, 필수 열 누락을 검사한다. 결과에는 event_001 형식의 가상 ID, 행 수, 시간 범위, 채널 존재 여부, SHA-256만 남는다.

READY_FOR_PROTOCOL_FREEZE는 입력 품질이 준비되었다는 뜻이다. 모델 점수나 안전성 검증 결과가 아니며, 그 다음 단계에서 모델과 평가 규칙을 먼저 동결한 뒤 별도의 외부 평가를 실행한다.

## 최소 묶음과 전체 평가

비식별 3건은 수용부 채널의 동기화와 역할을 확인하는 파일럿 묶음이다. 차량 압력·온도까지 포함되면 station-to-receiving-vessel 경계를 재생할 수 있다. 완전한 외부 검증과 일반화 주장은 사전 동결된 disjoint 이벤트 묶음으로 별도 평가한다.

원시 행은 보관자가 관리하고, 저장소에는 원시 데이터 대신 파일 해시·행 수·집계 지표·채널 역할 확인서만 전달한다. 이 절차는 실데이터의 비공개 조건을 유지하면서 재현 가능한 검증 기록을 남기기 위한 것이다.

