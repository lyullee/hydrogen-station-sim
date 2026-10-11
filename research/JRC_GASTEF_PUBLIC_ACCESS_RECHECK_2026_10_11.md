# JRC GasTeF public-access recheck — 2026-10-11

## 확인한 공개 범위

공개된 JRC GasTeF 논문은 70 MPa Type-III 40 L 탱크를 포함한 시험 구성을
설명한다. Type-III 시험은 총 23건으로 요약되어 있고, 탱크·가스라인 압력과
내부/외부 온도를 계측하며, 압력·온도 로깅 간격은 0.6 s로 기술되어 있다.
시험 조건 표에는 시작·종료 압력, APRR, 초기 온도가 제공된다.

- 논문: [JRC reference data from experiments of onboard hydrogen tanks fast filling](https://doi.org/10.1016/j.ijhydene.2014.03.227)
- 공개 PDF: [GasTeF reference-data paper](https://hysafe.info/ichs2013/images/papers/106.pdf)
- 공식 JRC 기록: [JRC76380](https://publications.jrc.ec.europa.eu/repository/handle/JRC76380)

## 원자료 접근 판정

논문과 공식 기록에서 확인되는 것은 시험 설명, 표, 그래프와 데이터베이스의
존재를 알리는 문구다. 현재 공식 기록의 `Datasets`와 `Dataset collections`에는
기계판독 압력·온도·시간 파일의 다운로드 URL 또는 원시 trace 재사용 조건이
없다. 따라서 다음 자료는 이번 릴리스의 독립 수치 holdout으로 사용하지 않는다.

- 논문 표·그래프를 digitize한 값
- 시험조건만 있는 표
- 데이터베이스가 존재한다는 설명

판정: `CONTROLLED_ACCESS_LEAD_NO_PUBLIC_RAW_ARCHIVE`.

이 결과는 데이터가 존재하지 않는다는 뜻이 아니다. 현재 공개 접근 경로에서
해시·채널 정의·단위·품질 플래그·재사용 허가를 갖춘 파일을 확보하지 못했다는
뜻이다. JRC 또는 지정 custodian이 비식별 원시 export와 서면 재사용 허가를
제공하면, 결과를 보기 전에 별도 protocol과 holdout을 동결한다.

## 주장 경계

현재 자료로는 GasTeF의 설비 구성, 계측 종류, 시험조건, Type-III 열응답의
문헌 근거를 설명할 수 있다. 이 자료만으로 모델의 독립 RMSE, 충전소 full-loop
정확도, 차량 제어기 성능 또는 현장 안전거리를 주장하지 않는다.

기존 접근 재검증 기록은
`research/jrc_gastef_public_access_recheck_2026_10_05.json`이며, 데이터 요청
초안은 `research/JRC_GASTEF_DATA_REQUEST_DRAFT.md`이다.
