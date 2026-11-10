# Unit 5 Functional Design Plan — Ranger and StarRocks Authorization

## Unit context

Unit 5 implements centralized StarRocks query authorization for the approved lakehouse roles. The existing StarRocks OSS cluster is pinned to 4.1.6 and uses a Hive external catalog backed by the existing Hive Metastore and RustFS. FreeIPA is the canonical source for human users and groups, but is currently only validated in an isolated profile; the MIT KDC remains active. Ranger and StarRocks work must first be designed and tested with isolated Ranger metadata and disposable StarRocks state. This unit does not authorize a production FreeIPA deployment, production policy changes, MIT KDC transition, user retirement, or production data mutation.

The Unit 5 design and later implementation must keep these boundaries clear:

- Ranger authorizes requests through StarRocks. It is not a RustFS policy engine and does not protect direct Spark-to-S3 requests.
- RustFS remains the enforcement point for direct Spark object reads and writes.
- The StarRocks service identity accesses Hive Metastore and RustFS to execute queries. End-user query authorization is a separate StarRocks/Ranger decision.
- Existing native StarRocks grants and service configuration must be inventoried before any test integration. Tests use isolated state and synthetic objects; do not reset production volumes or data.

## Baseline and documentation findings

- Compose pins `starrocks/fe-ubuntu:4.1.6` and `starrocks/be-ubuntu:4.1.6`; the optional StarRocks profile has Kerberos and RustFS service credentials and named FE/BE volumes.
- The approved role matrix is `developer-user`: read all environments and write development only; `analyst-user`: read production only and no writes; `write-service-account`: read/write all environments as a non-interactive service identity; platform `admin`: preserve administrator capability.
- StarRocks documentation says Apache Ranger authorization is supported starting at StarRocks 3.1.9; its Ranger integration guide lists Apache Ranger 2.1.0 or later. That establishes a documented minimum, not compatibility for this exact StarRocks/Ranger/plugin combination.
- StarRocks documents the Ranger StarRocks service/plugin for SQL authorization. Installing `ranger-starrocks-plugin` into Ranger Admin is optional for resource autocomplete; without it, Ranger's service test/autocomplete features are unavailable, while service creation can still be performed manually.
- StarRocks 3.5+ supports LDAP, OS, or file-based group providers. Security Integration can create session-scoped users for external authentication; StarRocks documentation says external Security Integration requires Ranger for authorization. Verify the exact LDAP and group-provider behavior in 4.1.6.
- StarRocks documents that Ranger servers using Kerberos authentication are unsupported by its integration. Ranger policy conditions evaluated by JavaScript are also unsupported by StarRocks FE on JDK 17+ and must not be used.
- Ranger audits for StarRocks can be sent to local files or Solr. Select and validate an isolated audit destination; do not claim durable centralized audit until retention and storage are implemented.
- Ranger policies may authorize external catalog resources using the StarRocks service or by reusing another Ranger service such as Hive. This project has no HiveServer2/Ranger Hive authorization service, so the design must validate a StarRocks-service policy for the existing external Hive catalog rather than assume a Hive plugin protects direct Spark.

Primary documentation:

