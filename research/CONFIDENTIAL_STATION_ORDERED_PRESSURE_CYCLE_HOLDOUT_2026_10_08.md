# Chronology-corrected station pressure-cycle holdout result

The hash-locked chronology correction recovered 16,770 eligible high-storage
pressure cycles from all 12 matching history files. The calibration partition
contained 11,565 cycles and the later holdout partition contained 5,205 cycles.
All source files were strictly reverse chronological; none had mixed timestamp
order.

## Prospective screens

The holdout pressure-drop distribution was 1.13894 MPa at P10, 4.6378 MPa at
the median and 9.02996 MPa at P90. The previously existing 4.5 MPa high-bank
restart margin was inside this interval and differed from the holdout median by
2.971236%. The calibration median was 4.5914 MPa, a 1.010585% shift from the
holdout median. File-count, cycle-count, coverage and all three primary screens
therefore passed without changing the candidate or thresholds after outcome
access.

The result corroborates the existing 4.5 MPa development default across two
formats in the same confidential station archive. It does not trigger a runtime
parameter change.

## Method history and boundary

The initial unsmoothed method and the causal-median revision both returned zero
cycles. A post-outcome diagnostic then established that the source histories
were stored newest-to-oldest. The third protocol disclosed those failures and
froze ascending timestamp sorting before any chronologically ordered cycle
outcome was computed. The earlier negative artifacts remain unchanged.

This is sequential same-site evidence. It is not an independent external
validation, vehicle-fill/full-loop validation, compressor-state classifier,
safety limit, accident-frequency estimate or field certification. The public
artifact contains no source identity, path, filename, header, tag, calendar
date, absolute timestamp or raw row.
