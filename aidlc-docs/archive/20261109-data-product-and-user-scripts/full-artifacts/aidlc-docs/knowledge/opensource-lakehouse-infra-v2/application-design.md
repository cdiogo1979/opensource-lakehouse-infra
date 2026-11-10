# Application Design — Keycloak, Polaris, RustFS, Jenkins, StarRocks, and Console/UI SSO

## Purpose

This project provides a local Docker Compose lakehouse platform-admin journey. It bootstraps an initial `default` lakehouse data product without migrating legacy Hive or FreeIPA state. The journey provisions:

- identity groups
- storage buckets
- Polaris catalogs and namespaces
- authorization grants
- RustFS console policies
- Spark smoke tables across production, dev, and UAT

## Components

- **Keycloak** provides the `lakehouse` OIDC realm, the four product role groups plus `role-platform-admin`, five bootstrap users, the `lakehouse-writer` workload client, the StarRocks clients (`srv-starrocks` service account and `starrocks` login), and browser-login clients for JupyterHub, Airflow, the RustFS console, and Jenkins. See `functional-design/lakehouse-product-access.md`.
- **Apache Polaris** provides Iceberg REST and management APIs, catalogs, namespaces, principal roles, grants, and scoped RustFS credential vending.
- **PostgreSQL** stores Keycloak and Polaris state in separate databases and named volumes.
- **RustFS** (1.0.4) provides the three S3-compatible environment buckets. Bootstrap creates missing resources and preserves existing objects. Its console accepts Keycloak OIDC sign-in, with root static keys kept as break-glass.
- **Host scripts** (`scripts/`): the entry points `lakehouse.sh` (start, status, stop, reset, StarRocks reconcile, Airflow commands) and `bootstrap-default-product.sh`, plus helpers grouped by purpose in `setup/`, `bootstrap/`, `operations/`, `clients/`, and `verify/`.
- **Apache Airflow** provides the production/UAT workload control plane and browser UI. It uses FAB authentication through Keycloak, with a local administrator recovery login.
- **Spark** runs on-demand Iceberg workloads using workload-specific OAuth identities and Polaris-vended S3 credentials.
- **JupyterHub** remains a separately supported interactive service with user-bound Spark authentication.
- **Jenkins** (2.580.1) runs the CI for the `opensource-lakehouse` workload repository. It uses Keycloak SSO and runs from `compose.jenkins.yml`. See `functional-design/jenkins-ci-access.md`.
- **StarRocks** (4.1.7, one FE and one BE) is the interactive SQL engine.
  - It runs from its own Compose module, `compose.starrocks.yml`, as part of `start`, unless `STARROCKS_ENABLED=false`.
  - It reads and writes the three Polaris catalogs as `srv-starrocks`, with vended RustFS credentials.
  - People log in with Keycloak tokens. See `functional-design/starrocks-sql-access.md`.
- **Deferred and retired**: FreeIPA, Hive Metastore, and MIT Kerberos are retired from the target default runtime, as are the FreeIPA-era RustFS identity scripts and the Kerberos, LDAP, and Hive-era StarRocks assets. On 2026-11-09 the following were also removed: the TPC-H generator and loader, the identity provisioner, the old bucket-init image, the one-time catalog path reset, the Ranger test secrets, the Jenkins home migration, the deferred-services inventory, and the root `Jenkinsfile`.

## Repository independence

This repository runs on its own. The only link to the `opensource-lakehouse` workload repository is Airflow cloning its Git Bundles over HTTPS into this repository's `.runtime/airflow-dag-bundles`. No sibling checkout is mounted or referenced, and there is no `LAKEHOUSE_PROJECT_ROOT` setting. The workload repository supplies DAGs, configuration, notebooks, and workload entry points. Its own knowledge documents were retired on 2026-10-31.

## Airflow and shared Spark runtime

The Airflow control plane and writer token broker run in the v2 Compose boundary. For each DAG run, Airflow:
1. resolves the selected Git Bundle revision
2. registers run-scoped broker state
3. creates an ephemeral Spark container with the bundle mounted read-only

The writer identity is the Keycloak user `srv-default-writer` (group `role-default-writer`). The broker gets its tokens through the password grant on the confidential `lakehouse-writer` client. The client secret and the user's password (`.runtime/credentials/srv-default-writer-password`, written from `infra/keycloak/bootstrap-users.json`) stay in the broker and Spark-bootstrap boundary. Polaris sees the principal `srv-default-writer`. Spark receives an initial access token and a run-scoped renewal capability, never the secret or password.

