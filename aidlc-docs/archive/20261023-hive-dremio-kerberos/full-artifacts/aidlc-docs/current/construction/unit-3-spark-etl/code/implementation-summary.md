# Unit 3 Code Generation — Implementation Summary

**Status:** Generated and verified for the Unit 3 workload. Compose rendering, image builds, writer Kerberos identity, both Hive/RustFS databases, Kerberized Dremio Hive source, and all 16 Dremio views passed. Per-user cross-engine allow/deny behavior remains separately unverified; see the Build and Test summary.

## Generated behavior

- The optional `workload` profile generates TPCH inputs only under ignored `.runtime/workload/tpch-data`.
- `tpch-loader` uses the pinned Spark/Iceberg runtime and Hive catalog to create or validate `databaseA` and `databaseB`, each with eight Iceberg tables. Existing matching schema/counts are preserved; mismatches fail without replace, drop, truncate, or append behavior.
- The ETL process checks the effective Hadoop identity, obtains a ticket from the writer keytab into container tmpfs, reads only writer-scoped RustFS credentials, destroys the ticket, and writes a mode-restricted redacted run manifest.
- A separate `tpch-jdbc` one-shot service reads the ETL manifest and creates or validates Dremio Spaces/views as the non-admin `write-service-account`. It receives only the Dremio writer password and manifest mount; it has no Kerberos or RustFS credentials. Failures produce truthful partial status and never trigger admin fallback.
- `scripts/run-tpch-workload.sh` sequences input generation, ETL, then JDBC with a shared run ID.

## File changes

- `docker-compose.yml` — profile-gated generator, ETL, and JDBC services; runtime-only input/results mounts; service-scoped credentials.
- `tpch-generator/generate.sh` — configurable generated output directory.
- `tpch/load_tpch.py` — Hive catalog ETL, create-or-validate semantics, identity/count/schema checks, and manifest helpers.
- `infra/tpch-loader/Dockerfile` — derived pinned workload image; includes the Dremio 26.0.5 JDBC driver and Kerberos client.
- `infra/tpch-loader/run-workload.sh`, `infra/tpch-loader/run-jdbc.sh`, `infra/tpch-loader/dremio_jdbc.py` — isolated one-shot phase entrypoints.
- `infra/dremio/dremio.conf`, `infra/dremio/hive3.d/conf/core-site.xml`, `docker-compose.yml` — Dremio's dedicated Kerberos service identity, realm config mount, and Hive plugin proxy-user allowlist.
- `infra/hive/core-site.xml.in` — Hive Metastore proxy-user allowlist for Dremio, constrained to the Compose subnet and four approved principals.
- `infra/kerberos/entrypoint.sh`, `infra/kerberos/healthcheck.sh`, `infra/identity-provisioner/provision-kerberos-identities.sh`, `scripts/provision-identities.sh`, `scripts/clean.sh` — Dremio service keytab bootstrap, verification, repeatable restart, and reset cleanup.
- `scripts/run-tpch-workload.sh` — operator invocation and phase sequencing.
- `README.md` and Unit 3 infrastructure architecture documents — usage, mounts, credential boundary, and remaining gates.
- `aidlc-docs/current/construction/plans/unit-3-code-generation-plan.md`, `aidlc-docs/current/aidlc-state.md`, and `aidlc-docs/current/audit.md` — workflow status and traceability.

## Necessary implementation detail

Read-only inspection of the pinned Spark container showed Java 17 and no `kinit` executable. The derived workload image therefore installs the Kerberos client package required for the approved keytab-to-ticket-cache flow. The Dremio JDBC driver is copied from the pinned Dremio 26.0.5 image. Both dependencies were confirmed in the successful image build; JDBC connectivity worked, while `CREATE SPACE` failed at the Dremio SQL parser.

## Build and Test outcome

- Compose rendering and derived-image build passed. Image inspection confirmed Java 17, `kinit`, `kdestroy`, and the Dremio JDBC JAR.
- Kerberos keytab authentication produced `write-service-account@LAKEHOUSE.LOCAL`; Spark's UGI was explicitly initialized from the protected ticket cache. ETL created/validated all 16 tables in Hive-backed Iceberg/RustFS with expected SF1 row counts.
- The JDBC writer authenticated and found both manually created Spaces. After Kerberos realm configuration, RustFS S3A credentials, and Hive-side Dremio proxy authorization were configured, the final retry created all 16 views. The final manifest reports `etl=complete`, `jdbc=complete`, and `overall=complete`. Per-user cross-engine allow/deny scenarios remain unverified.
- Persistent volumes and existing tables were preserved. Earlier partial attempts created only expected new tables; a successful rerun validated those tables by schema/count and created the remainder. No admin fallback or cleanup occurred.

Detailed commands and results are recorded in `aidlc-docs/current/construction/build-and-test/unit-3-build-and-test-summary.md`.

The detailed, approval-gated sequence is `aidlc-docs/current/construction/plans/unit-3-build-and-test-plan.md`.
