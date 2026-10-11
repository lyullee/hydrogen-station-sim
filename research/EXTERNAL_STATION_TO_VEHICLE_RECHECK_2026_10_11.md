# External station-to-vehicle raw-data recheck (2026-10-11)

This recheck searches for a public, reuse-cleared, measured station-to-vehicle
time series that could support an independent full-loop validation claim. The
eligibility rule requires station/controller and dispenser/nozzle channels plus
vehicle/receptacle pressure or temperature and transferred mass/flow on one
common clock, with units, initial conditions, tank capacity and protocol
metadata.

The recheck did not identify a new eligible raw set:

- [NREL H2FillS](https://www.nrel.gov/hydrogen/h2fills) is a thermodynamic
  fueling simulator. Its time-series fields are generated model outputs, not an
  independent measured station-to-vehicle logger trace.
- [NREL retail station composite data products](https://www.nlr.gov/hydrogen/infrastructure-cdps-retail)
  provide aggregate utilization, reliability, safety and fueling statistics;
  they do not publish synchronized raw station/dispenser/vehicle channels.
- [MetHyTrucks HySam Group B](https://zenodo.org/records/20590842) is an open,
  synchronized sampling-system measurement release. It has value for the
  existing component diagnostic, but does not contain the vehicle/receptacle
  tank channels or station controller state needed for the full-loop gate.

The primary-goal decision remains **out of scope** for synchronized
station-to-vehicle full-loop validation. The manuscript must state that no
openly reusable synchronized trace was identified and must not claim vehicle
controller accuracy, independent station-to-vehicle accuracy or field-safety
validation. The gate can be reopened only after a custodian supplies at least
three rights-cleared, independently documented common-clock events with the
required channels and metadata, followed by a pre-outcome frozen protocol.

This is a data-availability audit, not evidence that no such data exist behind
proprietary, restricted or unpublished custodial access.
