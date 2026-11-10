# Intent Summary: StarRocks Integration

## Intent
StarRocks Integration (`20261109-starrocks-integration`)

## Objective
Integrate StarRocks in a separate Compose file, create its Iceberg catalogs on Polaris from the product bootstrap, and align StarRocks roles with the Keycloak product groups.

## Date
2026-11-09

## Scope
Included: StarRocks 4.1.7 FE/BE in docker-compose.starrocks.yml (core start, opt-out); srv-starrocks and starrocks Keycloak clients; Iceberg REST catalogs (OAuth2, vended credentials); MV databases; group-named roles with exact enforcement; JWT users synced from Keycloak (bootstrap, on demand, scheduled); TLS for token login; CLI login and JDBC token helper; reset and lifecycle wiring; legacy StarRocks retirement; README. Excluded: shared-data mode, Ranger/LDAP, Power BI and long-lived BI tokens (follow-up intent), Polaris changes other than NAMESPACE_READ_PROPERTIES. Extensions: Security off, PBT partial, Resiliency off.

## Units / workstreams
Keycloak identities and credentials, Runtime Compose, configs, TLS, Bootstrap and user reconciler, Lifecycle, scheduled sync, reset, Login helpers, legacy retirement, README, tests, Build and Test, Deploy

## Major requirements
- StarRocks runs from docker-compose.starrocks.yml as part of the core start (STARROCKS_ENABLED=false opts out).
- The product bootstrap creates the Iceberg REST catalogs lakehouse, lakehouse_uat, lakehouse_dev on Polaris and the MV databases.
- StarRocks roles are named after the Keycloak groups with the Polaris matrix; platform admin also gets system administration.
- People log in with Keycloak tokens; StarRocks users and grants follow Keycloak product groups.

## Architecture and design decisions
- Catalogs use OAuth2 client credentials as the writer-level service account srv-starrocks (renewable), not per-user JWT pass-through (non-renewable, breaks MV refresh).
- Upstream 4.1.7 images pinned by digest, no custom build; config mounted read-only.
- Pure planners with pluggable SQL transports (docker exec on the host, network in the scheduled reconciler).
- Grant enforcement by coverage (ALL covers expanded privileges); unparsable grants reported, never revoked.

## Implementation decisions
- The scheduled sync runs in the extended polaris-group-reconciler (mariadb-client 11.8.9-r0, --skip-ssl).
- Token login uses a mysql 9.7.2 client container with the OpenID Connect plugin; JDBC uses Connector/J 9.1+ idTokenFile with starrocks-token.sh --watch.
- SQL TLS from a local CA and PKCS12 keystore; the FE entrypoint injects keystore settings from protected files.

## Deviations
- Build and Test fixes: SHOW BACKENDS reports the host in the IP column; reconciler role guard for the scheduled race.
- Approved additions: TLS on the SQL port (the client plugin refuses plaintext); NAMESPACE_READ_PROPERTIES in the Polaris read set; the JDBC token helper.
- Accepted limitation: owner and platform-admin cannot drop Iceberg tables through StarRocks.
- PBT P4 corrected from equality to coverage.

## Verification
See construction/build-and-test/build-and-test-summary.md. Live: runtime and reruns; catalogs and smoke reads via vended credentials; 75 grants and enforcement; JWT login over verified TLS for all five users; the full read/write matrix; MV create, sync and scheduled refresh; reconcile drift in both directions; opt-out; scheduled sync; JDBC Connector/J 9.3.0 (REQUIRED and VERIFY_IDENTITY); memory fit. Suite 219 passed, 1 skipped, 2 earlier Airflow drift failures. Regression verifiers pass except the known Jenkins CI job and the Spark parts blocked by the missing legacy image. Accepted limitation: no owner drops through StarRocks.

## Canonical documents updated
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/starrocks-sql-access.md

## Superseded decisions
- Legacy StarRocks on Kerberos, FreeIPA LDAP group provider, and a Hive-type Iceberg catalog replaced by Keycloak JWT users, native RBAC, and Polaris REST catalogs; legacy assets archived.
- StarRocks status 'unsupported-pending-migration' replaced by 'implemented-in-docker-compose.starrocks.yml'.

## Archived artifacts
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/aidlc-docs/current/compaction/20261109-starrocks-integration/manifest.json
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/application-design.md
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/aidlc-docs/knowledge/opensource-lakehouse-infra-v2/functional-design/lakehouse-product-access.md
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/docker-compose.starrocks.yml
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/starrocks/conf/fe.conf
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/starrocks/conf/be.conf
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/starrocks/fe-entrypoint.sh
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/starrocks/starrocks_common.py
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/starrocks/bootstrap-starrocks.py
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/starrocks/reconcile-starrocks-users.py
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/keycloak/bootstrap-realm.py
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/keycloak/realm-contract.json
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/polaris/bootstrap-product-authorization.py
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/polaris/reconciler/Dockerfile
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/infra/polaris/reconciler/run.sh
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/docker-compose.yml
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/docker-compose.deferred.yml
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/.env.example
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/scripts/lakehouse.sh
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/scripts/bootstrap-default-product.sh
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/scripts/reset-lakehouse.py
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/scripts/prepare-lakehouse-runtime.py
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/scripts/prepare-starrocks-certificates.py
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/scripts/starrocks-login.sh
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/scripts/starrocks-token.sh
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/README.md
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/tests/starrocks
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/tests/operations/test_reset_lakehouse.py
- aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/tests/keycloak/test_bootstrap_users_contract.py

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261109-starrocks-integration/full-artifacts/`
