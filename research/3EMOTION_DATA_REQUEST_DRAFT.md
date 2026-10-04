# Draft data request to the 3Emotion hydrogen-bus station operators

**Do not send without the project owner's review.**

To: 3Emotion project authors and the relevant station operators/data custodians

Subject: Request for de-identified 3Emotion HRS event logs for independent digital-twin validation

Dear authors,

I am preparing an academic validation study of a hydrogen-refuelling-station
safety digital twin. I read the 3Emotion operational analyses (DOI
10.1051/e3sconf/202233406008 and DOI 10.1016/j.ijhydene.2022.10.093), which
describe real 350-bar bus-station operations and operator logbooks across
multiple European sites.

Could you provide a de-identified event export, or identify the approved
custodian and access route, for an untouched validation split? The minimum
useful fields are:

- common timestamp or elapsed time, sampling interval and engineering units;
- vehicle/receptacle pressure, station/dispenser pressure, temperature and
  instantaneous flow or cumulative transferred mass;
- station identity pseudonym, fill/event identifier, vehicle tank capacity and
  initial conditions;
- storage-bank/compressor/cooler/valve state, protocol or pressure-ramp
  metadata, stop/abort markers and quality/calibration flags where available.

Station, operator and bus identities can be pseudonymized. CSV, Parquet or
Excel files with a channel dictionary are sufficient. Please state the licence
or written reuse and citation terms, including whether derived error metrics,
figures and anonymized event summaries may be published in an open repository
and journal article.

The requested use is independent evaluation, not model fitting. Any received
files would be quarantined and SHA-256 hashed before numerical outcomes are
opened; the model commit, eligibility rules and scoring protocol would be
frozen in advance. Aggregate tables and simulated or injected traces would be
reported separately and would not be presented as measured full-loop evidence.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
