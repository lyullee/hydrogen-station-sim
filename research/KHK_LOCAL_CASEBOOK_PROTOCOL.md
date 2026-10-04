# KHK local accident-grounding protocol

This repository contains the official KHK/METI FY2025 high-pressure-gas
accident workbook only as an ignored local file. KHK's terms prohibit transfer,
distribution, public posting and mirroring of all or part of the database, and
require permission for commercial use. The workbook and every casebook derived
from it therefore remain under `data/`, which is gitignored.

Run the local extraction with:

```text
.venv\Scripts\python scripts\prepare_khk_local_casebook.py
```

The command selects rows whose material contains hydrogen and whose title,
industry, equipment, handling state or description identifies an HRS boundary
(station, dispenser, filling hose/nozzle, trailer, cardle or fuel-cell
vehicle). It maps each selected row to candidate response families already
implemented in `src/h2station/data/emergency_playbooks.json`. Multiple families
are retained because one real event can combine a leak, failed isolation and a
fueling or trailer boundary condition.

The generated `casebook.json` and `manifest.json` are local-only. The mapping
is a scenario-coverage aid, not an expert-approved holdout, a frequency model,
or evidence that the response is effective. Any public de-identified aggregate,
case vignette or LLM evaluation requires written KHK/METI permission followed
by a coordinator-approved blinded protocol and independent expert review.
