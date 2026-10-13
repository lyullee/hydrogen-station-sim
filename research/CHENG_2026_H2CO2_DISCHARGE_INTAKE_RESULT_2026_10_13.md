# Cheng et al. 2026 discharge candidate intake result

The source was inspected only after the pre-access protocol was committed as
`eb68ec9`. The candidate is **not eligible as an independent numerical
holdout** for the current pure-hydrogen release model.

## What the publisher actually provides

- A four-page supplementary PDF (`SHA-256
  EEFD04DC1CCDA49A9DA55DD5EBFE1651219EB6148E4FF05B76DD492990A6834A`)
  gives narrative sensitivity summaries for article figures 7-11.
- A publisher ZIP (`SHA-256
  F1C2D2AE67DC4A186154CD067DB02B4C4937659387E46BA2BA8FBF9B0ED905AA`)
  contains one RAR package for the standalone `H2MixOrificeFlow` application.
- The RAR contains a compiled MATLAB R2025b application, an installer, build
  logs and images. It contains no CSV, workbook, source code or raw
  experimental time series. No executable was run during this audit.

The article reports its new experiment for a `0.7 H2 + 0.3 CO2` mixture and
describes the pure-H2 comparison as existing literature data. That composition
is outside the frozen pure-H2 production model, and no new pure-H2 raw cohort
is packaged.

## Decision

This record is retained as method and candidate-search context only. It does
not change an IJHE readiness gate, a runtime parameter or a safety claim. A
future numerical use requires reusable synchronized pressure, temperature and
flow or released-mass traces, apparatus and valve metadata, and a model frozen
for the measured gas composition before outcome access.

Source: [publisher article](https://doi.org/10.1016/j.ijhydene.2026.156114).
