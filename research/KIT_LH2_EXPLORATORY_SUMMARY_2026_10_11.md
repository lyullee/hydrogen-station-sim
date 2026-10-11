# KIT LH₂ workbook 탐색 요약 — 2026-10-11

stage-2 탐색 프로토콜에 따라 부분 아카이브에서 완전한 workbook 4개를 읽어 채널 커버리지와 기술통계만 산출했다. `Blastlogger`와 `BlastloggerClip`은 고속 원자료가 파일당 10만~50만 행이어서 헤더·행수만 기록했고, 원시 시계열을 저장하지 않았다.

네 workbook 모두 다음 채널군을 포함한다.

- `Flexlogger`: 주변·열전대 계열
- `Radiometers`: 3개 방사계 채널
- `Xensor`: 다중 출력 채널
- `Flowmeter`: 질량유량·밀도·주파수·진단 신호
- `Blastlogger` / `BlastloggerClip`: 고속 압력·충격 기록 계열로 보이는 19열 구조
- `LocalWeather`: 실내·외 온습도, 압력, 풍속·풍향

관찰된 자료 구조는 수소 방출·점화 consequence 구성요소 분석에 유용하지만, 현재 확보된 것은 전체 아카이브의 일부다. 출판자 MD5가 검증되지 않았고 장치별 단위·좌표·실험 조건 전체가 고정되지 않았으므로 이 요약은 검증 결과가 아니다. 런타임 파라미터와 HyRAM 설정은 변경하지 않았다.

세부 행수·범위·파일 해시는 `kit_lh2_exploratory_summary_2026_10_11.json`과 선택 파일 inventory에 기록했다.
