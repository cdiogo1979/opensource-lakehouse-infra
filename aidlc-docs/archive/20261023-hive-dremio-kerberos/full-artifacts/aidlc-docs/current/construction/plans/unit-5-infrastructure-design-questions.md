# Unit 5 Infrastructure Design Questions

Please answer each question with a letter after `[Answer]:`.

## Question 1 — Deployment Lifecycle
How should the JupyterHub service participate in the existing Compose lifecycle?

A) Add it to the default Compose profile so the normal PoC startup starts the Hub.

B) Put it behind an opt-in `jupyter` profile so the operator starts it only when demonstrating notebook access.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 2 — Compute and Image Build
How should the local single-user Spark image be built and made available to DockerSpawner?

A) Keep a separate documented `docker compose build` target/service for the single-user image, then let DockerSpawner start up to three containers from that local image.

B) Keep the existing manual `docker build` workflow for the single-user image and document it alongside Compose startup.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 3 — Workspace Storage
Where should each persistent per-user notebook work volume live?

A) Use separate Docker named volumes per username, independent of the Hub state volume.

B) Use separate host bind-mount directories under `.runtime/jupyter/work/` for easier operator inspection and manual backup.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 4 — Credential Delivery and Shared Infrastructure
How should the individual RustFS credentials be delivered to each spawned session?

A) DockerSpawner mounts only that user's existing local credential file read-only into the corresponding user container; startup reads it without printing the values. The Hub receives no RustFS keys.

B) The Hub reads each user's credential files and injects the matching values as environment variables into the corresponding user container.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 5 — Networking
Which network arrangement should the Hub and user containers use to reach the existing Hive/KDC/RustFS services?

A) Attach the Hub and spawned user containers to the existing `iceberg-poc-net` network and use existing service DNS names; publish the Hub only on `127.0.0.1:8008`.

B) Add a separate Jupyter control network for Hub-to-user-server traffic while also attaching user containers to `iceberg-poc-net` for platform access.

X) Other (please describe after `[Answer]:` below)

[Answer]:A

## Question 6 — Messaging
Should session startup remain synchronous through DockerSpawner?

A) Yes. Do not add a queue or message broker; a resource-constrained spawn fails for that session and is reported to the operator. (This matches the previously approved Unit 5 NFR Design.)

B) Add a queue to hold session-start requests until local resources become available.

X) Other (please describe after `[Answer]:` below)

[Answer]: A

## Question 7 — Monitoring and Health Visibility
How should Hub availability be exposed to the local operator?

A) Use existing Docker Compose service state and logs only; add no healthcheck or monitoring component.

B) Add a Compose-native Hub healthcheck while still adding no separate monitoring service.

X) Other (please describe after `[Answer]:` below)

[Answer]:A
