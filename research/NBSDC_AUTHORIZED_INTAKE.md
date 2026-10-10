# NBSDC authorized HRS intake

The official NBSDC record for the 35/70 MPa fixed hydrogen station demonstration
lists the workbook entity, but the file download is registration/login gated.
The repository therefore keeps only the public metadata and a privacy-bounded
intake utility. It does not contain the workbook or any private station rows.

After an authorized custodian downloads the file, run the intake from a path
outside this repository:

```powershell
.venv\Scripts\python.exe scripts\intake_nbsdc_station_workbook.py `
  --input C:\\authorized\\fixed_station_operation.xlsx `
  --output research\\nbsdc_authorized_schema_intake.json `
  --access-attested
```

The receipt contains the file hash, format, aggregate semantic-channel counts,
and a stricter role-aware contract check. That contract requires explicit
vehicle pressure/temperature and identity columns together with station or
dispenser pressure, delivered-gas temperature, flow, storage-bank and control
state channels in one logical table. It does not retain raw rows, original
headers, worksheet names, absolute timestamps, or the source path. Schema
presence alone never promotes the data to the external full-loop holdout; a
custodian must attest units, calibration, common-clock station/dispenser/vehicle
linkage, reviewer access, and a frozen outcome-free split first.

The public record is [NBSDC 35/70 MPa fixed HRS demonstration](https://www.nbsdc.cn/general/dataDetail?id=64f08267bb16e06dfdc78c57&type=1).
The page displays [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/deed.zh-hans),
but the repository treats rights for the actual downloaded entity file as an
attestation requirement before publication or reviewer sharing.
