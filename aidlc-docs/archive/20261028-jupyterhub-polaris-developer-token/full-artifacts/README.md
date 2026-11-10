# Open Source Lakehouse Infrastructure

This project is being rebuilt around a fresh local platform-admin journey. The supported Unit 1 runtime is Keycloak, its PostgreSQL database, Apache Polaris with its own PostgreSQL database, and RustFS. FreeIPA, MIT Kerberos/KDC, and Hive Metastore are retired from the supported stack. No data migration is performed.

## Start the core providers

Requirements: Docker with Compose V2 and Python 3.

```sh
cp .env.example .env
./scripts/lakehouse.sh start
./scripts/lakehouse.sh status
```

Open the local endpoints:

- Keycloak: <http://127.0.0.1:8080>
- Polaris: <http://127.0.0.1:8181>
- RustFS S3 API: <http://127.0.0.1:9000>
- RustFS console: <http://127.0.0.1:9001>
- JupyterHub: <http://jupyterhub.localhost:8000>

The first Keycloak start creates the local `admin` bootstrap administrator from a protected runtime file. Unit 2 operator commands create the `lakehouse` realm and four product groups, bootstrap Polaris's internal operator principal, and apply the product authorization model after the three catalogs exist. These are explicit commands; provider startup does not apply realm, identity, grant, catalog, bucket, or table changes.

The operator command creates only missing provider credentials/configuration under `.runtime/credentials/`, with directory mode `0700` and file mode `0600`. It never prints credential values or replaces existing credentials. It merges only the tracked Keycloak hostname and Polaris OIDC properties into their protected configuration files, preserving unrelated settings such as database credentials. For non-root images, it refreshes read-only container mount copies under `.runtime/container-mounts/`; that directory is also `0700`, with mount files mode `0644` so the container service users can read them. The host-private parent directory protects these copies from other host users. Keep `.runtime/` private and backed up securely. Credential filenames are listed in `scripts/prepare-lakehouse-runtime.py`; names are not values.

The runtime uses a separate PostgreSQL volume for each provider and a new RustFS volume. It does not mount or delete any legacy volume or RustFS object. `stop` preserves all three new volumes:

```sh
./scripts/lakehouse.sh stop
```

Use `STARTUP_TIMEOUT_SECONDS` to change the default 600-second readiness deadline. Host port variables are listed in `.env.example`; all published endpoints bind to loopback. PostgreSQL and Polaris management endpoints are not published.

## Polaris metadata prerequisite

Before Polaris starts, the operator script invokes an idempotent one-shot step that creates only the `polaris_schema` PostgreSQL schema. Polaris 1.8.0 requires this schema before its later Admin Tool bootstrap. The schema step does not initialize a realm or catalog.

## Unit 2 identity and catalog authorization

The tracked Keycloak contract is in `infra/keycloak/realm-contract.json`. The idempotent realm bootstrap creates the four product groups, the writer service identity, and a dedicated `platform-admin` identity if absent. The generated one-time password is stored in `.runtime/credentials/platform-admin-password`; Keycloak requires changing it at first login. The account is assigned to the product-owner group and is not a realm administrator:

```sh
python3 infra/keycloak/bootstrap-realm.py
```

The human CLI client remains without a callback until the actual application callback is known. Configure it only when the consuming application supplies its exact local callback URI:

```sh
python3 infra/keycloak/bootstrap-realm.py \
  --owner-username YOUR_LAKEHOUSE_USERNAME \
  --redirect-uri 'http://localhost:PORT/EXACT/CALLBACK'
```

The Keycloak bootstrap administrator belongs to the separate `master` realm and does not automatically become a product owner. The `write-service-account` client is a separate client-credentials identity assigned only to the writer group.

Bootstrap Polaris's protected internal operator principal explicitly:

```sh
./scripts/bootstrap-polaris-realm.sh
```

The authorization commands do not create catalogs or object-storage resources. Before catalogs exist, create only the four Polaris product principal roles and reconcile current Keycloak group membership:

```sh
python3 infra/polaris/bootstrap-product-authorization.py --roles-only
python3 infra/polaris/reconcile-keycloak-groups.py
python3 scripts/verify-polaris-keycloak-auth.py
```

