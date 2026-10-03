# HyRAM+ 6.1 production-adapter verification

Generated: `2026-10-03T00:44:50.842010+00:00`  
Digital-twin source: `2cef4513fed1dc2688ae55d790a3d9f1e05f41ec` (dirty=False)  
Installed HyRAM: `6.1`  
Upstream reference: `v6.1` / `b45abf9a6d995951311be6aad836f1874e4d420b`

## Result

- Sandia validation suite: **PASSED** (47 tests, 803 subtests).
- Installed/upstream Python source identity: **MATCH**.
- Production-adapter API parity: **PASS**.

| Case | Parity | modeled flow (kg/s) | 4 vol% plume distance (m) | visible flame length (m) |
|---|---:|---:|---:|---:|
| low-bank-1mm | PASS | 0.016613 | 4.339 | 2.326 |
| mid-bank-2mm-cold | PASS | 0.108305 | 11.382 | 6.057 |
| high-bank-3mm-override | PASS | 0.296366 | 17.224 | 9.246 |

## What this establishes

Sandia's tests exercise HyRAM against published plume, flame-radiation and unconfined-overpressure experiments. The local parity cases separately establish that the production adapter preserves SI units, coordinates, contour selection and output indexing for the exact installed package.

## Claim boundary

This verification does not independently revalidate HyRAM physics, establish a regulatory separation distance, or validate the station geometry. The 4 vol% result is a directional centerline distance. Radiation and overpressure values apply only at the listed observation coordinates. The upstream validation acceptance limits belong to HyRAM's maintainers; they are not new acceptance criteria created by this project.

## Reproduction

```powershell
git clone --depth 1 --branch v6.1 https://github.com/sandialabs/hyram.git data\public_validation\raw\hyram-v6.1
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe scripts\run_hyram_adapter_verification.py
```

Machine-readable details, per-field errors and captured upstream test output are written to the selected output directory as `verification.json`.
