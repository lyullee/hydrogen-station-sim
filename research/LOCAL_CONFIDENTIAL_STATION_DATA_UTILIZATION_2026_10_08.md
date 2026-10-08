# Local confidential station-data utilization audit

The local station archive is **not sparse**. The privacy-bounded rescan found
33 CSV files occupying 4.749 GiB and containing 59,272,300 physical data rows
after one header per file. One exact duplicate payload accounts for 2,418,157
rows, leaving 32 unique CSV payloads and 56,854,143 deduplicated rows. No raw
row, path, filename, source header, site, company, manufacturer, or calendar
date is included in the committed audit.

The archive has two complementary structures:

- 25 narrow, long-history tables with nine columns each; and
- 8 wide controller/equipment tables with 64 columns each.

The current analysis has already extracted substantial station-side evidence:

- 16,770 chronologically ordered high-bank pressure cycles;
- 11,770 paired medium/high pressure episodes, of which 11,131 follow the
  observed medium-to-high sequence;
- 1,418 causal short-horizon storage-pressure forecast cases;
- 733 conditional compressor-recharge flow episodes; and
- 27 strong instantaneous/totalizer consistency pairs.

This is enough for station-side pressure-envelope, cascade-sequence,
recharge-pressure response, controller-state, lifecycle, and conditional-flow
work. The limiting issue is semantic closure and vehicle-side coverage, not
record volume. Some temperature, flow, valve, reset, sign, and calibration
meanings remain unattested. No synchronized vehicle tank pressure, vehicle
tank temperature, delivered mass, or SOC channel has been confirmed, so a
complete station-to-vehicle validation claim remains disabled.

The next implementation work should therefore use the long pressure-flow
histories for de-identified operating-episode segmentation, use the wide logs
for pressure/state dynamics, exclude the exact duplicate before every
chronological split, and reserve full-loop claims for a later attested
vehicle-side cohort. The machine-readable audit is
`local_confidential_station_data_utilization_2026_10_08.json`; the reusable
scanner is `scripts/audit_local_station_data_utilization.py`.
