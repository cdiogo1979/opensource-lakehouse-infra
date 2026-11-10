# Hive, RustFS, Kerberos, Spark, and JupyterHub PoC

This local Docker Compose project uses Hive Metastore 3.1.3 as the Iceberg catalog, PostgreSQL for metastore metadata, RustFS for S3-compatible table storage, and Spark for TPCH sample workloads and JupyterHub sessions.

## Components

| Service | Purpose |
|---|---|
| `freeipa-validation` | Optional isolated FreeIPA validation profile; it does not replace the active MIT KDC |
| `kdc` | MIT Kerberos realm and service/workload/user identities |
| `identity-provisioner` | One-shot Kerberos, RustFS IAM, and PostgreSQL role setup |
| `metastore-db` | PostgreSQL storage for Hive catalog metadata |
| `hive-schema-init` | Non-destructive Hive schema inspection/initialization |
| `hive-metastore` | Hive Thrift catalog on the internal Compose network |
| `object-store` | RustFS S3-compatible object storage |
| `create-bucket` | Ensure-only creation of the `lake` bucket |
| `spark` | Spark 3.5.5 and Iceberg 1.8.1 with Hive catalog configuration |
| `jupyterhub` | Local Hub that starts isolated Spark notebook containers |
| `airflow-postgres` | Dedicated PostgreSQL metadata store for Airflow |
| `airflow-api-server`, `airflow-scheduler`, `airflow-dag-processor`, `airflow-triggerer` | Airflow 3.3.2 LocalExecutor control plane and Git Bundle processing |
| `jenkins` | Jenkins LTS validation UI with persistent home |
| `tpch-generator` | Optional scale-factor-1 TPCH input generation |
| `tpch-loader` | Optional Spark ETL as `write-service-account` into Hive/RustFS |

TPCH generation and loading are available under the `workload` Compose profile and do not run during normal startup. Inputs, results, and local credentials are stored under ignored `.runtime/`; Iceberg objects remain in the RustFS volume.

## Prerequisites

- Docker Desktop or another Docker Engine with Docker Compose v2.
- Allocate enough Docker memory for Spark, RustFS, Hive, PostgreSQL, Kerberos, and JupyterHub.
- Hive 3.1.3 is an archived/EOL release and is intended for this local PoC only.

## Start and inspect

```bash
./scripts/bootstrap-local.sh
./scripts/provision-identities.sh
./scripts/freeipa-validation.sh start
./scripts/export-freeipa-ca.sh
./scripts/start.sh
docker compose ps
docker compose logs -f hive-metastore
```

Bootstrap creates missing local credentials under `.runtime/credentials/`, preserves existing values, and does not print credential contents. It creates the JupyterHub auth-state crypt key and the password file for the dedicated FreeIPA LDAP reader; it does not create that directory account or change its permissions. Before user login, create the reader account in FreeIPA with the protected file's value and grant only the documented read/search attributes. Create the FreeIPA human users separately. First-time setup provisions the writer keytab before startup because the Spark service requires it; `scripts/start.sh` checks for the file and builds the local Spark image. Later, `scripts/provision-identities.sh` can be rerun to reconcile identities.

When migrating an existing local installation, run the one-time Dremio cleanup described below before starting or stopping the full stack. If the KDC container is stopped or absent, first run `docker compose up -d kdc`, which reuses the existing KDC volume.

Developer endpoints bind to loopback:

- RustFS console: <http://127.0.0.1:9001>
- Spark UI: <http://127.0.0.1:8082>
- JupyterHub: <http://127.0.0.1:8008>