- [StarRocks Ranger integration](https://docs.starrocks.io/docs/administration/user_privs/authorization/ranger_plugin/)
- [StarRocks authentication and authorization overview](https://docs.starrocks.io/docs/best_practices/authentication_authorization/)
- [StarRocks security integration](https://docs.starrocks.io/docs/administration/user_privs/authentication/security_integration)
- [Apache Ranger downloads and supported releases](https://ranger.apache.org/download.html)
- [Apache Ranger project overview and component/plugin model](https://github.com/apache/ranger)

## Functional design checklist

- [x] Map the approved user and service roles to StarRocks authentication, group resolution, Ranger users/groups, policies, and SQL objects; see the business rules and domain entities.
- [x] Select FreeIPA-backed LDAP authentication and directory groups as the working direction; Security Integration behavior is an exact-version Build and Test gate.
- [x] Select Ranger authorization for all SQL objects queried through StarRocks, including the Hive external catalog; exact resource/action identifiers are an exact-version Build and Test gate.
- [x] Define Ranger UserSync as read-only synchronization from isolated FreeIPA and identify sync/removal/nested-group behavior for later measurement.
- [x] Identify the StarRocks FE enforcement integration versus the optional Ranger Admin autocomplete plugin; pin exact artifacts only after compatibility checks.
- [x] Define that legacy native grants must not provide an unintended allow path when Ranger is enabled.
- [x] Define default-deny and record outage, cache/polling, and revocation semantics as Build and Test probes, not assumptions.
- [x] Define a protected administrator break-glass path without relying on legacy test-user grants.
- [x] Define allow/deny audit fields and select isolated local-file audit storage as the test default; production retention is not claimed.
- [x] Define synthetic-data acceptance probes for role decisions, DDL/DML, membership change, Ranger outage, audit, and direct Spark/RustFS independence.
- [x] Record documented StarRocks/Ranger limitations and list unresolved exact-version compatibility checks.
- [x] Generate Unit 5 Functional Design artifacts and update the canonical design/state/audit for review before NFR Requirements.

## Design questions and recommended direction

The user approved this plan and requested continuation. The recommended directions below were used as working design decisions. Unverified implementation behavior remains explicitly listed in `construction/unit-5/functional-design-clarification.md` and is not represented as passed.

1. **StarRocks authentication:** Use FreeIPA LDAP authentication with directory-backed groups. Prefer StarRocks Security Integration only if tests confirm it works with Ranger authorization and the 4.1.6 LDAP/group-provider behavior. Do not use local StarRocks passwords as the human identity source. Is this acceptable?
2. **Authorization scope:** Use the StarRocks Ranger service/plugin for all SQL objects queried through StarRocks, including the external Hive catalog; do not configure a Hive Ranger plugin or claim Ranger governs direct Spark. Is this scope acceptable?
3. **Group and policy mapping:** Map `lakehouse-developers`, `lakehouse-analysts`, and `lakehouse-writers` to Ranger policies. Developers receive SELECT across the three environment databases and write privileges only on development databases; analysts receive SELECT only on production databases; the writer receives required read/write access for all three; `admin` retains administrative control. Confirm the SQL action matrix and whether writer requires DDL in addition to DML.
4. **UserSync lifecycle:** Use Ranger UserSync with read-only LDAP access to FreeIPA, synchronizing only approved users and groups. Treat LDAP membership as canonical and verify removals propagate within a measured bound. Accept?
5. **Ranger service/plugin compatibility:** Keep StarRocks 4.1.6 as the current candidate; select a pinned Apache Ranger release only after build/runtime compatibility checks. Use the StarRocks Ranger Admin autocomplete plugin only if needed; otherwise register the service definition manually. Accept?
6. **Ranger transport and credentials:** Use TLS for LDAP and Ranger Admin API connections where supported. Because StarRocks Ranger integration documents no Kerberos-authenticated Ranger server support, do not plan Kerberos auth between the FE plugin and Ranger; use a protected supported transport/authentication configuration and document the local-POC limitation. Accept?
7. **Policy and outage behavior:** Default deny for unknown users/groups/resources, avoid JavaScript-evaluated policy conditions, test Ranger outage and stale cached policy behavior, and do not fall back to broad native grants. Accept?
8. **Audit destination:** Begin with local Ranger/StarRocks audit files on a dedicated persistent test volume, with explicit access controls and rotation. Solr is out of scope unless a durable searchable audit requirement needs it. Accept?
9. **Test boundary:** Use separately named test Ranger database/metadata and disposable StarRocks FE/BE volumes, synthetic tables/objects, and temporary identities. Do not point Ranger reconciliation or the new integration at production FreeIPA, production RustFS, or existing StarRocks metadata. Accept?

## Expected artifacts

- `construction/unit-5/functional-design/business-logic-model.md`
- `construction/unit-5/functional-design/business-rules.md`
- `construction/unit-5/functional-design/domain-entities.md`
- `construction/unit-5/functional-design-clarification.md` only for unresolved decisions or exact-stack behavior that needs later verification.

## Safety and scope boundary

This stage is functional design planning only. Do not add/start Ranger services, modify StarRocks configuration or grants, create Ranger users/policies, change FreeIPA membership, touch production buckets or objects, rotate credentials, or alter KDC routing. Preserve the existing StarRocks FE/BE volumes and all current data. Unit 5 runtime tests require later approved NFR/infrastructure/code-generation/build-test stages and must use disposable data and state.

The Ranger OSS feature and exact integration must be verified against the pinned components. Ranger authorization of StarRocks SQL does not establish direct Spark authorization, and an allow/deny result in Ranger must be paired with a separate RustFS enforcement probe for direct Spark.

## Approval gate

The production-change plan is approved by the user on 2026-10-27. Review and approve this Unit 5 Functional Design Plan before generating the detailed Unit 5 Functional Design artifacts. Production deployment and KDC transition remain later, separately approved change gates.
