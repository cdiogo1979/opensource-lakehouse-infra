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
6. [Data products](#data-products)
   - [Create or change a product](#create-or-change-a-product)
   - [Remove a product](#remove-a-product)
7. [Adding users](#adding-users)
8. [Services](#services)
   - [Keycloak](#keycloak)
   - [Polaris](#polaris)
   - [RustFS](#rustfs)
   - [JupyterHub](#jupyterhub)
   - [Airflow](#airflow)
   - [StarRocks](#starrocks)
   - [Jenkins](#jenkins)
9. [Workload Python environment](#workload-python-environment)
10. [Operations](#operations)
   - [Status and stop](#status-and-stop)
   - [Reset the platform](#reset-the-platform)
   - [Backup](#backup)
   - [Secrets and rotation](#secrets-and-rotation)
   - [Running bootstrap steps individually](#running-bootstrap-steps-individually)
11. [Scripts](#scripts)
12. [Known limitations](#known-limitations)

## Components

| Component | What it does | URL | Compose module |
|---|---|---|---|
| Keycloak 26.8 | Groups and single sign-on (realm `lakehouse`); keeps users in the LDAP directory | <http://127.0.0.1:8080> | core |
| OpenLDAP 2.6 | The users and passwords, shared by Keycloak and StarRocks (LDAPS only, internal) | none (not published) | core |
| Apache Polaris 1.8 | Iceberg REST catalog; enforces data permissions and issues short-lived storage credentials | <http://127.0.0.1:8181> | core |
| RustFS 1.0.4 | S3-compatible object storage, with a web console | S3 <http://127.0.0.1:9000>, console <http://127.0.0.1:9001/rustfs/console/> | core |
| JupyterHub 6.1 | Notebooks with Spark, signed in as yourself | <http://jupyterhub.localhost:8000> | jupyter |
| Airflow 3.3 | Scheduled Spark workloads from Git DAG bundles | <http://127.0.0.1:8085> | airflow (optional) |
| StarRocks 4.1.7 | Interactive SQL over the Iceberg tables | `127.0.0.1:9030` (MySQL protocol) | starrocks |
| Jenkins 2.580 | CI for each data product's repository, one folder per product | <http://127.0.0.1:8090> | jenkins |

## Quick start

Requirements: Docker with Compose V2, Python 3, and OpenSSL. StarRocks needs about 6 GB of memory; turn it off if your machine is small (see [Compose modules](#compose-modules)).

```sh
cp .env.example .env                    # first time only
./scripts/lakehouse.sh start            # 1. start core and the enabled modules
./scripts/bootstrap-default-product.sh  # 2. create realm, users, and every data product
./scripts/lakehouse.sh start-airflow    # optional: Airflow
```

- **Step 1** creates missing credentials under `.runtime/credentials/` and starts the containers. It never changes realm, users, buckets, or catalogs.
- **Step 2** reruns step 1, then creates the Keycloak realm, clients, and [bootstrap users](#users-and-sign-in), and every [data product](#data-products) in `data-products/` (at first only `default`):
  - Keycloak groups
  - buckets and storage policies
  - Polaris catalogs, namespaces, and grants
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

**One password everywhere**: users and passwords live in the LDAP directory (`ldap` service), which Keycloak reads and writes. Groups stay in Keycloak. The same username and password sign in to Keycloak (and every web app) and to StarRocks. A password changed in Keycloak (account page or admin console) changes it everywhere.

| User | Group | Purpose |
|---|---|---|
| `joe-developer` | `role-default-developer` | Develops in dev; reads UAT and production |
| `peter-analyst` | `role-default-analyst` | Reads production |
| `maria-owner` | `role-default-owner` | Owns the data product |
| `srv-default-writer` | `role-default-writer` | Service user for Airflow and Spark writes |
| `platform-admin` | `role-platform-admin` | Administers the platform |

**What each group can do** (for `default`, as set in `data-products/default.yaml`; every other product's groups work the same way unless its file says otherwise):

| Group | Data (Polaris, StarRocks, RustFS) | JupyterHub | Airflow | Jenkins | Keycloak |
|---|---|---|---|---|---|
| `role-default-owner` | manage all environments | — | User | admin of folder `default` | — |
| `role-default-developer` | read prod and UAT; read and write dev; author MVs in dev | user | User | read and build in folder `default` | — |
| `role-default-analyst` | read prod | user | User | read folder `default` | — |
| `role-default-writer` | read and write all environments | — | Viewer | — | — |
| `role-platform-admin` | owner of every product, plus StarRocks system admin | Hub admin | Admin | Administer (all of Jenkins) | admin of the `lakehouse` realm |

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
- **Moving an existing stack to LDAP** (stacks created before the directory existed): users created earlier live in Keycloak's own database and cannot carry their passwords over. Run the one-time migration:

  ```sh
  python3 scripts/operations/migrate-users-to-ldap.py --dry-run   # list users and password sources
  python3 scripts/operations/migrate-users-to-ldap.py             # type "migrate" to run
  ```

  - **Passwords**: bootstrap users get `ChangeM3!`, product writer users the password in their file, and anyone else `ChangeM3!` (the report names them).
  - **Kept**: groups, names, email, and enabled state.
  - **Jupyter homes**: users get a new Keycloak ID, so each Jupyter home is copied to the new ID's volume and verified. Then the old volume and the old Hub user are deleted. Stop users' Jupyter servers first.
  - **Safety**: the Keycloak database is backed up to `.runtime/backups/<time>-pre-ldap/`. A user's old record is deleted only after the LDAP password works, and a rerun continues an interrupted migration.

## Data layout

Every data product has three environments in the **shared** Polaris catalogs, each with its own namespace, bucket, and StarRocks MV database. The `default` product:

| Environment | Polaris catalog | Namespace | Bucket | StarRocks MV database |
|---|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` | `default_lh` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` | `default_lhuat` |
| Dev | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` | `default_lhdev` |

- **Paths**: tables live at `<bucket>/<catalog>/<namespace>/<table>`, for example `s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test/`.
- **Smoke tables**: each environment has a one-row `bootstrap_smoke_test` table, created by the product bootstrap.
- **Credentials**: no workload ever receives RustFS root keys. Polaris issues short-lived, table-scoped credentials (one hour, cached for 10 minutes).
- **Other products**: a product `sales` uses `sales_lh`, `sales_lhuat`, `sales_lhdev` in the same catalogs, in the buckets `bucket-sales`, `bucket-sales-uat`, `bucket-sales-dev`. Each catalog allows every product's bucket.

## Data products

Each data product, `default` included, is one YAML file in `data-products/` that holds its whole configuration. Every component reads these files, so the file is the single place to look at or change a product:

```yaml
apiVersion: lakehouse.local/v1
name: sales
description: The sales data product
environments:              # catalogs are the shared ones; the rest is the product's
  prod: {catalog: lakehouse, namespace: sales_lh, bucket: bucket-sales, mv_database: sales_lh}
  uat: {catalog: lakehouse_uat, namespace: sales_lhuat, bucket: bucket-sales-uat, mv_database: sales_lhuat}
  dev: {catalog: lakehouse_dev, namespace: sales_lhdev, bucket: bucket-sales-dev, mv_database: sales_lhdev}
groups:                    # Keycloak groups, role-<token>-<role>
  owner: role-sales-owner
  developer: role-sales-developer
  analyst: role-sales-analyst
  writer: role-sales-writer
access:                    # none, read, write, manage: Polaris, StarRocks, and RustFS
  owner: {prod: manage, uat: manage, dev: manage}
  developer: {prod: read, uat: read, dev: write}
  analyst: {prod: read, uat: none, dev: none}
  writer: {prod: write, uat: write, dev: write}
materialized_views:        # none, read, author, manage (StarRocks MV databases)
  owner: {prod: manage, uat: manage, dev: manage}
  developer: {prod: read, uat: read, dev: author}
  analyst: {prod: read, uat: none, dev: none}
  writer: {prod: author, uat: author, dev: author}
apps:
  jupyterhub: [developer, analyst]
  airflow: {owner: User, developer: User, analyst: User, writer: Viewer}
  jenkins:                 # rights on the product's Jenkins folder; the owner is always its admin
    developer: [Job/Read, Job/Build, Job/Cancel, Job/Workspace]
    analyst: [Job/Read]
writer_user:
  username: srv-sales-writer
  password_file: .runtime/credentials/srv-sales-writer-password
repo:                      # optional: the product's DAG and CI repository (read anonymously)
  url: https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git
  prod_branch: main
  uat_branch: uat
```

**The `repo` block** (optional) gives the product its own Airflow DAG bundles: `<name>-main` tracks `prod_branch` and `<name>-uat` tracks `uat_branch`. The URL must be credential-free `https`; the repository is read without credentials. Several products may share one repository. `default` uses `opensource-lakehouse-sample-dp` (`main` and `uat`). There is no writer field: runs from a product's bundles always write as that product's `writer_user` (see [Airflow](#airflow)). The same block gives the product its Jenkins jobs `<name>_ci` and `<name>_cd` (see [Jenkins](#jenkins)).

**What the levels mean:**

| Level | Polaris (on the product namespace) | StarRocks (on the product database) | RustFS (on the product bucket) |
|---|---|---|---|
| read | list and read tables and views | `SELECT` | read |
| write | read, plus create tables and write data | read, plus `INSERT` and `CREATE TABLE` | read and write |
| manage | write, plus drop and full table and view metadata | `ALL` on the database and its tables | all actions |

- **Isolation**: product roles reach only their own namespaces, databases, and buckets. Anyone with access to a catalog can see every product's namespace **names**, but not their tables or data.
- **No namespace management**: product roles cannot create, drop, or move namespaces. Each product has exactly the three namespaces in its file.
- **Platform admin**: `role-platform-admin` is owner of every product.
- **Airflow is platform-wide**: it has no per-product permissions, so the Airflow roles in any product's file apply to the whole Airflow. Owners and developers are `User` (run, pause, and clear DAGs, read logs), and only `role-platform-admin` is `Admin`.
- **Jenkins is per folder**: each product's owners are admins of its folder (jobs, runs, views, folder credentials), and `apps.jenkins` grants the other roles rights on that folder only. Product groups can read Jenkins but see no other product's folder. Only `role-platform-admin` and the break-glass account administer Jenkins. `apps.jenkins` refuses `owner` and any `Overall/*` permission.

### Create or change a product

```sh
./scripts/operations/create-data-product.sh --init sales                       # write data-products/sales.yaml
./scripts/operations/create-data-product.sh data-products/sales.yaml --dry-run # show the plan
./scripts/operations/create-data-product.sh data-products/sales.yaml           # apply it
```

- **Applying** creates what is missing and makes every component match the file:
  - Keycloak groups and roles, the writer user (password `ChangeM3!`, in its password file), and the platform-admin owner role
  - buckets and storage policies
  - Polaris namespaces and grants
  - StarRocks roles and MV databases
  - the Jenkins folder and its permissions, and the `<name>_ci` and `<name>_cd` jobs when the file has a `repo` block
  - the Airflow bundles and writer, when the file has a `repo` block
- **Changing**: edit the file and apply it again. Access levels and app mappings can change at any time, and removed grants are revoked. **Names are locked once applied**: to rename a bucket, namespace, group, or the writer user, remove the product and create it again.
- **Restarts**: Jenkins, when its folders, jobs, or permissions change, and Airflow, when the bundles or writers change (a `repo` block added, edited, or removed). Airflow is recreated with `scripts/lakehouse.sh start-airflow` only if it is running; otherwise its next start picks the change up. `--no-restart` prints the commands instead, and `--dry-run` lists the Jenkins folders and jobs to create or delete and the bundles Airflow would get. Removing the `repo` block deletes the product's two Jenkins jobs and their build history; its folder stays. Sign-in roles need no restart: JupyterHub and Airflow read the files at each sign-in.
- **StarRocks delay**: a new product's tables become readable through StarRocks within about five minutes, when the shared catalogs renew their Polaris token and pick up the new writer group. Polaris, Spark, and the apps work right away.
- **Credentials**: the script signs in to Keycloak as a platform administrator and refuses users outside `role-platform-admin`. Pass `--admin-user USER` (default `platform-admin`) and `--admin-password-file FILE`, or set `LAKEHOUSE_ADMIN_PASSWORD`; otherwise it asks for the password without echo. The other services use the protected bootstrap credentials.
- **Safe to rerun**: a failed apply can simply be run again. One create or remove runs at a time.
- **People**: add users to the product's groups in Keycloak (see [Adding users](#adding-users)).
- **Checking access**: `python3 scripts/verify/role-matrix.py --product sales` tests every role with temporary identities, including that it cannot reach other products. It creates the product's smoke tables if they are missing.

### Remove a product

```sh
./scripts/operations/remove-data-product.sh sales --dry-run
./scripts/operations/remove-data-product.sh sales                # stops if the product still holds data
./scripts/operations/remove-data-product.sh sales --purge-data   # also deletes its tables and objects
```

- **Never `default`**: the default product cannot be removed.
- **Data check**: it lists the product's tables, MVs, and bucket objects, and the members who will lose access. It stops while any data exists, unless you pass `--purge-data`.
- **Confirmation**: you type the product name (`--yes` skips this, for scripts). It takes the same admin credentials as the create script.
- **What goes**: the Jenkins folder (with its jobs and build history) and entries, StarRocks roles and MV databases, Polaris roles and namespaces, buckets and policies, the Keycloak groups and writer user, and finally the product file. Its Airflow bundles go last (Airflow is recreated, as for create). The file and its applied state are backed up to `.runtime/backups/<time>-remove-<name>/` first.
- **Users stay**: only their memberships go. A failed removal can be rerun with the same command.

## Adding users

```sh
./scripts/operations/create-user.sh anna --email anna@example.com --first-name Anna --last-name Lee
```

- **The user**: enabled in the `lakehouse` realm with the permanent password `ChangeM3!`, or the first line of `--password-file FILE`. No groups, and an existing username is refused.
- **Stored in LDAP**: Keycloak writes the new user and its password to the LDAP directory, so the same password works for StarRocks once the user is in a product group.
- **Credentials**: as for the product scripts, `--admin-user` and `--admin-password-file`, `LAKEHOUSE_ADMIN_PASSWORD`, or a prompt.
- **Access**: add the user to product groups in the [Keycloak admin console](http://keycloak.localhost:8080/admin/lakehouse/console/) as `platform-admin`. Polaris and StarRocks follow within five minutes, or right away with `python3 infra/polaris/reconcile-keycloak-groups.py` and `./scripts/lakehouse.sh reconcile-starrocks`. JupyterHub, Airflow, and Jenkins follow at the next sign-in.

## Services

### Keycloak

- **Realm**: the realm `lakehouse` holds every data product's groups, the bootstrap users, and one client per application. The contract is `infra/keycloak/realm-contract.json`, applied idempotently by `infra/keycloak/bootstrap-realm.py` (with the product groups from `data-products/`), which refuses conflicting changes.
- **Users in LDAP**: the realm's user storage is the provider `lakehouse-ldap`. It reads and writes users and passwords in the `ldap` service over LDAPS (`ldaps://ldap:636`, bind `cn=keycloak,ou=services,dc=lakehouse,dc=local`), and Keycloak trusts its CA through `truststore-paths`. Groups stay in Keycloak. Client service accounts (`service-account-*`) and the `master` realm stay local.
- **Hostnames**: browsers use `keycloak.localhost:8080`, the canonical issuer. Containers call `keycloak:8080`, because `.localhost` means loopback inside a container.
- **Writer identity**: workload writes use `srv-default-writer` through the confidential `lakehouse-writer` client (password grant, one-hour tokens).
- **Optional CLI client**: the human CLI client `lakehouse-cli` has no callback until an application needs one: `python3 infra/keycloak/bootstrap-realm.py --redirect-uri 'http://localhost:PORT/EXACT/CALLBACK'`.

### Polaris

- **Catalogs**: three shared catalogs, one per environment. Each allows every product's bucket, and each product's namespace lives in its own bucket (this needs the Polaris feature `ALLOW_NAMESPACE_CUSTOM_LOCATION`, set in `infra/polaris/oidc.properties`).
- **Roles**: Polaris accepts Keycloak tokens and maps any product group (`role-<token>-<role>`) to the principal role of the same name.
- **Grants**: per product role and catalog, a catalog role with `NAMESPACE_LIST` and `CATALOG_READ_PROPERTIES`, plus the [level's privileges](#data-products) on the product's namespace only. Grants that no product file describes are revoked and reported.
- **Principals**: Polaris needs a principal for every Keycloak user. The scheduled reconciler (`polaris-group-reconciler`, every `POLARIS_GROUP_RECONCILE_INTERVAL_SECONDS`, default 300) creates them and keeps their roles in sync with Keycloak groups.
- **Management endpoint**: it stays inside the container (port 8182 is not published). Check readiness with `docker compose -f compose.core.yml exec polaris curl --fail --silent http://127.0.0.1:8182/q/health/ready`.

### RustFS

- **Buckets**: three per data product, created only if missing. Existing objects are kept.
- **Console sign-in**: the console at <http://127.0.0.1:9001/rustfs/console/> offers **Keycloak** sign-in. Each Keycloak group maps to a RustFS policy with the same name, kept in line with the product files. For `default`:

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

- **Who gets in**: the groups each product file lists under `apps.jupyterhub` (by default developers and analysts), and `role-platform-admin`. The files are read at every sign-in. Platform admins are also Hub admins: they can see, stop, and open other users' servers. Admission is checked at login and again before each server starts.
- **Your server**: each user gets one Spark server (default 1 CPU and 2 GiB; at most two servers run at once). Your `~/work` folder is a named volume that survives server restarts; the rest of the home directory (`/home/jovyan`, the image's fixed Jupyter user) is reset when the server restarts. Settings: `JUPYTERHUB_SINGLEUSER_CPU_LIMIT`, `JUPYTERHUB_SINGLEUSER_MEMORY_LIMIT`, `JUPYTERHUB_HOST_PORT`.
- **Spark in a notebook** — data access is your own:

  ```python
  from lakehouse_spark import create_spark_session
  spark = create_spark_session()
  ```

  The Hub's internal token broker renews your Keycloak token over TLS. Polaris issues the storage credentials. Product repositories wrap this in their own start-up (`start_spark_job`); see the [workload Python environment](#workload-python-environment).
- **Widgets**: `ipywidgets` works in the kernel (JupyterLab has the matching `jupyterlab_widgets`), for example for a notebook's input fields.
- **Git**: user servers have `git` and the JupyterLab Git extension (the Git sidebar), so you can clone a product repository into `~/work`, for example `git clone https://github.com/cdiogo1979/opensource-lakehouse-sample-dp.git`. No Git credentials are stored on the platform.
- **Kernel**: the only kernel is **Lakehouse (Python 3.10)**, the same Python and packages as Airflow's Spark runs (see [Workload Python environment](#workload-python-environment)). Notebooks saved with the earlier `python3` kernel open with it. JupyterLab itself runs on its own Python.
- **A product's extra packages**: in a terminal, or with `!` in a cell, run `lakehouse-install-requirements` in the product repository (or `lakehouse-install-requirements path/to/repo`), then restart the kernel. They go to `~/.local/lakehouse/python3.10` and never change the platform's versions. That folder is outside `~/work`, so it lasts only for the current server session: **rerun the command after every server start**. After a platform lock change the command asks you to rerun it with `--reset`.
- **Network**: user servers run on the `jupyter-user` network (default `172.30.240.0/24`, Hub at `172.30.240.2`). If start reports a subnet conflict, change `JUPYTER_USER_SUBNET` and `JUPYTERHUB_BROKER_BIND_IP` together.
- **Rotating broker trust**:
  1. `./scripts/lakehouse.sh stop`
  2. `python3 scripts/setup/prepare-jupyterhub-broker-certificates.py --rotate`
  3. `./scripts/lakehouse.sh start`

### Airflow

- **Start and stop**: start it with `./scripts/lakehouse.sh start-airflow`. Use `airflow-status` and `stop-airflow` to check and stop it.
- **Sign-in**: the UI at <http://127.0.0.1:8085> uses Keycloak sign-in. Roles come from each product file's `apps.airflow`, read at every sign-in, and apply to the whole Airflow. The local FAB login is for recovery only and is limited to `AIRFLOW_ADMIN_USERNAME`.
- **DAG bundles**: every product with a `repo` block gets two Git bundles, `<name>-main` (its `prod_branch`, production) and `<name>-uat` (its `uat_branch`). `default` has `default-main` and `default-uat` from `opensource-lakehouse-sample-dp`. The bundles are cloned into this repository's `.runtime/airflow-dag-bundles` and refresh every five minutes. `start-airflow` generates the list from `data-products/*.yaml` and checks it.
- **Runs**: each DAG run starts its own Spark container, with the bundle mounted read-only, and gets its write token from a token broker that keeps all credentials out of DAG code and Spark.
- **Which writer**: the broker takes the product from the DAG ID, which must start with the bundle name (`default-main-test_environment` writes as `srv-default-writer`). It then asks Airflow, as the read-only user `lakehouse-broker`, which bundle the DAG really comes from, and refuses the run unless that is the product's own bundle. A refused run fails at `create_cluster` with `unknown_product`, `unknown_dag`, or `bundle_mismatch`.
- **DAGs come from JSON, built by the platform**: a product repository declares DAGs in `workflows/<name>.json` and keeps its code in `notebooks/` and its settings in `configs/` (both also used from Jupyter). Its only DAG file is the stub `dags/lakehouse.py`, which calls the platform factory `infra/airflow/lakehouse_dags` (mounted read-only into the dag-processor and the scheduler). The factory builds `<bundle>-<name>` with `create_cluster`, `install_requirements` (the repository's optional root `requirements.txt`; see [Workload Python environment](#workload-python-environment)), `validate_environment` (the repository's own `config_loader`, run inside the Spark container), one `submit_<task>` per task in `runs_after` order, `stop_cluster`, and `verify_workloads_succeeded`. No repository code runs in the scheduler, which holds the Docker socket and the broker token.

  ```json
  {
    "apiVersion": "lakehouse.local/workflow/v1",
    "name": "test_environment",
    "schedule": null,
    "tasks": [
      {"name": "load", "entrypoint": "load.py", "args": ["--date", "2026-11-10"], "retries": 2, "retry_delay_seconds": 60},
      {"name": "count", "entrypoint": "count_sample_rows.py", "runs_after": ["load"], "execution_timeout_seconds": 3600}
    ]
  }
  ```

  - **Fields**: `apiVersion`, `name` (equal to the file name), `schedule` (`null` or a cron or preset string), optional `description` and `tags`; each task has `name`, `entrypoint` (a file in `notebooks/workload/`), and optional `runs_after`, `args` (passed after `--` to the entry point), `retries` (0 to 10), `retry_delay_seconds` (with retries), and `execution_timeout_seconds`. Unknown keys and invalid values are refused.
  - **Errors**: one invalid workflow file is an import error for the stub, so none of that bundle's DAGs load until it is fixed. Product CI catches it first: the Jenkins image has `lakehouse-validate-workflows`, which checks the workflows, the exact stub, and that `dags/` holds nothing else, and then a root `requirements.txt` against the platform lock.
  - **Bundles**: only `<product>-main` (environment `prod`) and `<product>-uat` (`uat`) are accepted. Each bundle checks out `dags`, `workflows`, `notebooks`, and `configs`, plus the files at the repository root (Git always includes them), such as `requirements.txt`. Airflow looks for DAG files only in `dags/` (the bundles' `subdir`), so code under `notebooks/` is never imported by the DAG processor.
  - **Changing the factory**: edits under `infra/airflow/lakehouse_dags` are visible to the containers at once through the mount; apply them with `./scripts/lakehouse.sh start-airflow`, and run `scripts/verify/dag-factory-tests.sh` (inside the Airflow image) first.
- **Checks**: `scripts/verify/airflow-dags.sh` waits for DAGs from every product bundle and warns about DAG IDs without their bundle prefix. `scripts/verify/broker-unit-tests.sh` runs the broker tests inside its image, and `scripts/verify/dag-factory-tests.sh` the DAG factory tests inside the Airflow image.

### StarRocks

StarRocks (one FE and one BE) reads and writes the three Polaris catalogs.
- **Memory**: `STARROCKS_FE_MEMORY_LIMIT` (default `2g`) and `STARROCKS_BE_MEMORY_LIMIT` (default `4g`).
- **Ports**: SQL `9030` and HTTP `8030`, both on loopback.

**Log in** with your username and password, the same as for Keycloak sign-in. StarRocks checks the password against the LDAP directory, and **every connection must use TLS** (plain-text connections are refused):

```sh
./scripts/clients/starrocks-login.sh joe-developer                  # asks for the password
./scripts/clients/starrocks-login.sh maria-owner -e "SHOW CATALOGS"
./scripts/clients/starrocks-login.sh --password-file ~/.srv-pw srv-default-writer -e "SELECT 1"
```

Service users (`srv-*-writer`) log in the same way, with the password in their file under `.runtime/credentials/`. The emergency admin account is `root`, with the password in `.runtime/credentials/starrocks-root-password`. Avoid it for normal work, because it bypasses the role model.

**DBeaver and other JDBC clients** use username and password over TLS:

1. **In DBeaver**:
   - Create a **StarRocks** connection to host `127.0.0.1`, port `9030`, with your username and password.
   - On the **SSL** tab, enable SSL (or set the driver property `sslMode=REQUIRED`).
2. **Other JDBC and BI clients** (MySQL Connector/J, or ODBC): username and password, with `sslMode=REQUIRED`. The client sends the password with the MySQL clear-text authentication plugin, which these drivers use only over TLS.

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
- **Roles**: StarRocks roles are named after the groups (`role_default_owner`, `role_sales_owner`, and so on) and grant the same access as Polaris, on the product's database in each catalog only:
  - read is `SELECT`
  - write adds `CREATE TABLE` and `INSERT`
  - manage is everything except dropping Iceberg tables (see [Known limitations](#known-limitations))
  - `role_platform_admin` manages the whole catalogs
- **MV databases** (one per product and environment, levels from the file; for `default`):
  - the writer creates, refreshes, and drops materialized views in all three
  - developers do the same in dev, and read production and UAT
  - analysts read production
  - owners and platform admins manage them
- **Enforcement**: the bootstrap revokes and reports any privilege added to these roles by hand.

**Users**: every Keycloak user in a product group has a StarRocks user with exactly their groups' roles.
- **Sync**: in step 2, every five minutes, or on demand with `./scripts/lakehouse.sh reconcile-starrocks [--dry-run]`.
- **Leaving a group**: removing someone from all groups drops their StarRocks user.
- **Safety**: if Keycloak cannot be read, nothing changes.
- **Secret rotation**: to rotate the `srv-starrocks` secret, or to repair the catalogs, run `python3 infra/starrocks/bootstrap-starrocks.py --recreate-catalogs`. Data is untouched.

### Jenkins

Jenkins runs CI for each data product in a folder named after the product (`default` for the default product). With a `repo` block, the folder holds two multibranch pipelines on the repository's `Jenkinsfile`:

| Job | Builds | Source | Checks for changes |
|---|---|---|---|
| `<name>_ci` | `prod_branch` and `uat_branch`, when they get new commits | Git, anonymous | every 5 minutes |
| `<name>_cd` | every branch of the repository that is the source of an open pull request; forks are not built | GitHub, anonymous (github.com repositories only) | every 30 minutes |

- **Builds**: on the built-in node, without the Docker socket. There are no webhooks, so changes are picked up by the scheduled scans; **Scan Multibranch Pipeline Now** checks right away. A branch whose pull request closes, or that leaves the filter, is removed with its build history.
- **GitHub limit**: without a token, GitHub allows 60 API requests per hour for this machine. Each `_cd` scan uses a few, so about five products with a GitHub `repo` fit. A repository on another host gets only `<name>_ci`.
- **Folders and jobs as code**: `render_jenkins.py` writes the folders, their permissions, and the jobs as a Job DSL script (`.runtime/container-mounts/jenkins-jobs.groovy`) and the expected set (`jenkins-products.json`). At every start, also after a reset, the hook `infra/jenkins/init.groovy.d/reconcile-data-products.groovy` applies the script, then deletes the managed folders and jobs that left the product files; it never touches other items. Edits made in the UI to the folders and jobs are overwritten at the next start; jobs that owners add to their folder are kept.
- **Sign-in**: through Keycloak, with permissions as in [Users and sign-in](#users-and-sign-in).
- **Configuration**:
  - **Plugins**: the image pins exactly the plugins in `infra/jenkins/plugins.txt`.
  - **Security as code**: `infra/jenkins/casc/jenkins.yaml` is the template for the security realm, the project-based matrix, and the break-glass account. `infra/products/render_jenkins.py` adds the product groups, folders, and jobs and writes `.runtime/container-mounts/jenkins-casc.yaml`, which Jenkins applies at every start. UI changes to these are overwritten.
  - **Build history**: it lives in the volume `lakehouse-local_jenkins-home` and is lost on a reset.
- **Break-glass**: if Keycloak is down, use the escape-hatch login as `jenkins-break-glass`. The password is in `.runtime/credentials/jenkins-break-glass-password`.

## Workload Python environment

Workload code runs on the same Python 3.10 and the same packages everywhere: in each Airflow DAG run's Spark container and in the Jupyter kernel.

- **The platform's packages**: `infra/workload-python/requirements.in` pins the top-level packages (PyYAML, requests, pandas, numpy, pyarrow, ipykernel, jupytext, ipywidgets); `requirements.lock` pins every package, dependencies included. PySpark is not in it: both images use the one in `/opt/spark`. Other packages of the Spark base image (such as scipy, matplotlib, pyiceberg) are not available to workload code unless added here.
- **Where it lives**: both `local/lakehouse-spark-runtime` and `local/lakehouse-jupyter-singleuser` hold `/opt/lakehouse/venv` with exactly the lock, and `PYSPARK_PYTHON` points at it. Each image build fails if the venv differs from the lock.
- **Changing it**: edit `requirements.in`, run `scripts/setup/lock-workload-python.sh` (it resolves the lock in the Spark runtime's base image, so the Python, architecture and glibc match), rebuild the images with `./scripts/lakehouse.sh start` (or `start-airflow` for the runtime image only), and run `scripts/verify/workload-python-parity.sh`. Never edit the lock by hand.
- **A product's extra packages**: an optional `requirements.txt` at the product repository's root.
  - **Lines**: plain requirements only, such as `duckdb==1.5.6` or `requests[socks]>=2.31,<3`, with comments and environment markers. Refused: options (`-r`, `-e`, `--index-url`, ...), URLs, paths and `name @ url` references, and `pyspark`, `py4j`, `pip`, `setuptools`, `wheel`.
  - **Constrained**: the lock is always a constraint, so extras can add packages but never change a locked version; a conflict fails.
  - **Wheels only**: every package needs a prebuilt wheel for CPython 3.10 on Linux aarch64 with glibc 2.31 or older (`manylinux_2_17` to `manylinux_2_31`, or `manylinux2014`). For example, `pytpch` 0.2.0 has only an x86_64 wheel for glibc 2.34, so it can't be used.
  - **CI**: `lakehouse-validate-workflows` resolves the file against the lock for that platform (it needs PyPI) and lists what it would add.
  - **Airflow**: `install_requirements` installs it into the run's own container before `validate_environment`, retrying twice 30 seconds apart; a failure stops the run before any workload code, and the container is cleaned up as usual. Without a `requirements.txt` the task does nothing and needs no network.
  - **Jupyter**: `lakehouse-install-requirements` (see [JupyterHub](#jupyterhub)).
- **Spark sessions**: `lakehouse_spark.create_spark_session(app_name, catalog)` (`infra/workload-python/python/`, at `/opt/lakehouse/python` in both images, on the venv's path through `lakehouse-platform.pth`) is the platform's only copy of the Polaris catalogs (`lakehouse`, `lakehouse_uat`, `lakehouse_dev`), the token source and redaction.
  - **Token source**: an Airflow run's broker settings, or the JupyterHub user's token; anything else is an error, with no fallback.
  - **Reuse**: a running session is returned when its default catalog matches; another catalog needs a kernel restart.
  - **Repositories** load their own `configs/<env>.yml` and pass its `catalog_name`; `spark-defaults.conf` holds only the Iceberg extensions and redaction.
- **Checks**: `scripts/verify/workload-python-parity.sh` checks that both built images hold the workspace lock and identical packages, and that Jupyter offers only the Lakehouse kernel.

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
| `.runtime/credentials`, `.runtime/container-mounts`, `.runtime/airflow-dag-bundles`, `.runtime/state` (secrets, certificates, bundles, applied product names); the LDAP directory (`ldap-data`) | Other `.runtime` entries, such as `.runtime/backups`, and the product files in `data-products/` |

**The reset cannot be undone.** Back up anything you want to keep first.
- **Prompts**: without a terminal, it refuses unless you pass `--yes`.
- **Failures**: if a step fails, fix the cause and rerun.
- **Afterwards**: start again with the two [Quick start](#quick-start) steps. Step 2 recreates every product in `data-products/`, with empty buckets.

### Backup

- **Data**: stop the owning service, then back up its Docker volume with your usual volume backup method. The volumes are named `lakehouse-local_*`, for example `lakehouse-local_jenkins-home`, `lakehouse-local_rustfs-data`, and `lakehouse-local_ldap-data` (the users and password hashes; back it up with `lakehouse-local_keycloak-db-data`).
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
- **LDAP**:
  - **Keycloak's bind password** (`.runtime/credentials/ldap-keycloak-password`): change the file, then restart `ldap` (it re-hashes the bind entry at start) and rerun `python3 infra/keycloak/bootstrap-realm.py`, which updates and tests the provider.
  - **The LDAP admin password** (`ldap-admin-password`) is for recovery only.
  - **Certificates**: `python3 scripts/setup/prepare-ldap-certificates.py --rotate`, then restart `ldap`, Keycloak, and the StarRocks FE.

### Running bootstrap steps individually

`bootstrap-default-product.sh` runs these in order for every product file; each is idempotent, and the product steps also take `--product FILE` and `--dry-run`:

```sh
python3 infra/keycloak/bootstrap-realm.py               # realm, clients, product groups, missing users
./scripts/bootstrap/bootstrap-users.sh                   # reset the five users to their defaults
./scripts/bootstrap/bootstrap-polaris-realm.sh           # Polaris internal operator principal
python3 infra/rustfs/bootstrap-buckets.py                # buckets
python3 infra/rustfs/bootstrap-policies.py               # RustFS group policies
python3 infra/polaris/bootstrap-catalogs.py              # catalogs and namespaces
python3 infra/polaris/bootstrap-product-authorization.py # Polaris grants
python3 infra/polaris/reconcile-keycloak-groups.py       # Polaris principals from Keycloak groups
docker compose -f compose.core.yml --profile scheduled-reconciliation up -d --build polaris-group-reconciler  # 5-minute sync
python3 scripts/verify/polaris-keycloak-auth.py          # writer token check
./scripts/bootstrap/smoke-spark.sh                       # Spark smoke tables
python3 infra/starrocks/bootstrap-starrocks.py           # StarRocks catalogs, MV databases, roles
python3 infra/starrocks/reconcile-starrocks-users.py     # StarRocks users from Keycloak groups
python3 infra/products/product-cli.py record --all       # lock the applied product names
```

## Scripts

| Path | Purpose |
|---|---|
| `scripts/lakehouse.sh` | `start`, `status`, `stop`, `reset`, `reconcile-starrocks`, and the Airflow commands |
| `scripts/bootstrap-default-product.sh` | the product bootstrap (Quick start step 2) |
| `scripts/setup/` | credentials, certificates, and preflight checks used by `start`; `lock-workload-python.sh` regenerates the workload lock |
| `infra/workload-python/` | the shared workload Python packages (`requirements.in`, `requirements.lock`) and `workload_python.py`, their checks and installer |
| `scripts/bootstrap/` | realm users and Spark smoke steps used by the product bootstrap |
| `scripts/operations/` | `create-data-product.sh`, `remove-data-product.sh`, `create-user.sh`, `migrate-users-to-ldap.py` (once, for older stacks), and the full reset |
| `data-products/` | one configuration file per data product |
| `infra/products/` | the product model, template, Jenkins renderer, and `product-cli.py` |
| `scripts/clients/` | `starrocks-login.sh` (username and password over TLS) |
| `scripts/verify/` | verifiers. Most are read-only. `role-matrix.py` creates temporary users and data, and `keycloak-outage.py` stops Keycloak briefly |
| `scripts/aidlc_intent.py` | the AI-DLC workflow tool |

Tests: `python3 -m pytest -q tests` (`pytest.ini` adds the Hub modules' folder to the import path). The token broker's behavioral tests run inside its image (`scripts/verify/broker-unit-tests.sh`), and the DAG factory's Airflow-side tests inside the Airflow image (`scripts/verify/dag-factory-tests.sh`).

## Known limitations

- **Local only**: browser logins use plain HTTP, and the default password is published. Do not expose this stack beyond your machine.
- **RustFS console bucket list**: for Keycloak users, the console's bucket-list page keeps reloading. This is upstream bug [rustfs/console#271](https://github.com/rustfs/console/issues/271). Open a bucket directly instead, for example <http://127.0.0.1:9001/rustfs/console/browser?bucket=bucket-default-dev>.
- **No table drops through StarRocks**: StarRocks reaches Polaris at writer level, so not even owners can drop Iceberg tables through it. Drop tables through Spark or Polaris as an owner.
- **StarRocks materialized views**: a materialized view keeps its author. If the author leaves every product group, it may stop refreshing, and an owner must re-create it.
- **LDAP outage**: while the `ldap` service is down, Keycloak sign-ins and StarRocks password logins fail. Client service accounts, issued tokens, and open sessions keep working.
- **Jenkins scans, no webhooks**: Jenkins is reachable only on this machine, so it notices commits and pull requests by scanning (5 and 30 minutes). Pull request discovery is github.com only and unauthenticated (60 requests per hour for this machine), so many products with GitHub repositories would exhaust it. Pull requests from forks are not built.
- **Reconciler identity**: the reconcilers use the Keycloak `admin` account. Use a narrower identity before any shared deployment.
- **Platform-wide Airflow rights**: Airflow has no per-product permissions, so a product's Airflow roles apply to all of Airflow.
- **Namespace names**: every product's namespace names are visible to anyone with access to a shared catalog.
- **Adding or removing a data product restarts Airflow**: Airflow 3.3 reads its DAG bundle list only at startup, and the token broker reads its writers only at startup. So creating or removing a product with a `repo` block (or changing that block) recreates the Airflow containers, which interrupts running DAG runs (tasks run inside the scheduler with LocalExecutor). Use `--no-restart` and run `scripts/lakehouse.sh start-airflow` when nothing is running.
- **Unused images may be deleted**: on Rancher Desktop with Kubernetes enabled, images no container uses can be removed when the VM disk fills up. `start` and `start-airflow` rebuild or pull them. If an Airflow DAG run fails at `create_cluster` because `local/lakehouse-spark-runtime` is missing, run `scripts/lakehouse.sh start-airflow` to rebuild it.
- **Product extras need PyPI**: runs, CI, and the Jupyter command fetch a product's extra packages from public PyPI each time; there is no private index or cache. Packages without a suitable aarch64 wheel can't be used. DuckDB also downloads its `tpch` extension at first use in each run.
- **Public repositories only**: product repositories are read anonymously by Airflow and Jenkins, so they must be public (or reachable without credentials).
