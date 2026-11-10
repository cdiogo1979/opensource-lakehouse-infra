# Application Design — Keycloak, Polaris, and RustFS Bootstrap

## Purpose

This project provides a local Docker Compose platform-admin journey that bootstraps an initial `default` lakehouse data product without migrating legacy Hive or FreeIPA state. The journey provisions identity groups, storage buckets, Polaris catalogs and namespaces, authorization grants, and Spark smoke tables across production, dev, and UAT.

## Components

- **Keycloak** provides the `lakehouse` OIDC realm, the product role groups, the initial `platform-admin` identity, and the `write-service-account` client.
- **Apache Polaris** provides Iceberg REST and management APIs, catalogs, namespaces, principal roles, grants, and scoped RustFS credential vending.
- **PostgreSQL** stores Keycloak and Polaris state in separate databases and named volumes.
- **RustFS** provides the three S3-compatible environment buckets. Bootstrap creates missing resources and preserves existing objects.
- **Host scripts** prepare protected credentials, start/check/stop local services, and run the idempotent data-product bootstrap.
- **Spark** runs on-demand Iceberg workloads using the writer OAuth identity and Polaris-vended S3 credentials.

Airflow is supported for production and UAT workload execution through the v2 Compose control plane. JupyterHub remains a separately supported interactive service with user-bound Spark authentication. Jenkins and StarRocks remain deferred. FreeIPA, Hive Metastore, and MIT Kerberos are retired from the target default runtime.

## Airflow and shared Spark runtime

The Airflow control plane and writer token broker run in the v2 Compose boundary. For each DAG run, Airflow resolves the selected Git Bundle revision, registers run-scoped broker state, and creates an ephemeral Spark container with the bundle mounted read-only. The writer client secret remains in the broker/Airflow boundary; Spark receives an initial access token and run-scoped renewal capability, never the secret.

The shared runtime uses Spark 3.5.5, Java 17, and Iceberg 1.10.2. Its JVM `AuthManager` renews access tokens through identity-specific adapters: Airflow uses the run-scoped writer broker, while Jupyter Spark uses the authenticated user's Hub broker. These identities and capabilities are not interchangeable. Polaris remains the authorization and scoped RustFS credential vending point; no RustFS root credential is handed to Spark.

The active Airflow contract preserves exactly two Git Bundles: `lakehouse-main` tracking `main` and `lakehouse-uat` tracking `uat`. The writer client has a one-hour access-token lifetime override; human JupyterHub token lifetimes remain unchanged.

## Resource and role model

| Environment | Catalog | Namespace | Bucket |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` |
| Dev | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` |

Each catalog's default base location is `<bucket>/<catalog>/`; its database namespace contributes the next path segment. Iceberg tables therefore resolve beneath `<bucket>/<catalog>/<database>/<table>` exactly once. For example, the production smoke table is `s3://bucket-default/lakehouse/default_lh/bootstrap_smoke_test/`.

`role-default-developer` can read all environments and write dev. `role-default-analyst` can read production and cannot write. `role-default-owner` can manage product authorization and data across all environments. `role-default-writer` is the service role for read/write across all environments. Polaris enforces catalog operations; RustFS policies and vended credentials constrain object storage access.

## Startup and bootstrap

The local runtime starts Keycloak, its PostgreSQL database, Polaris, its PostgreSQL database, and RustFS. `scripts/lakehouse.sh start` creates only missing protected runtime credentials, runs the required Polaris schema initialization, and waits for health. `scripts/bootstrap-default-product.sh` explicitly provisions provider resources and grants, reconciles memberships, verifies writer authentication, and runs Spark smoke-table create/write/read checks. Reruns preserve bucket objects and do not duplicate smoke rows. `scripts/lakehouse.sh stop` preserves named volumes.

All published host endpoints bind to loopback. Protected credentials remain under `.runtime/credentials/` and must be backed up separately using encrypted storage. No secrets belong in source control, reports, or command output.

## Verification status and known limits

U1 runtime readiness, U2 writer and negative-token checks, U3 RustFS bucket/STS checks, and U4 end-to-end bootstrap and four-role positive/negative Spark access matrix passed on the local `linux/arm64` Docker engine. For the Airflow writer-token intent, builds, static checks, and automated suites passed; the designated main E2E run passed. The user subsequently reported building the shared image and successful main and UAT DAG runs. Those later run IDs/revisions were not independently retrievable in that session and are recorded as user-confirmed. During a Keycloak outage, new token issuance and group reconciliation fail while already-issued unexpired access tokens may continue until expiry.

The prior bootstrap intent's closure was user-approved with a verification waiver. For that intent, the human PKCE callback browser flow and some reconciliation failure-path diagnostics were not tested. The reconciler currently uses a protected Keycloak bootstrap administrator, which must be replaced by a least-privilege identity before shared deployment. The approved Polaris `require-header=false` setting was specific to the single configured realm and earlier Iceberg 1.8.1 behavior; reassess strict realm-header enforcement before adding realms. For the Airflow intent, concurrent workload, resilience, and live role-matrix checks remain unverified and outside the approved verification boundary. This local single-node setup is not a production, HA, or multi-host certification.

## Operational entry points

See `README.md` for operator commands, the guarded one-time local storage reset, backup guidance, and shutdown boundaries. Detailed intent designs and test reports are preserved in the intent archive.
