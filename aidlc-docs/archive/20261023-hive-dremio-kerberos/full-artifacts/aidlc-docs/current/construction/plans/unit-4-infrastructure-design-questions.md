# Unit 4 Infrastructure Design Questions

Please answer each question by filling in the letter after `[Answer]:`. Choose `X` and describe your preference if none of the options fits.

## Question 1 — Deployment environment

Where should Unit 4 run?

A) Use the current single-host Docker Compose PoC and existing operator workflow; add no cloud or remote environment (recommended; matches approved scope).

B) Add a separate deployment target. Name the environment and required differences after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 2 — Compute infrastructure

What compute should run the authorization checks?

A) Use the operator's existing local Dremio UI/JDBC or SQL client and existing Dremio, Hive, KDC, and RustFS containers; add no query-runner container or resource-sizing target (recommended).

B) Add a dedicated query-runner container or specify resource requirements. Describe it after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 3 — Storage infrastructure

How should Unit 4 handle its data and credential storage?

A) Reuse the existing Hive/PostgreSQL metadata and RustFS warehouse volumes without reset; store distinct Dremio test passwords and redacted evidence only in ignored, restricted `.runtime/` paths; do not rotate the RustFS writer key (recommended).

B) Add a new storage service or lifecycle policy. Describe the required boundary after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 4 — Messaging infrastructure

Does Unit 4 need messaging or asynchronous infrastructure?

A) No. Run the small verification sequence synchronously and serially; do not add a queue or event bus (recommended).

B) Add a messaging component. Name it and state the use case after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 5 — Networking infrastructure

What network boundary should Unit 4 use?

A) Reuse the existing private `iceberg_net` and existing loopback-only host ports; expose no new host port, gateway, or public endpoint (recommended).

B) Add or change a network path. Specify endpoints and exposure after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 6 — Monitoring and logging infrastructure

What observability infrastructure is required?

A) Use existing container logs and concise local redacted query results; add no monitoring, alerting, or centralized log service (recommended; matches approved NFRs).

B) Add a named monitoring/logging service or a retention requirement. Describe it after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A

## Question 7 — Shared infrastructure and isolation

How should Unit 4 share existing platform infrastructure?

A) Reuse the existing single Compose deployment. Keep Dremio test passwords distinct, preserve component credential boundaries, and use the already bounded proxy-user allowlist; add no tenant or service isolation layer (recommended).

B) Add a new isolation boundary or separate deployment. Describe it after `[Answer]:`.

X) Other (please describe after `[Answer]:`)

[Answer]: A
