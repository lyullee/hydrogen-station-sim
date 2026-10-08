# Confidential station cascade-sequence holdout protocol

This protocol is frozen before any chronologically ordered joint medium/high
pairing outcome is computed. Individual high-pressure cycle results and the
reverse source order are already known and disclosed.

The evaluator sorts each matching file by timestamp, resolves duplicate times
deterministically, applies the previously fixed seven-sample causal median and
detects pressure drawdowns with the unchanged cycle rules. Each high-bank
drawdown is paired once to the nearest preceding or slightly overlapping
medium-bank drawdown inside a fixed -300 to +900 second handoff window.

The first 70% of each file supplies calibration summaries and the last 30% is
the holdout. Eligibility requires at least six files, 60 calibration pairs, 24
holdout pairs and four holdout files. The holdout must pair at least 60% of high
drawdowns, show at least 90% medium-to-high order, keep pair-coverage and
sequential-fraction drift within 0.20 and 0.10, and retain its median handoff
gap inside the calibration P10--P90 interval. Every criterion is required.

A pass supports only a same-site medium/high pressure sequence compatible with
the controller structure. Without synchronized vehicle, valve and dispenser
states, the episodes are not uniquely identified vehicle fills. The result
cannot validate the low bank, a complete fill, a safety limit, accident
frequency or field operation, and it cannot change runtime parameters.
