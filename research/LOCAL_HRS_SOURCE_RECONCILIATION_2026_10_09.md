# Local HRS source reconciliation (2026-10-09)

The local search confirms that the hydrogen-station data are not sparse. The privacy-bounded curated bundle contains 33 measured CSV files, about 4.749 GiB and 59,272,300 physical rows (56,854,143 after duplicate exclusion). It is divided by measurement role so a station-side trace is not presented as vehicle-fueling validation.

## What is present

- **Station pressure and meter bundle:** 12 narrow files with pressure, rate-like and totalizer-like channels. This supports station pressure-cycle, cascade and recharge chronology checks. Flow units and the reference basis still require custodian attestation.
- **Bank lifecycle and thermal bundle:** 13 narrow files with high- and medium-pressure bank lifecycle counters and temperature-like channels. This supports lifecycle/recharge and continuity checks; it does not contain a synchronized vehicle event.
- **Wide compressor/equipment bundle:** eight 64-column files with compressor pressure/temperature, chiller and cooling states, valve/status candidates, equipment communication/alarm candidates and mass-flow-meter candidates. It contains 653,442 rows with a median 1 s sample period and a maximum observed gap of 3 s. The expanded header screen found no vehicle or dispenser boundary.

## What can be used now

The pressure, lifecycle and wide equipment bundles are suitable for chronological station-side holdouts, compressor/cooling/valve/ESD sequence plausibility, recharge-state screening and continuity checks. They should be used through the controlled-data profile with unit and role attestation gates intact.

## What is still missing

The local measured bundle does not establish one synchronized event containing dispenser and receiving-vehicle/receptacle pressure, receiving gas temperature, delivered mass or SOC, and controller/protocol/ESD state on a common time base. Therefore it cannot by itself close the station-to-vehicle full-loop validation gate or support site-specific consequence-distance claims.

The machine-readable record is [`local_hrs_source_reconciliation_2026_10_09.json`](local_hrs_source_reconciliation_2026_10_09.json). Raw rows, paths, filenames, exact dates and site/manufacturer identifiers remain outside the repository.
