# Application Design — Keycloak, Polaris, RustFS, Jenkins, StarRocks, and Console/UI SSO

## Purpose

This project provides a local Docker Compose lakehouse platform. It hosts one or more **data products**, each described by one YAML file in `data-products/` (`default` is the first and cannot be removed). Legacy Hive or FreeIPA state is not migrated. For every product it provisions:

- identity groups and a writer user
- storage buckets
- namespaces in the shared Polaris catalogs
- namespace- and database-scoped authorization grants
- RustFS console policies
- app mappings (JupyterHub, Airflow, Jenkins)

The product bootstrap also creates Spark smoke tables for `default` across production, dev, and UAT.

## Components

- **Keycloak** provides the `lakehouse` OIDC realm, four groups per data product plus `role-platform-admin`, five bootstrap users, one writer user per product, the `lakehouse-writer` workload client, the `srv-starrocks` catalog service account, and browser-login clients for JupyterHub, Airflow, the RustFS console, and Jenkins. Users and passwords are stored in the LDAP directory through the writable `lakehouse-ldap` provider; groups stay in Keycloak. See `functional-design/lakehouse-product-access.md`.
- **LDAP directory** (`ldap`, OpenLDAP 2.6.8 from pinned Alpine 3.22 packages, `infra/ldap/`):
  - **Holds**: the users and passwords shared by Keycloak and StarRocks.
  - **Access**: LDAPS only (636) plus a local `ldapi` socket for the healthcheck, Argon2 password hashes, no host port, on the `core` network only.
  - **Tree**: `dc=lakehouse,dc=local`, with `ou=people` (users, `uid` = username) and `ou=services` (`cn=keycloak`, the only identity allowed to write `ou=people`).
  - **Seeding**: an empty volume is seeded once, and the Keycloak bind hash is refreshed from its protected file at every start.
