# Local station-data revalidation (2026-10-09)

The local source directory was audited again with
`scripts/audit_local_station_data_utilization.py`. The aggregate result
matches the committed privacy-bounded inventory: 33 CSV files, 4.749 GiB,
59,272,300 physical rows and 56,854,143 rows after exact duplicate exclusion.
No raw rows, source names, paths, tags, site identifiers or exact source dates
were written to the repository.

The sampled candidate manifest contains 20 tables with 2,000 rows inspected
per table. Twelve have station pressure/flow/time-like coverage and eight also
contain temperature- and controller-state-like fields. These are useful for
station-side pressure, recharge, compressor, cooling and state-transition
checks. Header screening still finds no attested vehicle or dispenser boundary.

A broader local screen covered 38,528 machine-readable files and 13,050 CSV
files in the refined pass. It found no synchronized station/dispenser/vehicle
cohort satisfying the full-loop contract. Derived simulator exports remain
excluded from external validation.

The machine-readable record is
[`local_station_data_revalidation_2026_10_09.json`](local_station_data_revalidation_2026_10_09.json).
The result strengthens the station-side evidence inventory but does not close
the independent full-loop gate. The next required input is a custodian-approved,
de-identified cohort with a common clock, receiving-vessel/vehicle pressure and
temperature, delivered mass or attested mass flow, controller/protocol state and
reuse permission.
