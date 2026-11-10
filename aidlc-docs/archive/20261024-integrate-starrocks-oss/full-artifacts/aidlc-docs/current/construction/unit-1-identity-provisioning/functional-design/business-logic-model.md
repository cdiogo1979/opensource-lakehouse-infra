# Business Logic Model — Unit 1 Identity Provisioning

## Purpose

Provision StarRocks-only credentials that let the StarRocks service authenticate to the existing Kerberos-protected Hive Metastore and access the current Iceberg sample databases in RustFS. Keep the Kerberos and RustFS identities separate, preserve all existing platform identities, and never rotate an existing secret implicitly.

## Actors and External Systems

- **Platform operator:** Runs the existing `scripts/provision-identities.sh` workflow.
- **Local credential bootstrap:** Ensures protected credential files exist under `.runtime/credentials/` without replacing existing files.
- **Kerberos KDC:** Stores the `starrocks@<realm>` principal and issues a TGT when the keytab is valid.
- **RustFS IAM/S3 service:** Stores the `starrocks` account, its scoped policy, and accepts signed S3 list requests.
- **Identity provisioner:** Coordinates Kerberos and RustFS provisioning, validation, and redacted status reporting.

## Domain Objects and Relationships

The logical `StarRocksServiceIdentity` has two provider-specific children:

- **KerberosIdentity:** principal `starrocks@<realm>`, with keytab reference `.runtime/credentials/keytabs/starrocks.keytab`.
- **RustFSIdentity:** access-key ID `starrocks`, with secret reference `.runtime/credentials/rustfs-starrocks-secret-key` and policy `lakehouse-starrocks` scoped to `lake/warehouse/databaseA.db/` and `lake/warehouse/databaseB.db/`.

The two credentials are never interchangeable. The Kerberos identity authenticates the StarRocks service to HMS. The RustFS identity authorizes StarRocks S3 access to the two approved database object prefixes.

## Provisioning Workflow

1. If local credential files have not been initialized, the operator first runs `scripts/bootstrap-local.sh`; existing files are preserved. This creates the StarRocks RustFS access-key ID `starrocks` and independent secret material with protected permissions.
2. The operator invokes `scripts/provision-identities.sh`, which follows the existing all-platform provisioning sequence.
3. The provisioner runs Kerberos and RustFS provisioning/validation branches independently. A failure in one branch does not prevent attempting the other.
4. Kerberos provisioning inspects `starrocks@<realm>`. If absent, it creates the principal. If the keytab file is absent, it exports a keytab for the current principal key without changing that key. It validates the keytab by obtaining a TGT and destroys the temporary ticket cache afterward.
5. RustFS provisioning defines the `lakehouse-starrocks` policy with read/write object access restricted to `lake/warehouse/databaseA.db/` and `lake/warehouse/databaseB.db/` and the corresponding bucket listing prefixes.
6. If the policy is absent, provisioning creates it. If an existing policy does not match the approved scope, provisioning fails closed and leaves the existing policy unchanged.
7. If the RustFS account is absent, provisioning creates account `starrocks` using the protected local secret. If it exists, provisioning attaches the approved policy without replacing the account secret.
8. RustFS validation signs non-mutating list requests scoped to both allowed database prefixes. Object read/write and deny probes are deferred to integrated verification.
9. The identity provisioner emits redacted per-provider results. The overall command succeeds only when both provider identities and validations succeed; successful resources are retained if the other provider fails.
10. When the full existing workflow succeeds, its current Hive configuration render/restart behavior remains in effect. The identity unit adds no direct Hive metadata or table changes.

## Lifecycle States

| State | Meaning |
|---|---|
| `NOT_PROVISIONED` | Neither StarRocks provider identity is confirmed. |
| `KERBEROS_READY` | Principal/keytab exist and keytab TGT validation passed. |
| `RUSTFS_READY` | Account/policy are present and scoped authentication checks passed. |
| `READY` | Both provider identities are validated and their references are available to the StarRocks Runtime unit. |
| `PARTIALLY_PROVISIONED` | One provider is ready and the other failed; keep the ready resource, report both results, and allow an idempotent retry. |
| `FAILED_RETRYABLE` | A provider failed for a retryable service/availability reason; preserve resources and allow an idempotent retry. |
| `FAILED_RECONCILIATION_REQUIRED` | Existing credential or policy state conflicts with the approved configuration; preserve resources and require operator reconciliation before retry. |

Kerberos and RustFS readiness are individually reported. Both provider branches are attempted even if one fails. A partial result reports each branch as ready or failed; the overall operation fails if either branch fails. A retry resumes by inspecting existing state and validating it; it does not remove the successful provider resource from a prior partial run.

## Result Contract

The operator receives provider-level outcomes (`created`, `already-present`, `validated`, `failed`, or `not-attempted`) and an aggregate success/failure result. Results may include safe principal/account names, policy names, and error classes/codes. Passwords, keytab contents, secret keys, signed request headers, and raw credential-bearing response bodies are never emitted.