JupyterHub authentication uses FreeIPA LDAPS. The Hub connects to FreeIPA through the internal `iceberg-poc-jupyterhub-ipa-net`; notebook containers are not attached to that network. Run `./scripts/bootstrap-local.sh` to create the protected reader-password and auth-state-key files, then start the `freeipa-validation` profile and complete the documented FreeIPA onboarding before starting Hub sessions. Create the `jupyterhub-ldap-reader` account with the value stored in `.runtime/credentials/freeipa-jupyterhub-ldap-reader-password`, and grant it read/search access only to user `uid`/`nsAccountLock` and role-group `cn`/`member` attributes. Provision the FreeIPA human user `administrator` separately; it maps to the existing MIT `admin` principal/keytab, RustFS admin credential pair, and preserved admin workspace. `user_a` and `user_b` are no longer accepted by JupyterHub, while their credential files and workspaces remain preserved. Authentication stays fail-closed until FreeIPA, the reader account, and the protected secret files are ready. LDAPAuthenticator/FreeIPA schema and TLS behavior still require the Unit 4 Build and Test checks.

Before switching from the former local authenticator, stop active notebook servers and rotate the persisted JupyterHub cookie secret to invalidate old login sessions. For role revocation, disable/remove the FreeIPA role and stop that user's active server from the JupyterHub admin interface; directory changes alone do not stop an existing server. Stopping the server destroys its tmpfs ticket cache while the named workspace remains persistent.

### Start Spark in a notebook

The notebook entrypoint stages the signed-in user's own keytab and obtains a MIT ticket. Before the first Hive/Iceberg operation, also load that identity into Hadoop's Java UserGroupInformation; the operating-system ticket reported by `klist` does not by itself initialize the JVM's Kerberos Subject. Use this sequence in a notebook:

```python
import os
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName(f"lakehouse-{os.environ['JUPYTERHUB_USER']}").getOrCreate()
ugi = spark.sparkContext._jvm.org.apache.hadoop.security.UserGroupInformation
ugi.loginUserFromKeytab(
    os.environ["KERBEROS_PRINCIPAL"],
    "/run/credentials/identity.keytab",
)
if not ugi.getLoginUser().hasKerberosCredentials():
    raise RuntimeError("Hadoop did not load the notebook Kerberos identity")

spark.sql("SHOW DATABASES IN iceberg").show(truncate=False)
```

The example notebook `infra/jupyter/examples/spark-authz.py` performs the same identity check and optionally queries `LAKEHOUSE_SAMPLE_TABLE`. Spark gets the matching user's RustFS credentials from its environment. It does not use the writer identity.

Airflow and Jenkins bind to all host interfaces by the approved local deployment design:

- Airflow: <http://localhost:8085>
- Jenkins: <http://localhost:8098>

These endpoints use HTTP without TLS termination. Apply host/network firewall rules appropriate to the machine. Airflow API health only verifies that its API process responds; it does not establish Spark, Kerberos, Hive, or RustFS readiness. The detailed Airflow component health endpoint is `/api/v2/monitor/health`; inspect the JSON component statuses rather than treating HTTP 200 as proof that every component is healthy.

Hive Thrift (`hive-metastore:9083`), PostgreSQL (`metastore-db:5432`), Kerberos, and kadmind are internal to the Compose network.

## Isolated FreeIPA validation

FreeIPA validation is opt-in and stays on a dedicated Docker network. The default stack and the existing `kdc` remain unchanged. FreeIPA publishes its HTTPS administration page on `127.0.0.1:8443`; LDAP, DNS, and Kerberos ports are not published to the host. Its canonical hostname is `ipa.lakehouse.local`, so add `127.0.0.1 ipa.lakehouse.local` to the host's `/etc/hosts` (or local DNS) and open `https://ipa.lakehouse.local:8443/ipa/ui/`. The readiness check adjusts FreeIPA's canonical redirects for the nonstandard published port. Do not connect production clients or assign the `kdc` network alias during this validation phase.

The local bootstrap creates protected FreeIPA admin/directory-manager credentials and an unattended installer-options file under ignored `.runtime/credentials/`. FreeIPA is built from the pinned AlmaLinux 9 FreeIPA 4.13.4 ARM64 image and applies `infra/freeipa/patch-ra-certificate-nss.py`. The patch uses Dogtag's JSS importer when NSS `pk12util` cannot import the generated CA-agent PKCS#12, then submits and retrieves the RA certificate through Dogtag's CLI using the key held in NSS. It validates the Dogtag TLS hostname and CA chain; revocation checking is skipped for this local bootstrap request because Dogtag's OCSP endpoint is not available during first install. Journaling is configured as volatile so installer process metadata is not persisted under `/data`. FreeIPA's current isolated state is in `iceberg-poc-freeipa-validation-data-nss-patched2`; earlier partial volumes are retained and untouched. The options file remains mounted read-only at `/run/secrets/freeipa-server-install-options`; the entrypoint symlinks it to the upstream image's `/data/ipa-server-install-options` path without copying the secret into persistent state.

