# Ramea California HRS capacity repository: evidence boundary

**Checked:** 2026-10-05  
**Repository:** [kramea/h2_station_capacity_data](https://github.com/kramea/h2_station_capacity_data)  
**Associated paper:** [10.1016/j.ijhydene.2019.05.053](https://doi.org/10.1016/j.ijhydene.2019.05.053)

## What is publicly present

The public repository contains 2,563 CSV files under 36 California station directories, spanning 2018-09-27 through 2018-12-18. The README describes approximately 30-minute collection intervals (the repository description calls the dataset hourly). The files expose `Time`, `H35`, and `H70`; the inspected sample is [`anaheim_09-27-2018.csv`](https://raw.githubusercontent.com/kramea/h2_station_capacity_data/master/data/anaheim/anaheim_09-27-2018.csv).

## Boundary

This is useful real-station aggregate capacity/availability context. It is not a synchronized fueling trace: no vehicle/receptacle pressure, vehicle/tank temperature, mass flow/transferred mass, protocol metadata, or common station-to-vehicle event time base is provided. The GitHub repository has no explicit license field, so the archive is linked and cited but not redistributed in this project.

The source is therefore recorded as `PUBLIC_AGGREGATE_STATION_CAPACITY_CONTEXT_ONLY`. It can support demand, capacity depletion/recovery, and face-validity checks, but cannot be used as an independent thermodynamic full-loop holdout or as evidence that the digital twin agrees with measured pressure/temperature/mass-flow trajectories.
