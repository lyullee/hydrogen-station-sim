# NBSDC liquid-HRS public-access recheck (2026-10-05)

The National Basic Science Data Center record **Operating Dataset of Liquid
Hydrogen Refueling Station** (`CSTR:16666.11.nbsdc.aI3fJrzX`, data id
`67d50e37195d260905af9869`) is a high-value real-station data lead. Its public
metadata reports `完全共享`, seven original XLSX/CSV/DOCX files, and a
concentrated 16-hour real monitoring window with one-second precision covering
35 MPa dispensers, a 90 MPa compressor, high-pressure storage cylinders and a
liquid-pump/tank system.

The public file tree was inspected. The description DOCX was downloaded and
hashed (`669bf3487f07714da3ed08f7d891077841c39ef38497dc2abb307a5877954142`).
Each of the six numerical XLSX/CSV files returned the portal's HTTP-200 JSON
wrapper with body code 403 and the message that data files require a data
application. No numerical cell was opened and no outcome was used.

The candidate therefore remains outside the full-loop holdout. Before any
numerical validation, the custodian must provide the files, channel/time-base
dictionary, vehicle/receptacle definitions, protocol and stop semantics,
quality/calibration metadata, and written permission for derived metrics and
IJHE publication. The prospective intake contract is frozen in
`research/nbsdc_liquid_hrs_intake_protocol_2026_10_05.json`.
