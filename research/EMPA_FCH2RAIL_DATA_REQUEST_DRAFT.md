# Public-data request draft: Empa and FCH2RAIL refuelling traces

This draft is prepared for a future data request. It does not claim that any
external party has granted access.

## Empa Type-IV tank-filling experiments

Reference: Couteau, Dimopoulos Eggenschwiler and Jenny, *Heat transfer analysis
of high pressure hydrogen tank fillings*, DOI
[10.1016/j.ijhydene.2022.05.127](https://doi.org/10.1016/j.ijhydene.2022.05.127).

Please consider sharing de-identified, machine-readable data for the four
Empa HRS Type-IV tank-filling experiments described in the article, or advise
where an archived dataset can be accessed. The minimum fields needed for a
reproducible tank-thermal holdout are:

- common time base and sampling interval;
- vehicle-tank pressure and gas or liner temperature;
- inlet pressure, inlet temperature and mass flow or transferred mass;
- initial pressure, ambient temperature, tank volume/type and fill target;
- nozzle/dispenser conditions and any pressure-ramp or protocol settings;
- sensor accuracy, missing-data convention and permitted reuse terms.

The data would be used only for a pre-registered tank-thermal submodel check;
the repository would retain hashes and derived metrics rather than republish
restricted raw files.

## FCH2RAIL reference HRS and rail vehicle

Reference: Wieser et al., *Development, application and optimization of
hydrogen refueling processes for railway vehicles*, DOI
[10.1016/j.ijhydene.2025.04.040](https://doi.org/10.1016/j.ijhydene.2025.04.040).

Please consider sharing a de-identified synchronized trace for one or more
reference refuelling events, including station and vehicle channels:

- vehicle-tank/module pressure and temperature;
- dispenser pressure, delivery temperature and mass flow;
- transferred mass, start/end conditions and vehicle tank capacity;
- pre-cooler state, pressure-ramp target and protocol/category;
- event timestamps, sensor accuracy and any gaps or filtering.

The intended use is an independent heavy-duty/rail full-loop validation
holdout. No data would be used for parameter fitting before the holdout
protocol is frozen, and any failed cases would remain reported.
