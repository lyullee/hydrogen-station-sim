# Confidential station schema audit

The restricted owner-controlled archive was inspected in place with
`scripts/audit_confidential_station_schema.py`. The audit reads CSV headers and
small timestamp samples only. It does not copy raw rows, filenames, source
paths, calendar values or station identifiers into the repository.

The resulting JSON inventory records two anonymised source bundles containing
pressure and equipment-state candidates. It also records temperature and
flow-related candidates, but keeps those channels out of parameter fitting
until the custodian confirms units, calibration and tag semantics. This is a
station-side intake and model-selection aid; it is not a station-to-vehicle
validation result.

The full-loop gate remains open because the archive does not provide an
approved synchronized vehicle pressure/SOC/nozzle-temperature/protocol trace.
The public artifact therefore contains no operational values from the private
rows and does not identify the operator, site, dates or equipment.

The latest privacy-bounded family screen found compressor pressure and
temperature, station pressure and temperature, flow-rate/totalizer, valve and
alarm-state, and lifecycle-counter families. It found **zero vehicle-side
channel families**. This narrows the safe use of the archive to station-side
boundary and equipment-state calibration; it must not be used as a vehicle-fill
accuracy claim until a custodian supplies the missing vehicle/receptacle
mapping and unit/semantics attestation.
