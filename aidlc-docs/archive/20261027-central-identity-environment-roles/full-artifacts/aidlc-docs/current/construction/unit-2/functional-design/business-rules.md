# Business Rules — RustFS Role Policies and Reconciliation

## Role and scope rules

| Rule | Required behavior |
|---|---|
| BR-RFS-01 | `lakehouse-developers` grants read access to all three buckets and write access only to `lake-dev`. |
| BR-RFS-02 | `lakehouse-analysts` grants read access only to `lake`; it grants no write action in any bucket. |
| BR-RFS-03 | `lakehouse-writers` grants read/write access to all three buckets. The identity remains non-interactive. |
| BR-RFS-04 | `admin` retains its current RustFS administration mapping; Unit 2 must not reduce or widen it automatically. |
| BR-RFS-05 | Role grants cover the full bucket as specified by the approved requirement, not only legacy `databaseA`/`databaseB` prefixes. |
| BR-RFS-06 | Data roles receive no bucket create/delete, IAM/admin, or cross-bucket enumeration permissions. Only the reconciler creates missing buckets. |
| BR-RFS-07 | `lake` is existing production data. Create `lake-dev` and `lake-uat` only when absent; never delete, replace, empty, or migrate contents. |
| BR-RFS-08 | A principal may have exactly one of the developer, analyst, or writer role mappings in this design. Conflicting role membership fails closed pending an approved multi-role policy design. `admin` remains a separate privilege mapping. |

## IAM identity and policy rules

| Rule | Required behavior |
|---|---|
| BR-RFS-09 | FreeIPA is the source of truth for users and role membership; RustFS group membership is a reconciled projection, not an independent grant workflow. |
| BR-RFS-10 | RustFS usernames/access-key IDs use canonical FreeIPA usernames; the reconciler rejects invalid or colliding identifiers. |
| BR-RFS-11 | A role policy is attached to its corresponding RustFS group. A role identity receives no unmanaged direct policy in addition to its group policy. |
| BR-RFS-12 | Managed policy documents are exact and version-controlled. Unknown statements, extra actions/resources, and broader attachments stop reconciliation for operator review. |
| BR-RFS-12a | Existing bucket-level policies that grant access beyond the approved identity matrix are a blocking conflict; the reconciler does not silently rewrite or remove unrelated bucket policies. |
| BR-RFS-13 | Never use RustFS root credentials to test a data role. Root owner semantics can bypass IAM identity policies and make allow/deny results invalid. |
| BR-RFS-14 | Normal reconciliation never resets or rotates the writer's S3 secret. Rotation is a separate explicitly approved operation with coordinated consumer update. |
| BR-RFS-15 | Existing `user_a` and `user_b` and their credentials/policies are left intact by Unit 2. Retirement occurs only after integrated acceptance in the cutover unit. |
| BR-RFS-16 | The FreeIPA `admin` and membership-change principal are not used as the directory read identity. RustFS reconciliation requires a separate authenticated, read-only directory query contract; its concrete credential provisioning is resolved in infrastructure design. |

## Reconciliation and failure rules

| Rule | Required behavior |
|---|---|
| BR-RFS-17 | Validate desired policy and identity state before mutation; unknown role, bucket, action, or malformed response stops before mutation. |
| BR-RFS-18 | Treat only an explicit not-found response as absence. Timeout, 401/403, 5xx, malformed response, and network failure are errors, not permission to create/replace state. |
| BR-RFS-19 | Reconciliation is idempotent: repeated application of the same approved directory and policy state yields no additional change. |
| BR-RFS-20 | Reconcile group membership as a set delta; do not delete unknown users, groups, policies, or IAM state outside the explicit managed allowlist. |
| BR-RFS-21 | Compare complete normalized policy documents and bindings. A check that merely finds expected actions/resources while allowing extra grants is insufficient. |
| BR-RFS-22 | If an existing managed state is broader or ambiguous, stop and report its identifier and safe reason; require review before repair. |
| BR-RFS-23 | Because RustFS admin operations are not a cross-resource transaction, record partial failure and stop. Never report success until post-apply reads and S3 authorization probes pass. |
| BR-RFS-24 | No credentials, secret-bearing request/response bodies, key material, or object contents are included in logs or status output. |
| BR-RFS-25 | User membership removal changes group-derived authorization on reconciliation. Disabling individual credentials and terminating active sessions are coordinated with the notebook identity unit. |

## Verification rules

- Use temporary probe object keys in dedicated test prefixes and disposable test identities; cleanup only those exact probe keys.
- Verify listing and reading of known objects in every allowed bucket and denial in every disallowed bucket.
- Verify developer PUT succeeds only in `lake-dev` and fails in `lake`/`lake-uat`; analyst PUT and DELETE fail in all three buckets; writer read/write succeeds in all three buckets.
- Verify bucket creation occurs only for missing `lake-dev`/`lake-uat` and pre-existing objects remain unchanged.
- Verify policy documents and bindings by readback, then confirm effective S3 behavior using each role's non-root credential.
- Verify writer access-key identifier and secret fingerprint remain unchanged before and after normal reconciliation without exposing the secret or fingerprint in general logs.
- Verify an unknown permission, extra direct grant, duplicate role mapping, or unreadable FreeIPA/RustFS state causes a pre-mutation failure.
