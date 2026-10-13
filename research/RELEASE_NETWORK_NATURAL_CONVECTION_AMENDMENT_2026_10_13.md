# Release-network natural-convection amendment

The apparatus-resolved release candidate now supports a state-dependent
gas-to-wall heat-transfer option before any qualifying apparatus logger outcome
has been received or inspected. This is a prospective physics amendment, not a
repair or reinterpretation of a failed holdout.

## Why this change was made

The original frozen PRESLHY local-aperture evaluation remains a negative result
at 11/22 jointly passing cases. A separate development-only model on that
already consumed campaign showed that non-adiabatic wall coupling is a material
physical term. The apparatus candidate previously represented wall energy but
accepted only one constant internal coefficient for every state and control
volume. That made its thermal boundary less transferable across pressure,
temperature and geometry.

The new `natural_convection` mode evaluates the Churchill--Chu correlation from
local CoolProp HEOS hydrogen properties, the instantaneous wall-gas temperature
difference and a separately declared characteristic length. Source and line
control volumes use independent geometry inputs. No coefficient is optimized
against a case. The previous `constant` mode remains the default and reproduces
the earlier trajectory.

## Freeze rules

For a future confirmatory campaign, the manifest must select the heat-transfer
mode and freeze source/line characteristic lengths from apparatus geometry
before numerical outcomes are opened. Selecting a mode or length from residuals
is prohibited. The model now archives the coefficient history for every control
volume so reviewers can verify the applied thermal boundary.

The prior candidate is recoverable at commit
`eb68ec9448dc094d5cd4c4d3210e8baa79615bf7`; its model SHA-256 is
`FA0267FD6C06450C46651A019FA152BAD599DEFD3EB7C2854DBE638618B0C39A`.
The amended model SHA-256 is
`BA240756C4DDDB55AA7A98FC40B3635494BF157E7FBE4835BBDDB2F06AFECED6`.
The machine-readable amendment records both protocol hashes.

## Claim boundary

Unit tests establish backward compatibility, state dependence, fail-closed
geometry validation and numerical mass/energy closure. They do not establish
external physical accuracy. The IJHE readiness gate therefore remains unchanged
until an untouched pure-hydrogen apparatus campaign satisfying the synchronized
channel contract is evaluated once under the frozen protocol.