Unit 1 isolated Build and Test is complete: identity and role bootstrap, scoped membership denials, service keytabs, LDAP TLS/Kerberos readiness, integrated DNS/external forwarding, persistence through recreation, volatile journaling, and a protected backup/isolated restore passed. The current host/Docker subnet preflight passed; repeat it if connecting a VPN with routes not present during this check. The active MIT KDC remains unchanged. JupyterHub authentication, Hive/RustFS authorization, and service-name resolution across the eventual shared client network remain later integration gates. Keep FreeIPA isolated and do not assign the active `kdc` network alias or cut over clients yet. Set `FREEIPA_DNS_FORWARDER` to a reachable resolver that answers root SOA queries; Docker DNS at `127.0.0.11` does not pass FreeIPA's forwarder validation.

Before starting, verify that the validation subnet is free on the host/VPN and select a non-overlapping subnet in `.env` if needed. The helper also checks it against existing Docker network subnets and refuses to start on overlap:

```bash
./scripts/bootstrap-local.sh
./scripts/freeipa-validation.sh start
./scripts/freeipa-validation.sh status
docker compose --profile freeipa-validation logs --tail=100 freeipa-validation
```

The readiness state requires a Kerberos ticket from the server host keytab and an LDAP-over-TLS query using the integrated CA. A first installation can take several minutes. The service image runs systemd internally. The isolated startup, DNS, certificate, Kerberos, and persistent-state checks passed. Stop the validation service without deleting its state with `./scripts/freeipa-validation.sh stop`.

After the first install is healthy, the public CA may be exported for later client configuration with `./scripts/export-freeipa-ca.sh`. The export is public certificate material; the helper refuses to replace a different existing CA file.

For isolated identity setup, first obtain an administrator ticket interactively in the validation container with `docker compose --profile freeipa-validation exec freeipa-validation kinit admin`, then run `./scripts/freeipa-validation.sh bootstrap-identities`. This creates the approved role groups, the `developer-user`, `analyst-user`, `write-service-account`, and `starrocks` identities, a dedicated `lakehouse-membership/ipa.lakehouse.local` service principal, and validation-only keytabs inside `/data/keytabs` in the named volume. The membership principal is distinct from FreeIPA's own `HTTP/ipa.lakehouse.local` server principal. Export only the intended files with `docker cp` when staging them for a later unit. It creates the built-in FreeIPA `admin` as part of installation; it does not create a second administrator. Human passwords are not generated here; Unit 4 owns account onboarding.

FreeIPA requires service principals to be associated with host identities. The validation setup therefore uses `HIVE_SERVICE_FQDN` (default `hive-metastore.lakehouse.local`) for an isolated Hive service principal. This does not change the active Hive configuration or MIT keytab; matching and installing the service identity is part of the later coordinated cutover. Never use `ipa-getkeytab` to overwrite an existing keytab as a routine retry: issuing a new key changes the principal's key and can invalidate other copies.

Routine group membership changes can be applied to the isolated FreeIPA authority with `./scripts/provision-identities.sh freeipa-membership USER GROUP add|remove`. Only the three `lakehouse-*` groups are accepted. The dedicated service principal is granted read/search access to membership and write access to the `member` attribute on those groups only, allowing it to verify the result. This command does not provision user accounts, alter service keytabs, or switch the active authority. The new human accounts have no password until the Unit 4 onboarding flow sets one.

Do not perform the MIT-to-FreeIPA authority cutover as part of validation. The active KDC, its database/keytabs, client mounts, RustFS S3 credentials, buckets, and data remain untouched. A cutover requires a separate preflight, matching protected backups, and a coordinated maintenance procedure; never run both independent KDC databases as authorities for `LAKEHOUSE.LOCAL`.

