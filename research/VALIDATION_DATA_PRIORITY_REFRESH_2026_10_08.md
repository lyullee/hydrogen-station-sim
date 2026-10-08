# Validation data priority refresh — 2026-10-08

This queue prioritizes the data requests most likely to remove several model
and publication blockers at once. It is an acquisition plan, not validation
evidence, and no request is recorded as sent.

| Rank | Candidate | Why it has the largest expected effect | Required next step |
|---:|---|---|---|
| 1 | HyFill heavy-duty HRS experiments | More than 50 reported 350/700 bar tests can test pressure, flow, tank temperature and station delivery together. | Send `HYFILL_HD_HRS_DATA_REQUEST_DRAFT.md` through an approved institutional route and request an undisclosed split. |
| 2 | Wan et al. Type III/IV aspect-ratio experiments | Directly tests the current Type-III temperature failure and the geometry-sensitive mixed-convection model. | Send `WAN_2026_TYPE_III_IV_DATA_REQUEST_DRAFT.md` and request at least six custodian-held blind cases. |
| 3 | Deng et al. large Type-IV high-flow experiment | Supplies real transient mass flow and spatial temperature response for large tanks. | Send the strengthened `DENG_2025_HIGHFLOW_DATA_REQUEST_DRAFT.md`; require unreported repeats or a blind split. |
| 4 | 250 bar ferry Type-IV experiment | Tests capacity and geometry transfer on a 28 kg class tank with internal thermocouples. | Send `FERRY_250BAR_TYPE_IV_DATA_REQUEST_DRAFT.md`; use as a bounded transfer test outside H70 scope. |
| 5 | RHeaDHy Mid Flow Twin | Real heavy-duty campaign can support a station-to-vehicle full-loop holdout if the logger channels are released. | Send `RHEADHY_DATA_REQUEST_DRAFT.md` and freeze at least eight eligible fills before inspection. |

The first three requests have the highest expected value because they can
address the full-loop, Type-III thermal and geometry-transfer failures with one
coordinated acquisition round. Public article plots and aggregate errors do not
close any readiness gate. A dataset qualifies only after rights, hashes,
channel definitions, a frozen split and a no-fitting score are recorded.
