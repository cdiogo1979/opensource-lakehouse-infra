# Unit 2 Identity — Code Generation Summary

## Generation status

**Code generated; runtime verification remains.** The one-shot profile now contains Kerberos, RustFS IAM, and PostgreSQL role adapters. The host helper applies the named Hive S3A credential and restarts Hive after the profile succeeds. No build or provisioning has been run; Build and Test must validate all pinned interfaces and the migration before operators use the flow.

## Implemented

- Local bootstrap now creates missing, mode-restricted Dremio, PostgreSQL-admin, RustFS-admin, RustFS-writer, and Hive-RustFS credential files. Existing files are preserved and values are not printed.
- KDC bootstrap creates a distinct `kadmin/provisioner@LAKEHOUSE.LOCAL` keytab, grants the final `admin@LAKEHOUSE.LOCAL` KDC administration ACL, and preserves the existing Hive Metastore service identity.
- An explicit `identity-provisioning` Compose profile and one-shot provisioner creates keytabs for `admin`, `write-service-account`, `user_a`, and `user_b` without rotating principals on rerun.
- A PostgreSQL migration adapter creates a distinct superuser `admin` role and demotes Hive's `hive` login from superuser while preserving ownership. The migration has not been executed or runtime-verified.
- A RustFS SigV4 admin API adapter creates named `admin`, `write-service-account`, `hive-metastore`, `user_a`, and `user_b` identities; adds scoped named policies; and validates the generated IAM keys through an S3 list request.
- Hive configuration rendering selects the named `hive-metastore` RustFS credentials after the provisioner writes its completion marker. The host helper rerenders and restarts Hive after successful account and PostgreSQL setup.
- Spark no longer receives `.runtime/credentials/rustfs.env` (the RustFS root credentials).
- README documents invocation and the incomplete result. Explicit volume reset removes generated KDC keytabs along with the Hive keytab.

## Verification gates and remaining work

- **RustFS native accounts/policies:** adapter code now uses RustFS's SigV4 admin endpoints and limits writer/read policies to `databaseA.db` and `databaseB.db` warehouse prefixes. It has not been run against the pinned image. Build and Test must validate API response formats, policy attachment, Iceberg list/write actions, and idempotent reruns before reporting success.
- **Dremio accounts:** per the user's clarification, these are created manually through the UI. Use `dremio-admin-password` during first-run for the `admin` user, then create `write-service-account` with `dremio-writer-password` and leave it out of the `ADMIN` role. The one-shot provisioner does not manage Dremio accounts.
- **PostgreSQL roles:** migration code exists but has not run. Until it succeeds, `hive` retains its current superuser capability on fresh volumes and `postgres-admin-password` is only a prepared credential.
- **Hive S3A identity isolation:** configuration and host orchestration are generated but have not run. Hive still uses root credentials until the explicit provisioner/helper succeeds.
- **Permission outcomes:** there is no verified cross-component admin mapping, writer permission, Hive/RustFS enforcement, or Dremio JDBC Space-write authorization.

## Operator command

```bash
./scripts/provision-identities.sh
```

The helper has not been run as part of Code Generation. Successful runtime setup is not verified yet.

## Changed files

- `scripts/bootstrap-local.sh`
- `scripts/clean.sh`
- `docker-compose.yml`
- `infra/kerberos/entrypoint.sh`
- `infra/identity-provisioner/Dockerfile`
- `infra/identity-provisioner/provision-kerberos-identities.sh`
- `infra/identity-provisioner/provision-postgres-roles.sh`
- `infra/identity-provisioner/provision-rustfs-identities.py`
- `scripts/provision-identities.sh`
- `scripts/render-metastore-config.py`
- `README.md`
- `aidlc-docs/current/aidlc-state.md`
- `aidlc-docs/current/audit.md`
- `aidlc-docs/current/construction/plans/unit-2-code-generation-plan.md`
- `aidlc-docs/current/construction/unit-2-identity/infrastructure-design/infrastructure-design.md`
- `aidlc-docs/current/construction/unit-2-identity/infrastructure-design/deployment-architecture.md`

## Checks

No tests, builds, Compose validation, or identity provisioning were run during Code Generation, per the approved plan. Build and runtime verification belongs to the following Build and Test stage.
