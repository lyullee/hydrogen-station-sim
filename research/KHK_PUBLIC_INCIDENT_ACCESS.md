# KHK public accident database access record

On 2026-10-04 the FY2025 KHK high-pressure-gas accident database was downloaded
from the official KHK page and opened locally. The workbook contains a structured
high-pressure-gas accident sheet with hydrogen-station-relevant cases, including
leaks, fires, relief-device operation, compressor, valve, hose, dispenser and
storage-equipment events.

The source is useful for a local SAGA safety-grounding casebook, but it is not an
open dataset for repository or paper deposit. KHK states that the copyright belongs
to METI, commercial use requires METI approval, and the whole or any part of the
database may not be transferred, lent, distributed, publicly posted or mirrored.
Therefore the raw workbook remains under the gitignored
`data/public_validation/raw/` directory. No incident text, row-level records or
derived counts are committed here.

The access manifest records the archive hash and the claim boundary in
`research/khk_public_incident_access_2026_10_04.json`. A de-identified subset or
derived aggregate may be used for the IJHE study only after written permission and
an explicit reuse/publication agreement are obtained. This source does not close
the independent synchronized station-to-vehicle numerical holdout gate.

Source: [KHK accident case database](https://www.khk.or.jp/public_information/incident_investigation/hpg_incident/incident_db.html)
