# Deploy Handoff — JupyterHub and Polaris User Access

## Handoff status

This handoff describes the verified local Docker Compose proof-of-concept. The user accepted the documented Build and Test limitations on 2026-10-29. No production deployment, public exposure, commit, or release is authorized by this handoff.

The primary journey is complete: a developer authenticates through Keycloak, starts an isolated JupyterHub server, creates a Spark session, reads production/UAT/dev smoke tables, writes only to dev, and is denied writes to production and UAT. Analyst production-only read access was also verified. The user reports completing GUI browser verification.

## Components and access URLs

| Service | Local URL / use |
|---|---|
| JupyterHub | `http://jupyterhub.localhost:8000` |
| Keycloak | `http://127.0.0.1:8080` |
| Polaris REST | `http://127.0.0.1:8181` |
| RustFS S3 API | `http://127.0.0.1:9000` |
| RustFS console | `http://127.0.0.1:9001` |

Published service ports bind to host loopback. This profile uses HTTP for browser login and is for local development only; do not expose it to a network. The broker uses internal HTTPS between JupyterHub and user containers. Polaris management port 8182 is not published.

## Start and bootstrap

Requirements: Docker Engine, Docker Compose V2, and Python 3. From the project root:

```sh
cp .env.example .env  # only on first setup; preserve an existing .env
scripts/bootstrap-default-product.sh
./scripts/lakehouse.sh status
```

The bootstrap prepares protected runtime credentials and certificates, starts the providers and JupyterHub, applies the Keycloak realm and Polaris product configuration, creates missing buckets/catalogs/namespaces/authorization, reconciles group membership, verifies writer authentication, and creates or verifies smoke tables. It is additive and intended to be safe to rerun; it does not clear existing bucket contents.

The layout is `<bucket>/<catalog>/<database>/<table>`:

| Environment | Polaris catalog | Database namespace | RustFS bucket |
|---|---|---|---|
| Production | `lakehouse` | `default_lh` | `bucket-default` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` |
| Development | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` |

The bootstrap includes a scheduled Keycloak group reconciler that runs immediately and every five minutes. For an immediate membership sync, run:

```sh
python3 infra/polaris/reconcile-keycloak-groups.py
```

## User onboarding and access

Create or manage human users in the `lakehouse` Keycloak realm. Add each user to the appropriate product group:

| Group | JupyterHub admission | Data access |
|---|---|---|
| `role-default-developer` | Allowed | Read all three environments; write to dev only |
| `role-default-analyst` | Allowed | Read production only; no writes |
| `role-default-owner` | Not admitted by group alone | Product-owner permissions in Polaris |
| `role-default-writer` | Not admitted by group alone | Writer service/product permissions in Polaris |

Membership changes are reconciled within five minutes. Run the immediate sync command above if access is needed sooner. Start a new Jupyter server after changing admission; a running server is not stopped automatically when membership is revoked.

At first login, users authenticate at the JupyterHub URL with their Keycloak credentials. In a notebook, start a user-bound Spark session with:

```python
from lakehouse_spark import create_spark_session

spark = create_spark_session()
```

Polaris receives that user's Keycloak access JWT. Polaris separately vends temporary RustFS credentials scoped to the authorized table location. Do not pass RustFS administrator keys, Polaris bootstrap credentials, Keycloak client secrets, or the JupyterHub broker key into notebooks or user containers.

## Credential lifetime behavior

- Polaris-vended RustFS storage credentials are configured for **one hour**, with a **10-minute cache**. Live checks confirmed approximately one hour remaining in all three catalogs and read-only access within each smoke-table location.
- The Keycloak user access JWT remains **five minutes**. Extending the Polaris storage credential TTL does not extend the user's JWT. After the JWT expires, Polaris operations and credential refresh fail closed; start a new Spark session to obtain a fresh user token.
- A strict five-second end-to-end STS deadline is not enforced or proven. Three observed requests were below five seconds but are too small a sample to establish a latency percentile or hard bound.

## Routine operations

```sh
./scripts/lakehouse.sh status
./scripts/lakehouse.sh stop
./scripts/lakehouse.sh start
```

`stop` removes only project Jupyter user-server containers and stops the services. It preserves database/RustFS volumes, Hub state, and per-user home volumes. Logs can be inspected with `docker compose logs --tail=200 jupyterhub keycloak polaris rustfs`; redact before sharing and do not publish tokens or secret-bearing configuration.

Before manual backup/restore, stop the owning services. Back up named volumes `lakehouse-local_keycloak-db-data`, `lakehouse-local_polaris-db-data`, and `lakehouse-local_rustfs-data` using Docker volume backup procedures. Back up `.runtime/credentials/` separately with encrypted storage. Keep `.env` and `.runtime/` private.

## Limitations accepted at test completion

These are limitations, not passing test results:

- Direct credential tests covered read access within each smoke-table scope and denial of a production credential against an existing dev object. Other S3 operations (listing, writes, deletes, multipart) and broader resource cases were not individually tested.
- Automatic renewal of the Keycloak user JWT inside an existing Spark session is not implemented.
- No strict five-second end-to-end STS deadline or p95 claim is established.
- Concurrent Spark workload/performance testing was deferred. Resiliency validation is deferred and has no scheduled date.
- Full transitive dependency locking and vulnerability scanning remain follow-up work.
- Polaris currently defaults to its configured `lakehouse` realm because `polaris.realm-context.require-header=false` works around Iceberg 1.8.1 dropping the realm header during credential refresh. Do not add another Polaris realm without correcting client behavior and restoring strict realm-header enforcement.
- The group reconciler currently reads the protected local Keycloak bootstrap administrator credential. Replace this with a narrowly scoped reader identity before shared or production use.

See the [Build and Test summary](../construction/build-and-test/build-and-test-summary.md) for evidence and per-unit details.

## Rollback and recovery

For a routine service rollback, stop the stack with `./scripts/lakehouse.sh stop`; this preserves persistent data. Restore a previously reviewed project version/configuration and use `./scripts/lakehouse.sh start` to recreate service containers. Reconcile Keycloak group memberships with Polaris after identity or group changes.

Do not use `docker compose down -v`, delete named volumes, clear RustFS buckets, or run `infra/polaris/reset-default-product-once.py` as routine rollback. Those actions destroy persistent state. The one-time reset was used during the earlier catalog path correction and is not part of normal bootstrap. Data restoration requires a separately verified backup.

## Handoff boundary

This document records the local operating path and test evidence. It does not publish the service, change host/network exposure, rotate credentials, create permanent users, or perform a production rollout.
