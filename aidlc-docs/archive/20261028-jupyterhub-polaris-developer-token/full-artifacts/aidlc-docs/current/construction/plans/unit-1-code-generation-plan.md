# Unit 1 Code Generation Plan — JupyterHub Foundation and OIDC Admission

## Purpose

Implement the approved Unit 1 outcome: a developer or analyst authenticates to the `lakehouse` Keycloak realm through OIDC, passes group admission, and starts one isolated Jupyter/Spark container with a persistent per-user home. The Hub stores OAuth auth state encrypted and alone controls Docker. Units 2 and 3 own the token broker, Spark JWT handoff, Polaris authorization, and RustFS credential vending; this plan must not implement those later-unit behaviors.

This is the single source of truth for Unit 1 Code Generation. The plan covers application/configuration files and focused test source. Test execution belongs to Build and Test.

## Unit context and contracts

- **Stories:** US-01 (Keycloak login), US-02 (approved-group admission and isolated persistent server), US-06 (operator-managed identity/configuration and safe lifecycle).
- **Requirements:** FR-1, FR-2, FR-7; Unit 1 security, persistence, 2-user capacity, callback ≤5 seconds and server-ready ≤120 seconds NFRs.
- **Upstream dependencies:** Existing Keycloak realm `lakehouse`, existing Keycloak/PostgreSQL and Polaris/RustFS Compose services, protected `.runtime/credentials` conventions, local Docker Compose.
- **Downstream dependencies:** Unit 2 will add the Hub token broker and Spark identity handoff; Unit 3 will validate Polaris role/audience claims and scoped RustFS access. Keep their interfaces available without implementing them here.
- **Trust boundaries:** Hub alone receives the Docker socket, OIDC confidential-client secret, and auth-state crypt key. User servers join `jupyter-user` and `data-access`, not `core`; they receive no administrative credentials or other users' homes.
- **Persistent state:** SQLite Hub state and crypt key remain separate from per-user named home volumes. Routine stop/recreate preserves all three categories of state.
- **Scope exclusions:** No FreeIPA dependency for this JupyterHub journey; no token broker, token injection, Spark-to-Polaris authentication, catalog grant changes, or RustFS root-key mount; no TLS/public exposure, new database, queue, or data migration.

## Code targets

Modify existing implementation files in place and create only the listed new test/helper files:

- `infra/jupyter/hub/Dockerfile`
- `infra/jupyter/hub/requirements.txt` and a new exact dependency lock/constraints file under `infra/jupyter/hub/`
- `infra/jupyter/hub/jupyterhub_config.py`
- Retire the active legacy auth inputs `infra/jupyter/hub/lakehouse_ldap.py` and `infra/jupyter/hub/user-identities.json` from the Hub image/configuration; do not delete unrelated FreeIPA services or archives.
- `infra/jupyter/singleuser/Dockerfile`
- `infra/jupyter/singleuser/requirements.txt`
- `infra/jupyter/singleuser/spark-defaults.conf`
- `infra/jupyter/singleuser/start-session.sh`
- `infra/keycloak/realm-contract.json`
- `infra/keycloak/bootstrap-realm.py`
- `docker-compose.yml`
- `docker-compose.deferred.yml`
- `.env.example`
- `scripts/prepare-lakehouse-runtime.py`
- Replace old Jupyter credential checks in `scripts/validate-jupyterhub-credentials.py`
- `scripts/lakehouse.sh`
- `README.md`
- New focused tests under `tests/jupyterhub/` and `tests/keycloak/` for configuration, client reconciliation, eligibility decisions, spawner settings, and credential bootstrap behavior.

The user/server images shall use a matching JupyterHub 6.1.1 release. Resolve and pin compatible Python minor, OAuthenticator, DockerSpawner, Docker SDK and transitive dependencies, plus immutable base-image digests during implementation. Record the resolved choices in the Hub lock file and Dockerfiles. Do not retain LDAP authenticator/ldap3 packages, Kerberos/keytab setup, Hive metastore settings, or user-container RustFS root credentials in the active Jupyter path.