The verification command obtains a fresh writer token without printing it, confirms Polaris resolves the writer identity and denies a privileged management read with HTTP 403, then confirms a corrupted-signature token is rejected with HTTP 401.

## Unit 3 RustFS storage

The operator's protected RustFS bootstrap keys are mounted into Polaris for server-side STS calls. Human and Spark clients use Polaris OAuth and request Polaris-vended credentials; they never receive the root access key or secret. The RustFS STS implementation enforces a minimum 15-minute session duration.

Polaris's STS pool is bounded to eight HTTP connections, with one-second connection-acquisition and connect limits and a two-second read limit. These are per-stage limits; they do not guarantee a five-second end-to-end deadline. Polaris management is configured for container loopback and port 8182 is not published. To inspect readiness from inside the service, run `docker compose exec polaris curl --fail --silent http://127.0.0.1:8182/q/health/ready`. The pinned image's effective bind and credential settings still require runtime verification.

Create only missing buckets; existing buckets and their objects are preserved:

```sh
python3 infra/rustfs/bootstrap-buckets.py
python3 scripts/verify-rustfs-sts.py
```

The STS verification creates a unique object under a dev-only probe key, checks that the session can list/write in dev but cannot list/write production, and deletes only that exact probe object. U4 remains responsible for validating Polaris catalog configuration and Spark/Iceberg end-to-end credential vending.

After the catalogs `lakehouse`, `lakehouse_uat`, and `lakehouse_dev` exist, add the catalog-scoped roles/grants and reconcile again:

```sh
python3 infra/polaris/bootstrap-product-authorization.py
python3 infra/polaris/reconcile-keycloak-groups.py
```

The current reconciler uses the protected local Keycloak bootstrap administrator; replacing it with a narrowly scoped Keycloak reader identity remains a hardening item before shared or production use. Polaris keeps the canonical Keycloak issuer but fetches signing keys over the private `keycloak` Compose service DNS name because `.localhost` resolves to loopback inside containers.

## One-time catalog path reset

The catalog layout is `<bucket>/<catalog>/<database>/<table>`:

| Environment | Catalog | Database namespace | Bucket |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` |
| Development | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` |

For the one-time local reset only, install the pinned boto3 dependency, start the providers, prepare the identity and Polaris operator principal, ensure the three buckets exist, and run the guarded reset. This deletes every object (including object versions) in those three buckets and removes namespaces, table metadata, and catalog metadata only within the known old/new default-product catalogs. It does not delete buckets or named volumes. Review the target mappings before running:

```sh
python3 -m pip install -r infra/bucket-init/requirements.txt
./scripts/lakehouse.sh start
python3 infra/keycloak/bootstrap-realm.py
./scripts/bootstrap-polaris-realm.sh
python3 infra/rustfs/bootstrap-buckets.py
python3 infra/polaris/reset-default-product-once.py --confirm-reset-default-product
```

Then run the normal bootstrap below to recreate the catalogs, namespaces, authorization, and smoke tables. The reset script is separate and is never invoked by normal bootstrap.

The one-command operator path is:

```sh
scripts/bootstrap-default-product.sh
```

It starts the core stack, provisions the identity/catalog/storage resources and grants, reconciles group memberships, verifies writer authentication, then submits the Spark smoke-table job. The approved local single-realm configuration sets `polaris.realm-context.require-header=false` because Iceberg 1.8.1 drops the realm header during vended-credential refresh. This makes the configured `lakehouse` realm the default; restore strict header enforcement and use a client fix before adding another Polaris realm. Normal bootstrap is idempotent and safe to rerun; it preserves existing bucket contents.

The default-product bootstrap also starts `polaris-group-reconciler`, which synchronizes Keycloak product-group membership into Polaris immediately and every five minutes. Start it separately with `docker compose --profile scheduled-reconciliation up -d --build polaris-group-reconciler` if the default product was provisioned outside the one-command bootstrap. Set `POLARIS_GROUP_RECONCILE_INTERVAL_SECONDS` in `.env` to change the interval. A group change can take up to one interval to reach Polaris; run `python3 infra/polaris/reconcile-keycloak-groups.py` for immediate synchronization. The reconciler reads the protected Keycloak administrator password and Polaris bootstrap credentials read-only. Keep its Compose profile enabled only after those credentials have been provisioned.

## JupyterHub developer and analyst access

