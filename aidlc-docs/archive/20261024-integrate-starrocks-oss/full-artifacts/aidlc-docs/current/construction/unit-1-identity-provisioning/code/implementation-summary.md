# Unit 1 Implementation Summary — Identity Provisioning

## Implemented Scope

Unit 1 adds the StarRocks service identity inputs and provisions its dedicated Kerberos and RustFS identities through the existing local Compose identity-provisioning workflow.

## Changed Application Files

- `scripts/bootstrap-local.sh` creates the StarRocks RustFS secret only when missing and applies protected credential-file permissions.
- `docker-compose.yml` declares the file-backed RustFS secret and grants it to the existing identity-provisioner service.
- `infra/identity-provisioner/provision-kerberos-identities.sh` creates/reuses `starrocks@${KERBEROS_REALM}` and its keytab, validates TGT acquisition, enforces keytab permissions, and attempts the RustFS provider independently of Kerberos success.
- `infra/identity-provisioner/provision-rustfs-identities.py` provisions account `starrocks`, validates the exact `lakehouse-starrocks` policy scope and scoped list access, and limits provider error output to safe codes/categories.
- `README.md` documents bootstrap, provisioning, outcomes, safe reruns, credential references, and reconciliation behavior.

## Credential Contract for Unit 2

| Identity material | Host path | Unit 1 provisioning access | StarRocks runtime contract |
|---|---|---|---|
| Kerberos keytab | `.runtime/credentials/keytabs/starrocks.keytab` | Existing keytabs bind mount is writable; file mode `0600` | Mount the file read-only and use principal `starrocks@<realm>` |
| RustFS secret key | `.runtime/credentials/rustfs-starrocks-secret-key` | Compose file-backed secret at `/run/secrets/rustfs-starrocks-secret-key` | Provide read-only at the runtime's documented secret path |
| RustFS access-key ID | Stable value `starrocks` | Defined as the provisioned account/access-key ID | Configure as the S3 access-key ID with the secret above |

Both credentials are distinct, protected by owner-only host directories/files, ignored by Git, and not emitted in command output. Existing credential contents and Kerberos principal keys are not implicitly replaced.

## Operational Behavior

- Invoke `scripts/bootstrap-local.sh` if protected local credentials have not been initialized.
- Invoke `scripts/provision-identities.sh` to run the existing all-platform Compose provisioner.
- Kerberos and RustFS are each attempted once. The outcome for each is reported; aggregate status is failure if either provider fails.
- Successful resources are retained after partial failure. Correct the cause and rerun to reconcile idempotently.
- Existing StarRocks policy drift is left unchanged and requires manual reconciliation.
- PostgreSQL identity provisioning and Hive configuration rendering/restart keep their existing successful-flow ordering.

## Verification Status and Limitations

No tests have been added or run during Code Generation. Build, test, and live provider verification are deferred to the AI-DLC Build and Test phase. Unit 2 still needs to mount and consume the credential contract; Unit 3 still owns StarRocks SQL users, grants, and catalog bootstrap.