## Ordered generation steps

### Step 1 — Confirm compatibility pins and existing interfaces

- [x] Validate official JupyterHub 6.1.1, OAuthenticator 17.4.0, DockerSpawner 14.0.0, Docker SDK 7.1.0, and the single-user image compatibility, including group claim/auth-state APIs and the DockerSpawner lifecycle path.
- [x] Record exact compatible direct dependencies and immutable image digests. Package indexes are not resolvable in this code-generation environment, so the complete transitive lock is a hard prerequisite for Build and Test; no reproducible-build claim is made before that gate passes.
- [x] Confirm DockerSpawner's single-network setting and Hub-side lifecycle attachment of `data-access` before Hub readiness checks. Network attachment is awaited after container start and before returning from `start()`.
- [x] Record direct package pins, image digests, and lifecycle implementation in `infra/jupyter/hub/requirements.txt`, `requirements-lock.txt`, and both image definitions.

### Step 2 — Define the Keycloak JupyterHub client and claims

- [x] Extend `infra/keycloak/realm-contract.json` with a dedicated confidential `jupyterhub` OIDC client, Authorization Code + PKCE S256, the exact default callback `http://jupyterhub.localhost:8000/hub/oauth_callback`, canonical issuer, and the developer/analyst group claim contract.
- [x] Preserve the existing Polaris client role mapper, audience configuration, group roles, and other clients; add only the same Polaris role claim mapper to the JupyterHub client for the downstream user's token flow.
- [x] Extend `infra/keycloak/bootstrap-realm.py` to idempotently create/reconcile the client and group mapper using a protected persistent secret; refuse unrelated client conflicts and never print secret values. Exact local callback port changes are reconciled only on the approved JupyterHub host/path.
- [x] Configure OIDC token/userinfo endpoints for the fixed `lakehouse` realm and obtain only identity, Polaris role, and group claims required by admission/downstream authorization; no role grants were broadened.

### Step 3 — Replace LDAP Hub authentication with OIDC admission

- [x] Rework `infra/jupyter/hub/jupyterhub_config.py` to use OAuthenticator Generic, a confidential PKCE client, browser authorization URL, internal Keycloak token/userinfo back-channel URLs, and the fixed canonical Keycloak realm endpoints.
- [x] Enable encrypted auth-state storage using the protected crypt key; persist state only in Hub-owned SQLite and do not log token values.
- [x] Admit only users in developer or analyst groups; missing/malformed group claims and failed userinfo refresh fail closed. Owner/writer-only membership does not grant Hub access.
- [x] Re-check current eligibility before every spawn. Existing running servers are not monitored for instantaneous group revocation; operators must stop them when group removal is processed, as defined by the approved functional-design fallback.
- [x] Remove active FreeIPA LDAP, keytab, static identity registry, Hive, and RustFS credential references from the active Jupyter path. Unit 2 token forwarding and broker routes are not implemented.

### Step 4 — Build and configure the Hub image

- [x] Update `infra/jupyter/hub/Dockerfile` to the pinned JupyterHub 6.1.1-compatible base and install the pinned direct Hub/OIDC/DockerSpawner dependencies.
- [x] Copy the OIDC Hub configuration and lock inputs; remove legacy LDAP and static identity files from the active Hub source/image.
- [x] Keep runtime secrets out of image layers, build args, and logs; the Hub runs as the image's root service user because it alone needs Docker Engine access.

### Step 5 — Implement per-user server, volume, resource, and network lifecycle