`./scripts/lakehouse.sh start` prepares protected Hub credentials, prepares/validates the broker CA and server certificate, checks the configured Docker subnet against local routes and networks, builds the pinned Hub and Spark-enabled single-user images, starts the providers, reconciles the confidential `jupyterhub` client and group claims in Keycloak, then starts JupyterHub. `./scripts/lakehouse.sh status` includes Hub health and the internal broker TLS readiness check. Hub is published only on loopback at `http://jupyterhub.localhost:8000`; Keycloak login uses the canonical `http://keycloak.localhost:8080/realms/lakehouse` issuer. This local profile uses HTTP for browser login and is not suitable for exposure beyond the local machine.

Only members of `role-default-developer` or `role-default-analyst` are admitted. Owner/writer-only membership does not allow Hub login. Group admission is refreshed before each server spawn. If access is removed while a server is already running, stop the server in JupyterHub or stop the service with `./scripts/lakehouse.sh stop`; revocation is enforced at the next admission check and is not instantaneous.

Each user receives one Spark-enabled Jupyter server, limited by default to 1 CPU and 2 GiB RAM, with a maximum of two active servers. Override `JUPYTERHUB_SINGLEUSER_CPU_LIMIT`, `JUPYTERHUB_SINGLEUSER_MEMORY_LIMIT`, and `JUPYTERHUB_HOST_PORT` in `.env` after reviewing host capacity. When the port changes, the startup command reconciles the exact Keycloak callback for that port. User servers join only `jupyter-user` and `data-access`; the Hub alone has Docker socket access and joins `core`. User homes are separate named volumes derived from the stable Keycloak subject and survive server stop/recreate. `scripts/lakehouse.sh stop` removes only containers carrying the project’s Jupyter user-server label before stopping services; it does not remove home or Hub state volumes. Permanent user-home deletion requires explicit operator review and removal of that exact named volume; do not use `docker compose down -v` for routine operation.

The token broker listens on `https://jupyterhub:8443` only on the configured `jupyter-user` address. Compose does not publish port 8443. The user container receives the public CA certificate read-only; the Hub server certificate/key are mounted read-only into Hub, and the CA signing key remains on the host. Subnet defaults are `172.30.240.0/24` and Hub address `172.30.240.2`; adjust `JUPYTER_USER_SUBNET` and `JUPYTERHUB_BROKER_BIND_IP` together in `.env` if the preflight reports a conflict. Start the stack through `scripts/lakehouse.sh` so the preflight runs before Compose creates IPAM.

To rotate broker trust deliberately, stop the stack (which removes running user-server containers but preserves named homes), run `python3 scripts/prepare-jupyterhub-broker-certificates.py --rotate`, then run `./scripts/lakehouse.sh start`. The new CA is trusted only after Hub and user servers are recreated. Routine startup validates existing certificates and preserves their identity. Do not copy or mount `jupyterhub-broker-ca-key.pem` into any container.

The protected runtime bootstrap creates `.runtime/credentials/jupyterhub-oidc-client-secret` and `.runtime/credentials/jupyterhub-auth-state-crypt-key` once and stages Hub-only read-only copies. Keep `.runtime/` private. To rotate the confidential client secret, update the Keycloak client and protected file as one coordinated operation, then restart Hub; do not regenerate the auth-state crypt key while Hub auth state must remain readable. The encrypted auth-state key protects OAuth state at rest, and neither it nor the OIDC client secret is mounted into user servers.

The first login requires an existing Keycloak user in one of the two approved groups. Confirm the client and group claim with `python3 infra/keycloak/bootstrap-realm.py`; it refuses client-secret or callback mismatches. To create a user-identity Spark session from a notebook, use `from lakehouse_spark import create_spark_session` followed by `spark = create_spark_session()`. The factory requests the bound user's current access JWT over verified HTTPS immediately before session creation, configures it only in that session's in-memory Iceberg catalog, and disables OAuth token refresh so an existing session never silently changes identity. It does not return the token to notebook code. Polaris can separately vend and refresh temporary S3 credentials through Iceberg's REST credential-refresh protocol; those temporary credentials do not refresh the user's Keycloak JWT. The current Keycloak access JWT lifetime is five minutes, so after it expires Polaris operations and a later S3 credential-refresh request fail closed. Start a fresh Spark session to obtain a new user token. No static or root RustFS credential is used as fallback. Polaris-vended RustFS credentials are configured for one hour with a 10-minute cache. Live checks verified the returned lifetime, read access within each smoke-table location, and denial of a production credential against a dev object. Other S3 operations and a strict five-second end-to-end latency bound remain unverified; the user accepted these limitations at Build and Test completion. See `aidlc-docs/current/construction/build-and-test/` and `aidlc-docs/current/deploy/deploy-handoff.md`.