## Airflow and Jenkins

Airflow and Jenkins are included in the default Compose project. Before starting them, provision only their dedicated secret files and provide the deployment-specific host paths and Git Bundle configuration. This helper creates missing files only, uses secure random values, sets mode `0600`, refuses to rotate or repair existing files, and does not print their contents:

```bash
./scripts/provision-airflow-secrets.sh
mkdir -p .runtime/airflow-dag-bundles
```

Set these non-secret variables in the shell or ignored `.env` file before Compose starts:

| Variable | Required value |
|---|---|
| `LAKEHOUSE_PROJECT_ROOT` | Absolute path to this project on the Docker host |
| `LAKEHOUSE_BUNDLE_HOST_ROOT` | `${LAKEHOUSE_PROJECT_ROOT}/.runtime/airflow-dag-bundles` |
| `LAKEHOUSE_BUNDLE_CONTAINER_ROOT` | Absolute path inside Airflow containers, for example `/opt/airflow-bundles` |
| `AIRFLOW_UID` | Numeric host user ID that owns the mode-`0600` Airflow secret files; containers use this UID with the Airflow image's writable root group |
| `DOCKER_GID` | Numeric group allowed to access the host Docker socket |
| `AIRFLOW_ADMIN_USERNAME` | Optional Airflow admin name; defaults to `admin` |
| `LAKEHOUSE_SPARK_IMAGE` | Spark image used for DAG runs; defaults to the local Kerberos-enabled image built by Compose |
| `LAKEHOUSE_SPARK_DOCKER_NETWORK` | Docker network for Spark run containers; defaults to `iceberg-poc-net` |

Compose preserves the sibling project's two-entry Bundle list: `lakehouse-main` tracks `main`, and `lakehouse-uat` tracks `uat`, both from `https://github.com/cdiogo1979/opensource-lakehouse.git`, with `git_conn_id=lakehouse_git`, a 300-second refresh, and sparse directories `dags`, `configs`, and `notebooks`. Create/configure the `lakehouse_git` Airflow connection as required by your Git access. The Bundle list contains no separate `lakehouse-prod` entry: `lakehouse-main` creates the production DAGs, with the `main-` DAG ID prefix. UAT and production DAGs should appear in Airflow, while their workload configurations remain disabled and fail closed before Spark containers are created.

Set the initial values from the project directory as follows:

```bash
export LAKEHOUSE_PROJECT_ROOT="$(pwd -P)"
export LAKEHOUSE_BUNDLE_HOST_ROOT="${LAKEHOUSE_PROJECT_ROOT}/.runtime/airflow-dag-bundles"
export LAKEHOUSE_BUNDLE_CONTAINER_ROOT="/opt/airflow-bundles"
export AIRFLOW_UID="$(id -u)"
export DOCKER_GID="$(stat -f '%g' /var/run/docker.sock)"  # macOS initial value
```

Docker Desktop may expose the mounted socket inside Linux containers with a different numeric group ID than macOS reports. After the first startup, check the container-visible value with `docker compose exec -T airflow-scheduler stat -c '%g' /var/run/docker.sock`. If it differs from `DOCKER_GID`, export the container-visible value and recreate the scheduler with `docker compose up -d --no-deps airflow-scheduler`. On Linux, set `DOCKER_GID` to `stat -c '%g' /var/run/docker.sock` on the host.

Start the integrated control plane after setting the variables and running the helper:

```bash
docker compose up -d --build airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer jenkins
docker compose ps airflow-postgres airflow-init airflow-api-server airflow-scheduler airflow-dag-processor airflow-triggerer jenkins
./scripts/verify-airflow-environment-dags.sh
```

The verification waits up to five minutes for Airflow to register both `main-init_environment` from `lakehouse-main` (production) and `uat-init_environment` from `lakehouse-uat`. It fails if either bundle is missing, has import errors that prevent DAG creation, or does not register the expected DAG. It only checks DAG registration; it does not run either DAG or enable UAT/production workload execution.

### Jenkins CI service

