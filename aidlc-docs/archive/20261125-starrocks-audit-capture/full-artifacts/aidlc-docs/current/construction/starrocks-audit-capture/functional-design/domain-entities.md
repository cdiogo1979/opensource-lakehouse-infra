# Domain Entities — StarRocks Audit Capture

## Staging table `starrocks_audit_db__.starrocks_audit_tbl__` (AC-1)
StarRocks 4.1 docs DDL plus `ScanStats`; written by AuditLoader 5.0.0 as `srv-auditloader`; read by product roles with `platform_sources.starrocks_audit: read`.

| Column | Type | Null |
|---|---|---|
| queryId | VARCHAR(64) | yes |
| timestamp | DATETIME | no |
| queryType | VARCHAR(12) | yes |
| clientIp | VARCHAR(32) | yes |
| user | VARCHAR(64) | yes |
| authorizedUser | VARCHAR(64) | yes |
| resourceGroup | VARCHAR(64) | yes |
| catalog | VARCHAR(32) | yes |
| db | VARCHAR(96) | yes |
| state | VARCHAR(8) | yes |
| errorCode | VARCHAR(512) | yes |
| errorMessage | VARCHAR(1048576) | yes |
| queryTime | BIGINT | yes |
| scanBytes | BIGINT | yes |
| scanRows | BIGINT | yes |
| returnRows | BIGINT | yes |
| cpuCostNs | BIGINT | yes |
| memCostBytes | BIGINT | yes |
| stmtId | INT | yes |
| isQuery | TINYINT | yes |
| feIp | VARCHAR(128) | yes |
| stmt | VARCHAR(1048576) | yes |
| digest | VARCHAR(32) | yes |
| planCpuCosts | DOUBLE | yes |
| planMemCosts | DOUBLE | yes |
| pendingTimeMs | BIGINT | yes |
| candidateMVs | VARCHAR(65533) | yes |
| hitMvs | VARCHAR(65533) | yes |
| QueriedRelations | ARRAY<VARCHAR(65533)> | yes |
| warehouse | VARCHAR(128) | yes |
| ScanStats | JSON | yes |

Duplicate key (queryId, timestamp, queryType); partitions by day of `timestamp` (UTC: the FE runs in UTC), 7 live partitions. `queryType`: `query`, `slow_query`, `connection`, `disconnection`.

## Plugin lock `infra/starrocks/plugins/auditloader.lock`
```yaml
version: 5.0.0
file: auditloader-5.0.0.zip
source_url: https://releases.starrocks.io/resources/auditloader.zip
sha256: cd2a8aceb7943675192e80d7a6d02d675170ab3beba2d0d2f49b5bc8955a8ea2
license: Apache-2.0
retrieved: 2026-11-25
```

## Runtime files (`.runtime/`, never committed)
| Path | Mode | Content |
|---|---|---|
| `.runtime/credentials/srv-auditloader-password` | 0600 | the loader password |
| `.runtime/starrocks-audit/` | 0700 | mounted read-only into the FE at `/opt/lakehouse/starrocks-audit/` |
| `.runtime/starrocks-audit/auditloader.zip` | 0600 | built package with the rendered `plugin.conf` |
| `.runtime/starrocks-audit/installed.sha256` | 0600 | digest of the package installed last |

## Product file block (AC-13)
```yaml
platform_sources:
  starrocks_audit: {owner: read, developer: read, analyst: none, writer: read}
```
`data_products.Product.platform_sources: dict[str, dict[str, str]]` (source → role → level), empty when absent.

## StarRocks grant object (AC-15)
`Grant(role="role_audit_owner", privilege="SELECT", catalog="default_catalog", object="TABLE starrocks_audit_db__.starrocks_audit_tbl__")`.

## Helper settings (AC-17, AC-18)
`Settings(mode: "airflow"|"jupyter", host: str, port: int, ca_file: str, user: str)`.
