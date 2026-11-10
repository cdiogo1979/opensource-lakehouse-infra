# Unit 2 Functional Design Plan — RustFS Role Policies and Reconciliation

## Unit Context

Unit 2 maps canonical FreeIPA group membership to RustFS users, groups, IAM policies, and the three approved buckets: production `lake`, development `lake-dev`, and UAT `lake-uat`. The approved access matrix is defined in `inception/requirements/requirements.md`: `developer-user` reads all three buckets and writes only `lake-dev`; `analyst-user` reads production only; `write-service-account` reads/writes all three; `admin` retains its current platform administration mapping. RustFS remains the object-storage enforcement point; Ranger does not authorize direct S3 requests.

Unit 1 isolated FreeIPA validation is complete, but FreeIPA remains isolated and MIT Kerberos remains authoritative. Unit 2 design can specify the directory-to-RustFS contract and validation fixtures; implementation must not assume that production clients have moved to FreeIPA. Preserve all existing production objects and the writer's RustFS S3 key. Do not revoke `user_a` or `user_b`, change active policies, create buckets, or run reconciliation during design.

Initial source inspection found `infra/identity-provisioner/provision-rustfs-identities.py` currently builds policy documents around bucket `lake`, contains `databaseA`/`databaseB` prefixes for legacy users and StarRocks, and has special-case update behavior for the writer and StarRocks policies. `infra/bucket-init/ensure_bucket.py` ensures only `lake`. The design must account for these existing responsibilities and fail safely on drift rather than silently broadening access.

## Functional Design Checklist

- [x] Trace Unit 2 requirements and stories to policy, reconciliation, lifecycle, failure, and verification behavior.
- [x] Inspect the complete current RustFS provisioner, bootstrap wiring, Compose secrets, and existing IAM state interfaces without changing them.
- [x] Review current RustFS IAM documentation for bucket lifecycle, user/group management, policy attach/detach, policy inspection, and policy evaluation semantics. Pinned-image behavior remains a Build and Test gate.
- [x] Define the canonical desired-state policy model for role groups, identities, buckets, prefixes, and allowed actions.
- [x] Define idempotent reconciliation, drift detection, fail-closed behavior, and safe reporting for partial API failures.
- [x] Define human IAM-key create/rotate/revoke ownership and the explicit preservation contract for the writer's existing S3 key.
- [x] Define positive and negative S3 verification probes for every role and bucket, including listing, reads, object writes, deletes, and multipart actions.
- [x] Define bucket creation behavior that preserves existing contents and stops on conflicting ownership/configuration.
- [x] Generate the Unit 2 Functional Design artifacts for review before Unit 2 NFR Requirements.

## Design Questions to Resolve

1. **Policy granularity:** Should permissions apply to all object paths in each bucket, as the approved matrix states, or should the existing warehouse/prefix-level behavior remain for selected service users? Any narrower interpretation must retain required role access and be reconciled with the requirements before implementation.
2. **RustFS identity mapping:** Determine whether FreeIPA users/groups map one-to-one to native RustFS IAM users/groups, and how group membership is represented and reconciled without enabling unintended local authentication paths.
3. **Writer key preservation:** Specify how the reconciler verifies that the existing `write-service-account` access key remains unchanged while policies are updated; it must not read key material into logs or regenerate it during routine reconciliation.
4. **Legacy identities:** Keep `user_a`/`user_b` state intact through Unit 2. Define whether they remain provisioned without policy changes until the later cutover, and how their eventual revocation is gated on the complete role-matrix acceptance tests.
5. **Administrator mapping:** Inspect current RustFS admin privilege assignment and define how to preserve it without granting platform administration to data-role users.
6. **Drift policy:** Decide which existing policy mismatches can be safely updated automatically and which require stopping for operator review. Unknown or broader-than-approved grants must fail closed.
7. **Credential lifecycle:** Define where per-user RustFS credentials are stored/delivered to downstream JupyterHub work, how rotation and revocation are represented, and what Unit 2 owns versus Unit 4.
8. **Reconciliation trigger:** Define the local PoC trigger (operator command, scheduled job, or explicit invocation) and how FreeIPA unavailability, RustFS API errors, and partial reconciliation are surfaced without claiming atomic multi-resource updates.

## Expected Functional Design Artifacts

- `construction/unit-2/functional-design/business-logic-model.md`
- `construction/unit-2/functional-design/business-rules.md`
- `construction/unit-2/functional-design/domain-entities.md`
- Update `construction/unit-2/functional-design-clarification.md` only if source/requirement evidence leaves a material decision unresolved; otherwise record resolved decisions in the design artifacts.

## Design Decisions Captured for Review

- Apply policy scopes to entire buckets, as required by the approved matrix. Retire `databaseA`/`databaseB` prefix-specific role policies only through reviewed reconciliation after the new matrix is proven.
- Use RustFS native IAM groups named after the canonical FreeIPA role groups and attach one exact project-managed policy to each group. RustFS documentation confirms groups inherit group policies and multiple policies are merged; pinned `rustfs/rustfs:1.0.0-glibc` runtime behavior still requires Build and Test verification.
- Reconcile the three role memberships as exclusive for the fixed personas in this design. Conflicting memberships, direct additive policies, or bucket-level grants outside scope block reconciliation.
- Treat “write” as object create/overwrite/delete plus multipart write lifecycle. Data roles cannot create/delete buckets or administer IAM.
- Do not mutate `user_a`/`user_b` or any bucket/object while implementing Unit 2; their eventual retirement remains gated on integrated cutover acceptance.
- Use a distinct authenticated read-only FreeIPA directory query identity/interface. Do not broaden the group-mutation principal or use FreeIPA `admin` for synchronization.

## Safety and Scope Boundaries

- This plan is for design only. Do not create `lake-dev` or `lake-uat`, attach or remove policies, alter RustFS users/groups, rotate any key, or invoke the identity provisioner.
- Do not change FreeIPA, MIT Kerberos, Hive database locations, JupyterHub, Spark, Ranger, StarRocks, production objects, or `user_a`/`user_b`.
- Unit 2 designs RustFS enforcement and reconciliation only. Hive/Spark metadata authorization, per-user notebook credential delivery, Ranger/StarRocks query authorization, and final cutover are separate units.
- Any API limitation that prevents exact allow/deny enforcement or safe writer-key preservation returns for a reviewed design change before implementation.

## Approval Gate

The user approved continuation on 2026-10-27. The detailed Functional Design artifacts are ready for review. Implementation and live policy changes remain behind later unit gates.