Compose builds a local Jenkins image from `infra/jenkins/Dockerfile`, using the pinned Jenkins LTS JDK 21 image plus Python 3.10, Bash, and Git. Start or rebuild Jenkins with:

```bash
docker compose up -d --build jenkins
```

Jenkins runs the pipeline defined by the connected source repository. The Airflow/Spark workload pipeline is maintained in `opensource-lakehouse/Jenkinsfile`; this repository does not define a separate Jenkins job or pipeline.

The Jenkins service retains the approved Docker socket mount. Code running on its built-in executor could use that socket to control the Docker host, so restrict pipeline sources and permissions to trusted maintainers and do not use this setup for arbitrary contributors or multi-tenant CI. Jenkins recommends isolating builds from the controller: <https://www.jenkins.io/doc/book/security/controller-isolation/>.

Compose starts the dedicated `airflow-postgres` and one-shot `airflow-init` dependencies. Airflow metadata is persisted separately in `iceberg-poc-airflow-postgres-data`; Jenkins state is in `iceberg-poc-jenkins-home`. These volumes are not shared with or used to reset Hive, RustFS, KDC, JupyterHub, or StarRocks state. The API health check probes `/api/v2/version`; consult `/api/v2/monitor/health` separately for component status.

Only the Airflow scheduler and Jenkins receive new Docker socket mounts. The existing JupyterHub socket mount remains. The scheduler receives a temporary path view containing non-secret Spark/Hive configuration and empty permission-matched credential placeholders so the existing DAG factory can validate Docker bind-mount paths. The real writer keytab and RustFS files are resolved by Docker Engine on the host and mounted directly into each Spark run container; their contents are not mounted into Airflow or Jenkins. The DAG processor and scheduler share a writable Bundle checkout root so the Git provider can fetch revisions; each Spark driver receives its pinned revision read-only. Automatic Bundle revision pruning is disabled; retained revisions may use disk until a race-safe active-run reference mechanism is implemented.

No Airflow/Jenkins image build or service startup has been performed during Code Generation. Runtime health, host path mapping, permissions, data persistence, socket behavior, Git access, and the Spark workflow remain Build and Test checks.

## Spark writer runtime

The `spark` service builds a local image from the pinned `tabulario/spark-iceberg:3.5.5_1.8.1` base digest and adds Debian `krb5-user` for `kinit` and `klist`. It starts the master, worker, history server, and existing notebook command only after the writer TGT is valid. In-network Spark drivers use `spark://spark:7077`.

The runtime uses the existing `.runtime/credentials/keytabs/write-service-account.keytab` (mounted read-only at `/run/credentials/write-service-account.keytab`) and the existing file-backed RustFS secrets (`rustfs-writer-access-key` and `rustfs-writer-secret-key`). Keep all three host files at mode `0600`. The entrypoint reads the RustFS secret files into a private `[default]` AWS credentials file under `/run/krb5`; only its path is passed to Spark. `/run/krb5` is a private 16 MiB tmpfs, so the ticket cache and generated credentials file are removed when the container stops. Do not copy credential values into `.env`, Spark configuration, notebook code, or logs.

Inspect startup and health without reading credential files:

```bash
docker compose ps spark
docker inspect --format '{{.State.Health.Status}}' iceberg-poc-spark
docker compose logs --tail=50 spark
```

Health is `healthy` only while the lifecycle state is `READY`, the writer TGT is valid, and the Spark master reports an alive worker. The supervisor reacquires tickets from the keytab starting 15 minutes before expiry. If it cannot reacquire by the two-minute guard, it marks the service unhealthy, gracefully decommissions the worker, and waits for current work to drain. After it obtains a fresh TGT and the old worker exits, it starts and verifies a replacement worker. Build and Test must verify this decommission and recovery behavior; the code and health check alone do not establish that in-flight jobs drain successfully.

## Provision identities

For a first-time setup, run this before `scripts/start.sh` to provision the Hive, workload, and StarRocks identities. The script starts or reuses the required KDC and Hive dependencies. It can also be rerun later to reconcile identities:

```bash
./scripts/provision-identities.sh
```

