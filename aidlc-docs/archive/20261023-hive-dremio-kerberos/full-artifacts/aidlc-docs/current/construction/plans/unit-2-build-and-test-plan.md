# Build and Test Plan — Unit 2 Identity Provisioning

## Objective

Build the generated identity-provisioner image and validate Unit 2 against the existing local Compose environment without deleting or recreating its KDC, PostgreSQL, RustFS, or Dremio volumes. Preserve current secrets and account state. The test run mutates account state only through the approved idempotent provisioner.

## Preconditions

- User approves this Build and Test plan.
- Docker Compose v2 and the running Unit 1 stack are available.
- `scripts/bootstrap-local.sh` has run and preserved all existing runtime credentials.
- Dremio first-run `admin` exists; `dremio-admin-password` matches its current password. The `write-service-account` local user exists with `dremio-writer-password` and is not assigned the `ADMIN` role.
- No manual reset or credential rotation is performed as part of this plan.

## Test sequence

### 1. Static Compose and image build

- Run `./scripts/bootstrap-local.sh`.
- Run `docker compose config --quiet`.
- Build `kdc`, `identity-provisioner`, `create-bucket`, `hive-schema-init`, and `hive-metastore` images.
- Confirm default Compose startup does not include the identity-provisioning profile.
- Inspect service configuration without displaying secret values: Spark has no RustFS root `env_file`; Hive has no root RustFS environment file; the provisioner has no published ports and receives only named credential secrets.

**Pass:** configuration parses and all local images build; no secret values appear in command output.

### 2. Preserve and upgrade the existing KDC

- Start/reconcile the core stack so the updated KDC entrypoint can add the separate `kadmin/provisioner` bootstrap keytab to the existing realm volume without rotating the Hive service principal/keytab.
- Confirm KDC and Hive Metastore become healthy and existing Spark-to-Hive behavior remains available.
- Check the Hive service keytab's principal and version metadata without printing keytab contents.

**Pass:** existing realm and Hive service continue to work; a protected bootstrap keytab exists; no volume was reset.

### 3. One-shot account provisioning

- Manually confirm the Dremio accounts from the preconditions.
- Run `./scripts/provision-identities.sh` once.
- Review redacted status output and Compose service status. Do not display environment values or secret files.

**Pass:** Kerberos principals/keytabs are available for `admin`, `write-service-account`, `user_a`, and `user_b`; RustFS named identities and expected policies exist; PostgreSQL `admin` exists as a login/superuser; Hive `hive` is no longer a superuser; the RustFS completion marker is present; Hive restarts healthy using the named service key.

### 4. Credential and authorization checks

- Authenticate to RustFS S3 with each generated identity and test only its approved scope. Verify writer can list/write required `databaseA.db` and `databaseB.db` paths; verify readers can list/read only their intended prefixes; verify out-of-scope access is denied. Confirm admin operations use the named RustFS admin identity.
- Verify the RustFS IAM admin API returns stable user/policy state on a second provisioner run without rotating credentials or duplicating grants.
- Verify Hive S3A can access the configured warehouse using its named key and does not receive the root key in environment configuration.
- Restart Hive and confirm it remains healthy with the named key. Run the existing Kerberos Spark namespace smoke interaction, using a specifically provisioned test identity only if its writer credentials are in scope.
- Inspect `docker inspect` environment names/mounts and local file modes without printing values; confirm Spark does not receive root or writer credentials before Unit 3 wiring.

**Pass:** documented allow/deny outcomes and stable reruns; any unsupported RustFS action, path condition, or Hive behavior is recorded as a blocker without broadening policy scope.

### 5. PostgreSQL role migration checks

- Confirm `admin` can authenticate with its local password file and has superuser status; confirm `hive` retains database/schema ownership and login but has no superuser status.
- Confirm Hive remains healthy and the Hive Metastore schema can be inspected by the existing `schematool` operation.
- Run the provisioner again and confirm role state and passwords are preserved.
- Do not test against a fresh disposable data volume in this pass; verify existing-volume safety first. If a disposable fresh-volume check is later requested, require a separate explicit reset because the current project uses persistent volumes.

**Pass:** Hive functions with the demoted service role and the admin role remains distinct. If Hive fails, use the created PostgreSQL admin to restore only the required privilege; never reset the metastore volume.

## Stop conditions

- Any credential mismatch, unreadable secret, KDC principal/keytab mismatch, RustFS admin endpoint failure, policy mismatch, unexpected broad permission, or PostgreSQL migration failure.
- Hive Metastore fails after the role migration or named S3 credential switch.
- An account already exists with a credential that does not authenticate. Do not rotate it implicitly.
- Any observed requirement for bucket-wide writer access or RustFS root credentials in Spark/Hive after the named service account is provisioned.

On failure, preserve volumes, report the exact failed component with secrets redacted, and leave prior safe state intact. Do not invoke `scripts/clean.sh`.

## Explicit exclusions

- No sample database/table ETL; Unit 3 owns that.
- No Dremio Hive source, JDBC Space-write, query-user mapping, or end-user impersonation acceptance claim; later units own those.
- No JupyterHub or Airflow/Jenkins deployment.
- No security scanner or performance benchmark; no corresponding target is in scope.

## Completion artifact

Record commands and pass/fail results in `construction/build-and-test/unit-2-build-and-test-summary.md`. Mark Unit 2 Build and Test complete only if the expected outcomes pass. Otherwise retain the failed gates and remediation decision in the summary.

## Approval status

Approved by the user on 2026-10-23. **Complete.** Compose validation and image builds passed; the native-arm64 Hive Metastore is healthy against the preserved schema; the approved identity provisioner completed and reran idempotently; Kerberos, RustFS, PostgreSQL, named Hive S3 credentials, and Spark namespace checks passed. RustFS authorization probes verified the approved writer/reader scopes and removed their temporary objects. Dremio JDBC Space-write and end-user cross-engine authorization remain explicitly deferred to later units. See `aidlc-docs/current/construction/build-and-test/unit-2-build-and-test-summary.md`.
