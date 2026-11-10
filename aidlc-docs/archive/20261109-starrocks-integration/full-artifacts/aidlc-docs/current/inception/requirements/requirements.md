# Requirements — StarRocks Integration

## Intent Analysis
- **User request**: "lets start a new aidlc to finally integrate starrocks. Starrocks should also be in a separate compose file . the initalization file that initailzes the buckets and databases should also create the catalog on iceberg. also the roles for the different databases should be aligned"
- **Request type**: new capability (interactive SQL engine) integrated with existing identity, catalog, and storage.
- **Scope**: multiple components: a new StarRocks service set; Keycloak clients and users; Polaris principals; the product bootstrap; `lakehouse.sh`; the reset; the README; tests.
- **Complexity**: high. A new engine, a new authentication method, and cross-service role alignment.
- **Depth**: standard. Answers are in `requirement-verification-questions.md` (Q1–Q11) and `requirement-clarification-questions.md` (C1–C4).

## Functional Requirements

### FR-1 Separate Compose file (Q1: A)
- StarRocks runs from its own file, `docker-compose.starrocks.yml`, in Compose project `lakehouse-local`.
- One FE and one BE (shared-nothing), from the latest stable StarRocks 4.x upstream images, pinned by digest. The image must run on `linux/arm64`. The exact version is confirmed in design.
- Host ports bind to loopback only: the MySQL protocol, default 9030, and the FE HTTP port. They are configurable in `.env.example`.
- FE metadata and BE storage use named volumes.

### FR-2 Lifecycle (Q8: C, C4: A)
- `scripts/lakehouse.sh start`, `status`, and `stop` include StarRocks through the separate Compose file, unless `.env` sets `STARROCKS_ENABLED=false`.
- The StarRocks `root` password is generated once into `.runtime/credentials/` and never printed. It is the break-glass admin.
- `scripts/lakehouse.sh reset` also deletes the StarRocks containers, volumes, and networks.
- The legacy `iceberg-poc-starrocks-*` volumes are not used or touched.

### FR-3 StarRocks identity toward Polaris (Q3: A, C2: A)
- A new confidential Keycloak client, `srv-starrocks`, has its service account enabled. That service-account user is a member of `role-default-writer`.
- Its secret is created once in `.runtime/credentials/` and kept out of Compose files, `docker inspect`, and output.
- Polaris sees it as principal `service-account-srv-starrocks`, with read and write on all three catalogs. The reconciler creates that principal.

### FR-4 Iceberg catalogs in StarRocks (request, Q4: A)
- The product bootstrap (`scripts/bootstrap-default-product.sh`) also creates three StarRocks external catalogs of type Iceberg REST on Polaris. Their names match the Polaris catalogs:

  | StarRocks catalog | Polaris warehouse | Namespace | Bucket |
  |---|---|---|---|
  | `lakehouse` | `lakehouse` | `default_lh` | `bucket-default` |
  | `lakehouse_uat` | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` |
  | `lakehouse_dev` | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` |

- Each catalog authenticates as `srv-starrocks` through OAuth2 client credentials.
- Each catalog uses Polaris-vended RustFS credentials. No RustFS root or static key goes to StarRocks.
- The step is idempotent. It creates missing catalogs, accepts equal ones, and refuses a conflicting existing catalog without printing secrets.
- When `STARROCKS_ENABLED=false`, the step is skipped with a notice.

### FR-5 Role alignment (Q5: A, Q6: A)
- StarRocks roles are named after the Keycloak groups, with underscores: `role_default_owner`, `role_default_developer`, `role_default_analyst`, `role_default_writer`, and `role_platform_admin`.
- They follow the same matrix as Polaris and RustFS:

  | Role | `lakehouse` (prod) | `lakehouse_uat` | `lakehouse_dev` |
  |---|---|---|---|
  | `role_default_owner` | manage | manage | manage |
  | `role_default_developer` | read | read | read/write |
  | `role_default_analyst` | read | — | — |
  | `role_default_writer` | read/write | read/write | read/write |
  | `role_platform_admin` | manage | manage | manage |

- `role_platform_admin` also gets StarRocks system administration: users, roles, catalogs, and cluster.
- **Change note (2026-11-09, Build and Test, accepted by the user)**: "manage" through StarRocks cannot drop Iceberg tables. Polaris refuses `TABLE_DROP` for the writer-level `srv-starrocks`. Owners drop tables through Spark or Polaris. `srv-starrocks` stays writer-level for least privilege.
- **Change note (2026-11-09, Build and Test, approved by the user)**: the Polaris read set gains `NAMESPACE_READ_PROPERTIES` for all reading roles, because StarRocks loads namespace metadata when it opens a database. This is the only change to Polaris authorization.
- No role gets more than its Polaris counterpart on the external catalogs. Polaris remains the final enforcer, through the writer-level `srv-starrocks` identity, which is broader. StarRocks RBAC narrows it per user.

