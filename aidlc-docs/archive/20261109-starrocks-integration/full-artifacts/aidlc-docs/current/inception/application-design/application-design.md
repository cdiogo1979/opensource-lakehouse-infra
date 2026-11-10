# Application Design — StarRocks Integration (consolidated)

See `components.md`, `component-methods.md`, `services.md`, and `component-dependency.md` for detail. This file consolidates the decisions and the runtime topology.

## Decisions
| Ref | Decision |
|---|---|
| Q1/AD-Q2 | Upstream `starrocks/fe-ubuntu:4.1.7@sha256:f6dd1491f0dd9bdcaeb29fac53c49727b20603d708530f0e5156cfd501425462` and `starrocks/be-ubuntu:4.1.7@sha256:39f7320127c9924abb1f1ce0ba0583ab11989cbe5bd1bb6274ada6f89ba5740d` (multi-arch index digests, arm64 included). No custom build. Config is mounted read-only. |
| Q3/AD-Q1 | The catalogs use `iceberg.catalog.security=oauth2` as `srv-starrocks`, with `oauth2.server-uri` set to the Keycloak token endpoint and `oauth2.scope=openid` (Keycloak rejects Iceberg's default scope `catalog`; to confirm). Token refresh is on and vended credentials are on. JWT pass-through is not used because its tokens cannot be renewed (MV refresh). |
| Q2/C1/C3 | Users are JWT-authenticated StarRocks users, one per Keycloak user in a product group, checked for issuer `http://keycloak.localhost:8080/realms/lakehouse`, audience `starrocks`, principal field `preferred_username`, and JWKS `http://keycloak:8080/realms/lakehouse/protocol/openid-connect/certs`. Login is through `starrocks-login.sh` and a MySQL 9.x client. |
| Q5/Q6 | Five roles named after the groups with underscores, using the Polaris matrix. `role_platform_admin` adds the built-in `user_admin`, `db_admin`, and `cluster_admin`. |
| Q7 | Internal MV databases `default_lh`, `default_lhuat`, `default_lhdev`. |
| Q8/C4 | Part of core start through the separate file. `STARROCKS_ENABLED=false` opts out. Core start does runtime setup only (root password, BE registration). Catalogs, roles, and users come from the product bootstrap. |
| AD-Q3 | `bootstrap-starrocks.py` and `reconcile-starrocks-users.py`, with pure planners and pluggable SQL transports. |
| AD-Q4, follow-up 1 | Reconcile runs in the bootstrap, on demand, and on a schedule in the extended `polaris-group-reconciler` (MySQL client added; skipped when StarRocks is disabled). |

## Runtime topology (`docker-compose.starrocks.yml`)
| Service | Image | Ports (loopback) | Networks | Volumes | Limits (`.env`) |
|---|---|---|---|---|---|
| `starrocks-fe` | fe-ubuntu 4.1.7 (digest) | `${STARROCKS_QUERY_PORT:-9030}` to 9030, `${STARROCKS_HTTP_PORT:-8030}` to 8030 | `core`, `data-access`, `starrocks` | `starrocks-fe-meta` | `STARROCKS_FE_MEMORY_LIMIT` (default 2g) |
| `starrocks-be` | be-ubuntu 4.1.7 (digest) | none | `data-access`, `starrocks` | `starrocks-be-storage` | `STARROCKS_BE_MEMORY_LIMIT` (default 4g) |

- **Networks**: the `core` and `data-access` networks are referenced from the core file. `starrocks` is internal to this file.
- **Health**: FE `/api/health`, and BE through the FE backend status. The bootstrap waits until the BE is alive.
- **Secrets**: not in Compose or the environment. The root password and the `srv-starrocks` secret are read from `.runtime/credentials` by the host bootstrap. The secret is embedded in the catalog definition inside StarRocks metadata, which is in the reset scope.

## Risks to verify in Build and Test
1. The MySQL 9.x community client ships the `authentication_openid_connect_client` plugin. Fallback: a documented alternative client or a JWT-capable JDBC driver.
2. StarRocks accepts hyphenated usernames such as `joe-developer` for JWT users. Fallback: a documented name mapping.
3. Keycloak accepts `scope=openid` for client credentials, and Polaris accepts the `srv-starrocks` token, including its principal roles.
4. Vended credentials carry the RustFS endpoint and path-style settings. If not, the catalog sets `aws.s3.endpoint=http://rustfs:9000` and `aws.s3.enable_path_style_access=true` without keys.
5. Asynchronous MV refresh over an Iceberg source works under the writer-level catalog identity.
6. FE and BE fit within the default memory limits on the laptop.

## Build and Test outcomes (2026-11-09)
- **Risk 1, MySQL client plugin**: resolved. `mysql:9.7.2` ships `authentication_openid_connect_client`. It refuses plaintext, so TLS was added (C12, approved by the user).
- **Risk 2, hyphenated usernames**: resolved. `joe-developer` and the other users log in.
- **Risk 3, Keycloak and Polaris**: resolved.
  - `scope=openid` works.
  - Polaris resolves `service-account-srv-starrocks` with `role-default-writer`.
  - Polaris needed `NAMESPACE_READ_PROPERTIES` in its read set (approved).
- **Risk 4, vended credentials**: resolved. All three smoke tables are read through the catalogs.
- **Risk 5, MV refresh**: resolved. Synchronous and scheduled refreshes succeed under the writer.
- **Risk 6, memory**: resolved. FE uses about 0.8 of 2 GiB and BE about 0.45 of 4 GiB.
- **SQL forms on 4.1.7**:
  - `SHOW BACKENDS` reports the host in `IP`.
  - The roles, grants, catalogs, and JWT users SQL is accepted as written.
- **Limitation, accepted**: owner and platform-admin `DROP TABLE` through StarRocks is refused by Polaris (writer-level catalog identity).
