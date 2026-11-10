# Business Logic Model — RustFS Role Policies and Reconciliation

## Purpose

Translate canonical FreeIPA role membership and the reviewed version-controlled role policy into RustFS IAM users, groups, canned policies, and exact group-policy bindings. RustFS remains the enforcement point for S3 object and bucket requests. This unit does not authorize SQL queries or replace FreeIPA/Kerberos.

## Desired access matrix

| Identity / role | `lake` (production) | `lake-dev` (development) | `lake-uat` (UAT) |
|---|---|---|---|
| `lakehouse-developers` / `developer-user` | Read | Read and write | Read |
| `lakehouse-analysts` / `analyst-user` | Read | Deny by default | Deny by default |
| `lakehouse-writers` / `write-service-account` | Read and write | Read and write | Read and write |
| `admin` | Preserve current full administrative mapping | Preserve | Preserve |

Read means `GetBucketLocation`, `ListBucket`, and `GetObject` for the approved bucket. Write means `PutObject`, `DeleteObject`, `AbortMultipartUpload`, and `ListMultipartUploadParts`, with `ListBucketMultipartUploads` where required by the client. No data role receives bucket creation/deletion, IAM administration, `ListAllMyBuckets`, or unrelated RustFS admin actions. RustFS's built-in `readonly` policy is not sufficient because it lacks `ListBucket`; use project-owned policies scoped to the exact bucket ARNs.

## Reconciliation flow

1. **Load and validate desired state.** Read the reviewed policy document and validate its schema, known role names, known bucket names, allowed S3 action set, exact identity mapping, and policy version. Reject unknown fields, roles, buckets, actions, duplicate principals, and ambiguous human memberships before issuing mutations.
2. **Acquire inputs.** Query FreeIPA through an authenticated read-only directory interface for the approved users and group memberships. The RustFS reconciler must not use FreeIPA `admin` or the separate membership-change principal for reads. RustFS root credentials are loaded from protected mounted secret files and used only for IAM administration. Human RustFS credential delivery remains a Unit 4 responsibility.
3. **Preflight RustFS.** Verify server readiness and inspect all managed buckets, users, groups, policy documents, and bindings. Treat only an explicit not-found response as absence. Authentication errors, timeouts, malformed responses, and unexpected API status codes stop before mutation.
4. **Build a plan.** Compare observed IAM state with desired state and produce a redacted operation summary: bucket create-if-absent, missing user/group, membership delta, policy create/replace, and binding correction. Never print credentials, full API bodies, object names, or secret-bearing configuration.
5. **Check conflicts.** Stop before applying if a managed user/group has unexpected direct or inherited policies, an unmanaged identity is occupying a required canonical name, a role identity has conflicting role memberships, an existing managed policy is broader than desired, a bucket-level policy grants broader role access, or resource state cannot be classified safely. Require explicit operator review for unexpected broad grants rather than deleting unrelated IAM state.
6. **Create missing buckets.** Create only `lake-dev` and `lake-uat` when an explicit absence is confirmed. Never delete, empty, rename, or migrate buckets. Existing `lake` and all contents are preserved. Any non-absence error stops reconciliation.
7. **Ensure managed IAM users/groups.** Use canonical usernames as RustFS IAM access-key IDs. Add only FreeIPA-derived users assigned to the three approved groups; do not enroll role memberships from local guesses or environment names. Reconcile RustFS group membership to the directory membership delta.
8. **Ensure policy documents and bindings.** Store exact version-controlled policy JSON for each role. Compare normalized policy documents; create missing documents and update only recognized managed documents to their reviewed desired version. Bind exactly one role policy to each managed role group using replacement semantics after preflight. Verify policy entities after applying. Do not attach role policy additively when that could preserve an unexpected broader grant.
9. **Handle writer/admin specially.** Preserve the `write-service-account` access-key ID and secret exactly during normal reconciliation; never call the update-user secret path for it except through a separately approved credential-rotation operation. Preserve the current `admin` identity and `consoleAdmin` mapping; treat any discrepancy as an operator-reviewed stop condition.
10. **Verify effective access.** Run positive and negative S3 probes with non-root role credentials against all three buckets and each action category. A successful IAM API update alone is not acceptance. If a mutation partially succeeds or a probe fails, mark reconciliation incomplete, report the sanitized failed resource/action, and stop; do not claim transactionality across RustFS APIs.
11. **Report and repeat safely.** Report `complete`, `no-change`, `blocked`, `already-running`, or `partial-failure` and a redacted count/action summary. Rerunning after correcting a failure converges idempotently. Never silently broaden access to get a green result.

## Grant and revocation path

- **Grant:** Add the person to one approved FreeIPA role group. On the next explicit reconciler run, that user is represented in the matching RustFS IAM group and receives its group policy. Verify access with a positive probe and all relevant negative probes.
- **Revoke:** Remove membership in FreeIPA. Reconciliation removes that user from the RustFS role group and verifies the reduced effective permissions. Credential disabling/revocation and termination of active notebook sessions are coordinated with Unit 4; this unit does not promise that a previously issued access key is invalidated merely by group removal.
- **Role change:** Reconcile membership removal from the old group before addition to a different role group. If conflicting membership is observed, fail before changing RustFS state.
- **Identity deletion:** User removal, key deletion, and final `user_a`/`user_b` retirement are not routine reconciliation actions in Unit 2. Old identities remain unchanged until the integrated cutover gate authorizes retirement.

## Trust and failure boundaries

RustFS IAM policies combine by adding statements across user and group assignments; an unexpected extra policy may therefore grant access beyond the intended role. Preflight requires exact managed bindings and rejects unmanaged additive grants. Preflight also inspects any bucket-level policy capable of extending effective access and blocks on conflicting grants. RustFS's documented default-deny behavior applies when no allow matches, but does not neutralize another attached allow policy. Root credentials bypass IAM identity policies, so root must not be used for access probes. Multi-resource updates are not atomic; incomplete changes must be reported honestly and reconciled again after review.

## External contracts

- **Input:** Canonical FreeIPA usernames and role-group membership from an authenticated read-only directory query; approved policy document; RustFS root admin credential files; configured endpoint/region.
- **Output:** RustFS IAM users/groups, exact managed policy documents and bindings, ensure-only buckets, verification evidence, and sanitized reconciliation status.
- **Non-output:** No human passwords, Kerberos tickets/keytabs, writer S3 secret rotation, Hive database/table grants, Jupyter credentials, Ranger policies, or production data migration.

## References

- RustFS [Identity and Access Management](https://docs.rustfs.com/en/security-compliance/iam) documents user/group policy inheritance, root owner semantics, explicit allow/default deny, and merged policy evaluation.
- RustFS [Users, Groups, and Policies](https://docs.rustfs.com/en/security-compliance/iam/policies) documents admin API operations for users, group membership, policy bindings, and policy documents. These APIs and semantics must still be verified against the pinned project image during Build and Test.
