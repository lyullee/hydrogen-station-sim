# Draft data request to ENGIE/IMT Mines Albi for HyFill heavy-duty HRS experiments

**Do not send without the project owner's review.**

To: Thomas Guewouo and the HyFill/ENGIE Lab CRIGEN data custodian

Subject: Request for de-identified synchronized HyFill heavy-duty HRS validation traces

The open-access paper *Levelized cost of hydrogen: A dynamic simulation-based methodology for heavy-duty refuelling stations* (DOI `10.1016/j.ijhydene.2026.153374`) reports more than 50 measured heavy-duty refuelling and defuelling tests. The paper identifies synchronized measurements of dispenser mass flow, dispenser pressure and temperature, tank injection temperature, tank pressure and average tank-gas temperature across 350/700 bar test rigs. The published figures and summary errors establish provenance, but the raw time-series archive is not attached to the public article.

For an independent, no-fitting holdout of the HRS digital twin, could you provide a de-identified export for a representative subset of the reported tests, or an approved custodian/access route? The minimum fields are:

- common timestamp or elapsed time and sampling interval;
- dispenser pressure, dispenser/delivery temperature and instantaneous mass flow or cumulative transferred mass;
- tank pressure, injection temperature, average gas temperature and, where available, tank-wall thermocouple channels;
- tank geometry/type, capacity, initial conditions and the refuelling or defuelling direction;
- protocol, pressure ramp, precooling set point and stop/abort conditions;
- compressor, cascade-bank, precooler and valve states when available; and
- run identifier, calibration information, units and quality flags.

A de-identified CSV, Parquet or Excel export is sufficient. Please state the licence or written reuse terms, including permission to publish derived error metrics and figures and to deposit de-identified files or derived tables in an open repository. If only plots or endpoint tables are available, we will retain them as context and will not score them as a synchronized transient holdout.

Any received files will be quarantined and hashed before numerical outcomes are inspected. The model commit, eligibility criteria, split and scoring protocol will be frozen first, and every eligible failure will be retained.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
