# KIT LH2 선택 파일 접근 기록 — 2026-10-11

KIT 공개 RADAR 아카이브(10.35097/1483)는 4,971,447,808 byte의 대용량 자료라서 전체를 열지 않고, 현재 확보된 아카이브 접두부에서 완전하게 끝나는 계측 통합문서만 바이트 범위로 분리했다. 헤더와 XLSX ZIP의 시트 이름만 확인했고 셀 값·압력·유량·열유속·영상 결과는 읽지 않았다.

확인된 네 파일은 `ignited_trial_15`, `16`, `17`, `19`이며 모두 `Flexlogger`, `Radiometers`, `Blastlogger`, `BlastloggerClip`, `Xensor`, `Flowmeter`, `LocalWeather` 시트를 포함한다. 파일별 오프셋·크기·SHA-256은 JSON 기록에 고정했다.

현재 아카이브는 964,689,920 byte의 부분 파일이고 출판자 MD5와 일치하지 않는다. 따라서 이 자료를 수치 검증 holdout으로 승격하지 않았다. 전체 아카이브 무결성, 전체 실험 목록과 장치·단위·좌표 문서를 확인한 뒤 별도의 결과 비공개 stage-2 프로토콜을 먼저 고정해야 한다.

근거: `research/kit_lh2_selective_member_inventory_2026_10_11.json`, `research/kit_lh2_consequence_intake_protocol_2026_10_08.json`.
