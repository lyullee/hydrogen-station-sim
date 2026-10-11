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
- [California ARB's light-duty HRS in-use study](https://ww2.arb.ca.gov/sites/default/files/2024-12/Existing%20Light-Duty%20Hydrogen%20Refueling%20Stations%20In-Use%20Study%20Report%20ADA%20AL.pdf)
  publishes pressure, temperature and mass-flow figures from station tests,
  but no reusable machine-readable synchronized logger archive was identified.
- The [Cal State LA / 3Emotion back-to-back fueling study](https://doi.org/10.1016/j.jclepro.2021.129737)
  describes multi-year operator logs and station/vehicle metrics. The public
  article record still does not expose the event rows, channel dictionary,
  clock alignment and reuse terms needed for an untouched holdout, so it is a
  custodian request lead only.
- The [H2-Stations Europe API v2](https://docs.h2-stations.eu/for-data-users/api-v2/)
  exposes station layout and aggregate availability/usage/storage status. It
  does not expose synchronized dispenser/controller and vehicle-side pressure,
  temperature and transfer-flow channels.
- [Hydrogen Fueling in FCEV: A Study](https://zenodo.org/records/12737240) is
  an open article about fueling conditions and standards, not a measured raw
  station-to-vehicle logger release.
- The [JRC GasTeF reference-data record](https://publications.jrc.ec.europa.eu/repository/handle/JRC76380)
  describes measured onboard-tank temperature histories, but its public record
  contains no downloadable machine-readable dataset or reuse terms.
- The open [Zhao et al. Type-III study](https://doi.org/10.3390/en15103811)
  reports an air test rig and Type-III numerical study, but does not publish a
  machine-readable measured fill trace for an independent holdout.
- The [NREL H2IQ 2024 heavy-duty fueling summary](https://www.energy.gov/sites/default/files/2024-04/h2iqhour-03262024.pdf)
  shows a valuable single-event plot and aggregate metrics, but no row-level
  logger export, channel dictionary or reuse terms.
- The recent [Empa high-aspect-ratio Type-IV campaign](https://doi.org/10.1016/j.ijhydene.2025.152513)
  is a strong raw-data request lead, but the public record did not expose a
  rights-cleared station/vehicle logger bundle.

The primary-goal decision remains **out of scope** for synchronized
station-to-vehicle full-loop validation. The manuscript must state that no
openly reusable synchronized trace was identified and must not claim vehicle
controller accuracy, independent station-to-vehicle accuracy or field-safety
validation. The gate can be reopened only after a custodian supplies at least
three rights-cleared, independently documented common-clock events with the
required channels and metadata, followed by a pre-outcome frozen protocol.

This is a data-availability audit, not evidence that no such data exist behind
proprietary, restricted or unpublished custodial access.

## Current search additions (2026-10-11)

The current web recheck also found the following related records. They do not change the eligibility decision:

- [European Hydrogen Observatory HRS datastream](https://observatory.clean-hydrogen.europa.eu/hydrogen-landscape/distribution-and-storage/hydrogen-refuelling-stations) provides station availability and infrastructure information, not synchronized station/dispenser/vehicle transients.
- [USN open-ended rectangular-channel hydrogen dispersion data](https://figshare.com/articles/dataset/Experimental_Data_of_Hydrogen_Dispersion_in_an_Open-ended_Rectangular_Channel/26117989) (DOI [10.23642/usn.26117989.v2](https://doi.org/10.23642/usn.26117989.v2)) is retained for actual-hydrogen consequence/component evidence; it has no vehicle/receptacle fill channels or station controller state.
- [Robotic hydrogen-filling system design data](https://figshare.com/articles/dataset/Data_of_Design_of_Robotic_Hydrogen-filling_System_for_Hydrogen-powered_Vehicles/20097317) is a design/robotics release, not measured station-to-vehicle filling data.
- The [SARTA heavy-duty refueling campaign](https://www.sciencedirect.com/science/article/pii/S0360319921036144) and [Lototskyy integrated-metal-hydride station paper](https://zenodo.org/record/3582985/files/Hydrogen%20refuelling%20station%20with%20integrated%20metal.pdf) report valuable operating ranges or aggregate fills, but no rights-cleared synchronized row-level station/vehicle logger archive.

The machine-readable search log is `external_station_to_vehicle_recheck_2026_10_11.json`. This remains a data-availability audit; it does not establish that restricted or unpublished records do not exist.
