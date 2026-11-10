# Open Source Lakehouse Infrastructure

A local, single-machine lakehouse platform on Docker Compose:
- **Keycloak** for identity
- **Apache Polaris** as the Iceberg catalog
- **RustFS** for S3-compatible storage
- **JupyterHub**, **Airflow** and Spark, **StarRocks**, and **Jenkins** on top

Access everywhere follows the same Keycloak groups. Everything binds to `127.0.0.1` and is meant for local development only.

## Contents

1. [Components](#components)
2. [Quick start](#quick-start)
3. [Compose modules](#compose-modules)
4. [Users and sign-in](#users-and-sign-in)
5. [Data layout](#data-layout)
6. [Services](#services)
   - [Keycloak](#keycloak)
   - [Polaris](#polaris)
   - [RustFS](#rustfs)
   - [JupyterHub](#jupyterhub)
   - [Airflow](#airflow)
   - [StarRocks](#starrocks)
   - [Jenkins](#jenkins)
7. [Operations](#operations)
   - [Status and stop](#status-and-stop)
   - [Reset the platform](#reset-the-platform)
   - [Backup](#backup)
   - [Secrets and rotation](#secrets-and-rotation)
   - [Running bootstrap steps individually](#running-bootstrap-steps-individually)
8. [Scripts](#scripts)
9. [Known limitations](#known-limitations)

## Components

| Component | What it does | URL | Compose module |
|---|---|---|---|
| Keycloak 26.8 | Users, groups, single sign-on (realm `lakehouse`) | <http://127.0.0.1:8080> | core |
| Apache Polaris 1.8 | Iceberg REST catalog; enforces data permissions and issues short-lived storage credentials | <http://127.0.0.1:8181> | core |
| RustFS 1.0.4 | S3-compatible object storage, with a web console | S3 <http://127.0.0.1:9000>, console <http://127.0.0.1:9001/rustfs/console/> | core |
| JupyterHub 6.1 | Notebooks with Spark, signed in as yourself | <http://jupyterhub.localhost:8000> | jupyter |
| Airflow 3.3 | Scheduled Spark workloads from Git DAG bundles | <http://127.0.0.1:8085> | airflow (optional) |
| StarRocks 4.1.7 | Interactive SQL over the Iceberg tables | `127.0.0.1:9030` (MySQL protocol) | starrocks |
| Jenkins 2.580 | CI for the `opensource-lakehouse` workload repository | <http://127.0.0.1:8090> | jenkins |

## Quick start

Requirements: Docker with Compose V2, Python 3, and OpenSSL. StarRocks needs about 6 GB of memory; turn it off if your machine is small (see [Compose modules](#compose-modules)).

```sh
cp .env.example .env                    # first time only
./scripts/lakehouse.sh start            # 1. start core and the enabled modules
./scripts/bootstrap-default-product.sh  # 2. create realm, users, buckets, catalogs, grants, and StarRocks setup
./scripts/lakehouse.sh start-airflow    # optional: Airflow
```

- **Step 1** creates missing credentials under `.runtime/credentials/` and starts the containers. It never changes realm, users, buckets, or catalogs.
- **Step 2** reruns step 1, then creates the default data product:
  - the Keycloak realm, groups, clients, and [bootstrap users](#users-and-sign-in)
  - buckets and storage policies
  - Polaris catalogs and grants
  - Spark smoke tables
  - StarRocks catalogs, roles, and users

Both steps are safe to rerun, and existing data is preserved. Then sign in to any product as one of the [bootstrap users](#users-and-sign-in) with the password `ChangeM3!`.

## Compose modules

The stack is one Compose project, `lakehouse-local`, split into module files. `scripts/lakehouse.sh` combines them.

| File | Module | Services | Runs |
|---|---|---|---|
| `compose.core.yml` | Core | Keycloak and its database, Polaris and its database, schema init, the scheduled group reconciler, RustFS | always |
| `compose.jupyter.yml` | Jupyter | JupyterHub and per-user Spark servers | unless `JUPYTER_ENABLED=false` |
| `compose.jenkins.yml` | Jenkins | Jenkins | unless `JENKINS_ENABLED=false` |
| `compose.starrocks.yml` | StarRocks | StarRocks FE and BE | unless `STARROCKS_ENABLED=false` |
| `compose.airflow.yml` | Airflow | Airflow and its writer token broker | through `start-airflow`, `airflow-status`, and `stop-airflow` |

- **Opt-outs**: set the flags in `.env`. A disabled module is not started, shown in `status`, or stopped, and its volumes are kept.
- **Core dependency**: every module needs core. When you run Compose yourself, always pass `compose.core.yml` first:

  ```sh
  docker compose -f compose.core.yml -f compose.jenkins.yml logs -f jenkins
  docker compose -f compose.core.yml -f compose.starrocks.yml ps
  ```

- **Orphan warnings and rebuilds**: a manual command that leaves out some modules makes Compose call the other modules' containers "orphans". **Never** add `--remove-orphans`, because it deletes them. Set `COMPOSE_IGNORE_ORPHANS=true` to hide the warning. If you rebuild images by hand, set `BUILDX_NO_DEFAULT_ATTESTATIONS=1`, as the scripts do, so unchanged images keep their ID and containers are not recreated.
- **Other settings**: ports, memory limits, and the startup timeout (`STARTUP_TIMEOUT_SECONDS`, default 600) are in `.env.example`.

## Users and sign-in

Step 2 creates five users in the `lakehouse` realm, defined in `infra/keycloak/bootstrap-users.json`. Each has the permanent password `ChangeM3!`, a local-development default documented here on purpose, and belongs to one group.

| User | Group | Purpose |
|---|---|---|
| `joe-developer` | `role-default-developer` | Develops in dev; reads UAT and production |
| `peter-analyst` | `role-default-analyst` | Reads production |
| `maria-owner` | `role-default-owner` | Owns the data product |
| `srv-default-writer` | `role-default-writer` | Service user for Airflow and Spark writes |
| `platform-admin` | `role-platform-admin` | Administers the platform |

**What each group can do:**

| Group | Data (Polaris, StarRocks, RustFS) | JupyterHub | Airflow | Jenkins | Keycloak |
|---|---|---|---|---|---|
| `role-default-owner` | manage all environments | — | Admin | Administer | — |
| `role-default-developer` | read prod and UAT; read and write dev | user | User | read and build | — |
| `role-default-analyst` | read prod | user | User | read only | — |
| `role-default-writer` | read and write all environments | — | Viewer | — | — |
| `role-platform-admin` | as owner, plus StarRocks system admin | Hub admin | Admin | Administer | admin of the `lakehouse` realm |

**Where to sign in:**

| To do this | Go to | As |
|---|---|---|
| Use a product | the product URL in [Components](#components) | a user whose group the product admits |
| Check your own account | <http://keycloak.localhost:8080/realms/lakehouse/account/> | any bootstrap user |
| Administer the `lakehouse` realm (users, groups, clients) | <http://keycloak.localhost:8080/admin/lakehouse/console/> | `platform-admin` |
| Administer Keycloak itself (the `master` realm, server settings) | <http://127.0.0.1:8080/admin/> | `admin`, with the password in `.runtime/credentials/keycloak-admin-password` |

- **No `master` access**: the bootstrap users exist only in `lakehouse`, so they cannot sign in to `master`. This is intended.
- **Restoring defaults**: later runs of step 2 never change existing users, so password and group changes survive. To put the five users back to their defaults, run:

  ```sh
  ./scripts/bootstrap/bootstrap-users.sh
  python3 infra/polaris/reconcile-keycloak-groups.py
  ```

  It changes only those five users.
- **Writer password**: Airflow and Spark read `srv-default-writer`'s password from `.runtime/credentials/srv-default-writer-password`. If you change it in Keycloak, run `bootstrap-users.sh` to restore it.
- **Group changes**: these reach Polaris and StarRocks through a reconciler that runs every five minutes, or immediately with `python3 infra/polaris/reconcile-keycloak-groups.py` and `./scripts/lakehouse.sh reconcile-starrocks`.

## Data layout

The `default` data product has three environments:

| Environment | Polaris catalog | Namespace | Bucket | StarRocks MV database |
|---|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` | `default_lh` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` | `default_lhuat` |
| Dev | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` | `default_lhdev` |

- **Paths**: tables live at `<bucket>/<catalog>/<namespace>/<table>`, for example `s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test/`.
- **Smoke tables**: each environment has a one-row `bootstrap_smoke_test` table, created by the product bootstrap.
- **Credentials**: no workload ever receives RustFS root keys. Polaris issues short-lived, table-scoped credentials (one hour, cached for 10 minutes).

## Services

### Keycloak

- **Realm**: the realm `lakehouse` holds the product groups, the bootstrap users, and one client per product. The contract is `infra/keycloak/realm-contract.json`, applied idempotently by `infra/keycloak/bootstrap-realm.py`, which refuses conflicting changes.
- **Hostnames**: browsers use `keycloak.localhost:8080`, the canonical issuer. Containers call `keycloak:8080`, because `.localhost` means loopback inside a container.
- **Writer identity**: workload writes use `srv-default-writer` through the confidential `lakehouse-writer` client (password grant, one-hour tokens).
- **Optional CLI client**: the human CLI client `lakehouse-cli` has no callback until an application needs one: `python3 infra/keycloak/bootstrap-realm.py --redirect-uri 'http://localhost:PORT/EXACT/CALLBACK'`.

### Polaris

- **Catalogs**: three catalogs, one per environment. Polaris accepts Keycloak tokens and maps the token's Polaris client roles to principal roles with the same names as the groups.
- **Grants**:

  | Level | Polaris privileges |
  |---|---|
  | read | catalog, namespace, and table metadata and table data |
  | write | read, plus create namespaces and tables and write data; no drop |
  | manage | `CATALOG_MANAGE_CONTENT` and `CATALOG_MANAGE_ACCESS` (owners) |

- **Principals**: Polaris needs a principal for every Keycloak user. The scheduled reconciler (`polaris-group-reconciler`, every `POLARIS_GROUP_RECONCILE_INTERVAL_SECONDS`, default 300) creates them and keeps their roles in sync with Keycloak groups.
- **Management endpoint**: it stays inside the container (port 8182 is not published). Check readiness with `docker compose -f compose.core.yml exec polaris curl --fail --silent http://127.0.0.1:8182/q/health/ready`.

### RustFS

- **Buckets**: three buckets, one per environment, created only if missing. Existing objects are kept.
- **Console sign-in**: the console at <http://127.0.0.1:9001/rustfs/console/> offers **Keycloak** sign-in. Each Keycloak group maps to a RustFS policy with the same name:

  | Group | `bucket-default` | `bucket-default-uat` | `bucket-default-dev` |
  |---|---|---|---|
  | `role-default-owner`, `role-platform-admin` | all actions | all actions | all actions |
  | `role-default-developer` | read | read | read and write |
  | `role-default-analyst` | read | — | — |
  | `role-default-writer` | read and write | read and write | read and write |

- **Logins and sessions**:
  - Users without one of these groups are refused.
  - Start logins on the console port 9001, not the S3 port.
  - Sessions last one hour, and logging out also ends the Keycloak session.
- **Root keys**: the keys in `.runtime/credentials/rustfs-access-key` and `rustfs-secret-key` are for recovery only. Polaris uses them server-side to issue temporary credentials.
- **Bucket list**: see [Known limitations](#known-limitations) for the console bucket-list issue.

### JupyterHub

- **Who gets in**: JupyterHub admits `role-default-developer`, `role-default-analyst`, and `role-platform-admin`. Platform admins are also Hub admins: they can see, stop, and open other users' servers. Admission is checked at login and again before each server starts.
- **Your server**: each user gets one Spark server (default 1 CPU and 2 GiB; at most two servers run at once). Your home directory is a named volume that survives server restarts. Settings: `JUPYTERHUB_SINGLEUSER_CPU_LIMIT`, `JUPYTERHUB_SINGLEUSER_MEMORY_LIMIT`, `JUPYTERHUB_HOST_PORT`.
- **Spark in a notebook** — data access is your own:

  ```python
  from lakehouse_spark import create_spark_session
  spark = create_spark_session()
  ```

  The Hub's internal token broker renews your Keycloak token over TLS. Polaris issues the storage credentials.
- **Network**: user servers run on the `jupyter-user` network (default `172.30.240.0/24`, Hub at `172.30.240.2`). If start reports a subnet conflict, change `JUPYTER_USER_SUBNET` and `JUPYTERHUB_BROKER_BIND_IP` together.
- **Rotating broker trust**:
  1. `./scripts/lakehouse.sh stop`
  2. `python3 scripts/setup/prepare-jupyterhub-broker-certificates.py --rotate`
  3. `./scripts/lakehouse.sh start`

### Airflow

- **Start and stop**: start it with `./scripts/lakehouse.sh start-airflow`. Use `airflow-status` and `stop-airflow` to check and stop it.
- **Sign-in**: the UI at <http://127.0.0.1:8085> uses Keycloak sign-in, with roles as in [Users and sign-in](#users-and-sign-in). The local FAB login is for recovery only and is limited to `AIRFLOW_ADMIN_USERNAME`.
- **DAG bundles**: two Git bundles, `lakehouse-main` (branch `main`, production) and `lakehouse-uat` (branch `uat`), from the `opensource-lakehouse` repository. They are cloned into this repository's `.runtime/airflow-dag-bundles` and refresh every five minutes.
- **Runs**: each DAG run starts its own Spark container, with the bundle mounted read-only. It writes as `srv-default-writer` through a token broker that keeps the client secret out of Spark.

### StarRocks

StarRocks (one FE and one BE) reads and writes the three Polaris catalogs.
- **Memory**: `STARROCKS_FE_MEMORY_LIMIT` (default `2g`) and `STARROCKS_BE_MEMORY_LIMIT` (default `4g`).
- **Ports**: SQL `9030` and HTTP `8030`, both on loopback.

**Log in** with your Keycloak account. StarRocks checks your Keycloak token, over TLS with a local certificate:

```sh
./scripts/clients/starrocks-login.sh joe-developer                  # asks for the Keycloak password
./scripts/clients/starrocks-login.sh maria-owner -e "SHOW CATALOGS"
```

The emergency admin account is `root`, with the password in `.runtime/credentials/starrocks-root-password`. Avoid it for normal work, because it bypasses the role model.

**DBeaver and other JDBC clients** use the same token login:

1. **Keep a fresh token in a file.** Tokens last five minutes and are checked when a connection opens, so leave this running:

   ```sh
   ./scripts/clients/starrocks-token.sh --watch joe-developer ~/.starrocks/token
   ```

2. **In DBeaver**:
   - Create a **StarRocks** connection.
   - Connect to host `127.0.0.1`, port `9030`, with your Keycloak username and an **empty** password.
   - Under **Driver properties**, set only `idTokenFile` to the absolute path of the token file, for example `/Users/<you>/.starrocks/token`.

3. **Other JDBC clients**: use MySQL Connector/J 9.1 or later, with these properties:

   | Property | Value |
   |---|---|
   | `idTokenFile` | absolute path of the token file |
   | `defaultAuthenticationPlugin` | `authentication_openid_connect_client` |
   | `sslMode` | `REQUIRED`, or `VERIFY_IDENTITY` with a truststore |

   **Optional: verify the certificate.**
   - Import the CA:

     ```sh
     keytool -importcert -noprompt -alias starrocks-ca -file .runtime/container-mounts/starrocks-ca.crt \
       -keystore ~/.starrocks/truststore.p12 -storetype PKCS12 -storepass <choose-one>
     ```

   - Set `sslMode=VERIFY_IDENTITY`, `trustCertificateKeyStoreUrl=file:/Users/<you>/.starrocks/truststore.p12`, and `trustCertificateKeyStorePassword=<choose-one>`.
   - Import the CA again after a reset.

**Catalogs and roles**:
- **Catalogs**: `lakehouse`, `lakehouse_uat`, and `lakehouse_dev` reach Polaris as the service account `srv-starrocks` (writer level) and use Polaris-issued storage credentials.
- **Roles**: StarRocks roles are named after the groups (`role_default_owner`, and so on) and grant the same access as Polaris:
  - read is `SELECT`
  - write adds `CREATE DATABASE`, `CREATE TABLE`, and `INSERT`
  - manage is everything except dropping Iceberg tables (see [Known limitations](#known-limitations))
- **MV databases**:
  - the writer creates, refreshes, and drops materialized views in all three
  - developers read all three, and analysts read production
  - owners and platform admins manage them
- **Enforcement**: the bootstrap revokes and reports any privilege added to these roles by hand.

**Users**: every Keycloak user in a product group has a StarRocks user with exactly their groups' roles.
- **Sync**: in step 2, every five minutes, or on demand with `./scripts/lakehouse.sh reconcile-starrocks [--dry-run]`.
- **Leaving a group**: removing someone from all groups drops their StarRocks user.
- **Safety**: if Keycloak cannot be read, nothing changes.
- **Secret rotation**: to rotate the `srv-starrocks` secret, or to repair the catalogs, run `python3 infra/starrocks/bootstrap-starrocks.py --recreate-catalogs`. Data is untouched.

### Jenkins

Jenkins runs the CI for the `opensource-lakehouse` workload repository through the multibranch pipeline `opensource-lakehouse-dp/opensource-lakehouse-ci`.
- **Builds**: it scans GitHub anonymously and runs that repository's `Jenkinsfile` on the built-in node, without the Docker socket.
- **Sign-in**: through Keycloak, with permissions as in [Users and sign-in](#users-and-sign-in).
- **Configuration**:
  - **Plugins**: the image pins exactly the plugins in `infra/jenkins/plugins.txt`.
  - **Security as code**: `infra/jenkins/casc/jenkins.yaml` sets the security realm, permissions, and break-glass account at every start. UI changes to these are overwritten.
  - **Jobs and history**: they live in the volume `lakehouse-local_jenkins-home` and are not configuration as code.
- **Break-glass**: if Keycloak is down, use the escape-hatch login as `jenkins-break-glass`. The password is in `.runtime/credentials/jenkins-break-glass-password`.

## Operations

### Status and stop

```sh
./scripts/lakehouse.sh status   # health of core and the enabled modules
./scripts/lakehouse.sh stop     # stops them; volumes and data are kept
```

`stop` also removes running Jupyter user servers. Their home volumes are kept. Avoid `docker compose ... down -v`: it deletes volumes.

### Reset the platform

The reset deletes all local platform state, so the next start begins from nothing:

```sh
./scripts/lakehouse.sh reset --dry-run   # list what would be deleted
./scripts/lakehouse.sh reset             # list it, then type "reset" to confirm
./scripts/lakehouse.sh reset --yes       # no prompt, for scripts
```

| Deleted | Kept |
|---|---|
| All `lakehouse-local` containers, including Jupyter user servers and Airflow Spark runs | Docker images |
| All platform volumes: realm and users, catalogs, buckets and objects, JupyterHub state and user homes, Jenkins home, Airflow metadata, and StarRocks metadata and storage | Other projects' containers, volumes, and networks |
| The `lakehouse-local` networks | Tracked files in this repository |
| `.runtime/credentials`, `.runtime/container-mounts`, `.runtime/airflow-dag-bundles` (secrets, certificates, bundles) | Other `.runtime` entries, such as `.runtime/backups` |

**The reset cannot be undone.** Back up anything you want to keep first.
- **Prompts**: without a terminal, it refuses unless you pass `--yes`.
- **Failures**: if a step fails, fix the cause and rerun.
- **Afterwards**: start again with the two [Quick start](#quick-start) steps.

### Backup

- **Data**: stop the owning service, then back up its Docker volume with your usual volume backup method. The volumes are named `lakehouse-local_*`, for example `lakehouse-local_jenkins-home` and `lakehouse-local_rustfs-data`.
- **Credentials**: back up `.runtime/credentials/` separately, in encrypted storage.

### Secrets and rotation

- **Where they live**: all secrets are in `.runtime/credentials/` (directory mode `0700`, files `0600`). They are created once by `scripts/setup/prepare-runtime.py`, never printed, and never written into Compose files.
- **Container copies**: containers that cannot read host-private files get read-only copies in `.runtime/container-mounts/`.
- **Rotating a client secret** (RustFS, Jenkins, JupyterHub, Airflow, StarRocks):
  1. Write the new value to the file.
  2. Set the same value on the Keycloak client.
  3. Rerun `python3 scripts/setup/prepare-runtime.py`.
  4. Restart the service, for example `docker compose -f compose.core.yml up -d rustfs`.

  `infra/keycloak/bootstrap-realm.py` refuses to continue while the file and Keycloak disagree.
- **JupyterHub auth-state key**: do not regenerate it while Hub sessions must stay readable.

### Running bootstrap steps individually

`bootstrap-default-product.sh` runs these in order; each is idempotent:

```sh
python3 infra/keycloak/bootstrap-realm.py               # realm, groups, clients, missing users
./scripts/bootstrap/bootstrap-users.sh                   # reset the five users to their defaults
./scripts/bootstrap/bootstrap-polaris-realm.sh           # Polaris internal operator principal
python3 infra/rustfs/bootstrap-buckets.py                # buckets
python3 infra/rustfs/bootstrap-policies.py               # RustFS group policies
python3 infra/polaris/bootstrap-default-catalogs.py      # catalogs and namespaces
python3 infra/polaris/bootstrap-product-authorization.py # Polaris grants
python3 infra/polaris/reconcile-keycloak-groups.py       # Polaris principals from Keycloak groups
docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build polaris-group-reconciler  # 5-minute sync
python3 scripts/verify/polaris-keycloak-auth.py          # writer token check
./scripts/bootstrap/smoke-spark.sh                       # Spark smoke tables
python3 infra/starrocks/bootstrap-starrocks.py           # StarRocks catalogs, MV databases, roles
python3 infra/starrocks/reconcile-starrocks-users.py     # StarRocks users from Keycloak groups
```

## Scripts

| Path | Purpose |
|---|---|
| `scripts/lakehouse.sh` | `start`, `status`, `stop`, `reset`, `reconcile-starrocks`, and the Airflow commands |
| `scripts/bootstrap-default-product.sh` | the product bootstrap (Quick start step 2) |
| `scripts/setup/` | credentials, certificates, and preflight checks used by `start` |
| `scripts/bootstrap/` | realm users and Spark smoke steps used by the product bootstrap |
| `scripts/operations/` | the full reset |
| `scripts/clients/` | `starrocks-login.sh` and `starrocks-token.sh` |
| `scripts/verify/` | verifiers. Most are read-only. `role-matrix.py` creates temporary users and data, and `keycloak-outage.py` stops Keycloak briefly |
| `scripts/aidlc_intent.py` | the AI-DLC workflow tool |

Tests: `python3 -m pytest -q tests`. The JupyterHub broker tests need `PYTHONPATH=infra/jupyter/hub`.

## Known limitations

- **Local only**: browser logins use plain HTTP, and the default password is published. Do not expose this stack beyond your machine.
- **RustFS console bucket list**: for Keycloak users, the console's bucket-list page keeps reloading. This is upstream bug [rustfs/console#271](https://github.com/rustfs/console/issues/271). Open a bucket directly instead, for example <http://127.0.0.1:9001/rustfs/console/browser?bucket=bucket-default-dev>.
- **No table drops through StarRocks**: StarRocks reaches Polaris at writer level, so not even owners can drop Iceberg tables through it. Drop tables through Spark or Polaris as an owner.
- **StarRocks materialized views**: a materialized view keeps its author. If the author leaves every product group, it may stop refreshing, and an owner must re-create it.
- **Reporting tools** such as Power BI are not supported yet, because StarRocks tokens are short-lived.
- **Jenkins CI job**: the workload CI job must be restored or recreated after a reset. A pre-reset copy of the home is in `.runtime/backups/20261031-pre-reset/jenkins-home.tar.gz`.
- **Reconciler identity**: the reconcilers use the Keycloak `admin` account. Use a narrower identity before any shared deployment.
