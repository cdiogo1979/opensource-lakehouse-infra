# Unit 4 NFR Design Questions

Please answer each question by filling in the letter after `[Answer]:`. Choose `X` and describe your preference if none of the options fits.

## Question 1 — Resilience and recovery pattern

How should a failed authorization scenario be handled?

A) Stop the affected scenario, preserve all data and credentials, classify the failure, and allow the operator to rerun only the failed non-destructive query after correcting a diagnosed issue; add no automatic retry/recovery service (recommended; matches approved NFRs).

B) Add bounded automatic retry for specified failure categories. Name those categories and retry limits after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 2 — Scalability pattern

What scale boundary should the design support?

A) Keep the fixed two-user/two-database sample scope and serial query checks; add no scaling mechanism or capacity target (recommended).

B) Add a specific user, database, or query concurrency target. Describe it after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 3 — Performance pattern

What query execution behavior should the design optimize for?

A) Prioritize clear identity and authorization evidence; execute checks serially and set no latency/throughput SLA or caching requirement (recommended).

B) Add a measurable latency/throughput objective or query optimization requirement. Specify it after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 4 — Security pattern

Which credential and evidence-handling pattern should be used?

A) Keep separate local Dremio passwords in restricted ignored runtime files, retain the Dremio Kerberos service identity and bounded proxy rules, redact evidence, and leave the RustFS writer key unchanged (recommended; matches approved NFRs).

B) Add a named security control, identity provider, or credential lifecycle requirement. Describe it after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 5 — Logical components

Should Unit 4 add any logical or infrastructure component?

A) Use only the existing Dremio, Hive Metastore, Kerberos, RustFS, and local evidence files; add no queue, cache, audit service, monitoring service, or authorization component (recommended; matches approved scope).

B) Add a named component and describe its responsibility and local deployment boundary after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A
