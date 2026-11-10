# Unit 1 Functional Design Plan — FreeIPA Identity Foundation

## Unit Context

Unit 1 establishes identity and group management needed by the RustFS reconciler, JupyterHub, Spark, and Ranger. The existing stack uses a standalone MIT Kerberos KDC in realm `LAKEHOUSE.LOCAL`. The approved transition is to replace that KDC with FreeIPA in the same realm through isolated validation and staged cutover. Preserve the writer's RustFS S3 access key, but reissue Kerberos keytabs for required service principals, including `write-service-account`.

The official FreeIPA migration guidance says pure Kerberos migration is not automatic, and Kerberos key material must be generated under FreeIPA's Kerberos configuration. Validate FreeIPA in isolation; do not treat two independent KDC databases for the same realm as co-authoritative. The user approved replacing Kerberos keytabs while preserving the distinct RustFS S3 key. See [FreeIPA migration guidance](https://www.freeipa.org/page/Howto/Migration) and [FreeIPA deployment recommendations](https://www.freeipa.org/page/Deployment_Recommendations).

This plan defines the behavior and decisions required for Unit 1. It does not deploy FreeIPA, change keytabs, modify the current KDC, or create users.

## Functional Design Checklist

- [x] Review approved requirements, stories, application design, unit definition, dependency map, and execution plan.
- [x] Inspect current Kerberos realm/service ownership at a high level.
- [x] Identify the distinction between Kerberos keytab replacement and preserving the writer's RustFS S3 access key.
- [x] Resolve the KDC/realm transition: option B selected by user on 2026-10-27.
- [x] Define FreeIPA user, group, service-principal, and administrator lifecycle behavior.
- [x] Define how identity/group changes are exposed to the RustFS and Ranger provisioners.
- [x] Define authentication, authorization, failure, audit, and rollback rules.
- [x] Generate Unit 1 Functional Design artifacts and present them for review.

## Functional Scope

- Establish central human users `developer-user` and `analyst-user`, role groups `lakehouse-developers`, `lakehouse-analysts`, and `lakehouse-writers`, service identities, and separate platform `admin` privileges.
- Ensure user/group lookups used by JupyterHub and downstream provisioners are deterministic and fail closed.
- Define service-principal and keytab ownership for Hive Metastore, Spark, StarRocks, and existing ETL writer.
- Keep existing service paths functional through a tested FreeIPA cutover; retain the current KDC and old keytabs only as protected rollback material until cutover acceptance.
- Do not change RustFS policies, deploy Ranger, configure JupyterHub, or migrate data in this unit.

## Decision Record — Kerberos authority and credential handling

FreeIPA cannot automatically migrate a pure MIT Kerberos KDC while retaining the existing principal key material. The user selected option B on 2026-10-27; the alternatives below are retained to document the decision context.

**A. Keep MIT Kerberos as the KDC for this intent; use FreeIPA as the authoritative LDAP user/group directory.** Automate required Kerberos principal provisioning separately, preserve existing service keytabs, and define per-user Kerberos credential creation. This changes the requirement that FreeIPA itself is the KDC.

**B. Replace MIT Kerberos with FreeIPA in the existing realm — SELECTED.** Re-create or migrate required service principals and issue new keytabs, including the writer keytab. Preserve compatible principal names, the writer's RustFS S3 access key, production data, and administrator privilege mapping. Validate in isolation, inventory consumers, update services in a staged cutover, and retain the old KDC/keytabs only as rollback material until acceptance checks pass.

**C. Use a separate FreeIPA realm for human identities and establish a Kerberos cross-realm trust to the existing MIT realm.** Keep existing service principals and writer keytab in the current realm. This preserves keys but adds trust and client-compatibility work; verify feasibility before committing.

**D. Other** — describe the desired realm and service-credential migration behavior.

The decision affects the identity/Kerberos requirement, writer keytab lifecycle, Jupyter-to-Spark ticket acquisition, and all downstream unit contracts. No runtime credential changes are authorized by this plan approval; those changes belong to later implementation and cutover gates.

## Approval Gate

Option B was approved by the user on 2026-10-27, and this revised plan was approved on 2026-10-27. The detailed Functional Design artifacts are now ready for review. The current MIT KDC, keytabs, services, and data remain unchanged during planning.
