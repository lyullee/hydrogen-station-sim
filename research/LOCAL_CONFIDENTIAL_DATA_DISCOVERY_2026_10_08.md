# Local confidential-data discovery

The owner-controlled archive is not sparse. A privacy-preserving structural
screen found 20,291 structured files, including 14,144 CSV files, and reduced
them to a small number of hydrogen-station and hydrogen-process candidate
sets. No path, filename, site, company, manufacturer, calendar date, tag or raw
row is included in this record.

The main confidential station bundle contains 33 CSV files plus one metadata
file, occupies 4.749 GiB and contains 59,272,275 schema-adjusted data rows. A
direct physical line count gives 59,272,300 rows after removing one header per
file; the 25 narrow exports each contain one additional schema or units row.
Eight wide equipment logs
contain 653,442 one-second rows with 64 columns per file. The available station
families include pressure, temperature, instantaneous flow, cumulative
totalizer, compressor load, cooling state and valve state. These files already
support the station-side signal-consistency, conditional recharge-flow and
thermal-stability diagnostics.

The remaining 25 station files are nine-column history exports containing
58,618,833 schema-adjusted data rows. Their generic
time/value structure is readable, but the proprietary column and channel
semantics are not attested. They are therefore a large unexploited source,
rather than evidence that can yet be used to fit a physical parameter.

Three additional candidate sets were found:

- Twenty compact files contain H35/H70 references, including two J2601 marker
  files. Their structure is consistent with protocol, property-table and
  boundary-condition material. They may support protocol and property checks,
  but they are not presently an independent synchronized station/vehicle
  trace.
- Two mirrored hydrogen component/process collections contain 281 files per
  copy. Fast content fingerprints reduce them to 260 distinct payloads and
  1.929 GiB. Pressure, temperature, flow and totalizer candidates are present,
  but the duplicates and component provenance must be resolved before use.
- A mixed engineering and safety set contains 37 structured files. Thirteen
  have strong process headers. Two files contain vehicle/SOC keywords, but the
  closer structural screen did not identify aligned station-to-vehicle
  telemetry.

The limiting issue is therefore semantic closure, not volume. The archive is
substantial enough for station-side mass-balance, recharge and thermal
diagnostics. It still does not confirm vehicle tank pressure, vehicle tank
temperature, delivered mass or SOC on the same relative-time axis as the
station controller. A privacy-safe dictionary for the 25 narrow history
exports is the highest-value next input. Until then, automatic runtime fitting
and full-loop vehicle-fill claims remain disabled.

The machine-readable aggregate is
`local_confidential_data_discovery_2026_10_08.json`.

A later exact-content rescan additionally found one redundant CSV payload.
After excluding it, 32 unique payloads and 56,854,143 rows remain. The linked
utilization audit records 16,770 ordered pressure cycles, 11,770 paired
medium/high episodes, 1,418 pressure-forecast cases and 733 recharge-flow
episodes already extracted from the archive. See
`local_confidential_station_data_utilization_2026_10_08.json` and
`LOCAL_CONFIDENTIAL_STATION_DATA_UTILIZATION_2026_10_08.md`.
