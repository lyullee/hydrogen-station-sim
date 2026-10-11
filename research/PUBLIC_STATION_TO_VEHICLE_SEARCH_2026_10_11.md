# 공개 station-to-vehicle 원자료 검색 결과 — 2026-10-11

이번 검색은 **동기화된 원시 시계열을 실제로 내려받아 재사용할 수 있는지**만 확인했다. 논문, 시험 보고서, 집계 그래프, 상용/등록형 시뮬레이터 출력은 원자료로 세지 않았다. 2026-10-11에 공식 설명 페이지와 공개 문서를 다시 확인하고, 각 항목이 제공하는 데이터의 종류와 검증 admissibility를 분리해 기록했다.

| 출처 | 공개적으로 확인한 범위 | 판정 |
|---|---|---|
| [FCH2RAIL D6.1](https://fch2rail.eu/wp-content/uploads/2025/01/FCH2RAIL_D6.1_Report-on-KPI-assessment.pdf) | 철도 차량 탱크·충전소 압력/온도/질량유량을 기록했다는 집계 설명 | 원시 파일·재사용 조건 미확인 |
| [DLR/FCH2RAIL 논문](https://elib.dlr.de/213625/1/manuscript_final_published_version.pdf) | 탱크 압력, 디스펜서 압력, 온도, 질량유량 예시 | 예시 trace만으로 holdout 불가 |
| [NREL H2FillS](https://www.nrel.gov/hydrogen/h2fills) | 완전 충전소/차량 모델과 실험 데이터가 있다는 설명 | 등록·제공기관 승인 전 원시 파일 미확인 |
| [NREL H2FillS 사용자 설명서](https://www.nrel.gov/docs/libraries/hydrogen/h2fills-user-manual.pdf) | station→FCEV 열유체 모델, 압력·온도·질량유량 출력 및 경험자료 기반 검증 설명 | 모델/소프트웨어 문서이며 권리 확인된 station-to-vehicle logger 묶음은 아님 |
| [JRC reference data](https://www.researchgate.net/publication/262017374_JRC_reference_data_from_experiments_of_on-board_hydrogen_tanks_fast_filling) | 다수 충전 사이클과 압력/온도 trace 설명 | 공개 재사용 가능한 동기화 station-side 파일 미확인 |
| [ESST 2020 dispenser study](https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702.shtml) | 35/70 MPa 실험 요약과 보충 표 | 3행 요약표만 확인, full-loop 원자료 아님 |
| [H2-Stations API v2](https://docs.h2-stations.eu/for-data-users/api-v2/) | 유럽 충전소 배치·디스펜서·노즐·저장장치와 availability/usage/storage/pricing 신호 | 차량 탱크 압력·온도, 공통 시각축, 원시 제어기·ESD trace가 없어 station registry context만 가능 |
| [H2-Stations 데이터 사용자 문서](https://docs.h2-stations.eu/for-data-users/) | 정적 station 정보와 availability·usage·hydrogen storage·pricing export API | 등록/운영 신호와 집계 수준이며 station·vehicle 동기 원시 충전 trace가 아님 |
| [European Hydrogen Observatory HRS 데이터](https://observatory.clean-hydrogen.europa.eu/hydrogen-landscape/distribution-and-storage/hydrogen-refuelling-stations) | 위치, 운영 여부, dispenser type 및 XLSX station inventory | 시설 목록·시점별 집계 자료로서 vehicle-side transient 원자료가 아님 |
| [ENDA HRS Connect](https://enda.eu/en/h2_monitoring) | 90개 HRS의 75–400개 신호를 짧은 간격으로 기록하는 실제 모니터링 시스템 설명 | 원자료 공개·재사용 경로와 차량 측 채널이 없어 접근 요청 후보로만 기록 |
| [Lototskyy et al. (2020)](https://doi.org/10.1016/j.ijhydene.2019.05.133) | 38개월 실제 HRS 운전, 압력·온도 그래프와 제어 순서 | 그래프·운영 요약만 공개되어 기계판독 full-loop holdout 불가 |

## 결론

공개 검색과 로컬 비식별 스키마 점검에서 **station·dispenser·vehicle/receptacle·공통 시각축·제어/ESD 상태·재사용 권한**을 한 묶음으로 충족하는 원자료는 확인되지 않았다. H2FillS는 station-to-vehicle를 모사하고 경험자료로 검증한 소프트웨어지만, 이번 저장소가 재사용할 수 있는 원시 logger archive를 제공하는 자료원으로 확인되지 않았다. H2-Stations와 European Hydrogen Observatory는 정적·가용성·사용량·저장량 또는 시설 목록을 제공하지만 차량 탱크와 station 제어의 동기 transient를 제공하지 않는다. 따라서 이 항목은 주 목표에서 제거하고, 논문에는 다음 한계를 쓴다.

> 본 연구는 station-side 수소충전소 디지털 트윈과 구성요소 검증에 초점을 둔다. 공개 재사용 가능한 동기화 station-to-vehicle 원자료가 없어 차량 측 제어기와 완전한 현장 full-loop 검증은 수행하지 않았으며, 해당 결과를 현장 충전소 안전성이나 차량 인증으로 확대 해석하지 않는다.

이 검색 결과는 원자료 부재를 입증하는 것이 아니라, **현재 공개 접근 경로에서 검증에 사용할 수 있는 파일을 찾지 못했다는 범위 기록**이다. 향후 승인된 custodian 파일이 들어오면 별도 사전 동결 절차로 평가한다.

## 논문에서 허용할 표현

- 허용: “공개된 문헌·시뮬레이터 설명·station registry를 조사했으나, 권리 확인된 동기 station-to-vehicle 원자료를 validation holdout으로 채택하지 못했다.”
- 금지: “공개 station-to-vehicle 데이터가 존재하지 않는다”라고 단정하거나, H2FillS 출력·예시 figure를 실측 외부검증으로 계산하는 표현.
- 향후 재개 조건: station/dispenser와 vehicle/receptacle 채널, 공통 clock, 단위·프로토콜 메타데이터, 최소 3개 독립 충전 episode, 재사용·출판 권리를 custodian이 확인하고 해시를 사전 동결할 것.
