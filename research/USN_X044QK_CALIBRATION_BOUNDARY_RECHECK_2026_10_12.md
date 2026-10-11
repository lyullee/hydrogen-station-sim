# USN X044QK calibration boundary recheck (2026-10-12)

The DataverseNO record `10.18710/X044QK` is a public CC0 release containing 40 laboratory-scale delayed-ignition hydrogen-jet experiments. Its raw CSV files expose four dynamic pressure channels and a nozzle-pressure channel, but the published channel units are volts.

The related open article reports an AST4000-series upstream pressure transducer rated 0–250 bar(g), with ±0.5% FSO (±1.25 bar) uncertainty, and reports the associated 2–5% mass-flow uncertainty. That information establishes the instrument boundary, but it does not provide the experiment-specific voltage-to-pressure transfer for the released CSV channels. A generic AST4000 datasheet cannot be substituted for the actual DAQ/conditioning calibration.

The earlier frozen X044QK intake therefore remains a fail-closed pre-screen: no pressure or overpressure score is computed, no case is fitted, and no runtime parameter or validation gate is changed. The next admissible step is to obtain an authenticated campaign calibration or engineering-unit trace, freeze a new protocol, and only then access the selected outcome windows.

Sources:

- [DataverseNO dataset 10.18710/X044QK](https://dataverse.no/dataset.xhtml?persistentId=doi:10.18710/X044QK)
- [Open article, DOI 10.1016/j.firesaf.2026.104812](https://doi.org/10.1016/j.firesaf.2026.104812)

This artifact is provenance and eligibility evidence only. It does not validate an HRS, a vehicle fueling loop, a field safety distance, or operator/SAGA effectiveness.
