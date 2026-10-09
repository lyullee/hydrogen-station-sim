# NBSDC liquid-HRS access recheck (2026-10-10)

The National Basic Science Data Center catalogue exposes a high-value real liquid-hydrogen refueling-station record: seven files, approximately 42 MB, a concentrated 16-hour window at one-second precision, and station-side channels covering pressure, temperature, flow, dispensed mass, current, frequency, liquid level and volume. The public record identifies the provider as Tongji University and reports the data as fully shared.

The file tree is visible and the description document is downloadable. A numerical XLSX/CSV download probe returns HTTP 200 with portal code **403** and the message that only description files are currently downloadable and numerical files require a data application. Therefore no numerical cell was opened, copied, or used for calibration. This is a concrete access boundary, not evidence that the dataset is absent.

The dataset is retained as a high-priority request candidate. Before using it in a model or publication, the custodian must provide the numerical files, hashes, channel dictionary, common time base, vehicle/receptacle mapping if present, protocol and stop semantics, alarm/ESD metadata, calibration/quality information, and written permission for derived metrics and IJHE publication. Until then it remains metadata-only and cannot close the full-loop validation gate.

Source: [NBSDC catalogue record](https://nbsdc.cn/general/dataDetail?id=67d50e37195d260905af9869&type=1).

The check is repeatable without retaining the response bodies:

```powershell
.venv\Scripts\python.exe scripts/recheck_nbsdc_liquid_hrs_access.py --output $env:TEMP\nbsdc_liquid_live.json
```
