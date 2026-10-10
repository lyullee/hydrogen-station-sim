# Public full-loop search recheck (2026-10-10)

The recheck added official public sources that looked promising because they describe real hydrogen-refuelling operation. None provides a rights-cleared, synchronized station/dispenser/receiving-vessel trace that satisfies the frozen full-loop admission contract.

- Cal State LA back-to-back fueling study ([10.1016/j.jclepro.2021.129737](https://doi.org/10.1016/j.jclepro.2021.129737)): real-station event and cooling/storage context; no reproducible raw logger export identified.
- Cal State LA multi-year performance study ([10.1016/j.ijhydene.2023.04.084](https://doi.org/10.1016/j.ijhydene.2023.04.084)): approximately 4,500 fills and 8,800 kg aggregate context; not a synchronized holdout.
- NLR HITRF official facility reference ([NLR HITRF](https://www.nlr.gov/hydrogen/hitrf)): H70/H35, SAE J2601/MC and storage capability context; no downloadable process trace.
- H2-Stations API v2 ([API documentation](https://docs.h2-stations.eu/for-data-users/api-v2/)): public layout/status context; no thermodynamic fueling historian.

The project therefore stops broad public-data searching at this stage. The next useful input is a small, de-identified three-event pilot with common elapsed time, station/dispenser pressure, boundary temperature, mass flow or transferred mass, and protocol phase. Until that exists, station-side and component claims continue, while the full-loop gate remains explicitly closed.

## Latest search additions

The same recheck also examined the FCH2Rail station-and-vehicle measurement paper ([10.1016/j.ijhydene.2025.04.040](https://doi.org/10.1016/j.ijhydene.2025.04.040)) and the UCI operational measurement study ([10.1016/j.ijhydene.2020.08.251](https://doi.org/10.1016/j.ijhydene.2020.08.251)). They provide credible measured-operation context, but no rights-cleared synchronized raw archive was located. The documented European HRS status API was retained for layout/status context only.

No private path, facility identity, tag, date or raw measurement was added.

## Additional protocol recheck

The 35/70 MPa dispenser-performance article was checked again because its page
exposes four CSV ZIP links.  The files are endpoint tables only: they contain
initial/final conditions and no common time axis, so they remain a diagnostic
and protocol reference rather than a full-loop holdout.  The official DOE H2IQ
heavy-duty report was also checked; its synchronized-looking plot is embedded
in a PDF and is not accompanied by a downloadable raw logger cohort.  These
findings do not change the full-loop gate.
