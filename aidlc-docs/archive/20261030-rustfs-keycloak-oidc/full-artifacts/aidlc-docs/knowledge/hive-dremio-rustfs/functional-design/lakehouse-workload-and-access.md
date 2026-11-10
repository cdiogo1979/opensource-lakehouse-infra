# Current Functional Design — Lakehouse Product Access

This file retains its earlier knowledge namespace for continuity. The complete current architecture is in [`../../opensource-lakehouse-infra-v2/application-design.md`](../../opensource-lakehouse-infra-v2/application-design.md); previous Hive/FreeIPA workload behavior is preserved in the immutable intent archives.

## Data product layout

| Environment | Keycloak group / Polaris role | Catalog | Namespace | RustFS bucket | Access |
|---|---|---|---|---|---|
| Production | `role-default-analyst`, `role-default-owner`, `role-default-writer` | `lakehouse` | `default_lh` | `bucket-default` | Analyst reads; owner and writer read/write |
| Dev | `role-default-developer`, `role-default-owner`, `role-default-writer` | `lakehouse-dev` | `default_lhdev` | `bucket-default-dev` | Developer reads/writes; owner and writer read/write |
| UAT | `role-default-owner`, `role-default-writer` | `lakehouse-uat` | `default_lhuat` | `bucket-default-uat` | Owner and writer read/write |

All roles may read all three environments except the analyst, who is limited to production. The developer writes only to dev. The owner manages the product's Polaris resources and data across environments. The writer service identity reads and writes all environments.

## Authorization and workload boundaries

Keycloak groups supply identity and role claims. Polaris maps the approved role claims to Polaris principal roles and catalog grants. Polaris-mediated Iceberg access vends scoped, short-lived RustFS credentials. Direct S3 access is not granted to ordinary users. These layers are distinct: a Keycloak membership alone does not create a Polaris grant, and Polaris SQL/catalog authorization does not grant direct RustFS administration.

The current reconciler uses the protected local Keycloak bootstrap administrator. Replace it with a least-privilege identity before shared deployment. Airflow, JupyterHub, Jenkins, and StarRocks are deferred; no migration or integration is claimed.

## Verification and limitations

U4 verified the Spark smoke-table journey and positive/negative read/write behavior for developer, analyst, owner, and writer in all environments. U2 verified wrong-audience and expired-token rejection and Keycloak-outage behavior. The user accepted closure with a verification waiver for the human PKCE callback and some reconciliation failure-path diagnostics. Existing unexpired tokens can remain usable at Polaris while Keycloak is unavailable; new issuance and membership reconciliation fail. The local configuration's `polaris.realm-context.require-header=false` is approved only for the single configured `lakehouse` realm; restore strict header enforcement or fix Iceberg header propagation before adding realms.
