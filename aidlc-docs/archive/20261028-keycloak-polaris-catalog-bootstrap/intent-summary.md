# Intent Summary: Keycloak and Polaris Default Data Product Bootstrap

## Intent
Keycloak and Polaris Default Data Product Bootstrap (`20261028-keycloak-polaris-catalog-bootstrap`)

## Objective
Replace the supported FreeIPA/Hive bootstrap path with a local Keycloak, Apache Polaris, RustFS, and Spark platform-admin journey for the default data product across production, dev, and UAT.

## Date
2026-10-28

## Scope
U1–U4 design, implementation, local bootstrap and role verification, and deploy handoff. No migration, production deployment, or deferred Airflow/JupyterHub/Jenkins/StarRocks integration.

## Units / workstreams
U1: Keycloak, Polaris, PostgreSQL, and RustFS runtime foundation, U2: OIDC identity, Polaris RBAC mapping, and membership reconciliation, U3: RustFS buckets, scoped policies, and STS credential verification, U4: default product catalogs/namespaces/grants, Spark smoke tables, and four-role matrix, Deploy handoff: local operator sequence, evidence, limitations, and PR draft

## Major requirements
- Create the initial default data product in production, dev, and UAT using separate buckets, catalogs, and namespaces.
- Use Keycloak groups and Polaris grants for developer, analyst, owner, and writer behavior.
- Use Polaris-vended scoped RustFS credentials for Spark Iceberg access.
- Keep bootstrap reruns safe and preserve existing bucket objects and named-volume state.

## Architecture and design decisions
- Replace FreeIPA with Keycloak OIDC and Hive Metastore with Apache Polaris; retire MIT Kerberos from the supported bootstrap runtime.
- Use `bucket-default`, `bucket-default-dev`, and `bucket-default-uat`; catalogs `lakehouse`, `lakehouse-dev`, and `lakehouse-uat`; namespaces `default_lh`, `default_lhdev`, and `default_lhuat`.
- Keep only Keycloak, PostgreSQL, Polaris, and RustFS as long-running core services; run Spark on demand.
- User approved `polaris.realm-context.require-header=false` for the single configured realm because Iceberg 1.8.1 omits the realm header during vended credential refresh; revisit before adding realms.

## Implementation decisions
- Add explicit protected credential preparation, realm bootstrap, bucket/catalog/grant bootstrap, reconciliation, auth verification, and Spark smoke-table scripts.
- Run positive and negative access checks through temporary role identities; remove test identities and probe rows afterward.
- Preserve `.runtime` credentials and named volumes; archive workflow documentation only and do not deploy or open a PR during handoff.

## Deviations
- U2 closure is verification-waived for the unconfigured human PKCE callback and remaining reconciliation failure-path diagnostics.
- This intent verifies a local single-node environment only and does not establish production readiness, HA, or multi-host support.

## Verification
The user explicitly accepted the remaining gaps and instructed to proceed on 2026-10-28. U1 runtime readiness passed. U2 writer authentication, wrong issuer, invalid signature, wrong audience, expired-token rejection, analyst membership revocation, and Keycloak outage/reconciliation behavior passed. U2 remains incomplete for the human PKCE browser callback because no owner username or callback URI was supplied, and some duplicate/missing-user, unsupported-group, and incomplete-Polaris-update diagnostics remain untested. U3 bucket and scoped STS checks passed. U4 end-to-end default-product bootstrap, Spark smoke-table create/write/read across prod/dev/UAT, safe rerun, and positive/negative read/write matrix for all four roles passed. This is an explicit verification waiver, not a production pass or deployment authorization.

## Canonical documents updated
- aidlc-docs/knowledge/hive-dremio-rustfs/application-design.md
- aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md

## Superseded decisions
- FreeIPA groups and Hive Metastore are superseded in the supported runtime by Keycloak OIDC/groups and Polaris.
- Earlier shared-bucket and single-catalog directions are superseded by three environment buckets, catalogs, and namespaces.

## Archived artifacts
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/aidlc-docs/current/compaction/20261028-keycloak-polaris-catalog-bootstrap/manifest.json
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/aidlc-docs/knowledge
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/README.md
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/.env.example
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/.gitignore
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/docker-compose.yml
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/docker-compose.deferred.yml
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/infra
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/scripts
- aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/.agents

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261028-keycloak-polaris-catalog-bootstrap/full-artifacts/`
