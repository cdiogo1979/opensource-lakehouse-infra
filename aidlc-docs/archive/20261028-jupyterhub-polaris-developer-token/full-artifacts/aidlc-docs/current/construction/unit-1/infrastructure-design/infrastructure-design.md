# Unit 1 Infrastructure Design — JupyterHub Foundation

## Design scope

This design maps the approved Unit 1 functional and NFR decisions to the local single-host Docker Compose deployment. It adds the JupyterHub control plane and its two custom images while reusing Keycloak, Polaris, RustFS, and their existing database services. It supports at most two simultaneous user servers and adds no queue, external observability service, HA, or production TLS.

## Service and compute mapping

| Logical component | Infrastructure mapping | Configuration and lifecycle |
|---|---|---|
| JupyterHub | New `jupyterhub` Compose service built from `infra/jupyter/hub/` using JupyterHub 6.1.1 and a compatible pinned Python runtime. | Published as `127.0.0.1:8000:8000`; health endpoint `/hub/health`; Hub is the only user-facing service and the only service with Docker Engine access. |
| Hub database | SQLite file under `/srv/jupyterhub` on dedicated local named volume `jupyterhub-state`. | `JupyterHub.db_url` points to this persistent file. Hub is its sole reader/writer. This supersedes the earlier application-design dependency-table reference to PostgreSQL for Hub state; PostgreSQL remains in use by Keycloak and Polaris. JupyterHub documents SQLite as its default backend and appropriate to small deployments without replication needs. |
| Hub crypt key and OIDC client secret | Protected files under `.runtime/credentials/`, mounted read-only into the Hub container only. | Idempotent local bootstrap keeps a generated crypt key stable and ensures the confidential Keycloak client uses the same persistent secret file. Use restrictive host permissions and never print secret values. Do not place either file in an image, user home, or container environment where avoidable. |
| Hub image | Local custom build under `infra/jupyter/hub/` from the official JupyterHub 6.1.1 base pinned by immutable digest. | Lock Python, OAuthenticator, DockerSpawner, and all transitive dependencies to exact compatible versions. Build before spawn and record the resolved image digest. |
| Single-user image | Local Spark-enabled custom build under `infra/jupyter/singleuser/` from the matching JupyterHub single-user 6.1.1 base pinned by immutable digest. | Keep JupyterHub version exactly aligned with the Hub. Pre-build before login/spawn; include Spark and required catalog client dependencies in the image. No Hub client secret, refresh token, Docker socket, provider administrative credential, or Hub database mount. |
| User server | One DockerSpawner container per admitted Hub identity, capped at two concurrent servers. | Host-tunable defaults are 1 CPU and 2 GiB RAM per server. Check total host capacity and tune before the two-server acceptance check; Hub, Keycloak, Polaris, RustFS, database services, and the OS also need resources. Apply the CPU and memory constraints to each server, not the host as a whole. |
| User home | Per-user Docker named volume using a stable, collision-safe identity-derived name, mounted only into that user's server. | Preserve across server stop/recreate and identity disable/removal. Container removal does not remove the volume. Provide a distinct explicit operator cleanup action for permanent deletion. `docker compose down -v` must not be the routine stop procedure. |
| Keycloak | Reuse existing `keycloak` service and `lakehouse` realm. | Browser authorization uses the canonical local endpoint and callback. Hub back-channel token exchange uses Compose DNS (`http://keycloak:8080`) with explicit endpoint configuration; user tokens retain issuer `http://keycloak.localhost:8080/realms/lakehouse`. Validate issuer and audience normally. The Hub's bootstrap ensures the dedicated confidential client and persisted secret agree. |
| Polaris and RustFS | Reuse existing services; connect each to both `core` and the new isolated `data-access` network. | Polaris retains its `core` access to Keycloak/PostgreSQL and its data-access path to RustFS. User Spark reaches Polaris REST and RustFS S3 only on the data-access network, using user JWTs and Polaris-vended temporary credentials. No administrative credential is mounted into user servers. |
| Health and operations | Compose health check for Hub plus existing provider health checks; service-local logs. | Probe `/hub/health`; log safe categories, lifecycle timings, validated identity, and correlation IDs. Redact access/refresh tokens, client secrets, and vended S3 credentials. No external collector or alerting service. |

