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

## Deferred integrations

Airflow, JupyterHub, Jenkins, and StarRocks are deferred and unsupported pending migration. `docker-compose.deferred.yml` records this boundary only; it is not a runnable overlay and is not used by `scripts/lakehouse.sh`. The retired implementation directories `infra/freeipa`, `infra/hive`, and `infra/kerberos` were removed from this copy. Other legacy or deferred directories remain untouched and are not activated by the supported runtime.

## State and backup

Normal start, status, and stop commands preserve persistent state. Before manual backup or restore, stop the owning services and use Docker volume backup procedures for `lakehouse-local_keycloak-db-data`, `lakehouse-local_polaris-db-data`, and `lakehouse-local_rustfs-data`. Back up `.runtime/credentials/` separately using encrypted storage. Never use `docker compose down -v` unless you intend to destroy the corresponding state.

## Build and Test status

The current Polaris catalog path correction passed Build and Test on the local Docker Compose stack. Bootstrap and Spark verified table locations as `<bucket>/<catalog>/<database>/<table>` for production, dev, and UAT. Temporary identities verified the developer, analyst, owner, and writer access matrix across all three environments, with probe rows and principals removed afterward. A second bootstrap run preserved an existing bucket object. The approved one-time reset emptied the three default-product buckets before recreating the catalogs and smoke tables. See the [current Build and Test summary](aidlc-docs/current/construction/build-and-test/build-and-test-summary.md) and [deploy handoff](aidlc-docs/current/deploy/deploy-handoff.md) for the data-loss boundary, operating sequence, evidence, and limitations. Earlier intent reports remain in the archive.

Unit 2 created the Polaris product roles and reconciled Keycloak group memberships. Unit 4 created the catalogs and grants and verified the four-role matrix. OIDC wrong-audience, expired-token, and Keycloak outage checks passed; the human PKCE callback and some reconciler failure-path diagnostics remain open under the accepted verification waiver. See the archived deploy handoff and unit reports for evidence and operating limits.
