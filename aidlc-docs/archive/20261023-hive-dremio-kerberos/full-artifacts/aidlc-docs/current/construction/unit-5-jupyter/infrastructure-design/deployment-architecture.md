# Unit 5 Deployment Architecture — JupyterHub and Per-User Spark

## Existing Compose Project

Unit 5 extends the existing `hive-dremio-rustfs` Compose project. The Compose network key is `iceberg_net`, with Docker network name `iceberg-poc-net`. Existing platform services remain unchanged. JupyterHub is included in default startup, uses the existing private network, and binds its browser endpoint only to host loopback at port 8008.

## Runtime Path

1. The operator initializes the existing KDC, Hive Metastore, RustFS bucket, and per-user identities through their existing setup procedures.
2. The operator builds the pinned JupyterHub and single-user Spark images using explicit Compose build targets.
3. The operator starts the default Compose project. The Hub starts after KDC, Hive Metastore, and RustFS health prerequisites are met.
4. A user selects one of the configured development labels. JupyterHub/DockerSpawner starts a single-user container attached to `iceberg-poc-net`.
5. DockerSpawner mounts that user's keytab, RustFS access-key file, and RustFS secret-key file read-only, plus the stable named workspace volume for that username. No other user's files are mounted.
6. The user container authenticates to Kerberos, then local Spark connects to Hive Metastore and RustFS through existing Compose DNS names. Authorization checks use the user's matching identity.
7. On session stop, the container and ticket cache end; the per-user workspace volume remains. The operator inspects local container status/logs and manually restarts only the affected session after diagnosis.

## Deployment Components

| Component | Deployment unit | Persistence / exposure |
|---|---|---|
| JupyterHub | Default Compose service built from the target project | `jupyterhub-data` named volume; `127.0.0.1:8008:8000`; Docker socket mounted only here |
| Single-user image | Explicit Compose build target, not a default running service | Local image consumed by DockerSpawner; no host port |
| `user_a`, `user_b`, `admin` notebook servers | On-demand DockerSpawner containers, up to three concurrently | Separate named work volume per username; matching read-only credential file mounts; `iceberg-poc-net` only |
| Hive Metastore, KDC, RustFS | Existing Compose services | Existing ports, credentials, data volumes, and healthchecks remain unchanged |
| Logs/evidence | Docker logs and local workflow records | No centralized monitoring/logging service; redact credentials and tickets |

## Network and Trust Boundaries

- Browser traffic: local host → `127.0.0.1:8008` → Hub container.
- Spawn/control traffic: Hub → local Docker daemon through the Docker socket → isolated user containers. The socket is never mounted into a user server.
- User data traffic: user server → `hive-metastore:9083`, KDC service DNS, and `object-store:9000` over `iceberg-poc-net`.
- Credential access: Docker daemon attaches selected host files to the matching user container. The Hub holds only path references and has no mounted RustFS key files.
- Workspace access: each user server can write only to its own named workspace volume; no shared writable notebook volume is present.

## Lifecycle and Preservation

Stopping JupyterHub does not remove its state volume, per-user work volumes, KDC/Hive/RustFS volumes, or sample data. Stopping or recreating one notebook container removes its session ticket cache but preserves that user's named workspace. Cleanup of user workspaces or platform data is outside this unit and requires an explicit operator action.

No message broker, queue, monitoring service, healthcheck, shared Spark cluster, new host network, or public endpoint is part of this deployment design.
