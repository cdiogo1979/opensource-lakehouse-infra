# Application Design Plan — Central Identity and Environment Access

## Purpose and scope

Define the component boundaries and contracts needed to implement FreeIPA-backed identity, role-based access to three RustFS buckets, Spark and Hive Metastore authorization, JupyterHub authentication, and Ranger-backed StarRocks authorization. Preserve the existing production bucket and objects, the writer's RustFS S3 access key, and retire `user_a`/`user_b` only after successful verification. Service Kerberos keytabs are reissued under FreeIPA following the user's approved option B choice.

This stage will produce a component design, service and identity flows, interface contracts, dependency view, and a unit-of-work decomposition. It will not change Compose files, credentials, users, buckets, services, or runtime policies.

## Fixed requirements and design constraints

- `lake` remains production; create `lake-dev` and `lake-uat` idempotently without deleting or moving existing objects.
- `developer-user` reads all three environments and writes only to `lake-dev`.
- `analyst-user` reads production in `lake` and cannot write anywhere.
- `write-service-account` reads and writes all environments; preserve its RustFS S3 access key and reissue its Kerberos keytab under FreeIPA.
- `admin` keeps platform administration privileges and remains separate from ordinary data roles.
- FreeIPA is the identity, group-membership, and Kerberos source. Role groups are the canonical human access assignments.
- RustFS IAM is the object-request enforcement point. Ranger is for the supported StarRocks integration; it does not authorize direct Spark-to-RustFS requests.
- The current project has a Hive Metastore and no HiveServer2. Do not assume a HiveServer2 Ranger plugin is available to authorize direct Spark access.
- JupyterHub LDAP login and notebook Kerberos/S3 access are separate identity flows. The writer service identity must not be exposed to human notebook sessions.
- Role policy definitions should be declarative and version-controlled beside the identity provisioner. FreeIPA group membership changes assign a role; policy-definition changes alter the scope of that role. Provisioning must reconcile safely and fail closed on drift or partial failure.
- No implementation begins until the resulting design and unit decomposition receive explicit approval.

## Planned design artifacts

1. `inception/application-design/components.md` — component ownership and responsibility boundaries.
2. `inception/application-design/component-methods.md` — high-level inputs, outputs, and provisioning interfaces.
3. `inception/application-design/services.md` — service contracts and trust boundaries.
4. `inception/application-design/component-dependency.md` — dependencies and identity/data authorization flows.
5. `inception/application-design/application-design.md` — consolidated design decisions and diagrams.
6. `inception/application-design/unit-of-work.md` — independently reviewable implementation units and dependencies.

## Design questions to resolve

Record answers in `application-design-clarification.md` or directly in this plan. If an answer materially changes approved requirements, update and re-approve those requirements before design completion.

### Question 1 — RustFS identity and credential model for human Spark sessions

How should a notebook Spark session present the human user's identity to RustFS so the S3 policy for that user is enforced?

- **A.** Provision one RustFS IAM identity and access key per FreeIPA user; the provisioner manages the credential lifecycle and delivers the key only to that user's isolated notebook runtime.
- **B.** Add a credential broker that issues short-lived S3 credentials after authenticating the FreeIPA user.
- **C.** Use another design; describe the identity proof, credential scope, and isolation boundary.

### Question 2 — Revocation behavior for running sessions

What revocation guarantee should the design target after a user is removed from a FreeIPA role group?

- **A.** Reconcile the RustFS group policy promptly and document that already-issued Kerberos/S3 credentials remain usable only until their normal expiry or session termination.
- **B.** Reconcile policy and actively terminate/invalidate the affected user's running notebook/Spark sessions and credentials.
- **C.** Other; specify an acceptable maximum revocation delay and operational behavior.

### Question 3 — Hive Metastore authorization for direct Spark clients

Which boundary should protect metadata operations when Spark connects directly to the Hive Metastore?

- **A.** Retain Hive Metastore storage-based authorization and prove, with positive and negative tests, that its checks align with the three RustFS bucket/database locations under S3A.
- **B.** Add a Hive authorization integration that supports direct metastore clients, subject to version compatibility and design review.
- **C.** Add HiveServer2 and route user SQL through it; this changes the current direct-Spark access model and needs explicit requirement approval.

### Question 4 — Policy authoring and operational updates

How should role policies be changed and applied?

- **A.** Store role-to-bucket/path/action policy documents in a version-controlled declarative file; review changes through Git/Jenkins and apply them with the identity provisioner. User grants/revocations remain FreeIPA group-membership changes.
- **B.** Author RustFS policies directly in its administrative UI/API and keep only reconciliation tooling in Git.
- **C.** Other; identify policy owner, change approval, application mechanism, and drift detection.

### Question 5 — StarRocks/Ranger identity mapping

How should FreeIPA users/groups reach Ranger and StarRocks authorization?

- **A.** Ranger UserSync imports FreeIPA users/groups; StarRocks Ranger policies use those groups, with Ranger authorization applied to StarRocks queries only.
- **B.** Use another directory synchronization/mapping method supported by the selected StarRocks and Ranger versions; specify it.

## Recorded design decisions and assumptions

The user approved the plan and requested continuation without selecting individual options. The detailed design therefore uses these recommended working decisions for review; they are not deployment approval:

- **Question 1 — A**: provision per-user RustFS IAM identities and mount only each user’s credential material into that isolated notebook. A construction gate verifies Docker/Jupyter isolation; failure requires a broker design instead.
- **Question 2 — B**: revoke RustFS group access and terminate that user’s notebook/Spark sessions, destroying the user’s private ticket cache. Verify policy denial independently of session cleanup.
- **Question 3 — A, conditional**: retain Hive Metastore storage-based authorization only if S3A/RustFS allow/deny tests prove the required metadata boundary. Failure blocks cutover and requires architecture review.
- **Question 4 — A**: keep role policy definitions in a declarative, reviewed, version-controlled file; FreeIPA membership changes trigger reconciliation.
- **Question 5 — A**: Ranger UserSync imports FreeIPA users/groups over LDAP; StarRocks Ranger policies authorize only StarRocks queries.

## Execution checklist

- [x] Review approved requirements and stories.
- [x] Resolve design questions as reviewable working decisions and record compatibility assumptions.
- [x] Define FreeIPA ownership, user/group lifecycle, and service principals.
- [x] Define declarative RustFS policy data, reconciler behavior, credential delivery, and revocation boundary.
- [x] Define Hive Metastore and Spark identity/authorization contracts, with S3A authorization as a blocker gate.
- [x] Define JupyterHub LDAP authentication separately from notebook ticket acquisition.
- [x] Define Ranger/StarRocks group synchronization and query enforcement boundaries.
- [x] Define service dependencies, failure behavior, safe cutover, and rollback.
- [x] Generate the planned design artifacts and map stories to units.
- [ ] Request review and explicit approval before Units Generation.

## Approval gate

Review the recorded working decisions and the detailed artifacts. In particular, confirm the per-user RustFS key delivery model and session-revocation behavior. Unit 4 cannot pass its exit gate unless direct Hive Metastore/S3A authorization is demonstrated. Approve the design and unit decomposition before Units Generation. Runtime or service changes remain out of scope during application design.