The local bootstrap creates `.runtime/credentials/rustfs-starrocks-secret-key` if it is absent, with mode `0600`; existing contents are preserved. The provisioner creates or verifies the Kerberos principal `starrocks@<realm>` and keytab `.runtime/credentials/keytabs/starrocks.keytab`, plus the existing Hive and workload identities. It provisions RustFS account `starrocks` with policy `lakehouse-starrocks`, scoped to `databaseA` and `databaseB` in the `lake` bucket. The StarRocks credential is distinct from the Spark writer and other platform identities.

Kerberos and RustFS provisioning are attempted independently once each. The command reports separate provider outcomes and returns failure if either provider fails. Successful provider resources remain in place; after correcting the reported cause, rerun `./scripts/provision-identities.sh` to reconcile idempotently. Existing credentials and principal keys are not implicitly rotated. Existing RustFS policy drift fails closed and requires manual reconciliation. On success, the existing Hive configuration render/restart step still runs.

The StarRocks RustFS secret is provided to the provisioner as a file-backed Compose secret. The keytab is written to the existing protected host keytabs directory. The future StarRocks runtime must consume these credential files read-only; its service and mount configuration are added in Unit 2.

## RustFS role reconciliation (Unit 2)

The approved role policy is versioned in `infra/identity-provisioner/rustfs-role-policy.json`. It maps FreeIPA groups to RustFS IAM groups for `lake`, `lake-dev`, and `lake-uat`. The one-shot reconciler has its own explicit entrypoint and mounts only test RustFS credentials, the FreeIPA query password, the public FreeIPA CA, the policy file, and test-scoped protected runtime state. It connects only to the internal `identity_test_net` and isolated FreeIPA validation network, never the normal lakehouse network. It does not run the aggregate Kerberos/PostgreSQL provisioner.

`./scripts/bootstrap-local.sh` creates missing developer and analyst deployment credentials under `.runtime/credentials/`, and separate RustFS/LDAP test credentials under `.runtime/identity-provisioning/test-credentials/`; existing values are preserved and never printed. Create the FreeIPA account `rustfs-reconciler` only in the isolated FreeIPA validation service. Obtain an administrator ticket interactively, then run:

```bash
docker compose --profile freeipa-validation exec -it freeipa-validation kinit admin
docker compose --profile freeipa-validation exec -it freeipa-validation bash /usr/local/sbin/freeipa-create-rustfs-reader
```

Enter the contents of `.runtime/identity-provisioning/test-credentials/freeipa-rustfs-reader-password` at the interactive password prompts. Do not add this account to any role group or grant it directory write permissions. The Build and Test stage must verify it can read the three role groups' `cn`/`member` attributes and user `uid`/`nsAccountLock` attributes over LDAP TLS, and cannot modify FreeIPA. Export the public CA with `./scripts/export-freeipa-ca.sh` after FreeIPA is healthy.

Code Generation does not start or run the reconciler. Do not invoke `identity-reconciler` against the existing `object-store` service. Build and Test must first provide an isolated RustFS target and verify API behavior, policy preservation, S3 allow/deny probes, cleanup, and protected snapshot restore. Live role reconciliation remains a later, separately approved operation.

## Run the TPCH workload

After identity provisioning, run the optional ETL:

```bash
LAKEHOUSE_ENVIRONMENT=prod TPCH_DATABASES=databaseA,databaseB ./scripts/run-tpch-workload.sh
```

Set `LAKEHOUSE_ENVIRONMENT` explicitly to `prod`, `dev`, or `uat`, and set `TPCH_DATABASES` to database names that are unique in the shared Hive Metastore. The workload generates scale-factor-1 input files under `.runtime/workload/tpch-data` and runs Spark as `write-service-account`. New databases use an explicit environment bucket location; existing production databases at their recognized current location are preserved, and location, schema, or row-count conflicts stop the run without relocating or replacing data. A redacted run manifest is written to `.runtime/workload/results/`.

## Start StarRocks

StarRocks is opt-in and does not start with the default platform stack. Provision its keytab and RustFS identity first with `./scripts/provision-identities.sh`, then start the FE and BE:

