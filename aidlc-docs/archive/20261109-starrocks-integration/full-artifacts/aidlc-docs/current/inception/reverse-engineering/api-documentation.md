# API Documentation (integration surfaces)

## REST APIs
### Polaris Iceberg REST
- `GET /api/catalog/v1/config?warehouse=<catalog>`, plus namespace and table endpoints. Bearer JWT from Keycloak, or an internal token.
- Vended credentials are returned when the client asks for access delegation.

### Polaris management
- `/api/management/v1/principals`, `principal-roles`, `catalogs/{c}/catalog-roles`. Used by the bootstrap and reconciler with the internal root credential.

### Keycloak token
- `POST /realms/lakehouse/protocol/openid-connect/token`. Grants in use: password (`lakehouse-writer`) and authorization code (browser clients).

## Internal APIs
### StarRocks SQL (planned)
- MySQL protocol on FE port 9030, HTTP on FE port 8030.
- Catalog DDL: `CREATE EXTERNAL CATALOG ... PROPERTIES (...)`.
- RBAC: `CREATE ROLE`, `GRANT ... ON CATALOG/DATABASE/TABLE`, `GRANT role TO USER` or `TO EXTERNAL GROUP`.

## Data Models
### Environment mapping
| Env | Polaris catalog | Namespace | Bucket | Legacy StarRocks MV database |
|---|---|---|---|---|
| prod | `lakehouse` | `default_lh` | `bucket-default` | `default_lh` |
| UAT | `lakehouse_uat` | `default_lhuat` | `bucket-default-uat` | `default_lhuat` |
| dev | `lakehouse_dev` | `default_lhdev` | `bucket-default-dev` | `default_lhdev` |
