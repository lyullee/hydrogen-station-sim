# Local station-data recheck

This record documents a direct re-scan of the owner-controlled local station bundle. Only aggregate counts are retained in the repository; raw rows, filenames, tags, timestamps, site identity, and equipment identity remain outside the repository.

The re-scan found 33 CSV files and 56,854,143 deduplicated data rows. The bundle contains station-side pressure, temperature-like, flow-like, compressor/state, lifecycle, and totalizer-like channel families. No header-level vehicle or dispenser candidate was found in this station bundle.

The scan is useful for station-side calibration, chronological episode analysis, and boundary replay. It does not establish a synchronized vehicle-side fill trace. That limitation is a measurement boundary, not a reason to discard the station-side evidence.

## Runtime decision

The fresh aggregate differs from the frozen opt-in profile in time span, sample period, maximum gap, and positive pressure ramp. The existing profile was therefore preserved and was not silently replaced. The mismatch is retained for custodian review. The normal simulator defaults remain unchanged.

The current bundle was nevertheless passed through a bounded measured pressure-boundary replay. The replay completed 300 simulated seconds and 1,501 solver samples. This demonstrates data-to-model wiring at the station boundary while keeping the full station-to-vehicle validation gate closed.

## Evidence files

- `local_station_data_utilization_recheck_2026_10_09.json`: privacy-bounded inventory and utilization counts.
- `local_operational_profile_recheck_2026_10_09.json`: fresh aggregate comparison and fail-closed replacement decision.
- `local_station_boundary_replay_2026_10_09.json`: measured boundary replay outcome.

## Claim boundary

These artifacts support station-side evidence integration and reproducibility. They are not a vehicle-side accuracy result, independent full-loop validation, safety certification, or a universal operating limit.
