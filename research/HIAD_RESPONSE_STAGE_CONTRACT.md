# HIAD response-stage contract audit

This deterministic audit checks the operator-facing response contract for
the public HIAD metadata mappings. It does not read HIAD emergency-action
or lesson text and does not establish correctness, safety, effectiveness,
or operator benefit.

- Contract result: **PASS**
- Cases mapped: **34/34**
- Required stages: **recognition, immediate, stabilize, restart, prevention**
- Cases with missing stages: **0**
- Normal periodic quiet contract: **PASS**
- Coverage/source hashes: **PASS**

## Contract checks

Every mapped family must expose recognition, immediate action, stabilization,
restart prerequisites and prevention/safety-management steps. Metadata that
explicitly describes ignition must include the hydrogen-fire family; structural
damage metadata must include the structural-damage family. A no-release row
must not invent a fire plan.

- Ignition rows without a fire family: `[]`
- Structural rows without a structural family: `[]`
- No-release rows with a fire family: `[]`

## Claim boundary

A passing result means the interface can carry staged, source-linked guidance
for this metadata inventory and stays quiet on an idle periodic frame. It is
not evidence that the stages are complete for a real site, that the physics
or distances are valid, or that an operator would perform better.

Public source: `https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt`
