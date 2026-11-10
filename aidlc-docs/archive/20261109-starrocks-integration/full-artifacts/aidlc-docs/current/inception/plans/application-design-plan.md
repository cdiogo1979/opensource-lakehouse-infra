# Application Design Plan — StarRocks Integration

## Technical verification of the requirement assumptions (2026-11-09)
| # | Assumption | Result | Evidence |
|---|---|---|---|
| 1 | Iceberg REST catalog with an OAuth2 service identity and vended credentials | Confirmed | StarRocks `branch-4.1` source, `IcebergRESTCatalog.java` and `OAuth2SecurityConfig.java`. Keys: `iceberg.catalog.security` = `oauth2`; `iceberg.catalog.oauth2.credential` (`client_id:secret`), `oauth2.server-uri`, `oauth2.scope`, `oauth2.audience`, `oauth2.token-refresh-enabled`. The FE can mint new tokens from the credential ("auth recovery"). `iceberg.catalog.vended-credentials-enabled` defaults to `true` and sends `X-Iceberg-Access-Delegation: vended-credentials`. |
| 2 | JWT user login | Confirmed (v3.5+) | StarRocks docs, JWT authentication: `CREATE USER <u> IDENTIFIED WITH authentication_jwt AS '{"jwks_url": ..., "principal_field": ..., "required_issuer": ..., "required_audience": ...}'`. Clients need MySQL 9.2+ with the `authentication_openid-connect_client` plugin and a token file. |
| 3 | Native RBAC for JWT users without Ranger | Likely; verify live | They are ordinary users created with `CREATE USER`. Confirm in Build and Test. |
| 4 | arm64 images | Confirmed | Docker Hub `starrocks/fe-ubuntu` and `starrocks/be-ubuntu` `4.1.7` (2026-10-26, latest stable) publish amd64 and arm64. |

**New option found**: `iceberg.catalog.security` = `jwt` forwards each logged-in user's token to Polaris. The source states that per-user JWTs cannot be renewed by the FE. Asynchronous MV refresh, which has no user session, and sessions longer than the token lifetime would fail against such a catalog.

## Plan
- [x] Answer the design questions below
- [x] Generate `application-design/components.md` with component definitions and high-level responsibilities
- [x] Generate `application-design/component-methods.md` with method signatures (business rules come later in Functional Design)
- [x] Generate `application-design/services.md` with service definitions and orchestration patterns
- [x] Generate `application-design/component-dependency.md` with dependency relationships and communication patterns
- [x] Generate the consolidated `application-design/application-design.md`, including the Compose and network topology, ports, volumes, resource limits, and the pinned 4.1.7 digests
- [x] Validate design completeness and consistency against FR-1..FR-9

## Questions

## Question 1 — Catalog security mode
How should the three StarRocks Iceberg catalogs authenticate to Polaris?

A) OAuth2 client credentials as `srv-starrocks` (writer-level), as chosen in Q3. StarRocks roles enforce per-user access. Tokens renew automatically, and MV refresh works (Recommended)

B) JWT pass-through: each user's own token goes to Polaris, which enforces per-user access. No `srv-starrocks` is needed, but MV refresh over these catalogs and sessions longer than the token lifetime fail

C) Both: per environment, one OAuth2 catalog (for writers and MVs) and one JWT catalog (for interactive users), with six catalogs in total

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2 — Images and configuration
How should FE and BE be packaged?

A) Use the upstream `starrocks/fe-ubuntu:4.1.7` and `be-ubuntu:4.1.7` images pinned by digest, with no custom build. Config is mounted read-only, and a small entrypoint injects the protected values. The legacy Dockerfiles are retired (Recommended)

B) Thin custom images built from the pinned upstream images, with config and entrypoint baked in

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3 — Bootstrap and reconciler structure
How should the StarRocks bootstrap code be organized?

A) One module, `infra/starrocks/bootstrap-starrocks.py`, for the root password, catalogs, roles and grants, and MV databases, plus a separate `infra/starrocks/reconcile-starrocks-users.py` for the user and role sync from Keycloak. Both run SQL through `docker exec` with the FE's bundled MySQL client over stdin, so no host MySQL client is needed. The pure planning functions are separated for tests (Recommended)

B) One combined script with subcommands (`catalogs`, `roles`, `users`, `all`)

C) Python with a MySQL driver (PyMySQL) running in a small bootstrap container on the StarRocks network

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4 — When the user and role reconcile runs
When should StarRocks users and grants be synchronized from Keycloak?

A) In `bootstrap-default-product.sh`, on demand (`scripts/lakehouse.sh reconcile-starrocks`), and on a schedule in the existing scheduled reconciler container, next to the Polaris group reconcile (Recommended)

B) In the bootstrap and on demand only, with no schedule

X) Other (please describe after [Answer]: tag below)

[Answer]: A


## Follow-up 1 — Scheduled reconcile transport (combines Q3: A and Q4: A)
The existing scheduled reconciler (`polaris-group-reconciler`, `python:3.12-alpine`, core Compose file, profile `scheduled-reconciliation`) has no Docker socket and no MySQL client, so it cannot use the `docker exec` channel from Q3. Placing the StarRocks sync there would also tie the core stack to the optional StarRocks file. How should the scheduled StarRocks sync run?

A) A separate small scheduled service, `starrocks-user-reconciler`, in `docker-compose.starrocks.yml`. It runs the same `reconcile-starrocks-users.py` with a network transport (a MySQL client in the image, the `root` password mounted read-only), while host runs keep `docker exec`. It starts only when StarRocks is enabled (Recommended)

B) Extend the existing `polaris-group-reconciler` image with a MySQL client, and skip StarRocks when it is disabled

C) No schedule after all; bootstrap and on-demand only

X) Other (please describe after [Answer]: tag below)

[Answer]: B
