# 비공개 실측 운전영역 프로필 재검산

소유자 관리 원자료를 저장소 밖에서 다시 집계하고, 저장소에 동결된 비식별
운전영역 프로필과 핵심 압력·시간 품질값을 대조하는 절차다. 실행 도구는
`scripts/recheck_confidential_operational_profile.py`이며 원자료 경로와 매핑은
호출자가 제공한다. 결과 파일에는 원시 행, 태그명, 위치, 운영자, 제조사,
원본 날짜 또는 원자료 경로를 기록하지 않는다.

대조가 일치하면 기존 프로필을 유지하고 `measured_boundary_calibration`을 켠
실행에서만 적용한다. 불일치하면 프로필을 자동 교체하지 않고 소유자 검토를
요구한다. 온도·유량·이산 상태 매핑이 제공되지 않은 실행에서는 해당 항목을
일치로 간주하지 않고 `fields_omitted_without_attestation`에 남긴다.

이 절차는 station-boundary 보정의 재현성과 provenance를 확인할 뿐이다. 차량측
채널, 디스펜서 프로토콜, 전체 station-to-vehicle 정확도, 사고 빈도, 안전거리
또는 안전 인증을 입증하지 않는다.
