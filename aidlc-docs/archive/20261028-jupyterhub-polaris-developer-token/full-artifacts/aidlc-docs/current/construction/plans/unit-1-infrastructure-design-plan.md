# Unit 1 Infrastructure Design Plan — JupyterHub Foundation

## Purpose

Map the approved Unit 1 functional and NFR design to the local Docker Compose deployment. Specify the JupyterHub control plane, custom matching single-user image, persistent volumes, credential mounts, networking, health checks, and host-tunable resource limits. This stage designs infrastructure only; implementation and runtime changes remain for Code Generation and Build and Test.

## Inputs

- `aidlc-docs/current/construction/unit-1/functional-design/`
- `aidlc-docs/current/construction/unit-1/nfr-requirements/`
- `aidlc-docs/current/construction/unit-1/nfr-design/`
- `aidlc-docs/current/inception/application-design/`
- `aidlc-docs/current/inception/application-design/unit-of-work.md`
- Existing `docker-compose.yml`, `.env.example`, `infra/`, and runtime credential conventions.

## Infrastructure design work plan

- [x] Define local Compose deployment and service/image build and pinning strategy.
- [x] Map Hub and single-user compute, including tunable resource limits for two concurrent servers.
- [x] Specify SQLite state, per-user persistent homes, volume ownership, and retention boundaries.
- [x] Specify protected credential file generation/mounts for OIDC client secret and Hub crypt key.
- [x] Define browser, Hub-to-Keycloak, and user-container network paths while preserving the canonical issuer.
- [x] Define health checks, lifecycle logs, and local operator diagnostics.
- [x] Confirm whether messaging infrastructure is unnecessary for this unit and define shared-network isolation.
- [x] Generate `infrastructure-design.md` and `deployment-architecture.md` after answers are resolved.
- [x] Validate the architecture against the approved two-server, callback, readiness, security, and persistence requirements.

## Clarification questions

### Q1 — Deployment target and image build

Which deployment and image workflow should this unit target?

A) Local single-host Docker Compose; build a custom Hub image and a matching Spark-enabled single-user image locally from version- and digest-pinned upstream bases, then start services with Compose (Recommended; fits the approved local profile and keeps heavy image work outside user spawn).

B) Local single-host Docker Compose; pull prebuilt custom images from a registry, with versions and digests supplied by the operator.

X) Other (please describe).

[Answer]: A — Local single-host Compose with local builds from pinned upstream image versions and digests.

### Q2 — User-server resource limits

What per-user CPU and memory limits should Compose/DockerSpawner apply? Limits must allow two servers to run together on the supported host.

A) Use host-tunable environment settings with conservative defaults of 1 CPU and 2 GiB memory per server; adjust the defaults to the machine before the two-server readiness check (Recommended).

B) Use host-tunable settings without defaults; require the operator to set both CPU and memory values before starting JupyterHub.

X) Other (please describe).

[Answer]: A — Host-tunable per-user limits, defaulting to 1 CPU and 2 GiB memory per server, adjusted for the supported host before two-server validation.

### Q3 — Browser and service networking

How should JupyterHub reach Keycloak while browsers use the approved local URLs and Polaris keeps its canonical issuer?

A) Publish Hub only on loopback as `http://jupyterhub.localhost:8000`; attach Hub and spawned user servers to the existing Compose network; configure a Keycloak internal service URL for back-channel calls while preserving `http://keycloak.localhost:8080/realms/lakehouse` as the issuer and validating issuer/audience normally (Recommended; avoids container loopback resolution failures).

B) Publish Hub only on loopback and route container back-channel requests through the host gateway using the canonical Keycloak URL.

X) Other (please describe).

[Answer]: A — Loopback browser endpoint, Compose service DNS for Keycloak back-channel requests, and the canonical issuer preserved for validation.

### Q4 — Volume lifecycle and retention

How should named Hub-state and per-user home volumes be handled during normal stop, user removal, and explicit cleanup?

A) Use Compose-managed persistent named volumes; preserve Hub state and user homes on normal stop/recreate and when disabling/removing a user; require a separate explicit operator cleanup action to delete a home (Recommended; prevents accidental notebook loss).

B) Preserve state on normal stop/recreate, but automatically delete a user's home when the identity is removed from Keycloak approved groups.

X) Other (please describe).

[Answer]: A — Preserve named volumes through normal restarts and user disabling/removal; delete a user's home only through an explicit operator cleanup.

### Q5 — Local secrets and health/diagnostic approach

Which infrastructure pattern should supply Hub secrets and expose service health?

A) Follow the existing protected `.runtime/credentials` file convention; generate missing random Hub crypt key and OIDC client secret files through an idempotent local bootstrap helper with restrictive permissions, mount them read-only into Hub only, and use Compose health checks plus redacted service logs (Recommended).

B) Require operators to create the secret files manually before Compose startup; use Compose health checks and redacted service logs.

X) Other (please describe).

[Answer]: A — Idempotently generate missing secret files with restrictive permissions, mount read-only into Hub, and use health checks with redacted logs.

### Q6 — Messaging and shared infrastructure

Should Unit 1 add any broker/queue or additional shared service for Hub, Keycloak, and spawned user containers?

A) No messaging service. Use the existing Compose network for Hub-to-Keycloak and Hub-to-container control, and a dedicated user-server network attachment for Hub reachability; keep provider services and credentials inaccessible to user containers (Recommended; no async workflow in Unit 1).

B) Add a dedicated queue/broker now for lifecycle and spawn work.

X) Other (please describe).

[Answer]: A — No queue; use separate user-server and data-access network attachments. The user-server network reaches only Hub, while the data-access network reaches Polaris and RustFS. Keep Keycloak, PostgreSQL, Docker Engine, and administrative credentials outside user containers.

## Category assessment

- **Deployment environment:** Local single-host Compose is the approved operating context; Q1 confirms build/pull behavior.
- **Compute infrastructure:** Hub plus at most two DockerSpawner containers; Q2 resolves per-user limits and host tuning.
- **Storage infrastructure:** SQLite on dedicated persistent volume and separate per-user homes are approved; Q4 resolves retention and deletion boundaries.
- **Messaging infrastructure:** No asynchronous messaging component appears in the approved flows; Q6 confirms N/A for Unit 1.
- **Networking infrastructure:** Browser callback, internal Keycloak back-channel, Hub control channel, and isolation of user containers are addressed by Q3 and Q6.
- **Monitoring infrastructure:** No external observability service is required; Q5 selects health checks and safe local lifecycle diagnostics.
- **Shared infrastructure:** Reuse the current Compose network and Keycloak service; Q6 clarifies user-server attachments and access boundaries.

## Next gate

The six answers and network clarification select a local Compose deployment with pinned local image builds, two 1-CPU/2-GiB default user servers, separated Hub and data-access networks, durable named volumes, idempotent protected credentials, and local health/log diagnostics. Generated the infrastructure design and deployment architecture for review. No application code or runtime configuration was changed.

**Approval prompt recorded 2026-10-28T18:59:34Z:** “Review Unit 1 Infrastructure Design at `aidlc-docs/current/construction/unit-1/infrastructure-design/`: `infrastructure-design.md` and `deployment-architecture.md`. They map JupyterHub to local Compose with pinned local images, SQLite Hub state, persistent per-user homes, protected credentials, host-tunable resources, and separate control/user/data-access networks. Approve to continue to Code Generation, or request changes.”
