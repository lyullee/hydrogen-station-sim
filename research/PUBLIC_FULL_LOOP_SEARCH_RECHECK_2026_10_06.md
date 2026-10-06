# Public full-loop data search recheck — 2026-10-06

This recheck looked for an independent, rights-cleared, synchronized
station-to-vehicle fueling dataset containing a common time base, vehicle or
receptacle pressure, and mass flow or transferred mass. Six current public
leads were inspected: 3Emotion operational logs, FCH2RAIL measurement records,
the FCH2RAIL KPI report, the H2-Stations API, the IPCEI HRS inventory, and the
open MetHyTrucks HySam system-measurement record
([Zenodo DOI 10.5281/zenodo.20590842](https://doi.org/10.5281/zenodo.20590842)).

The HySam record is rights-cleared and its three quarantined XLSX files match
the published byte counts and MD5 hashes. They provide 0.5 s sampling-system
measurements with pressure/temperature and flow/mass-like tags, but no public
channel dictionary, vehicle/receptacle mapping, protocol state, or
quality/calibration metadata. It is therefore useful instrumentation/timing
context only and is not promoted to calibration or full-loop holdout scoring.

The search found useful real-station context and published measurement claims,
but no new machine-readable raw set meeting the frozen full-loop holdout rule.
The result remains **NO_NEW_ELIGIBLE_PUBLIC_RAW_FULL_LOOP_SET**. Aggregate
operating ranges, component/system workbooks and plot-only curves remain
face-validity or data-request evidence; they are not promoted to calibration
or validation.

Machine-readable record: `research/public_full_loop_search_recheck_2026_10_06.json`.
