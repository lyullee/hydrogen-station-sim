# RHeaDHy 2026 campaign data boundary

The public Hydrogen Refueling Solutions announcement and the EU RHeaDHy project report describe a real heavy-duty refuelling campaign at Champagnier, France. They report 18 tests over six days, ambient temperatures of 15–40 °C, initial tank pressures of 60–300 bar, an example six-minute total refuelling duration, more than 95% state of charge, and the ISO 19885-3 Mid Flow Twin protocol.

The public records do not provide the synchronized row-level station/dispenser/vehicle pressure, temperature and mass-flow archive needed by the repository's full-loop protocol. They also do not provide a channel dictionary, calibration metadata, or explicit terms for redistributing raw logs and derived validation figures. The campaign is therefore retained as real-station face-validity context and a high-priority data-request lead. It is excluded from calibration, holdout scoring, and any claim of full-loop validation.

Sources:

- https://www.hydrogen-refueling-solutions.fr/en/news/hydrogen-very-high-flow-refueling/
- https://ebs.publicnow.com/view/2BE56BA08C750B576B05A61FFB967F70AFFEEC55
- https://cordis.europa.eu/project/id/101101443/reporting

The machine-readable decision is in `research/rheadhy_2026_campaign_data_boundary_2026_10_05.json`.
