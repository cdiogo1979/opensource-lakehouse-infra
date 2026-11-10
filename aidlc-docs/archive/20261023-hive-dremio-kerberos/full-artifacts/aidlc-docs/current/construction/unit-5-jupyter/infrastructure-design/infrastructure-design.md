# Unit 5 Infrastructure Design — JupyterHub and Per-User Spark

## Deployment Target

Integrate JupyterHub with the existing single-host Docker Compose project and network `iceberg-poc-net` (Compose key `iceberg_net`). Add the Hub to the default Compose lifecycle. Publish only the Hub UI at `127.0.0.1:8008:8000`. Reuse the existing KDC, Hive Metastore, and RustFS service DNS names. The Hub and spawned user servers use the existing private network; no extra network, published backend port, queue, or monitoring service is introduced.

## Logical-to-Concrete Mapping

| Responsibility | Infrastructure mapping |
|---|---|
| JupyterHub | Add a `jupyterhub` Compose service built from a new target-owned Hub image definition. Retain JupyterHub 5.3.0 and pinned compatible Python dependencies. Add it to the default profile and publish `127.0.0.1:8008:8000`. Preserve a separate Hub state volume. |
| Single-user image | Define a build-only Compose service/target for the Jupyter/Spark image, using the retained Spark 3.5.5/Iceberg 1.8.1 baseline and pinned dependencies. Build it explicitly before starting the Hub; DockerSpawner starts its local image on demand. Keep the build target out of the default startup set. |
| DockerSpawner | Run inside the Hub container and communicate with the host Docker daemon through the Docker socket. The socket is mounted only into the Hub. The Hub receives no RustFS key contents. |
| User notebook/Spark servers | DockerSpawner creates up to three containers (`user_a`, `user_b`, `admin`) on `iceberg-poc-net`. Run as non-root `jovyan`, without privileged mode, Docker socket, or cross-user mounts. Use the existing service names for Hive/KDC/RustFS access. |
| Kerberos credential source | For a spawned username, mount only `.runtime/credentials/keytabs/<username>.keytab` read-only into that user's container. The Hub does not mount or read keytab contents. Each user server has a private ephemeral ticket-cache path that is destroyed with its container. |
| RustFS credential source | Mount only that user's existing access-key and secret-key files from `.runtime/credentials/` read-only into the matching user container. Session startup reads the mounted files without printing values. Do not mount the full credentials directory and do not pass RustFS values through Hub environment variables. |
| User workspace | Attach a separate named Docker volume per username for writable notebook files. Keep it independent from the Hub state volume and the platform's catalog/storage volumes. Do not attach the sibling shared writable notebooks directory. |
| Existing platform services | Reuse `kdc`, `hive-metastore`, and `object-store` on `iceberg-poc-net`. User Spark uses the existing Hive Iceberg catalog and RustFS warehouse contract. No Nessie connection remains in the Jupyter path. |
| Operator visibility | Use `docker compose ps` and existing Hub/user container logs. Do not add a Compose healthcheck, metrics endpoint, alerting, log collector, or centralized evidence store. |

## Image Build and Startup Dependencies

1. Ensure the existing platform is initialized and the three identity/keytab and RustFS credential sets are already provisioned. Identity provisioning remains an explicit operator step; JupyterHub does not create or rotate accounts.
2. Build the Hub and single-user images explicitly using the documented Compose build targets. Pin DockerSpawner and related Hub Python packages to versions compatible with JupyterHub 5.3.0.
3. Start the existing default Compose stack. JupyterHub startup depends on the KDC, Hive Metastore, and RustFS being healthy, but it does not trigger identity provisioning, ETL, or storage initialization as a side effect.
4. A user login starts a single-user container on demand. If its prerequisites or resources are unavailable, only that session fails and the operator sees a spawn/startup failure.

## Credential and Host-Path Boundary

DockerSpawner asks the Docker daemon to mount individual host files into the matching user server. The Hub configuration may contain host path references, but it must not mount/read the credential files or place their values in its environment. The Hub's Docker socket remains a privileged host-control interface and is confined to the local-only Hub container.

The target credential files are owner-restricted. Before implementation is considered complete, confirm the non-root `jovyan` process can read only its own mounted files while the host-side credential permissions remain restrictive. Do not solve a UID/permission mismatch by making all credentials or the entire credential directory broadly readable. If secure per-file access cannot be achieved with this bind-mount design, stop and present a narrow alternative for review.

## Storage, Networking, and Recovery

- Use distinct Docker named volumes for `jupyterhub-data` and each user's workspace (for example, one stable volume name per configured username).
- Attach Hub and user containers to `iceberg-poc-net`; use `hive-metastore:9083`, the configured KDC hostname, and `object-store:9000` internally. User containers do not require new host-published ports.
- Keep Hub UI host binding on `127.0.0.1:8008`; do not bind to all host interfaces.
- Do not add messaging, session queues, autoscaling, resource limits, health/monitoring components, or shared Spark compute.
- On failure, stop/restart only the affected server after operator diagnosis. Preserve work volumes, existing platform volumes, data, and credentials. Do not restart a failed authorization query under another identity or rerun ETL.

## Infrastructure Verification Gates

- Confirm DockerSpawner's single-user bind mounts use host-resolved file paths and only attach the requested user's credentials.
- Confirm non-root file access works for the individually mounted keytab and RustFS files without weakening host credential permissions.
- Confirm spawned containers can contact the Hub API and the existing platform service DNS names on `iceberg-poc-net`.
- Confirm the named per-user work volumes survive container recreation and remain separate.
- Verify the Spark/Hive/RustFS authorization matrix and three-session capacity in the later Build and Test stage; this design alone does not establish either outcome.