### FR-6 Materialized-view databases (Q7: A)
- The bootstrap creates the internal databases `default_lh`, `default_lhuat`, and `default_lhdev` in StarRocks' `default_catalog`.
- Grants:

  | Role | Rights |
  |---|---|
  | writer | creates, alters, refreshes, and drops materialized views in all three |
  | developer | reads all three |
  | analyst | reads `default_lh` |
  | owner and platform admin | manage all three |

- Refresh of a writer's materialized views must keep working without the writer's session (the legacy finding). This is verified in Build and Test.

### FR-7 User login with Keycloak JWT (Q2: B, C1: A, C3: A)
- People log in to StarRocks with a Keycloak access token from the `lakehouse` realm, presented as the password. The token is checked for signature (JWKS), issuer, and audience.
- **Login client**: a new Keycloak client, `starrocks`, issues these tokens through the password grant, with an audience for StarRocks.
- **Users**: for every Keycloak user in a product group, the bootstrap creates a JWT-authenticated StarRocks user. That includes the five bootstrap users.
- **Grants**: each user gets exactly the StarRocks roles of their groups, set as default roles.
- **Reconcile**: a step run by the bootstrap and on demand adds missing users and grants, removes grants for removed memberships, and disables or drops StarRocks users that are no longer in a product group. It is modelled on the Polaris reconciler.
- **Helper**: `scripts/starrocks-login.sh <user>` asks for the Keycloak password, gets a token, and opens a MySQL session with it, without printing the token.
- **Service account**: `srv-starrocks` is not a SQL login.
- **Change note (2026-11-09, Build and Test, approved by the user)**: JWT login uses TLS on the StarRocks SQL port, because the MySQL OpenID Connect client plugin refuses to send a token in plaintext.
  - A local CA and FE certificate are created under `.runtime`.
  - The helper verifies the server identity.
  - Password logins such as root are not forced onto TLS.

### FR-8 Legacy retirement
- Retire the Kerberos, Hive, FreeIPA, and LDAP StarRocks assets. They are superseded and preserved in the intent archive at closure:
  - `infra/starrocks/kerberos`, `conf`, `ldap-access`, `sql-bootstrap`, `preflight`
  - `scripts/bootstrap-starrocks-sql.sh`
  - the FE/BE Dockerfiles, which are replaced
- `docker-compose.deferred.yml` marks StarRocks as implemented in its own file.
- No `write-service-account` reference remains under `infra/starrocks`.

### FR-9 README
- Document starting, stopping, and opting out of StarRocks.
- Document logging in with `starrocks-login.sh`, the catalogs and MV databases, the role matrix, the platform-admin rights, and reset coverage.

## Non-Functional Requirements
- **Secrets**: never printed or stored in Compose or images. Credential files use mode 0600.
- **Exposure**: published ports bind to loopback only. The stack is for local development only.
- **Idempotency**: all bootstraps and reconciles are idempotent and refuse conflicts.
- **Tests**:
  - contract tests for the Compose file, realm contract, catalog DDL, role matrix, and reset inventory
  - property-based tests (Q10: B, partial) for pure functions, such as role-to-grant generation and the user/grant reconcile plan, including round-trips where serialization is involved
- **Resources**: StarRocks must fit a laptop. FE and BE memory limits are configurable in `.env.example`.

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q9: B) |
| Property-Based Testing | Partial (pure functions and serialization round-trips) | Requirements Analysis (Q10: B) |
| Resiliency Baseline | No | Requirements Analysis (Q11: B) |

## Out of Scope
- StarRocks shared-data mode and multiple FE or BE nodes.
- Ranger or LDAP.
- Changing Polaris, RustFS, Airflow, or JupyterHub authorization.
- Migrating any legacy StarRocks data.

## Assumptions to confirm in design
1. The chosen 4.x version supports Iceberg REST catalogs with OAuth2 client credentials and Polaris-vended credentials.
2. It supports JWT authentication for users created with `IDENTIFIED WITH authentication_jwt`, with issuer, audience, and JWKS checks, and native RBAC grants for those users.
3. Users created that way do not need Ranger for authorization.
4. Upstream images exist for arm64.

If any assumption fails, design will present alternatives before code is generated.
