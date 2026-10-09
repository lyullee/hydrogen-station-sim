# Public vehicle-side H2 measurement lead (2026-10-09)

The NPL/Toyota study *Assessing the Performance of Fuel Cell Electric Vehicles
Using Synthetic Hydrogen Fuel* is an additional public lead for the missing
vehicle-side boundary. The paper reports HRS flow-meter mass and vehicle-tank
pressure/temperature based mass estimation, which is useful for designing a
cross-check against the simulator's delivered-mass state.

The record is deliberately classified as a lead rather than a validation
holdout. The public material checked here does not establish a synchronized
machine-readable trace with tank geometry, controller/cascade state and
calibration metadata. It therefore cannot close the station-to-vehicle gate or
be used for parameter fitting without an authorized data release and a frozen
protocol.

The open-access 2026 study *Representative Hydrogen Sampling at Hydrogen
Refuelling Stations: Interplay of Sampling Strategy and Station Parameters*
adds a second lead. It reports sampling-system mass-flow comparisons and
vehicle/large-tank context, which is useful for checking whether simulated flow
and instrumentation assumptions are plausible. It is still classified as
context only: a synchronized station-controller-vehicle raw trace with reuse
permission was not confirmed, so it is not admitted as a holdout or calibration
source.

Sources:

- Article DOI: <https://doi.org/10.3390/en17071510>
- NPL publication record: <https://eprintspublications.npl.co.uk/10158/>
- 2026 sampling study DOI: <https://doi.org/10.3390/cleantech8030091>
- 2026 sampling study page: <https://www.mdpi.com/2673-4591/8/3/91>

The machine-readable classification is in
`research/public_vehicle_side_h2_measurement_leads_2026_10_09.json`.
