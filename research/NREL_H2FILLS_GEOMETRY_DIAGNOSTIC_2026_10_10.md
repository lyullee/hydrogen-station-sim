# NREL H2FillS geometry diagnostic (2026-10-10)

This is a post-access component diagnostic for the public NREL H2FillS 2022 HDVS Type IV sample. It is not a full-station validation and does not establish field safety performance.

- Seven tank traces were screened on a common clock.
- The frozen legacy geometry produced 0/7 screening passes, with pressure RMSE **6.164 MPa** and final pressure error **-8.681 MPa**.
- Capacity-EOS geometry with the frozen thermal fit produced 7/7 passes and pressure RMSE **3.538 MPa**.
- Capacity-EOS geometry with no volume multiplier produced 7/7 passes and pressure RMSE **0.496 MPa**.

The result identifies a systematic geometry/pressure-boundary issue and supports a prospective capacity-EOS protocol. It does not authorize changing the frozen production default or promoting this post-access result to an IJHE validation gate.

Source: [NREL H2FillS download page](https://www.nlr.gov/hydrogen/h2fills-download). The raw workbook remains local and is not redistributed.
