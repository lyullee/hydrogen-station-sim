# Official public full-loop source access check (2026-10-09)

The official NREL/DOE/NLR fueling sources were checked before asking for more private data. They expose useful model definitions, test-facility descriptions, aggregate fueling results, station inventory/status, and some component measurements. They do **not** expose a rights-cleared, machine-readable cohort that synchronizes station or dispenser pressure, vehicle pressure and temperature, transferred mass/flow, a common time base, initial conditions, units, and reuse terms.

The check therefore records zero eligible public station-to-vehicle raw holdout sources. This is an access result, not a claim that the experiments do not exist. The current system should continue using the available station-side and component evidence, while requesting the smallest next bundle first: three de-identified component-pilot events with common time, dispenser pressure and mass flow, and protocol/ESD state. A full-loop request is only needed after that pilot schema is accepted.

The machine-readable source list and claim boundary are in [`public_full_loop_official_source_access_check_2026_10_09.json`](public_full_loop_official_source_access_check_2026_10_09.json).
