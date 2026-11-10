# Unit 2 Infrastructure Design Plan — Hub Token Broker and Spark Session Identity

## Purpose

Map the approved Unit 2 broker, internal TLS listener, certificate materials, and safe diagnostics to the existing local Docker Compose deployment. This stage selects concrete network, port, file, and mount patterns; implementation remains in Code Generation.

## Inputs

- `aidlc-docs/current/construction/unit-2/functional-design/`
- `aidlc-docs/current/construction/unit-2/nfr-requirements/`
- `aidlc-docs/current/construction/unit-2/nfr-design/`
- `aidlc-docs/current/construction/unit-1/infrastructure-design/`
- Existing `docker-compose.yml`, `.env.example`, `infra/jupyter/`, and `.runtime/` conventions.

## Infrastructure design work plan

- [x] Map the in-process TLS listener to a concrete Hub container address, internal port, and route without publishing it to the host.
- [x] Define internal CA and server-certificate files, permissions, runtime preparation, and explicit rotation steps.
- [x] Choose how the CA certificate is delivered read-only to spawned user servers and configured as the broker client's trust root.
- [x] Define any Compose network/IPAM or DockerSpawner changes needed while preserving the approved core, jupyter-user, and data-access boundaries.
- [x] Map certificate files to protected host storage and read-only container mounts; keep CA signing key out of containers.
- [x] Preserve process-local safe counters/logs with no metrics endpoint or new monitoring service.
- [x] Confirm messaging is unnecessary and identify shared network/resource impacts.
- [x] Generate `infrastructure-design.md` and `deployment-architecture.md` after answers are resolved.

## Clarification questions

### Q1 — Listener address and port

The Hub is multi-homed on `core` and `jupyter-user`; the broker TLS listener should be reachable from user servers but not from the host or provider network. Which binding pattern should Compose use?

A) Allocate the Hub a stable address on an explicitly configured `jupyter-user` subnet and bind the in-process TLS listener to that address on internal port `8443`; do not publish the port to the host. User servers use the `jupyterhub` service DNS name and port (Recommended; makes the interface boundary explicit, with subnet collision checked against the local host).

B) Bind to `0.0.0.0:8443` without host port publication and rely on broker API-token authentication (simpler, but the listener also accepts connections arriving through the Hub's other container network interfaces).

C) Other address/port/topology (please specify).

[Answer]: A — Give the Hub a stable address on an explicitly configured `jupyter-user` subnet, bind the broker listener to that address on internal port 8443, publish no host port, and use the `jupyterhub` service DNS name from user servers. Validate the subnet does not conflict with host/VPN routes before applying it.

### Q2 — Runtime certificate file layout

Where should runtime-prepared certificate material live and how should it be mounted?

A) Keep CA private key and Hub certificate/key under protected `.runtime/credentials/` paths with restrictive host permissions; mount only the Hub certificate/key read-only into the Hub. Store the public CA certificate under `.runtime/container-mounts/` for read-only user-server delivery. Never mount the CA private key (Recommended; aligns with existing runtime credential conventions and separates signing material from trust material).

B) Store all certificate files, including the CA private key, under `.runtime/container-mounts/` and mount only selected files (easier layout, but places signing material beside non-secret trust files).

C) Other file layout or storage (please specify).

[Answer]: A — Keep CA private key and Hub certificate/key in protected `.runtime/credentials/`; put the public CA certificate in `.runtime/container-mounts/`; mount the Hub certificate/key and user CA certificate read-only, and never mount the CA key.

### Q3 — CA trust delivery to user servers

How should spawned single-user containers receive the public CA certificate?

A) Add a read-only DockerSpawner bind mount for only the public CA certificate, and configure the broker HTTP client to use that explicit CA file and verify the `jupyterhub` DNS name (Recommended; certificate rotation updates the mounted file without rebuilding the pinned image).

B) Copy the public CA certificate into the pinned single-user image at build time (immutable image contents, but CA rotation requires rebuilding/redeploying the image).

C) Other trust delivery (please specify).

[Answer]: A — Use a read-only DockerSpawner bind mount for the CA certificate and configure the broker client to trust that file and validate the `jupyterhub` DNS SAN.

### Q4 — Listener startup and rotation behavior

How should Compose and the Hub behave when TLS files are absent, invalid, or being rotated?

A) Require an idempotent host-side preparation command before Hub startup; validate SAN, expiry, key/certificate match, and permissions before opening the listener. Fail Hub readiness if invalid. Rotation is explicit: prepare replacement files, recreate Hub and user servers, then verify the broker TLS handshake before use (Recommended; no startup self-signing or verification bypass).

B) Have the Hub generate certificates at startup when files are missing (simpler initial startup, but couples issuance to container lifecycle and can silently change trust identity).

C) Other lifecycle (please specify).

[Answer]: A — Run idempotent host-side certificate preparation before Hub startup; validate SAN, expiry, key match, and permissions; fail Hub readiness on invalid files; rotate explicitly and recreate Hub and user servers before verifying TLS.

## Category assessment

- **Deployment environment:** Inherit the approved single-host Docker Compose profile; no cloud provider is in scope.
- **Compute infrastructure:** Reuse the existing JupyterHub container and process; no broker service or sidecar is added. Q1 resolves listener binding and internal port.
- **Storage infrastructure:** No database, object store, or volume is added. Q2/Q3 resolve protected host files and read-only container delivery; Hub auth state remains on its existing named volume.
- **Messaging infrastructure:** Not applicable. The broker is synchronous request/response and refresh coordination is process-local; no queue or broker component is required.
- **Networking infrastructure:** Preserve `core`, `jupyter-user`, and `data-access`. Q1 resolves how the Hub's broker listener is isolated on a multi-homed container. The broker port remains unpublished on the host.
- **Monitoring infrastructure:** Reuse safe Hub logs and process-local counters from NFR Design; no external backend, scrape endpoint, or alerting service is added.
- **Shared infrastructure:** Reuse the Hub, Keycloak, existing Compose networks, and DockerSpawner lifecycle. User servers retain Polaris/RustFS access only through `data-access` and gain no Keycloak, database, Docker Engine, or Hub state access.

## Next gate

The user selected all four recommended options. These choices retain the broker in the Hub process, isolate its listener to a stable Hub address on `jupyter-user`, keep the port internal, deliver only public CA trust to servers, and require explicit certificate validation and rotation. Infrastructure artifacts are generated for review; no runtime configuration or containers were changed.
