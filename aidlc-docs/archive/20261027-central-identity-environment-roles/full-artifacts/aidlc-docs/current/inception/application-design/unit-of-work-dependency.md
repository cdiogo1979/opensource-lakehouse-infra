# Unit of Work Dependency Matrix — Central Identity and Environment Access

## Dependency table

| Unit/activity | Depends on | Consumes | Produces |
|---|---|---|---|
| Unit 1 — FreeIPA Identity Foundation | Existing realm, principal inventory, DNS and current KDC | Approved role/group names and service-principal inventory | Validated LDAP/TLS, Kerberos and group contracts; MIT KDC retained only as rollback material until staged cutover, never co-authoritative with FreeIPA |
| Unit 2 — RustFS Policies and Reconciliation | Unit 1 group/identity contract; existing RustFS | Declarative policies, protected RustFS admin credentials, bucket/path mapping | Idempotent RustFS users/groups/policies, bucket state, allow/deny evidence |
| Unit 3 — Hive Metastore and Direct Spark Authorization | Units 1 and 2; existing Hive Metastore and Spark | User Kerberos identity, S3 identity, database location mapping | Verified metadata and object allow/deny behavior under direct Spark/S3A |
| Unit 4 — JupyterHub Per-User Spark Identity | Units 1–3; JupyterHub isolation and Docker spawner | LDAP auth contract, user-specific Kerberos/RustFS credentials, revocation contract | Isolated notebook sessions with user-scoped access and revocation evidence |
| Unit 5 — StarRocks LDAP Group Roles | Unit 1 groups; StarRocks LDAP/RBAC support; Unit 2 storage identities | LDAP Group Provider, native roles/grants, StarRocks service identity and catalog | Native StarRocks authorization with role-matrix allow/deny evidence |
| Unit 6 — Staged Cutover and Integrated Verification | Units 1–5 | New identities, all access paths, rollback procedure, preserved state | Cutover report, denied/allowed matrix, preservation and rollback evidence |

## Required order

1. Validate FreeIPA in isolation; then stage the same-realm MIT-KDC replacement. Retain the old KDC only as secured rollback material and never run the independent databases as co-authorities.
2. Complete Unit 2 and prove RustFS policy enforcement before exposing new users.
3. Complete Unit 3. Its S3A/HMS metadata authorization gate must pass before Unit 4 or Unit 6 proceeds.
4. Complete Unit 4 and prove notebook isolation and per-user credential delivery.
5. Complete Unit 5; compatibility failure keeps StarRocks authorization unavailable rather than broadening access.
6. Complete Unit 6 only after all prior gates pass.

Research and documentation can run in parallel, but implementation changes must preserve reviewed identity and authorization contracts.

## Coordination contracts

- Unit 1 publishes stable user/group and Kerberos contracts while retaining old KDC functionality during migration.
- Unit 2 publishes the exact RustFS role policy schema and user-credential lifecycle consumed by Units 3–4.
- Unit 3 proves direct Spark HMS and S3 authorization; it may block the entire cutover if metadata checks do not map to S3A/RustFS permissions.
- Unit 4 owns notebook credential mounts, per-user cache cleanup, and active-session termination.
- Unit 5 authorizes only StarRocks SQL through native roles; it cannot waive the direct access gates in Units 2–4.
- Unit 6 retires test users only after all positive and negative checks pass and records rollback status.