Per-run execution contract:
1. Airflow resolves a run against the pinned checkout of the production or UAT Bundle.
2. The broker gets a writer token, associates it with that DAG run, and issues a high-entropy, run-scoped renewal capability.
3. Airflow starts one ephemeral Spark container, mounts the Bundle read-only, and passes only the initial token, broker endpoint and CA, run handle, and capability.
4. The Iceberg `AuthManager` renews the token through the broker over authenticated TLS. Polaris enforces the writer role and vends scoped RustFS credentials.
5. On completion or failure, Airflow removes the container and revokes broker run state. Run state also expires on its own.

Broker registration or renewal failures fail the task; there is no fallback identity.

The shared runtime uses Spark 3.5.5, Java 17, and Iceberg 1.10.2. Its JVM `AuthManager` renews access tokens through identity-specific adapters: Airflow uses the run-scoped writer broker, and Jupyter Spark uses the authenticated user's Hub broker. These identities and capabilities are not interchangeable. Polaris remains the authorization and scoped RustFS credential vending point; no RustFS root credential is handed to Spark.

The Airflow contract preserves two Git Bundles: `lakehouse-main` tracking `main` and `lakehouse-uat` tracking `uat`. `infra/airflow/validate-bundle-config.py` checks this list. With `--host-paths`, which `scripts/lakehouse.sh` passes, it also checks that the host Bundle root is this repository's `.runtime/airflow-dag-bundles`. The copy inside the image checks only the Bundle configuration. The writer client has a one-hour access-token lifetime override; human JupyterHub token lifetimes remain unchanged.

## Airflow browser authentication

The Airflow API server uses FAB OIDC with the confidential `airflow` client in the Keycloak `lakehouse` realm.

- **Endpoints**: browser authorization uses the host-reachable Keycloak hostname; token and user-info requests use Docker networking.
- **Token validation**: the configured issuer is validated explicitly. The RS256 JWKS is fetched from the internal Keycloak service address, so Docker loopback resolution does not send the request back to Airflow.
- **Callbacks**: the exact local callback URLs are `http://localhost:8085/auth/oauth-authorized/keycloak` and `http://127.0.0.1:8085/auth/oauth-authorized/keycloak`.
- **Exposure and recovery**: the Airflow service stays loopback-bound. The local FAB password login is a separate recovery route restricted to `AIRFLOW_ADMIN_USERNAME`.

| Keycloak group | Airflow role (as approved by the Airflow SSO intent) |
|---|---|
| `role-default-owner` | `Admin` |
| `role-default-developer` | `Admin` |
| `role-default-analyst` | `User` |
| `role-default-writer` | `Viewer` |
| `role-platform-admin` | `Admin` |

Users without an approved group are denied OAuth login. The Airflow OIDC integration is browser-only and does not change API or service-account authentication.

> As of 2026-10-30, `infra/airflow/airflow_sso_roles.py` and `webserver_config.py` map `role-default-developer` to `User`. This change was made outside any AI-DLC intent; `tests/airflow/test_keycloak_sso_contract.py` still expects `Admin`. Reconcile this table, the code, and the tests in a dedicated change.

## RustFS console authentication

**Login flow**
- The RustFS console offers Keycloak sign-in through the confidential `rustfs` client in the `lakehouse` realm: Authorization Code with PKCE S256.
- The callback is derived from the browser host: `http://{localhost,127.0.0.1}:<console port>/rustfs/admin/v3/oidc/callback/default`. The console port is `RUSTFS_CONSOLE_HOST_PORT`, default 9001.
- Keycloak registers exactly those two callbacks, plus the post-logout URIs `.../rustfs/console/auth/login`. RustFS rejects static loopback redirect URIs, so the exact Keycloak list is the allowlist. Logins started on the S3 port fail at Keycloak.

**Reaching Keycloak**
- Keycloak advertises `keycloak.localhost:8080` for token, JWKS, and logout endpoints, and that name resolves to loopback inside containers.
- RustFS therefore reaches Keycloak over the internal network `lakehouse-local_rustfs-identity`, where Keycloak carries the alias `keycloak.localhost`. No other service joins that network.
- `RUSTFS_OUTBOUND_ALLOW_ORIGINS` allows exactly `http://keycloak.localhost:8080`.
- The `lakehouse-rustfs-groups` mapper puts `groups` in the ID token.

