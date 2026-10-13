# Liang 2026 고압 수소 방출 무보정 벤치마크

## 목적과 증거 경계

2026년에 공개된 1 mm 원형 노즐 고압 수소 방출 실험의 Table 2 일곱 점을
현재 `DynamicLeakModel`에 그대로 넣었다. 입력은 노즐 인근 측정압력
11.124–63.999 MPa, 300.15 K, 대기압 101325 Pa이며, 생산 기본값
`Cd=0.8`을 유지했다. 수치 결과를 본 뒤 프로토콜을 작성했으므로 이 결과는
**post-access zero-fit benchmark**이다. prospective holdout, 독립 검증 또는
런타임 보정으로 부르면 안 된다.

원 논문: Liang Liyou et al., “Experimental research on high-pressure hydrogen
leakage from storage tanks,” *Acta Energiae Solaris Sinica* 47(4), 2026,
[doi:10.19912/j.0254-0096.tynxb.2024-2238](https://doi.org/10.19912/j.0254-0096.tynxb.2024-2238).

## 결과

| 평가층 | NRMSE | 중앙 APE | 평균 편향 | 판정 |
|---|---:|---:|---:|---|
| 현재 런타임 `Cd=0.8` 대 실측 유량 | 28.43% | 39.05% | +38.45% | FAIL |
| `Cd=1` 실가스 식 대 논문 Abel–Noble 이론값 | 0.59% | 0.81% | +0.78% | PASS |
| 진단 전용 `Cd=0.6` 대 실측 유량 | 3.62% | 4.29% | +3.84% | 참고만 |

현재 모델의 단위 방출계수 유량은 논문의 Abel–Noble 이론값과 1% 안에서
일치한다. 반면 생산 기본값 `Cd=0.8`은 모든 점을 과대예측했고, 실측값이
암시하는 유효 방출계수는 0.568–0.594였다. 따라서 이 캠페인에서의 주된
불일치는 수소 EOS나 임계유동 계산이 아니라 노즐의 수축·손실을 나타내는
방출계수 층이다.

## 시스템 해석

- 1 mm 원형 노즐 조건에서는 현재 생산 모델이 누출 질량유량을 평균 약
  38% 크게 계산한다. 이 조건에서 피해영향 범위가 작게 나온 원인을
  질량유량 과소예측으로 설명할 수는 없다.
- `Cd=0.6`은 이 자료에 잘 맞고 기존 Proust 2–3 mm 진단에서도 유리했지만,
  Proust 1 mm 장치와 다른 캠페인에는 동일하게 적용되지 않는다. 범용
  기본값으로 교체하면 장치별 배관·밸브·노즐 경계를 숨길 수 있다.
- 그러므로 현재 런타임은 변경하지 않는다. 대신 `Cd=0.8` 결과는 특정
  형상에 대해 보수적인 스크리닝일 수 있으며 현장 실측 방출량 또는 확정
  안전거리로 표시하지 않는다.
- 다음 모델 버전은 원형 노즐, 긴 배관, 밸브, 균열을 명시적으로 구분하고,
  형상별 계수 또는 장치 해석을 **새로운 미사용 실제 수소 캠페인**에서
  검증한 뒤에만 런타임으로 승격해야 한다.

## 재현 파일

- 수치 전사: `data/public_validation/derived/liang_2026_table2.csv`
- 출처·권리 메모: `data/public_validation/derived/LIANG_2026_TABLE2_README.md`
- 고정 프로토콜: `research/liang_2026_release_benchmark_protocol.json`
- 기계 판독 결과: `research/liang_2026_release_benchmark_2026_10_13.json`
- 실행기: `scripts/run_liang_2026_release_benchmark.py`

출판사 PDF는 저장소에 포함하지 않는다.
