# Draft data request to Cal State LA HRFF for cascade/directly-pressurized experiments

**Do not send without the project owner’s review.**

To: Cal State LA Hydrogen Research and Fueling Facility data custodian / corresponding authors

Subject: Request for de-identified raw traces from cascade and directly-pressurized H70 experiments

The open-access Energy paper, *Experimental Comparison of Directly-Pressurized and Cascade H2 Refueling Methods for Heavy-Duty Applications* (DOI 10.3390/en16155749), reports three real HRFF refuelling experiments. It reports approximately 1.6 kg per event, directly-pressurized terminal pressures near 550 and 710 bar, a cascade case beginning near 800 bar storage with a vehicle near 55 bar that reached about 550 bar, and measured chiller-energy and nozzle-temperature differences. The published figures and summary values are useful provenance, but the underlying synchronized logger export is not publicly attached.

For an independent, no-fitting holdout, could you provide a de-identified export for the reported runs or an approved custodian/access route? The minimum fields are:

- common timestamp or elapsed time and sampling interval;
- vehicle/receptacle, dispenser and storage-bank pressure;
- vehicle/tank, delivered-gas, nozzle and ambient temperature;
- instantaneous mass flow or cumulative transferred mass;
- initial pressure/SOC, tank capacity/type and gas protocol;
- cascade-bank selection, compressor/booster, chiller and valve states;
- stop/abort/fault, calibration and quality flags; and
- a run identifier linking the trace to the reported direct or cascade case.

A de-identified CSV, Parquet or Excel export is sufficient. Please state licence or written reuse terms, including permission to publish derived error metrics and figures and to deposit the de-identified files or derived tables in an open repository. If only plots or endpoint tables are available, we will retain them as context and will not score them as a synchronized transient holdout.

Any received files will be quarantined and hashed before numerical outcomes are inspected. The model commit, eligibility criteria, split and scoring protocol will be frozen first.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