- **Apache Polaris** provides Iceberg REST and management APIs, catalogs, namespaces, principal roles, grants, and scoped RustFS credential vending.
- **PostgreSQL** stores Keycloak and Polaris state in separate databases and named volumes.
- **RustFS** (1.0.4) provides S3-compatible storage: three environment buckets per data product. Bootstrap creates missing resources and preserves existing objects. Its console accepts Keycloak OIDC sign-in, with root static keys kept as break-glass.
- **Host scripts** (`scripts/`): the entry points `lakehouse.sh` (start, status, stop, reset, StarRocks reconcile, Airflow commands) and `bootstrap-default-product.sh`, plus helpers grouped by purpose in `setup/`, `bootstrap/`, `operations/`, `clients/`, and `verify/`. `operations/` holds the operator commands `create-data-product.sh`, `remove-data-product.sh`, and `create-user.sh` (see [Data products](#data-products)).
- **Data product model** (`infra/products/`): `data_products.py` loads and validates the product files and derives names. `template.yaml` is the `--init` template, `render_jenkins.py` renders the Jenkins configuration, product folders and jobs, and `product-cli.py` holds the operator helpers. Every component reads the files through this module.
- **Apache Airflow** provides the production/UAT workload control plane and browser UI. It uses FAB authentication through Keycloak, with a local administrator recovery login.
- **Spark** runs on-demand Iceberg workloads using workload-specific OAuth identities and Polaris-vended S3 credentials.
- **JupyterHub** remains a separately supported interactive service with user-bound Spark authentication.
- **Jenkins** (2.580.1) runs the CI for each data product: a folder per product, whose owner group is its admin, holding `<name>_ci` (prod and UAT branches) and `<name>_cd` (branches with an open pull request) when the product has a `repo`. It uses Keycloak SSO and runs from `compose.jenkins.yml`. See `functional-design/jenkins-ci-access.md`.
- **StarRocks** (4.1.7, one FE and one BE) is the interactive SQL engine.
  - It runs from its own Compose module, `compose.starrocks.yml`, as part of `start`, unless `STARROCKS_ENABLED=false`.
  - It reads and writes the three Polaris catalogs as `srv-starrocks`, with vended RustFS credentials.
  - People log in with Keycloak tokens. See `functional-design/starrocks-sql-access.md`.
- **Deferred and retired**: FreeIPA, Hive Metastore, and MIT Kerberos are retired from the target default runtime, as are the FreeIPA-era RustFS identity scripts and the Kerberos, LDAP, and Hive-era StarRocks assets. On 2026-11-09 the following were also removed: the TPC-H generator and loader, the identity provisioner, the old bucket-init image, the one-time catalog path reset, the Ranger test secrets, the Jenkins home migration, the deferred-services inventory, and the root `Jenkinsfile`.

## Repository independence

This repository runs on its own. The only link to workload repositories (today `opensource-lakehouse`, named in each product's `repo` block) is Airflow cloning their Git Bundles anonymously over HTTPS into this repository's `.runtime/airflow-dag-bundles`. No sibling checkout is mounted or referenced, and there is no `LAKEHOUSE_PROJECT_ROOT` setting. The workload repository supplies DAGs, configuration, notebooks, and workload entry points. Its own knowledge documents were retired on 2026-10-31.

## Airflow and shared Spark runtime

The Airflow control plane and writer token broker run in the v2 Compose boundary. For each DAG run, Airflow:
1. resolves the selected Git Bundle revision
2. registers run-scoped broker state
3. creates an ephemeral Spark container with the bundle mounted read-only

Each data product with a `repo` has its own writer identity, its `writer_user` (`srv-<name>-writer`, group `role-<name>-writer`; `srv-default-writer` for `default`). There is no writer field: the writer follows from the product name.

- **Selecting the writer**: a DAG ID starts with its bundle name (`<product>-main-...` or `<product>-uat-...`). The broker takes the product from that prefix, then asks the Airflow API, as the read-only FAB user `lakehouse-broker` (role Viewer, recreated by `airflow-init`; Viewer token cached until 60 s before expiry), which bundle holds the DAG. It issues a token only when `bundle_name` is `<product>-<env>`, and checks that the token's user and writer group are that product's. Refusals are 403 `unknown_product`, `unknown_dag`, or `bundle_mismatch`; 503 when Airflow cannot answer. Registrations keep their product, so renewals use the same writer.
- **Credentials**: the broker gets tokens through the password grant on the confidential `lakehouse-writer` client. `scripts/setup/stage-airflow-writers.py` stages `writers.json` (product → username, group, password file name) and the writers' passwords into `.runtime/container-mounts/airflow-writers/`, which only the broker mounts read-only. The client secret and passwords never reach Airflow DAG code or Spark; Spark receives an initial access token and a run-scoped renewal capability. Polaris sees the product's writer principal.

Per-run execution contract:
1. Airflow resolves a run against the pinned checkout of the product's production or UAT Bundle.
2. The broker checks the DAG's bundle, gets that product's writer token, associates it with that DAG run, and issues a high-entropy, run-scoped renewal capability.
3. Airflow starts one ephemeral Spark container, mounts the Bundle read-only, and passes only the initial token, broker endpoint and CA, run handle, and capability.
4. The Iceberg `AuthManager` renews the token through the broker over authenticated TLS. Polaris enforces the writer role and vends scoped RustFS credentials.
5. On completion or failure, Airflow removes the container and revokes broker run state. Run state also expires on its own.

Broker registration or renewal failures fail the task; there is no fallback identity.

The shared runtime uses Spark 3.5.5, Java 17, and Iceberg 1.10.2. Its JVM `AuthManager` renews access tokens through identity-specific adapters: Airflow uses the run-scoped writer broker, and Jupyter Spark uses the authenticated user's Hub broker. These identities and capabilities are not interchangeable. Polaris remains the authorization and scoped RustFS credential vending point; no RustFS root credential is handed to Spark.

**Bundles come from the product files.** Every product with a `repo` block (`url`: credential-free https; `prod_branch`; `uat_branch`) gets two GitDagBundles, `<name>-main` tracking its prod branch and `<name>-uat` tracking its UAT branch (`git_conn_id` `lakehouse_git`, refresh 300 s, sparse `dags`, `configs`, `notebooks`). `default` has `default-main` and `default-uat` from `opensource-lakehouse` (`main`, `uat`); the former `lakehouse-main`/`lakehouse-uat` names are retired. `scripts/setup/airflow-bundle-config.py` generates the list (`data_products.bundle_config`), and `infra/airflow/validate-bundle-config.py` checks its shape; with `--host-paths`, which `scripts/lakehouse.sh` passes, it also requires equality with the generated list and that the host Bundle root is this repository's `.runtime/airflow-dag-bundles`. The copy inside the image checks only the shape.

**Workload contract.** A workload repository's DAG factory must build IDs as `<bundle name>-<workload>`, and may read `configs/<product>/<env>.yml` before `configs/<env>.yml`. `opensource-lakehouse` follows it since `fedf0bc` (`e975471` plus a fix). Without it, both bundles build the same `dev-...` DAG ID, one bundle shows no DAG, and the broker refuses its runs.

**Airflow restarts.** Airflow 3.3 reads `dag_bundle_config_list` once per process (`DagBundlesManager`), from an environment variable, and the broker reads its writers at start. So a change to the bundles or writers recreates Airflow, interrupting running DAG runs (LocalExecutor). A fingerprint over the bundle list, the writer set, and password hashes (`stage-airflow-writers.py --fingerprint`) is recorded in `.runtime/state/airflow-bundles.json` after a successful `start-airflow`; the product commands recreate Airflow only when it differs and Airflow is running. Alternatives (broker hot reload with idle-only restart; one local platform bundle; other orchestrators) were discussed on 2026-11-09 and not adopted. The writer client has a one-hour access-token lifetime override; human JupyterHub token lifetimes remain unchanged.

## Airflow browser authentication

The Airflow API server uses FAB OIDC with the confidential `airflow` client in the Keycloak `lakehouse` realm.

- **Endpoints**: browser authorization uses the host-reachable Keycloak hostname; token and user-info requests use Docker networking.
- **Token validation**: the configured issuer is validated explicitly. The RS256 JWKS is fetched from the internal Keycloak service address, so Docker loopback resolution does not send the request back to Airflow.
- **Callbacks**: the exact local callback URLs are `http://localhost:8085/auth/oauth-authorized/keycloak` and `http://127.0.0.1:8085/auth/oauth-authorized/keycloak`.
- **Exposure and recovery**: the Airflow service stays loopback-bound. The local FAB password login is a separate recovery route restricted to `AIRFLOW_ADMIN_USERNAME`.

**Role mapping** (since 2026-11-09):
- At each sign-in, `LakehouseSecurityManager` maps the user's groups to Airflow roles from every product file's `apps.airflow`, with `role-platform-admin` always `Admin`. `AUTH_ROLES_MAPPING` is a fixed identity map of the three role names.
- The API server mounts the product model and `data-products/` read-only. Other Airflow services load the module without importing the model.
- Airflow has no per-product permissions, so these roles apply platform-wide.
- An invalid product file fails closed: only the platform administrator signs in.

| Group (default product file) | Airflow role |
|---|---|
| `role-default-owner` | `User` |
| `role-default-developer` | `User` |
| `role-default-analyst` | `User` |
| `role-default-writer` | `Viewer` |
| `role-platform-admin` | `Admin` |

Users without a mapped group are denied OAuth login. The Airflow OIDC integration is browser-only and does not change API or service-account authentication.

Only `role-platform-admin` is Airflow `Admin`. Owners and developers are `User` (decided 2026-11-09; supersedes the Airflow SSO intent's `Admin` for owners and developers). Roles sync at every sign-in (`AUTH_ROLES_SYNC_AT_LOGIN`).

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
- RustFS uses each `groups` value as a policy name. Each product's group policies and the aggregate `role-platform-admin` policy are described in `functional-design/lakehouse-product-access.md`.
- Users with no matching policy are refused a session. Console sessions last one hour.
- Logout is RP-initiated through Keycloak.
- If Keycloak is unavailable, new OIDC logins fail, existing sessions run to expiry, and RustFS retries discovery.

**Root and Polaris**: root static keys remain the break-glass console login and the identity Polaris uses server-side for STS.

**Known upstream limitation**: RustFS 1.0.4 embeds console v0.1.37. Its bucket-list page (`/rustfs/console/browser/`) remounts in a loop for non-admin users, which includes every OIDC user ([rustfs/console#271](https://github.com/rustfs/console/issues/271); fixed in console v0.1.38). Users open a bucket directly at `/rustfs/console/browser?bucket=<name>`. Follow-up: adopt the first RustFS release that bundles console v0.1.38 or later, and re-check the console's metadata-action needs.

## Jenkins CI authentication

**Service**
- Jenkins runs as the service `jenkins` in `compose.jenkins.yml` on `127.0.0.1:${JENKINS_HOST_PORT:-8090}`, unless `JENKINS_ENABLED=false`.
- Its home is `lakehouse-local_jenkins-home`, which holds the build history. Folders and jobs are configuration as code (see below) and are recreated at every start, also after a reset.

**Plugins**
- The image pins exactly 105 plugins in `infra/jenkins/plugins.txt`: the legacy versions plus `oic-auth 4.731.v4932b_506e767`, `nimbus-jose-jwt-api`, and `job-dsl 3732.v9a_c49a_61a_313`.
- The build compares `name:version` from every plugin manifest and fails on any mismatch, and `PLUGINS_FORCE_UPGRADE=true` makes the image authoritative over the home's plugins.

**Configuration as code**
- `infra/jenkins/casc/jenkins.yaml` is the template: the OIDC realm, the project-based matrix with its static entries (`role-platform-admin`, `jenkins-break-glass`), the escape hatch, executors, mode, crumb issuer, and root URL.
- `infra/products/render_jenkins.py` writes three files to `.runtime/container-mounts/`: `jenkins-casc.yaml` (the template plus `Overall/Read` per product group), `jenkins-jobs.groovy` (Job DSL: product folders with their permissions and jobs), and `jenkins-products.json` (the expected folders and jobs).
  - The init hook `infra/jenkins/init.groovy.d/reconcile-data-products.groovy` applies the Job DSL after Jenkins has loaded its jobs, then deletes the marked product folders and jobs that left the expected set. A Job DSL script in CasC would run before job loading and lose new folders.
  - `prepare-runtime.py` renders the files on `start`, and the operator scripts render them and restart Jenkins when one changed.
  - The files are rewritten in place, because a single-file bind mount keeps its inode.
- Endpoints follow the Airflow pattern: browser redirects use `keycloak.localhost:8080`; token, JWKS, and userinfo calls use `keycloak:8080`; the issuer is the canonical one. No network alias is needed.

**Keycloak client and secrets**
- The confidential `jenkins` client uses PKCE S256, exact `finishLogin` callbacks and `/` post-logout URIs for both loopback hosts, and a `groups` claim in the ID token (`lakehouse-jenkins-groups`).
- The client secret and the escape-hatch password are protected files read through `${trim:${readFile:...}}`.

**Builds**: pipelines run on the built-in node without the Docker socket. GitHub is scanned anonymously.

## Resource and data role model

Every data product has three environments in the **shared** Polaris catalogs, each with its own namespace, bucket, and StarRocks MV database. The `default` product:

| Environment | Catalog | Namespace | Bucket |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` |
| Dev | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` |

- **Paths**: each catalog's default base location is the default product's `<bucket>/<catalog>/`. Its allowed locations add `s3://<bucket>/<catalog>/` for every product.
- **Namespace locations**: a product's namespace has the location `s3://<bucket>/<catalog>/<namespace>/`, so tables resolve beneath `<bucket>/<catalog>/<namespace>/<table>`. For example, the production smoke table is `s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test/`.
- **Polaris flag**: a namespace outside the catalog's base bucket needs the server-wide Polaris feature `ALLOW_NAMESPACE_CUSTOM_LOCATION` (set in `infra/polaris/oidc.properties`). Polaris 1.8 ignores the per-catalog property and the `behavior-changes` form. Tables stay confined to the allowed locations.
- **OIDC filter**: it is the pattern `^role-[a-z][a-z0-9]{1,19}-(developer|analyst|owner|writer)$`, so new products need no Polaris restart.

Role semantics, Polaris grants, and RustFS console policies are described in `functional-design/lakehouse-product-access.md`. Polaris enforces catalog operations. Polaris-vended credentials constrain object access for workloads, and the group-named RustFS policies constrain direct console access. These data-platform privileges are distinct from the Airflow UI role mapping above. StarRocks adds its own role layer on top of Polaris (see `functional-design/starrocks-sql-access.md`).

## Data products

- **Configuration**: one YAML file per product in `data-products/` (`apiVersion: lakehouse.local/v1`). The file holds the environments, groups, access levels (none, read, write, manage), MV levels (none, read, author, manage), app mappings, and writer user.
- **Validation**: names, the group pattern `role-<token>-<role>`, the shared catalogs, collisions across files, and unknown keys. Names are locked once applied: `.runtime/state/data-products/<name>.json` records them.
- **Component interface**: every product-aware component script takes `--product FILE` (default: every file), `--dry-run`, and, where it holds data or members, `--inventory` and `--remove [--purge-data]`. Each script remains the only writer to its system.
- **Operator commands** (`scripts/operations/`):
  - `create-data-product.sh`: `--init <name>`; apply `<file>` with `[--dry-run] [--no-restart]`. Order: validate, Keycloak, RustFS, Polaris, Polaris sync, StarRocks, StarRocks sync, Jenkins render (folder, permissions, jobs), record state, Airflow.
  - `remove-data-product.sh <name> [--purge-data] [--yes] [--dry-run]`: refuses `default`, inventories, asks for the typed name, backs up to `.runtime/backups/<time>-remove-<name>/`, then removes in reverse order (Jenkins folder and entries, StarRocks, Polaris roles, Polaris namespaces and locations, RustFS, Keycloak). It syncs and deletes the file, then updates Airflow, so a failed run resumes.
  - `create-user.sh <username> …`: one enabled user, no groups.
  - **Admin sign-in**: all three sign in to the Keycloak `lakehouse` realm as a platform administrator (`--admin-user`, `--admin-password-file`, `LAKEHOUSE_ADMIN_PASSWORD`, or a hidden prompt; never an argument) and refuse non-members of `role-platform-admin`. Polaris, RustFS, and StarRocks use the protected bootstrap credentials.
- **Concurrency**: a lock directory, `.runtime/state/data-products/.lock`, allows one create or remove at a time.
- **Restarts**: Jenkins when its configuration, folders, or jobs change (the dry run prints the folders and jobs to create or delete), and Airflow when the bundles or writers change (a product with a `repo` created or removed, or its `repo` changed): `apply_airflow` in `scripts/operations/lib/data-products.sh` runs `start-airflow` when the fingerprint differs and Airflow is running (`--no-restart` prints the command; `--dry-run` lists the bundles). Sign-in mappings need no restart: JupyterHub, Airflow, and the scheduled sync read the mounted files.

## Compose modules

One Compose project, `lakehouse-local`, split into module files. Resource names are the same as in the former single `docker-compose.yml`.

| File | Services | Selected by |
|---|---|---|
| `compose.core.yml` | keycloak-db, keycloak, ldap, polaris-db, polaris-schema-init, polaris, polaris-group-reconciler, rustfs; networks core, data-access, rustfs-identity | always |
| `compose.jupyter.yml` | jupyterhub; network jupyter-user; volume jupyterhub-state | `JUPYTER_ENABLED` (default true) |
| `compose.jenkins.yml` | jenkins; volume jenkins-home | `JENKINS_ENABLED` (default true) |
| `compose.starrocks.yml` | starrocks-fe, starrocks-be; network starrocks | `STARROCKS_ENABLED` (default true) |
| `compose.airflow.yml` | Airflow and its token broker; networks airflow-internal, airflow-spark | the `start-airflow`, `airflow-status`, and `stop-airflow` commands |

- **One file list**: `scripts/lakehouse.sh` reads the flags from the environment or `.env` (case-insensitive) and builds `COMPOSE` (core plus enabled modules) and `AIRFLOW_COMPOSE` (that plus Airflow) in one place. Every other script passes its files explicitly, and no command relies on a default Compose file.
- **Reproducible builds**: both entry scripts export `BUILDX_NO_DEFAULT_ATTESTATIONS=1`. With the containerd image store, BuildKit otherwise adds a timestamped attestation, so every cached build gets a new image ID and running containers are recreated on each start.
- **Orphans**: both entry scripts export `COMPOSE_IGNORE_ORPHANS=true`. A command that passes only some module files would otherwise label the other modules' containers orphans and suggest `--remove-orphans`, which deletes them.

## Startup and bootstrap

**Start.** `scripts/lakehouse.sh start`:
1. creates only missing protected runtime credentials (`scripts/setup/prepare-runtime.py`), including the LDAP admin and bind passwords, the Hub maintenance token, the LDAP and StarRocks TLS material, and Keycloak's `truststore-paths`; builds the shared Spark runtime image
2. if Jupyter is enabled: prepares the Hub broker certificates, checks the user subnet and credentials, and builds the Hub and single-user images
3. starts the core databases, RustFS, and `ldap` (built from `infra/ldap/`), runs the Polaris schema initialization, then starts Keycloak (which waits for `ldap` and trusts its CA) and Polaris, and waits for health
4. runs the Keycloak realm bootstrap:
   - it first ensures and tests the `lakehouse-ldap` provider, so every user created afterwards lands in LDAP
   - it creates `role-platform-admin`, every product's groups (from `data-products/`), the clients, and any missing bootstrap users
   - it gives `role-platform-admin` the `lakehouse` realm's `realm-admin` role, and never changes an existing user
5. starts each enabled module (JupyterHub, Jenkins, StarRocks with its TLS material and runtime bootstrap), and prints a notice for each disabled one

**Product bootstrap.** `scripts/bootstrap-default-product.sh` provisions provider resources and grants for **every** product file (`default` first), then records the applied names:
1. reruns `start` and the realm bootstrap, then `scripts/bootstrap/bootstrap-users.sh`, which resets the five bootstrap users to their default password and single group
2. creates the buckets, then the RustFS group policies
3. creates catalogs and grants, and reconciles memberships
4. verifies writer authentication
5. runs Spark smoke-table create/write/read checks (`scripts/bootstrap/smoke-spark.sh`) on the shared runtime image `local/lakehouse-spark-runtime:3.5.5_1.10.2`, with explicit OAuth2 catalog authentication
6. runs the StarRocks bootstrap and user reconcile

Reruns preserve bucket objects and do not duplicate smoke rows. The realm and policy bootstraps refuse conflicting existing configuration. The only automatic change to existing configuration is narrow: a policy that exactly equals its previous approved definition is upgraded. `scripts/verify/rustfs-oidc.py` and `scripts/verify/jenkins-oidc.py` check the RustFS and Jenkins OIDC wiring read-only. `scripts/lakehouse.sh stop` stops the enabled modules and core, and preserves named volumes.

**Reset.** `scripts/lakehouse.sh reset` (`scripts/operations/reset-lakehouse.py`) deletes all local platform state:
- `lakehouse-local` containers, plus Jupyter user servers and Airflow Spark runs by runtime-role label
- the nine data volumes (including StarRocks and `ldap-data`) and the `lakehouse-jupyter-home-*` volumes
- the seven networks (including `lakehouse-local_starrocks`)
- `.runtime/credentials`, `.runtime/container-mounts`, `.runtime/airflow-dag-bundles`, and `.runtime/state` (the applied product names)

It lists what it will delete first. The product files in `data-products/` are kept, and the rebuild recreates every product with empty buckets. It needs the typed word `reset`, or `--yes`, and `--dry-run` only lists. A path guard refuses symlinks and other paths. Images, other projects, other `.runtime` entries such as `backups`, and anything outside the repository are kept. It is irreversible, and a rebuild is `bootstrap-default-product.sh`.

**Airflow.** `scripts/lakehouse.sh start-airflow`:
1. prepares Airflow secrets (including the broker's Viewer password) and certificates
2. stages the product writers and generates and validates the bundle list
3. additively bootstraps the Keycloak Airflow client and group mapper
4. builds the Airflow images and starts the control plane (`airflow-init` recreates the `lakehouse-broker` Viewer); recreates the broker when the fingerprint changed
5. waits for service readiness
6. waits for DAGs from every product bundle (`scripts/verify/airflow-dags.sh`), warning about DAG IDs without their bundle prefix, without running DAGs
7. records the fingerprint

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
  - **Forced TLS**: `fe.conf` sets `ssl_force_secure_transport = true`, so every MySQL-protocol connection must use TLS.
  - **LDAP**: LDAPS to `ldap:636`, verified with the LDAP CA mounted at `/run/certs/ldap-ca.crt`.
  - **Bind pattern**: `uid=${USER},ou=people,…` is a runtime setting. `fe.conf` would expand `${USER}` as an environment variable and the FE would refuse to start, so it is set by the runtime bootstrap and re-applied by every user sync.

**Lifecycle**
- `scripts/lakehouse.sh` adds `compose.starrocks.yml` to the module file list when enabled (see [Compose modules](#compose-modules)).
- `start` prepares the TLS material, starts FE and BE, and runs `bootstrap-starrocks.py --runtime-only` (root password once, BE registration, LDAP bind pattern).
- The product bootstrap runs `bootstrap-starrocks.py` (catalogs, MV databases, roles) and `reconcile-starrocks-users.py`.
- `status` and `stop` include StarRocks, and `reconcile-starrocks [--dry-run]` runs the user sync on demand.
- The reset removes both StarRocks volumes and the network.

**Identities**
- **Catalog identity**: the confidential Keycloak client `srv-starrocks`, whose service account is in every product's writer group. Its Polaris principal, `service-account-srv-starrocks`, is created by the existing group reconciler.
- **People and service users**: they log in with their own username and LDAP password (`authentication_ldap_simple`); the FE binds to LDAP as the user and holds no LDAP secret. The former token login, with the `starrocks` Keycloak client and `starrocks-token.sh`, was retired on 2026-11-09.
- **Secrets**: the root password, the `srv-starrocks` secret, and the TLS keys live in `.runtime/credentials`. The keystore and its password are staged read-only in `.runtime/container-mounts`.

**Interfaces**
- **Iceberg REST**: `http://polaris:8181/api/catalog` with OAuth2 client credentials against `http://keycloak:8080/.../token`, `scope=openid`, and vended credentials.
- **LDAP**: `ldaps://ldap:636`, binding as `uid=<user>,ou=people,dc=lakehouse,dc=local`.
- **SQL and JDBC**: username and password over TLS from the local StarRocks CA.
  - **CLI**: `scripts/clients/starrocks-login.sh` (MySQL 9.7 client, cleartext plugin, `VERIFY_IDENTITY`).
  - **JDBC, DBeaver, and BI tools**: username and password with `sslMode=REQUIRED` or `VERIFY_IDENTITY`. Connector/J 9.3.0 was verified, and a plain-text connection is refused.
- **Scheduled sync**: its MariaDB client connects with `--ssl --ssl-verify-server-cert` and the StarRocks CA.

## Verification status and known limits

**Platform bootstrap.** U1 runtime readiness, U2 writer and negative-token checks, U3 RustFS bucket/STS checks, and the U4 end-to-end bootstrap and four-role positive/negative Spark access matrix passed on the local `linux/arm64` Docker engine. During a Keycloak outage, new token issuance and group reconciliation fail, while already-issued unexpired access tokens may continue until expiry.

**Airflow writer token.** For this intent:
- builds, static checks, and automated suites passed
- the designated main E2E run passed
- the user subsequently reported building the shared image and successful main and UAT DAG runs

Those later run IDs and revisions were not independently retrievable in that session and are recorded as user-confirmed.

**Data product Airflow bundles (2026-11-09).** Suite 393 passed (1 known drift failure); broker tests in its image 11 passed (P4); workload repository 61 passed. Live: `default-main`/`default-uat` registered; Viewer only; `srv-default-writer` and `srv-bttest-writer` selected per product, renewals kept the writer, revoke worked; `unknown_product` and `unknown_dag` refused; a UAT DAG run succeeded end to end; a test product was created (Airflow recreated), re-applied (unchanged), and removed. `bundle_mismatch` is unit-tested only (no real DAG can produce it).

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

**Data product and user scripts** (2026-11-09). Passed:
- the `default` migration to namespace-scoped grants: the role matrix was identical before and after, and Polaris and StarRocks converged
- a new product `sales`, created, verified with cross-product isolation both ways, edited and reapplied with additions and revocations, then removed (refused with data, purged, resumed)
- a new user, with duplicate and non-admin refusals, and StarRocks access following the group
- app mappings checked in the running containers, and the rebuilt scheduled sync
- the sign-in verifiers

Not run: interactive browser sign-ins of a new product's users.

**StarRocks LDAP login** (2026-11-09). Passed:
- the LDAP image on its own (seed, verified LDAPS bind, plain LDAP refused, anonymous reads denied, restart)
- a start with the federation created and tested
- migration of the five existing users: Keycloak database backed up; entries written with known passwords (Argon2) and verified; users imported and restored; a Jupyter home copied and verified, the old volume and Hub user deleted; the token client removed; JWT StarRocks users switched in place; a rerun was empty
- Keycloak sign-ins
- StarRocks password logins for people and a service user, with exact roles; wrong-password and plain-text refusals
- a password change reaching StarRocks at once
- a new user and a product writer created in LDAP and logging in
- Connector/J with `REQUIRED` and `VERIFY_IDENTITY`
- writer token, role matrix, RustFS OIDC, and the scheduled sync over TLS
- self-heal of the bind pattern

Not run: interactive JupyterHub and Airflow sign-ins of migrated users (DBeaver and BI-tool logins were later user-confirmed, 2026-11-09); a destructive reset and fresh install; an Airflow DAG run.

**Data product Jenkins pipelines** (2026-11-10). Passed:
- the suite (422 passed, 2 skipped, Hypothesis P1 to P5) and the image's plugin version check
- `jenkins-oidc.py` 10/10, including the product folder check
- `default_ci` built `main` and `uat`; `default_cd` scanned unauthenticated
- the ACL for every group, with cross-product isolation both ways
- a test product created, its `repo` removed, removed, re-created from scratch, and re-applied unchanged (no restart)

Not run: a `_cd` build of a real pull request, a `reset`, interactive per-role Jenkins logins.

**Not run anywhere**: performance and vulnerability scanning.

**Other known limits.**
- The prior bootstrap intent's closure was user-approved with a verification waiver. For that intent, the human PKCE callback browser flow and some reconciliation failure-path diagnostics were not tested.
- The reconciler and the realm bootstrap use a protected Keycloak bootstrap administrator. Replace it with a least-privilege identity before shared deployment.
- The approved Polaris `require-header=false` setting was specific to the single configured realm and earlier Iceberg 1.8.1 behavior. Reassess strict realm-header enforcement before adding realms.
- Concurrent workload, resilience, and live role-matrix checks remain unverified where noted in their respective intent records.
- StarRocks owners and platform admins cannot drop Iceberg tables through StarRocks: Polaris refuses `TABLE_DROP` for the writer-level `srv-starrocks`. Owners drop through Spark or Polaris.
- Every product's namespace **names** are visible to anyone with access to a shared catalog (`NAMESPACE_LIST` is catalog-level); contents are not.
- A new product becomes readable through StarRocks within about five minutes, when the shared catalogs renew their `srv-starrocks` token with the new writer group.
- Airflow rights from any product file apply platform-wide. Jenkins rights apply to the product's folder only.
- Jenkins has no webhooks: it scans every 5 minutes (`_ci`) and 30 minutes (`_cd`), and pull request discovery is unauthenticated (60 GitHub API requests per hour) and github.com only.
- While `ldap` is down, Keycloak sign-ins of federated users and StarRocks password logins fail; client service accounts, issued tokens, and open sessions keep working. LDAP is a single local node.
- After an FE restart outside `lakehouse.sh start`, StarRocks password logins fail until the next user sync re-applies the bind pattern (at most five minutes).
- `lakehouse.sh start` replaces staged files in `.runtime/container-mounts/` atomically; running containers with single-file mounts see the new content only after a restart.
- This local single-node setup is not a production, HA, or multi-host certification.

## Operational entry points

See `README.md` for the quick start, Compose modules, users and sign-in, per-service operation (Keycloak, Polaris, RustFS, JupyterHub, Airflow, StarRocks, Jenkins), reset, backup, secret rotation, the scripts layout, and known limitations. Detailed intent designs and test reports are preserved in the intent archives, most recently [Data Product Jenkins Pipelines](../../archive/20261110-data-product-jenkins-pipelines/intent-summary.md), [Data Product Airflow Bundles](../../archive/20261109-data-product-airflow-bundles/intent-summary.md), [StarRocks LDAP Login](../../archive/20261109-starrocks-ldap-login/intent-summary.md), [Data Product and User Scripts](../../archive/20261109-data-product-and-user-scripts/intent-summary.md), [Cleanup and Modular Compose](../../archive/20261109-cleanup-modular-compose/intent-summary.md), [StarRocks Integration](../../archive/20261109-starrocks-integration/intent-summary.md), [Environment Reset and Bootstrap Users](../../archive/20261031-environment-reset-bootstrap-users/intent-summary.md), [Jenkins Onboarding and Keycloak SSO](../../archive/20261031-jenkins-keycloak-sso/intent-summary.md), [RustFS Keycloak OIDC](../../archive/20261030-rustfs-keycloak-oidc/intent-summary.md), and [Airflow Keycloak SSO](../../archive/20261029-airflow-keycloak-sso/intent-summary.md).