```bash
./scripts/start-starrocks.sh
docker compose --profile starrocks ps
docker compose --profile starrocks logs -f starrocks-fe starrocks-be
```

The startup wrapper builds only the local StarRocks runtime images, requires the existing KDC container to be healthy, checks both StarRocks volumes read-only, then starts FE followed by BE. It runs a new paired-state preflight on each invocation. A failed preflight container is preserved for inspection; a successful previous preflight is removed before the next check. After FE/BE start, it runs the secret-exposure canary against the current FE image/configuration, then registers and verifies the BE through the host SQL client, using the protected root password file when bootstrap has already secured root. The wrapper does not start/stop shared platform services or remove volumes.

The FE UI is at <http://127.0.0.1:8030>; the SQL endpoint is `127.0.0.1:9030`. Only these FE ports are published, and both bind to loopback. BE and coordination ports remain internal to `iceberg_net`.

`docker compose --profile starrocks ps` should show both FE and BE healthy. FE health uses its HTTP health endpoint because the root SQL account is password-protected after bootstrap. The project mounts minimal credential-free Hadoop/Hive Kerberos settings to enable SASL with the existing Hive service principal; it does not mount the full Hive configuration. Health indicates process/service readiness; catalog discovery and data access still require the Unit 3 canary/bootstrap and query checks.

Each node obtains a Kerberos ticket before starting and refreshes it hourly. Ticket caches live in separate memory-backed filesystems. Refresh failures emit a redacted status while the current ticket remains valid. Logs are available through Compose. Stop StarRocks without removing its state with:

```bash
docker compose --profile starrocks stop starrocks-be starrocks-fe
```

To restart after a stop, run `./scripts/start-starrocks.sh` again. It repeats the paired-state check before starting FE and BE in order.

FE metadata and BE storage use separate named volumes and survive stops/restarts. The preflight permits both volumes empty or recognized paired FE/BE state; one-sided, unreadable, or unknown contents fail closed. Inspect preserved preflight logs with `docker logs iceberg-poc-starrocks-preflight` and resolve the state manually before retrying. Do not delete or reset either volume as a routine recovery step.

Local verification on 2026-10-24, with cached images and existing paired state, reached FE healthy about 70 seconds after its container start and BE healthy about 56 seconds after its start (about 75 seconds from FE start until BE health). On 2026-10-25, a read-only TPC-H Q1 query against scale-factor-1 `databaseA.lineitem` completed as `user_b` in 3.1 seconds. One-second resource sampling observed FE at 855 MiB and BE at 486 MiB, with BE briefly reaching about 97% CPU. The query also passed with temporary limits of 2 CPUs and 2 GiB memory on each StarRocks node; treat these as the lowest tested limits for this one-query profile, not absolute minimums. The full stack was running on a Docker allocation of 6 CPUs and 15.6 GiB. Current FE/BE images are 2.79/3.82 GB and their volumes use 13.99/9.287 MB. Reserve at least 10 GB incremental Docker storage for StarRocks images and node state, excluding shared platform images and future warehouse growth. Host disk showed 217 GiB free, while Docker's own disk quota was not measured. Measure storage growth and the intended ETL/concurrency before reducing resources; lower limits have not been validated.

## Configure StarRocks SQL access and the Iceberg catalog

Install a MySQL-protocol-compatible `mysql` CLI on the host and ensure it is available on `PATH`. The scripts do not add a client package or service to Compose. Start StarRocks and complete the separate non-secret diagnostics canary before applying any RustFS or SQL-account credentials:

```bash
./scripts/verify-starrocks-sql-secret-safety.sh
./scripts/bootstrap-starrocks-sql.sh
```

The canary creates uniquely named disposable StarRocks user/catalog objects with non-secret marker values, scans FE output, configured FE log directories and query profile history, and removes only its own successfully created objects. It writes a pass marker under ignored `.runtime/state/` only after all inspections and cleanup succeed. The marker is tied to the current FE image, `fe.conf`, and dynamic FE logging configuration. If it cannot inspect a required surface, finds marker exposure, or cleanup fails, it exits without a pass marker. Do not clear FE logs or delete unrelated objects to make it pass. Resolve the cause or revisit the approved secret-handling requirement/design before proceeding.