Polaris also requires a principal record for each Keycloak username before that user's Spark queries can be authorized. After creating a user or changing product-group membership, reconcile the current Keycloak memberships before the user's first data query:

```sh
python3 infra/polaris/reconcile-keycloak-groups.py
```

This idempotent step creates missing Polaris principals and synchronizes their product principal-role assignments. JupyterHub checks Keycloak group admission when the user logs in and again before spawning a server; it does not create Polaris principals itself. The end-to-end test verified this sequence with a temporary developer and removed the temporary user and Polaris principal afterward.

## Deferred integrations

Airflow, Jenkins, and StarRocks remain deferred and unsupported pending migration. JupyterHub is implemented in the main Compose stack; `docker-compose.deferred.yml` retains only an inventory entry for it. The retired implementation directories `infra/freeipa`, `infra/hive`, and `infra/kerberos` were removed from this copy. Other legacy or deferred directories remain untouched and are not activated by the supported runtime.

## State and backup

Normal start, status, and stop commands preserve persistent state. Before manual backup or restore, stop the owning services and use Docker volume backup procedures for `lakehouse-local_keycloak-db-data`, `lakehouse-local_polaris-db-data`, and `lakehouse-local_rustfs-data`. Back up `.runtime/credentials/` separately using encrypted storage. Never use `docker compose down -v` unless you intend to destroy the corresponding state.

## Build and Test status

The previous Polaris catalog path correction passed Build and Test on the local Docker Compose stack. Bootstrap and Spark verified table locations as `<bucket>/<catalog>/<database>/<table>` for production, dev, and UAT. Temporary identities verified the developer, analyst, owner, and writer access matrix across all three environments, with probe rows and principals removed afterward. A second bootstrap run preserved an existing bucket object. The approved one-time reset emptied the three default-product buckets before recreating the catalogs and smoke tables. See the [previous Build and Test summary](aidlc-docs/archive/20261028-polaris-database-path-layout/full-artifacts/aidlc-docs/current/construction/build-and-test/build-and-test-summary.md) and archived deploy handoff for the data-loss boundary, operating sequence, evidence, and limitations.

The current JupyterHub intent has generated Units 1–4. Unit 1 passed its focused source tests and image builds; its accepted dependency-lock and live integration/performance/E2E gaps remain documented in `aidlc-docs/current/construction/build-and-test/unit-1-build-and-test-summary.md`. Unit 2 adds the in-process TLS token broker, per-user refresh coordination, certificate/subnet preparation, and Spark session handoff. Its 34 JupyterHub tests, 6 Keycloak contract tests, both image builds, Compose rendering, Python compilation, and shell syntax checks passed. Live integration and performance remain unverified; see `aidlc-docs/current/construction/build-and-test/unit-2-build-and-test-summary.md`.

Unit 3 passed 75 pytest cases plus 5 Hypothesis subtests, both images, Compose rendering, and static checks. The live developer/analyst/owner/writer role matrix passed across production, UAT, and dev; temporary test data and identities were cleaned up, and Polaris management-listener isolation was verified. Follow-up testing verified one-hour Polaris credentials, sampled RustFS table-prefix read scope and cross-environment denial, and fail-closed behavior after JWT expiry. Unit 4 passed 82 pytest cases, 5 Hypothesis subtests, both image builds, Compose validation, Python/Bash compilation, and Keycloak realm-contract JSON validation. The developer end-to-end journey, analyst authorization, server startup, and home persistence passed; the user reports GUI browser testing complete. The user considers Build and Test complete with the documented S3-operation, strict latency, JWT renewal, performance/concurrency, resiliency scheduling, and supply-chain limitations accepted. See `aidlc-docs/current/construction/build-and-test/build-and-test-summary.md` and the [Deploy Handoff](aidlc-docs/current/deploy/deploy-handoff.md).
