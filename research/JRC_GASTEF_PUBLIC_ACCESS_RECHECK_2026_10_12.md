# JRC GasTeF public-access recheck — 2026-10-12

공식 JRC 기록 세 건을 다시 확인했다.

- [JRC76380](https://publications.jrc.ec.europa.eu/repository/handle/JRC76380)
- [JRC90323](https://publications.jrc.ec.europa.eu/repository/handle/JRC90323)
- [JRC80910](https://publications.jrc.ec.europa.eu/repository/handle/JRC80910)

기록에는 GasTeF의 고압 수소탱크 충전 시험, 압력·온도 계측, 시험조건과
참고 데이터의 목적이 설명되어 있다. 그러나 현재 공개 화면의 `Datasets`와
`Dataset collections`에는 해시와 채널 정의를 확인할 수 있는 기계판독 원시
시계열 다운로드 URL이 없다. 원시 trace, 채널 사전, 교정 메타데이터와 재사용
허가도 확인되지 않았다.

보존된 HYTRANSFER 사이트의 [다운로드 페이지](https://arquivo.pt/wayback/20170622141339mp_/https://www.hytransfer.eu/downloads-press-1/)도 추가로 확인했다. 공개 링크 15개는 보고서·발표자료·이미지였고, CSV·XLSX·ZIP 등 기계판독 GasTeF 원시 파일이나 채널 사전은 포함하지 않았다. 따라서 이 경로 역시 원자료를 직접 검증에 사용할 수 있는 공개 데이터셋으로 분류하지 않았다.

따라서 이번 재확인은 **공개 원자료 확보**가 아니라 **관리기관 문의로 이어지는
공식 접근 경로 확인**으로 기록한다. 논문의 독립 수치 holdout이나
station-to-vehicle full-loop 검증으로 승격하지 않았고, 런타임 모델도 변경하지
않았다.

판정: `CONTROLLED_ACCESS_LEAD_NO_PUBLIC_RAW_ARCHIVE`.

다음 단계는 `research/JRC_GASTEF_DATA_REQUEST_DRAFT.md`에 따라 비식별 raw
export, 채널 정의, 교정·불확도 정보와 파생자료 재사용 허가를 요청하는 것이다.
새 trace를 받으면 수치 결과를 보기 전에 별도 protocol과 holdout을 동결한다.
