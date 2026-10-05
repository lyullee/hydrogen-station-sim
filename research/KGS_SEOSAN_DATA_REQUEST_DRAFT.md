# Draft data request to the KGS/Korea Gas Technology Corporation Seosan HRS study

**Do not send without the project owner’s review and an authorized institutional contact.**

To: Korea Gas Safety Corporation / Korea Gas Technology Corporation and the authors of “Development of Digital Twin for Real-Time Diagnosis of Hydrogen Refueling Stations”

Subject: Request for de-identified Seosan HRS normal/leak traces for independent safety-digital-twin validation

Dear authors and data custodian,

I am preparing an independent validation study of a hydrogen-refuelling-station safety digital twin and evidence-grounded decision-support assistant. I read the paper **수소충전소 실시간 진단을 위한 디지털 트윈 개발 / Development of Digital Twin for Real-Time Diagnosis of Hydrogen Refueling Stations**, presented in the 2024 Korean Gas Society spring proceedings (p. 146). The paper reports process-model validation with normal-operation data from a hydrogen station in Seosan, Korea, and a robustness demonstration using data from a period when hydrogen leakage occurred.

Could you identify the approved custodian and provide a de-identified extract, or an application route, for an independent holdout? The minimum useful fields are:

- a common timestamp or elapsed time and engineering units;
- sensor tag, location, range, calibration and quality flags;
- station/storage-bank/compressor/dispenser pressure, temperature and mass-flow channels;
- hydrogen detector concentration or leak-rate signal and any fire/gas detector state;
- operating mode, fueling start/stop markers, valve/ESD/controller state and alarm chronology;
- initial conditions, tank/storage geometry or capacity and protocol metadata;
- incident/maintenance annotations with event times, if release is permitted.

Station and operator identities can be removed. CSV, Parquet or Excel plus a data dictionary is sufficient. Please state whether derived error metrics, figures, masked event summaries and an anonymized dataset may be deposited in an open repository and used in a journal article.

The requested files would be used for independent evaluation, not model fitting. Any received files would be quarantined and hashed before outcomes are inspected; the eligible cases, model commit and scoring protocol would be frozen before numerical evaluation. Normal-only data can support false-alarm and sensor-quality checks, while the reported leak-period data would be retained as incident evidence only if the event provenance and measurement semantics are documented.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*

## Public provenance

- KGS proceedings landing page: https://kigas.or.kr/homepage/boardMedia/94986
- Local evidence hash recorded in `research/kgs_seosan_digital_twin_data_boundary_2026_10_05.json`; the public artifact is a proceedings PDF, not a raw dataset.
