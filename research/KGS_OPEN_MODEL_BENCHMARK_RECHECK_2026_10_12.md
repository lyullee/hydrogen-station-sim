# KGS open model benchmark recheck — 2026-10-12

The paper *Enhanced Thermofluidic Modeling and Open-Source Rigorous Simulation of Hydrogen Fueling Systems Validated with Real-World Data* reports a Python thermofluidic model evaluated against six Korean hydrogen-refuelling-station scenarios. It is useful aggregate benchmark context: the paper reports mean temperature accuracy/R² of 94.5%, mean pressure accuracy/R² of 96.7%, mean final pressure of 73.9 MPa and mean fueling time of 351.68 s.

The preprint says that the Python code is published in a Google Drive folder. A reproducible access check on 2026-10-12 returned HTTP 401/sign-in required for that folder. No raw code, row-level synchronized station/controller/dispenser/vehicle trace, or underlying-data reuse licence could therefore be independently inspected. The article is retained as published aggregate context and a code-access lead only.

This recheck does not alter runtime parameters, add a holdout, promote a validation gate, or support a full station-to-vehicle or field-safety claim. The machine-readable boundary is in `research/kgs_open_model_benchmark_recheck_2026_10_12.json`.
