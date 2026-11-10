# Domain Entities — starrocks-integration

## Environment
| Env | External catalog (StarRocks = Polaris warehouse) | Iceberg namespace | Bucket | Internal MV database |
|---|---|---|---|---|
| prod | `lakehouse` | `default_lh` | `bucket-default` | `default_lh` |
| uat | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` | `default_lhuat` |
| dev | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` | `default_lhdev` |

## CatalogDefinition
A mapping of property name to value for one external catalog. Fixed keys:

| Key | Value |
|---|---|
| `type` | `iceberg` |
| `iceberg.catalog.type` | `rest` |
| `iceberg.catalog.uri` | `http://polaris:8181/api/catalog` |
| `iceberg.catalog.warehouse` | the catalog name |
| `iceberg.catalog.security` | `oauth2` |
| `iceberg.catalog.oauth2.server-uri` | `http://keycloak:8080/realms/lakehouse/protocol/openid-connect/token` |
| `iceberg.catalog.oauth2.scope` | `openid` |
| `iceberg.catalog.oauth2.token-refresh-enabled` | `true` |
| `iceberg.catalog.vended-credentials-enabled` | `true` |
| `aws.s3.endpoint` | `http://rustfs:9000` |
| `aws.s3.enable_path_style_access` | `true` |
| `aws.s3.region` | `us-east-1` |
| `iceberg.catalog.oauth2.credential` | `srv-starrocks:<secret>`. This is the secret; it is never compared, logged, or printed. |

## AccessLevel
`none`, `read`, `write`, `manage`. They are ordered: none < read < write < manage.

## ManagedRole
The five roles `role_default_owner`, `role_default_developer`, `role_default_analyst`, `role_default_writer`, and `role_platform_admin`. Each has one source group, `role-default-*` or `role-platform-admin`. Platform admin also maps to the built-in roles `user_admin`, `db_admin`, and `cluster_admin`.

## AccessMatrix
External catalogs: (ManagedRole, Environment) to AccessLevel.

| Role | prod | uat | dev |
|---|---|---|---|
| owner | manage | manage | manage |
| developer | read | read | write |
| analyst | read | none | none |
| writer | write | write | write |
| platform_admin | manage | manage | manage |

MV databases: (ManagedRole, Environment) to MvLevel (`none`, `read`, `author`, `manage`).

| Role | prod | uat | dev |
|---|---|---|---|
| owner, platform_admin | manage | manage | manage |
| writer | author | author | author |
| developer | read | read | read |
| analyst | read | none | none |

## Grant
A tuple: (role, privilege, object type, object name). The object type is one of `CATALOG`, `ALL DATABASES IN CATALOG`, `ALL TABLES IN ALL DATABASES OF CATALOG`, `DATABASE`, or `ALL MATERIALIZED VIEWS IN DATABASE`. It renders to exactly one GRANT or REVOKE statement.

## ManagedUser
A StarRocks user authenticated with `authentication_jwt`. Its name equals the Keycloak `preferred_username`. It has a set of granted roles and default roles. `root` and built-in users are never managed.

## Plans
- **GrantPlan**: grants to add and grants to revoke. Revokes apply only to managed roles.
- **UserPlan**: users to create, (user, role) pairs to grant, (user, role) pairs to revoke, users whose default roles must be reset, and users to drop.
- **CatalogPlan**: `create`, `equal`, or `conflict` per catalog.
