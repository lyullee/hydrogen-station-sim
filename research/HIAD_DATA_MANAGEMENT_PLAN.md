# HIAD–SAGA expert study data-management plan

## Data classes

| Class | Examples | Repository status |
|---|---|---|
| Public source | HIAD event identifiers and public incident fields | May be archived subject to source terms |
| Generated research data | masked responses, latency, allocation, coded ratings | Release only as permitted by the institutional determination |
| Coded reviewer descriptors | role, experience, qualifications, conflicts | Aggregate publication; coded restricted file |
| Direct identifiers | name, personal/institutional contact, identity-code key | Never commit or deposit publicly |
| Credentials | API keys, tokens, passwords | Never collect in study artifacts |

## Storage and access

The public repository stores code, frozen protocols and non-identifying evidence.
The coordinator stores the allocation key separately from reviewer packets until
database lock. Each reviewer receives only their own pre-coded sheet and the
reference package. Any identity-code key is kept in institution-controlled storage
accessible only to the responsible investigator or delegated data custodian.

## Integrity and provenance

SHA-256 manifests lock the approved casebook, raw responses, randomized blank
form, allocation key, reviewer packets and final rating files. Collection records
software commit, provider/model, prompt hash, response failures and latency.
Analysis rejects missing/duplicate codes, modified response text, invalid values
and unexplained binary safety marks.

## Retention, withdrawal and destruction

The institution must set the retention period and withdrawal boundary before
recruitment. Direct identifiers and the code key should be destroyed at the end
of the approved retention period. De-identified research artifacts may be retained
with the article only if permitted by the determination and reviewer information
process. Backups follow the same access and destruction rules.

## Publication and repository release

The article reports aggregate reviewer characteristics, condition-level effects,
safety-event rates and agreement. A public replication package should omit direct
identifiers, the identity-code key, credentials and any free text that could
reasonably identify a reviewer. Free-text comments require disclosure review before
release. Restricted artifacts are described in a data-availability statement.

## Incident handling

Suspected disclosure, credential inclusion, unauthorized access or hash mismatch
halts collection/analysis. Preserve logs, notify the responsible investigator and
follow institutional privacy/security procedures. Do not rewrite or silently
replace affected records; document the deviation and recovery decision.
