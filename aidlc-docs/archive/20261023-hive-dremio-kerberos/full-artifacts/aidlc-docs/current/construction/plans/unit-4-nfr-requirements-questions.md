# Unit 4 NFR Requirements Questions

Please answer each question by filling in the letter after `[Answer]:`. Choose `X` and describe your preference if none of the options fits.

## Question 1 — Performance and scale

What performance and scale target should Unit 4 use for the Dremio authorization demonstration?

A) Keep the existing PoC scale: two query users, the existing 16 sample views/tables, serial allow/deny checks, and functional completion only; set no latency or throughput SLA (recommended).

B) Add a specified query concurrency or response-time target. State the target after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 2 — Availability and recovery

What availability behavior is required while running the authorization checks?

A) Keep single-host/manual recovery. Preserve current persistent volumes and data, report failures with redacted evidence, and rerun only the failed non-destructive query checks; no HA or uptime SLA (recommended).

B) Add automatic restart/recovery behavior beyond the existing Compose setup. Describe the required behavior after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 3 — Security evidence and retention

How should Unit 4 retain query identity and authorization evidence?

A) Record only redacted scenario results and the minimum service-log excerpts needed to identify effective user and denial component; keep artifacts local and do not set a formal retention period (recommended).

B) Retain a specified additional audit trail or retention period. Describe it after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 4 — Identity and credential boundary

Which authentication boundary should the Dremio allow/deny checks use?

A) Use separate Dremio local accounts for `user_a` and `user_b`, with distinct generated passwords stored only in ignored, permission-restricted `.runtime/credentials/` files; continue to use the existing Dremio Kerberos service identity for Hive and do not rotate the RustFS writer key (recommended; matches the approved identity model).

B) Use an existing external identity provider for Dremio users. Name the provider and describe the local setup after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A
