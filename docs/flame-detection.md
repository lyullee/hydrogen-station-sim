# 가상 화염검지 연동

수소 화염은 주간에 육안으로 확인하기 어렵다. [H2Tools의 화염검지 지침](https://h2tools.org/bestpractices/hydrogen-properties-and-leak-detection-considerations/flame-detection)과 [충전소 지침](https://h2tools.org/bestpractices/gaseous-gh2-and-liquid-hydrogen-lh2-fueling-stations)을 참고해 공급부, 압축기, 저·중·고압 저장뱅크, 두 디스펜서, 프리쿨러, 벤트·헤더의 가상 검지 채널 9개를 추가했다. `scripts/add_flame_detectors.py`가 기존 SQLite 정의 DB에 FD 센서·규칙·매핑·출처를 중복 없이 적용한다.

`external-fire`는 사고 **입력**이다. 모델에서 해당 대상에 대응하는 FD 채널은 화재 입력 후 0.5초가 경과하면 1, 그 전과 사고 종료 후에는 0을 출력한다. 화재가 없는 구역의 FD는 0을 유지한다. 규칙은 양호한 FD 신호가 0.5 이상일 때만 화염검지 경보 후보로 올린다. 3D·공정도·센서 목록·SAGA 분석도 사고 입력과 FD 검지를 구분한다.

이 신호는 주입된 사고 위치와 모의 응답시간으로 계산한 **가상 대리 신호**다. 실제 광학 센서의 시야, 차폐, 오경보, 고장, 검교정, 환경 영향을 검증한 결과가 아니다. 실제 설비에 연결할 때는 현장 구역 배치와 센서 적합성, 안전 PLC 입력 및 차단 동작을 별도로 설계·검증해야 한다. 현재 DB 규칙의 현장활성화는 `false`이며, FD 규칙은 실제 PLC를 구동하지 않는다.
