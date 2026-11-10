# Business Rules — Unit 1 Identity Provisioning

## Identity Separation

1. Provision Kerberos principal `starrocks@<realm>` and RustFS account/access-key ID `starrocks` as separate identities with separate credentials.
2. The Kerberos keytab is used only by the StarRocks service for HMS access; no human, notebook, Hive, or Spark keytab is reused.
3. The RustFS credential is used only for StarRocks object access; it is distinct from RustFS admin, Hive, Spark writer, and notebook credentials.
4. StarRocks SQL usernames/passwords belong to Unit 3 and are not created or managed by Unit 1.

## Scope and Least Privilege

5. The StarRocks RustFS policy grants read/write capabilities only for the bucket `lake` and current sample database object prefixes `warehouse/databaseA.db/` and `warehouse/databaseB.db/`.
6. Bucket listing permission must be prefix-conditioned to those two locations. No permission is granted to other database prefixes or unrelated buckets.
7. Exact action lists required for Iceberg commits, multipart operations, and cleanup are finalized in later Functional/NFR/Infrastructure Design. Those actions must remain resource-scoped to the two approved prefixes.

## Idempotency and Existing State

8. Create the Kerberos principal, keytab, RustFS credential files, RustFS policy, and RustFS account only when absent; preserve existing credential files and provider secrets.
9. Existing Kerberos principal material is not randomized or replaced. A missing keytab may be exported for the existing principal key and must pass TGT validation.
10. Existing RustFS account secrets are not changed. The provisioner authenticates with the configured local secret; an authentication mismatch is an error requiring manual reconciliation.
11. Create the named RustFS policy if absent. If the named policy exists but is broader or otherwise differs from the approved databaseA/databaseB scope, fail closed and preserve it for operator review; do not silently overwrite it.
12. Attach the expected policy to the StarRocks account only after the policy is validated. Existing unrelated account policies must not be silently removed or broadened by this unit.
13. Provisioning never rotates existing StarRocks or other platform credentials implicitly. Any replacement is outside the normal provisioning workflow and requires separate explicit operator action.

## Validation and Results

14. Kerberos validation must prove the keytab can obtain a TGT for `starrocks@<realm>`; temporary ticket-cache material is destroyed after validation.
15. RustFS validation must prove the configured key authenticates and can list within each of the two allowed prefixes without modifying objects.
16. Provisioning success requires both provider validations. Object-level read/write/deny probes are not part of the normal provisioning run; they are performed during integrated verification with disposable data and cleanup.
17. Report per-provider outcomes and aggregate failure without exposing secret values, keytab content, signed headers, or raw secret-bearing responses.

## Failure, Retry, and Preservation

18. Attempt Kerberos and RustFS provider provisioning independently. A failure in one provider must not suppress an attempt to provision and validate the other provider.
19. Retain successfully created or validated resources if either provider fails, report redacted status for both providers, and return overall failure when either provider fails.
20. A retry inspects existing provider state and continues idempotently; it does not delete resources from a prior partial run.
21. The existing all-platform identity command remains the invocation path, including its current Hive configuration render/restart behavior after successful provisioning.
22. Unit 1 does not alter Hive metadata, Iceberg tables/objects, existing principal secrets, existing account credentials, or non-StarRocks policies.