Bootstrap refuses to send real credential-bearing SQL unless that marker matches the current FE image and configuration. It reads the StarRocks RustFS secret from `.runtime/credentials/rustfs-starrocks-secret-key` and preserves that file. Missing SQL password files are generated only when absent under `.runtime/credentials/` with mode `0600`; directory mode is `0700`. New files are `starrocks-root-password`, `starrocks-admin-password`, `starrocks-user-a-password`, `starrocks-user-b-password`, and `starrocks-writer-password`. Existing file contents are never rotated or overwritten. The MySQL client receives SQL on stdin; its authentication option file is private and temporary, and client/server output is suppressed except for redacted status.

The workflow uses an owner-only lock at `.runtime/state/starrocks-sql.lock`. If a run is active, it exits without mutation. If the lock remains after an interrupted process, confirm no workflow is running, then remove that lock manually before retrying. The scripts may clean only their own private temporary client-input files after lock acquisition. They do not retry automatically or roll back completed additive changes.

The registered StarRocks catalog name is `iceberg`, backed by Hive Metastore `hive-metastore:9083` and RustFS `http://object-store:9000`. The SQL access matrix is:

| StarRocks SQL identity | `databaseA` | `databaseB` | Administration |
|---|---|---|---|
| `user_a` | Read | Denied | None |
| `user_b` | Read | Read | None |
| `write_service_account` | Read and DML on existing tables | Read and DML on existing tables | None |
| `admin` | Full access | Full access | Full StarRocks administration |

The bootstrap checks existing state before applying grants. Credential drift, unrecognized/broader privileges, or conflicting catalog state stops with a redacted error and preserves existing state. A bootstrap success is not a substitute for Build and Test: query/write compatibility, least-privilege allow/deny behavior, and actual log-history exposure still require integrated verification.

## JupyterHub

JupyterHub is available at <http://127.0.0.1:8008> and uses DummyAuthenticator for this development PoC. Usernames are labels, not verified human identities. Each user server runs in an isolated non-root container with its own persistent workspace and matching Kerberos/RustFS identity files. Keep the Hub bound to localhost.

Open the read-only example `/opt/jupyter-examples/spark-authz.py` from the notebook file browser to query the Hive catalog. The Hub and single-user images are built by `scripts/start.sh`.

## Stop and local state cleanup

Stop containers while preserving named volumes and local credentials:

```bash
./scripts/stop.sh
```

During migration from an existing installation, run `scripts/clean.sh` while the KDC is running, before `scripts/stop.sh`. It removes only leftover Dremio-specific local runtime state, requires typing `REMOVE DREMIO STATE`, and verifies the Compose project/container/volume before removal. It does not reset Hive metadata, the KDC database, RustFS objects, TPCH data/results, or notebook workspaces. It is not a general stack reset command.

## Scope

## Airflow Git Bundle workload source

Airflow DAG Bundle source is maintained in the separate `opensource-lakehouse` repository. Compose configures `lakehouse-main` and `lakehouse-uat` Git Bundles to fetch `dags/`, `configs/`, and `notebooks/` from that repository; those directories are not duplicated in this project. The main bundle supplies production DAGs with `main-` IDs; the UAT bundle supplies UAT DAGs with `uat-` IDs. Verify both DAGs are registered with `./scripts/verify-airflow-environment-dags.sh` after starting the Airflow control plane.

Each admitted DAG run uses its exact Bundle revision in a read-only driver mount and creates one ephemeral driver plus one worker-only Spark container attached to `iceberg-poc-net`. Airflow limits this workflow to two active runs and waits up to five minutes for a private writer TGT in each container, driver/master connectivity, and worker registration before submission. Cleanup removes only the run pair, requests Spark worker decommission, and observes worker occupancy for at most 60 seconds. Spark Standalone may place executors on any registered worker; a forced removal after a drain timeout can affect another run. Integrated Build and Test must verify this lifecycle and the three-catalog access matrix.

This repository is a local proof of concept, not a production authentication or deployment design.
