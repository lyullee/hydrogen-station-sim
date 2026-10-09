# Public full-loop search recheck (2026-10-10)

The recheck added official public sources that looked promising because they describe real hydrogen-refuelling operation. None provides a rights-cleared, synchronized station/dispenser/receiving-vessel trace that satisfies the frozen full-loop admission contract.

- Cal State LA back-to-back fueling study ([10.1016/j.jclepro.2021.129737](https://doi.org/10.1016/j.jclepro.2021.129737)): real-station event and cooling/storage context; no reproducible raw logger export identified.
- Cal State LA multi-year performance study ([10.1016/j.ijhydene.2023.04.084](https://doi.org/10.1016/j.ijhydene.2023.04.084)): approximately 4,500 fills and 8,800 kg aggregate context; not a synchronized holdout.
- NLR HITRF official facility reference ([NLR HITRF](https://www.nlr.gov/hydrogen/hitrf)): H70/H35, SAE J2601/MC and storage capability context; no downloadable process trace.
- H2-Stations API v2 ([API documentation](https://docs.h2-stations.eu/for-data-users/api-v2/)): public layout/status context; no thermodynamic fueling historian.

The project therefore stops broad public-data searching at this stage. The next useful input is a small, de-identified three-event pilot with common elapsed time, station/dispenser pressure, boundary temperature, mass flow or transferred mass, and protocol phase. Until that exists, station-side and component claims continue, while the full-loop gate remains explicitly closed.