- [x] Configure DockerSpawner for the matching local single-user image, one server per stable OIDC subject, a collision-resistant per-subject named home, and host-tunable 1 CPU/2 GiB defaults.
- [x] Enforce a two-user active-server limit and use JupyterHub's one-server-per-user start lifecycle.
- [x] Attach each server to `jupyter-user`, then attach `data-access` before readiness polling; spawned servers never join `core`.
- [x] On network attachment failure, stop/remove the partial container, preserve Hub state and the separately named home, and require retry.
- [x] Mount Hub state and Hub credentials only in Hub. User servers receive no Hub secret, Docker socket, provider database credential, or another user's home.

### Step 6 — Build a matching Spark-enabled single-user image

- [x] Update the single-user Dockerfile to use the pinned matching JupyterHub 6.1.1 base, retain pinned Spark 3.5.5/Iceberg 1.8.1 runtime components, and install only direct notebook requirements.
- [x] Replace HiveCatalog, metastore and Kerberos settings with non-secret Iceberg REST catalog client defaults; do not inject a user JWT in Unit 1.
- [x] Simplify `start-session.sh` to launch `jupyterhub-singleuser` without keytab staging, `kinit`, Hive, or RustFS root keys.
- [x] Keep confidential client secrets, refresh tokens, Docker socket, and RustFS bootstrap/root keys out of the single-user image and environment.

### Step 7 — Bootstrap protected credentials and verify Hub prerequisites

- [x] Extend runtime preparation to create missing Hub credentials atomically at restrictive permissions, preserve existing values, and stage read-only Hub-only mounts; Keycloak client reconciliation occurs after providers start and before Hub start.
- [x] Validate only Hub secret ownership, regular-file type, format, and restrictive mode; remove legacy user-registry/keytab/RustFS requirements and never display secret values.
- [x] Fail with redacted actionable errors for absent, unsafe, or mismatched credentials/client settings.

### Step 8 — Integrate the approved Compose topology and lifecycle commands

- [x] Add JupyterHub Compose service with loopback-only publication, `/hub/health`, and tunable server limits.
- [x] Add the approved three-network topology; Keycloak/PostgreSQL remain on `core`; Hub uses `core`+`jupyter-user`; Polaris/RustFS use `core`+`data-access`; user servers use only the two approved user/data networks.
- [x] Add persistent Hub state; create per-user homes as named volumes; mount Docker socket and Hub-only secrets only in Hub.
- [x] Add JupyterHub port and resource defaults in `.env.example`.
- [x] Update `scripts/lakehouse.sh` to prepare credentials, build both images before spawn, reconcile Keycloak before Hub start, report health, and remove only labelled user-server containers on stop without deleting volumes.
- [x] Mark JupyterHub implemented in deferred-service inventory; leave other deferred services unchanged.

### Step 9 — Add focused Unit 1 test coverage

- [x] Add JupyterHub tests for OIDC/auth-state configuration, approved-group admission, resource limits, stable home naming, spawn revalidation contract, dual-network attachment, partial-spawn cleanup, and home retention.
- [x] Add Keycloak tests for confidential client/callback/PKCE/group claims, idempotent mapper reconciliation, conflict refusal, and protected-secret mismatch.
- [x] Add credential staging tests for restrictive permissions, atomic creation, preservation on rerun, and value-free helper output.
- [x] Keep all tests source-only; no test was executed in Code Generation. Execution remains in Build and Test.

### Step 10 — Update operator documentation and story traceability

- [x] Update README with the local URL, startup/health/build sequence, approved groups, resource tunables, persistent homes, cleanup boundary, credential rotation, and local-only HTTP limitation.
- [x] Document the three-network topology and safe diagnostics without revealing secret values.
- [x] Cover US-01, US-02, US-06; explicitly hand token broker, JWT handoff, Polaris authorization, and RustFS vending to later units.

## Review and approval gate

Review this complete plan before any application/configuration code is changed. Approval authorizes only the listed Unit 1 generation steps. It does not authorize implementing Units 2–4, deleting provider data, exposing services outside loopback, or removing unrelated FreeIPA components.
