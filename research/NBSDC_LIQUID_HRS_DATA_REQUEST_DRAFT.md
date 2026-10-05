# NBSDC liquid-HRS data request draft

**Subject:** Research-access request — CSTR:16666.11.nbsdc.aI3fJrzX / data id `67d50e37195d260905af9869`

Dear Tongji University / National Basic Science Data Center data custodian,

We are preparing a reproducible safety digital-twin study for the
*International Journal of Hydrogen Energy*. The public record describes the
**Operating Dataset of Liquid Hydrogen Refueling Station** as a real 16-hour,
one-second monitoring dataset covering 35 MPa dispensers, a 90 MPa compressor,
high-pressure storage cylinders and a liquid-pump/tank system. The public file
tree lists the following original files:

- `35MPa加氢机1.xlsx`, `35MPa加氢机2.xlsx`, `70MPa加氢机.csv`
- `90MPa压缩机.xlsx`, `液氢泵-液氢储罐.xlsx`, `高压储氢瓶组.xlsx`
- `液氢加氢站运行数据集数据说明 .docx`

Please provide, if permitted for academic research, the six numerical files and
the following metadata:

1. channel dictionary, units, sampling/aggregation rule, timezone and missing-value codes;
2. timestamp alignment and clock-correction history across dispenser, storage,
   compressor, pump/tank and any vehicle/receptacle channels;
3. definitions for vehicle/receptacle pressure and temperature, mass flow or
   transferred mass, tank capacity and initial conditions;
4. station topology, cascade/bank assignment, valve/controller state,
   protocol pressure ramp, stop/abort, alarm and ESD semantics;
5. sensor calibration, quality flags, maintenance intervals and known outages;
6. written permission to publish only de-identified file hashes, derived
   traces and case-level error metrics in an IJHE manuscript and repository.

We will freeze the model commit, case eligibility rule and engineering screens
before opening numerical outcomes. The files will be quarantined outside Git,
hashed byte-for-byte, and evaluated once without fitting, time warping or
post-outcome threshold changes. The intake contract is attached as
`research/nbsdc_liquid_hrs_intake_protocol_2026_10_05.json`; the current public
access boundary is documented in
`research/nbsdc_liquid_hrs_public_access_recheck_2026_10_05.json`.

If vehicle/receptacle channels or publication rights are unavailable, please
state that explicitly so the dataset can be used only for a bounded station or
component analysis.

Sincerely,

`[researcher name / institution / institutional email]`
