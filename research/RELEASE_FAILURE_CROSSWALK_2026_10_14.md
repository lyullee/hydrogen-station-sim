# 방출모델 실패 게이트 교차분석

이 문서는 여러 독립 검증 실패에서 반복되는 모델 경계 원인을 묶은 개발 진단이다.
기존 PASS/FAIL/PENDING 판정과 런타임 파라미터는 변경하지 않는다.

## 공통 원인

### 1. apparatus_boundary_and_line_inventory
- 영향 게이트: schefer_transient_release_validation, proust_independent_release_validation, preslhy_blowdown_external_validation
- 해석: The controlling boundary is likely a network of vessel, line, valve and terminal restriction rather than a single fixed aperture coefficient.
- 다음 검증 입력: Freeze measured line length/diameter, valve opening law, upstream pressure-temperature boundary and terminal geometry before reading outcomes.
- 근거:
  - The Schefer line diagnostic preserves separate source/outlet boundaries but still fails the frozen timing and error screens.
  - Proust effective discharge coefficient varies by nominal diameter, so one global coefficient cannot reconcile all series.
  - PRESLHY performance varies strongly by nozzle diameter and pressure group.

### 2. valve_and_transient_timing
- 영향 게이트: schefer_transient_release_validation, schefer_2007_pressure_decay_validation
- 해석: Opening/closing dynamics and instrument boundary timing may explain the remaining transient mismatch, but the available traces cannot identify a production time constant.
- 다음 검증 입력: Obtain a new event with valve command, valve position or flow-meter timing on the same clock as vessel pressure.
- 근거:
  - A post-outcome 4 s source-valve sensitivity reduces Schefer 2006 outlet median APE to 19.83%, but does not establish a pass.
  - Schefer 2007 non-adiabatic wall sensitivity changes the pressure transient but leaves the joint screen failed.

### 3. diameter_and_discharge_regime
- 영향 게이트: preslhy_blowdown_external_validation, preslhy_partb_ambient_external_validation, preslhy_revised_holdout_validation, proust_independent_release_validation
- 해석: A single choked-flow relation is insufficient across the observed diameter and pressure regimes; a declared regime transition or measured manifold loss is needed.
- 다음 검증 입력: Use an untouched campaign spanning at least two diameters and pressure regimes with measured upstream conditions and aperture/manifold geometry.
- 근거:
  - PRESLHY's controlling frozen result is 0.500 (11/22); the later 0.727 rerun is post-outcome and demoted. The 1.0 mm group is 0/4 while 4.0 mm is 7/7 in the retained stratification.
  - Part-B non-adiabatic sensitivity remains 0.600; both 2 mm cases retain approximately 25.3% half-time error.
  - Proust reports diameter-dependent effective discharge coefficients.

### 4. thermal_boundary
- 영향 게이트: dickens_typeiii_prospective_validation, schefer_2007_pressure_decay_validation, preslhy_partb_ambient_external_validation
- 해석: Thermal state is a real limitation, but a generic wall heat-transfer coefficient alone is not sufficient; inlet and wall geometry/temperature history are under-specified.
- 다음 검증 입력: Freeze measured wall mass/heat capacity, inlet temperature history and geometry for a new independent charge or blowdown event.
- 근거:
  - Dickens passes pressure screens but fails gas-temperature screens.
  - Adding consumed wall-thermal sensitivity to Schefer 2007 and PRESLHY Part-B does not close the joint screens.

## 다음 모델 동결 순서

1. Resolve apparatus boundary and line/valve inventory.
2. Declare diameter/regime semantics and thermal boundary inputs.
3. Freeze the revised model and protocol before inspecting outcomes.
4. Evaluate a new independent holdout and retain the current negative controls.

## 경계

This crosswalk does not promote a failed result, select a runtime parameter, or establish an independent validation claim. A new untouched holdout is required after any model change.