**Client secret**
- The secret is `.runtime/credentials/rustfs-oidc-client-secret`.
- `infra/rustfs/rustfs-entrypoint.sh` exports it into the RustFS process at start, because RustFS 1.0.4 has no file-based OIDC secret setting.
- It is absent from Compose files and `docker inspect`.

**Authorization and sessions**
- RustFS uses each `groups` value as a policy name. The four product-group policies are described in `functional-design/lakehouse-product-access.md`.
- Users with no matching policy are refused a session. Console sessions last one hour.
- Logout is RP-initiated through Keycloak.
- If Keycloak is unavailable, new OIDC logins fail, existing sessions run to expiry, and RustFS retries discovery.

**Root and Polaris**: root static keys remain the break-glass console login and the identity Polaris uses server-side for STS.

**Known upstream limitation**: RustFS 1.0.4 embeds console v0.1.37. Its bucket-list page (`/rustfs/console/browser/`) remounts in a loop for non-admin users, which includes every OIDC user ([rustfs/console#271](https://github.com/rustfs/console/issues/271); fixed in console v0.1.38). Users open a bucket directly at `/rustfs/console/browser?bucket=<name>`. Follow-up: adopt the first RustFS release that bundles console v0.1.38 or later, and re-check the console's metadata-action needs.

## Jenkins CI authentication

**Service**
- Jenkins runs as the service `jenkins` in `compose.jenkins.yml` on `127.0.0.1:${JENKINS_HOST_PORT:-8090}`, unless `JENKINS_ENABLED=false`.
- Its home is `lakehouse-local_jenkins-home`, which holds jobs and build history. They are not configuration as code. The 2026-10-31 reset deleted the home, and Jenkins has no workload job since. The pre-reset home is saved at `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz`. Restoring the `opensource-lakehouse-dp/opensource-lakehouse-ci` job, or defining it as code, is open.

**Plugins**
- The image pins exactly 104 plugins in `infra/jenkins/plugins.txt`: the legacy versions plus `oic-auth 4.731.v4932b_506e767` and `nimbus-jose-jwt-api`.
- The build fails on any mismatch, and `PLUGINS_FORCE_UPGRADE=true` makes the image authoritative over the home's plugins.

**Configuration as code**
- `infra/jenkins/casc/jenkins.yaml` holds the OIDC realm, the authorization matrix, the escape hatch, executors, mode, crumb issuer, and root URL. It is reapplied at every start.
- Endpoints follow the Airflow pattern: browser redirects use `keycloak.localhost:8080`; token, JWKS, and userinfo calls use `keycloak:8080`; the issuer is the canonical one. No network alias is needed.

**Keycloak client and secrets**
- The confidential `jenkins` client uses PKCE S256, exact `finishLogin` callbacks and `/` post-logout URIs for both loopback hosts, and a `groups` claim in the ID token (`lakehouse-jenkins-groups`).
- The client secret and the escape-hatch password are protected files read through `${trim:${readFile:...}}`.

**Builds**: pipelines run on the built-in node without the Docker socket. GitHub is scanned anonymously.

## Resource and data role model

| Environment | Catalog | Namespace | Bucket |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` |
| Dev | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` |

Each catalog's default base location is `<bucket>/<catalog>/`, and its database namespace contributes the next path segment. Iceberg tables therefore resolve beneath `<bucket>/<catalog>/<database>/<table>` exactly once. For example, the production smoke table is `s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test/`.

Role semantics, Polaris grants, and RustFS console policies are described in `functional-design/lakehouse-product-access.md`. Polaris enforces catalog operations. Polaris-vended credentials constrain object access for workloads, and the group-named RustFS policies constrain direct console access. These data-platform privileges are distinct from the Airflow UI role mapping above. StarRocks adds its own role layer on top of Polaris (see `functional-design/starrocks-sql-access.md`).

## Compose modules

One Compose project, `lakehouse-local`, split into module files. Resource names are the same as in the former single `docker-compose.yml`.

| File | Services | Selected by |
|---|---|---|
| `compose.core.yml` | keycloak-db, keycloak, polaris-db, polaris-schema-init, polaris, polaris-group-reconciler, rustfs; networks core, data-access, rustfs-identity | always |
| `compose.jupyter.yml` | jupyterhub; network jupyter-user; volume jupyterhub-state | `JUPYTER_ENABLED` (default true) |
| `compose.jenkins.yml` | jenkins; volume jenkins-home | `JENKINS_ENABLED` (default true) |
| `compose.starrocks.yml` | starrocks-fe, starrocks-be; network starrocks | `STARROCKS_ENABLED` (default true) |
| `compose.airflow.yml` | Airflow and its token broker; networks airflow-internal, airflow-spark | the `start-airflow`, `airflow-status`, and `stop-airflow` commands |

- **One file list**: `scripts/lakehouse.sh` reads the flags from the environment or `.env` (case-insensitive) and builds `COMPOSE` (core plus enabled modules) and `AIRFLOW_COMPOSE` (that plus Airflow) in one place. Every other script passes its files explicitly, and no command relies on a default Compose file.
- **Reproducible builds**: both entry scripts export `BUILDX_NO_DEFAULT_ATTESTATIONS=1`. With the containerd image store, BuildKit otherwise adds a timestamped attestation, so every cached build gets a new image ID and running containers are recreated on each start.
- **Orphans**: both entry scripts export `COMPOSE_IGNORE_ORPHANS=true`. A command that passes only some module files would otherwise label the other modules' containers orphans and suggest `--remove-orphans`, which deletes them.

## Startup and bootstrap

**Start.** `scripts/lakehouse.sh start`:
1. creates only missing protected runtime credentials (`scripts/setup/prepare-runtime.py`), and builds the shared Spark runtime image
2. if Jupyter is enabled: prepares the Hub broker certificates, checks the user subnet and credentials, and builds the Hub and single-user images
3. starts the core databases and RustFS, runs the Polaris schema initialization, then starts Keycloak and Polaris and waits for health
4. runs the Keycloak realm bootstrap. It creates the five groups, the clients, and any missing bootstrap users, gives `role-platform-admin` the `lakehouse` realm's `realm-admin` role, and never changes an existing user
5. starts each enabled module (JupyterHub, Jenkins, StarRocks with its TLS material and runtime bootstrap), and prints a notice for each disabled one

**Product bootstrap.** `scripts/bootstrap-default-product.sh` provisions provider resources and grants:
1. reruns `start` and the realm bootstrap, then `scripts/bootstrap/bootstrap-users.sh`, which resets the five bootstrap users to their default password and single group
2. creates the buckets, then the five RustFS group policies
3. creates catalogs and grants, and reconciles memberships
4. verifies writer authentication
5. runs Spark smoke-table create/write/read checks (`scripts/bootstrap/smoke-spark.sh`) on the shared runtime image `local/lakehouse-spark-runtime:3.5.5_1.10.2`, with explicit OAuth2 catalog authentication
6. runs the StarRocks bootstrap and user reconcile

Reruns preserve bucket objects and do not duplicate smoke rows. The realm and policy bootstraps refuse conflicting existing configuration. The only automatic change to existing configuration is narrow: a policy that exactly equals its previous approved definition is upgraded. `scripts/verify/rustfs-oidc.py` and `scripts/verify/jenkins-oidc.py` check the RustFS and Jenkins OIDC wiring read-only. `scripts/lakehouse.sh stop` stops the enabled modules and core, and preserves named volumes.

**Reset.** `scripts/lakehouse.sh reset` (`scripts/operations/reset-lakehouse.py`) deletes all local platform state:
- `lakehouse-local` containers, plus Jupyter user servers and Airflow Spark runs by runtime-role label
- the eight data volumes (including StarRocks) and the `lakehouse-jupyter-home-*` volumes
- the seven networks (including `lakehouse-local_starrocks`)
- `.runtime/credentials`, `.runtime/container-mounts`, and `.runtime/airflow-dag-bundles`

It lists what it will delete first. It needs the typed word `reset`, or `--yes`, and `--dry-run` only lists. A path guard refuses symlinks and other paths. Images, other projects, other `.runtime` entries such as `backups`, and anything outside the repository are kept. It is irreversible, and a rebuild is `bootstrap-default-product.sh`.

**Airflow.** `scripts/lakehouse.sh start-airflow`:
1. prepares Airflow secrets and certificates
2. additively bootstraps the Keycloak Airflow client and group mapper
3. builds the Airflow images
4. starts the Airflow control plane and dependencies
5. waits for service readiness
6. verifies production/UAT DAG registration without running DAGs

`scripts/lakehouse.sh stop-airflow` stops Airflow services and Spark runs while preserving provider data, Airflow metadata, and Bundle checkouts. Keycloak clients and mappers are persistent realm configuration and are not removed by stopping services.

**Secrets.** All published host endpoints bind to loopback. Protected credentials remain under `.runtime/credentials/` and must be backed up separately using encrypted storage. No secrets belong in source control, reports, or command output.

## StarRocks SQL engine

**Runtime**
- `compose.starrocks.yml` holds `starrocks-fe` and `starrocks-be`. The upstream `starrocks/fe-ubuntu` and `be-ubuntu` 4.1.7 images are pinned by multi-arch digest, with no custom build.
- **Ports**: SQL on 9030 and HTTP on 8030, bound to loopback.
- **Networks**: `core` (Keycloak, Polaris, the scheduled reconciler), `data-access` (RustFS), and an internal `lakehouse-local_starrocks`.
- **Volumes**: `starrocks-fe-meta` and `starrocks-be-storage`.
- **Memory**: `STARROCKS_FE_MEMORY_LIMIT` (default 2g; FE heap 1280 MB) and `STARROCKS_BE_MEMORY_LIMIT` (default 4g).
- **Config**: the tracked `infra/starrocks/conf/{fe,be}.conf` is mounted read-only. `infra/starrocks/fe-entrypoint.sh` adds the TLS keystore settings from protected files.

**Lifecycle**
- `scripts/lakehouse.sh` adds `compose.starrocks.yml` to the module file list when enabled (see [Compose modules](#compose-modules)).
- `start` prepares the TLS material, starts FE and BE, and runs `bootstrap-starrocks.py --runtime-only` (root password once, BE registration).
- The product bootstrap runs `bootstrap-starrocks.py` (catalogs, MV databases, roles) and `reconcile-starrocks-users.py`.
- `status` and `stop` include StarRocks, and `reconcile-starrocks [--dry-run]` runs the user sync on demand.
- The reset removes both StarRocks volumes and the network.

**Identities**
- **Catalog identity**: the confidential Keycloak client `srv-starrocks`, whose service account is in `role-default-writer`. Its Polaris principal, `service-account-srv-starrocks`, is created by the existing group reconciler.
- **Login tokens**: the public `starrocks` client issues them (password grant, audience mapper `aud=starrocks`).
- **Secrets**: the root password, the `srv-starrocks` secret, and the TLS keys live in `.runtime/credentials`. The keystore and its password are staged read-only in `.runtime/container-mounts`.

**Interfaces**
- **Iceberg REST**: `http://polaris:8181/api/catalog` with OAuth2 client credentials against `http://keycloak:8080/.../token`, `scope=openid`, and vended credentials.
- **JWKS**: from `keycloak:8080`, with the issuer `keycloak.localhost:8080`.
- **SQL and JDBC**: SQL over TLS from the local StarRocks CA. Clients use the MySQL 9.7 CLI (`scripts/clients/starrocks-login.sh`) and JDBC with a token file kept fresh by `scripts/clients/starrocks-token.sh`. DBeaver's StarRocks connection needs only `idTokenFile`; other JDBC clients use Connector/J 9.1+ with `idTokenFile`, `defaultAuthenticationPlugin`, and `sslMode`.

## Verification status and known limits

**Platform bootstrap.** U1 runtime readiness, U2 writer and negative-token checks, U3 RustFS bucket/STS checks, and the U4 end-to-end bootstrap and four-role positive/negative Spark access matrix passed on the local `linux/arm64` Docker engine. During a Keycloak outage, new token issuance and group reconciliation fail, while already-issued unexpired access tokens may continue until expiry.

**Airflow writer token.** For this intent:
- builds, static checks, and automated suites passed
- the designated main E2E run passed
- the user subsequently reported building the shared image and successful main and UAT DAG runs

Those later run IDs and revisions were not independently retrievable in that session and are recorded as user-confirmed.

**Airflow Keycloak SSO.** Verification:
- the client contract tests (8) and SSO authorization tests (6) passed after the runtime corrections
- the local Airflow API/UI returned HTTP 200
- both exact callbacks matched
- the running FAB client retrieved the RS256 JWKS
- production/UAT DAG registrations were verified without running a DAG

Successful interactive login and role assignment after the JWKS correction were not verified. The user accepted that verification limitation as a waiver; it is not a successful end-to-end authentication result.

**RustFS console OIDC** (2026-10-30), verification passed:
- the RustFS, Keycloak, and Polaris suites (84 tests, including Hypothesis policy properties)
- `verify-rustfs-oidc.py` (7/7)
- bootstrap idempotency
- the Polaris STS regression check
- a headless login and authorization run with temporary users (19/19: per-role access, refusal without a product group, RP-initiated logout)
- a user-confirmed interactive developer login through a bucket view

The upstream bucket-list loop above is a documented limitation.

**Jenkins onboarding and SSO** (2026-10-31). Passed:
- `verify-jenkins-oidc.py` 9/9, also after a restart
- idempotent bootstrap and migration reruns
- the plugin set equals `plugins.txt`
- a verified home copy
- a headless SSO and permission run with temporary users: owner Administer; developer read and build; analyst read-only; writer and no-group users denied; escape hatch; logout
- RustFS, Airflow, and JupyterHub unaffected
- an interactive login confirmed by the user

**Verification waiver (user-accepted; not a pass)**: no successful workload CI build. `main` #11 and `uat` #4 ran the full pipeline and failed on one `opensource-lakehouse` unit test after commit `00b6623` ("rename dag"), a workload regression outside scope.

**Environment reset and bootstrap users** (2026-10-31). Passed:
- a real reset and a rebuild from nothing
- all five users log in with the default password, with one group each and the right Polaris role
- rerunning `bootstrap-users.sh` restored the defaults after deliberate changes, and left other users alone
- RustFS OIDC and STS, the Polaris negative cases, and the role matrix
- an Airflow broker token as `srv-default-writer`
- platform-admin realm administration: 200 on `lakehouse`, 403 on `master`
- a user-confirmed JupyterHub login

The Jenkins verifier passed 8 of 9; the CI job is absent after the reset. Not run: the Keycloak outage test.

**StarRocks integration** (2026-11-09). Passed:
- runtime, with idempotent reruns
- catalogs and smoke reads through vended credentials
- grant enforcement
- token login over verified TLS for all five bootstrap users
- the full read and write matrix
- MV create, sync refresh, and scheduled refresh
- reconcile drift in both directions, opt-out, and the scheduled sync
- JDBC with Connector/J 9.3.0 (`REQUIRED` and `VERIFY_IDENTITY`)
- memory fit (FE about 0.8 of 2 GiB, BE about 0.45 of 4 GiB)

Not run: load or performance tests, and Power BI.

**Cleanup and modular Compose** (2026-11-09). Passed:
- the product bootstrap end to end, including the Spark smoke tables and the StarRocks steps
- a repeat `start` and a stop and start leave container IDs unchanged
- opt-outs: core-only `status` and `start`, with module containers untouched
- verifiers: RustFS OIDC and STS, Polaris checks, the full role matrix including its Spark part, Airflow DAGs, and a StarRocks login

The Jenkins verifier passed 8 of 9 (the workload CI job is missing).

**Not run anywhere**: performance and vulnerability scanning.

**Other known limits.**
- The prior bootstrap intent's closure was user-approved with a verification waiver. For that intent, the human PKCE callback browser flow and some reconciliation failure-path diagnostics were not tested.
- The reconciler and the realm bootstrap use a protected Keycloak bootstrap administrator. Replace it with a least-privilege identity before shared deployment.
- The approved Polaris `require-header=false` setting was specific to the single configured realm and earlier Iceberg 1.8.1 behavior. Reassess strict realm-header enforcement before adding realms.
- Concurrent workload, resilience, and live role-matrix checks remain unverified where noted in their respective intent records.
- StarRocks owners and platform admins cannot drop Iceberg tables through StarRocks: Polaris refuses `TABLE_DROP` for the writer-level `srv-starrocks`. Owners drop through Spark or Polaris.
- This local single-node setup is not a production, HA, or multi-host certification.

## Operational entry points

See `README.md` for the quick start, Compose modules, users and sign-in, per-service operation (Keycloak, Polaris, RustFS, JupyterHub, Airflow, StarRocks, Jenkins), reset, backup, secret rotation, the scripts layout, and known limitations. Detailed intent designs and test reports are preserved in the intent archives, most recently [Cleanup and Modular Compose](../../archive/20261109-cleanup-modular-compose/intent-summary.md), [StarRocks Integration](../../archive/20261109-starrocks-integration/intent-summary.md), [Environment Reset and Bootstrap Users](../../archive/20261031-environment-reset-bootstrap-users/intent-summary.md), [Jenkins Onboarding and Keycloak SSO](../../archive/20261031-jenkins-keycloak-sso/intent-summary.md), [RustFS Keycloak OIDC](../../archive/20261030-rustfs-keycloak-oidc/intent-summary.md), and [Airflow Keycloak SSO](../../archive/20261029-airflow-keycloak-sso/intent-summary.md).
