# HIAD 2.2 data-use note

This note records the public acquisition route for the European Hydrogen Incidents and Accidents Database (HIAD 2.2). It is a provenance/use note for the validation-data tracker, not a validation result.

- Official page: <https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt>
- Download: <https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiad_22_export_for_users_2026_01_01xlsx>
- Version coverage: events through 2025-12-31
- Local acquisition artifact: `research/hiad_2_2_access_recheck_2026_10_05.json`
- Local source file: `data/public_validation/raw/hiad_2_2.xlsx` (ignored from Git)

The JRC states that use is free of charge subject to its download conditions and requires the following acknowledgement:

> European Hydrogen Incidents and Accidents Database HIAD 2.2, European Commission, Joint Research Centre, Petten, The Netherlands.

The indexed 34 hydrogen-refuelling-station records are suitable for scenario taxonomy, response grounding and a future coordinator-reviewed SAGA casebook. The workbook does not provide synchronized station-to-vehicle pressure, temperature and mass-flow traces, so it cannot close the numerical full-loop validation gate.

Before expert response collection, a non-rating coordinator must mask hindsight response/lesson leakage, the existing ethics determination must be completed, and the frozen casebook protocol must be followed.