## Network segmentation

Create three Compose bridge networks:

| Network | Members | Purpose |
|---|---|---|
| `core` | Existing Keycloak, Keycloak PostgreSQL, Polaris, Polaris PostgreSQL, RustFS, and JupyterHub | Existing control/provider connections; Hub reaches Keycloak by service DNS. User servers are excluded. |
| `jupyter-user` | JupyterHub and spawned user servers | Hub proxy/API connectivity for each single-user server and the later Hub-side token broker. No Keycloak or database services are attached. |
| `data-access` | Polaris, RustFS, and spawned user servers | Only the Spark-to-Polaris REST and Spark-to-RustFS S3 data path. Keycloak and PostgreSQL are excluded. |

The Hub retains Docker socket access on the host control plane. A spawned server is created on `jupyter-user` and connected to `data-access` before the server is marked ready. The Hub alone performs Docker API calls. DockerSpawner's documented `network_name` config selects one network; therefore the second attachment is a narrow Hub-side spawner lifecycle operation using the Docker Engine API and must complete before readiness is reported. If it fails, normal spawn cleanup removes the partial server and leaves its home volume intact. This integration requires a construction compatibility check against the pinned DockerSpawner release. [DockerSpawner network configuration](https://github.com/jupyterhub/dockerspawner/blob/main/dockerspawner/dockerspawner.py)

The browser reaches only the loopback-published Hub endpoint at `http://jupyterhub.localhost:8000`. Keycloak's browser authorization URL remains `http://keycloak.localhost:8080`; Hub-to-Keycloak exchange endpoints use internal service DNS without changing the canonical issuer claim. Polaris remains responsible for validating the JWT and vending scoped storage credentials. The user runtime network is not a general-purpose firewall; this local network split limits reachability to Compose members but does not claim host-level or internet egress filtering.

## Storage and secret lifecycle

- Compose owns the persistent `jupyterhub-state` volume. User homes are persistent named Docker volumes created and retained by the spawner lifecycle; they are not deleted as a side effect of stopping a server or disabling an identity.
- The Hub crypt key and confidential client secret are separate from the state and home volumes. Bootstrap runs before Compose startup, creates absent files atomically with restrictive permissions, and reconciles the corresponding Keycloak OIDC client using the existing Keycloak administrative provisioning mechanism. It must be safe to rerun without rotating an existing secret unexpectedly.
- Hub state and its matching crypt key are a backup pair. Operator-managed backups must include the Hub state, crypt key, and homes. No automated backup/restore is added.
- No user server mounts the Hub database volume, another user's home, the Docker socket, provider database files, or administrative secrets.

## Startup and failure behavior

1. Run the local credential/client bootstrap and build both pinned images before user activity.
2. Start the existing identity/provider services and JupyterHub on `core`; Compose health reporting supports operator checks, while OIDC login/admission remains fail-closed if Keycloak is unavailable.
3. On an admitted spawn, enforce the two-server limit, create the isolated server and stable home, apply resource limits, attach the required networks, and wait for readiness.
4. On partial failure, stop/remove transient server resources, preserve the home and Hub state, emit a safe failure category, and wait for deliberate retry.
5. Normal stop/recreate retains all named volumes. Only a separate explicit operator cleanup removes a user's home or Hub state.

## Compatibility and limits

- The official JupyterHub database guide confirms SQLite is the default and fits small single-Hub deployments; its file must live on local persistent storage, not network storage. [JupyterHub database guide](https://jupyterhub.readthedocs.io/en/6.1.0/explanation/database.html)
- Exact Python minor version, OAuthenticator and DockerSpawner package versions, upstream base digests, Spark dependencies, health-check timing, volume UID/GID ownership, and concrete host resource tuning are resolved and locked during Code Generation/Build and Test. Compatibility must be verified against JupyterHub 6.1.1 before those artifacts are pinned.
- Two servers at the default limits request up to 2 CPU and 4 GiB RAM collectively. The documented local machine must be able to provide that in addition to platform services; if not, tune limits while still verifying the approved two-server target.
- This design is local-only HTTP on loopback. It is not a production exposure, TLS, egress-control, HA, or security certification design.
