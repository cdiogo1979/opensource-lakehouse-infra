# Unit 5 Technology Decisions — NFR Requirements

> **Superseded direction (2026-10-28):** The Ranger entries below are preserved as the previously approved evaluation, not the current target. The user selected StarRocks native roles/grants mapped to FreeIPA LDAP groups and explicitly removed Ranger from Unit 5. Current decisions use explicitly registered LDAP users, the StarRocks LDAP Group Provider, native RBAC, explicit disjoint database lists, and TLS on both LDAPS and SQL client connections. See `../infrastructure-design/` and `../functional-design/`.

## Decision summary

| Area | Decision / candidate | Status |
|---|---|---|
| StarRocks | Keep existing OSS FE/BE 4.1.6 pins and digests. | Approved NFR constraint; do not upgrade without architecture approval. |
| Apache Ranger | Evaluate 2.9.0 as the current stable candidate. | Candidate only; exact compatibility with StarRocks 4.1.6 is unverified. Pin only after integration checks. |
| StarRocks Ranger enforcement | Use the Ranger integration supported by the StarRocks FE release. | Required component, but exact bundled/plugin artifact, service definition, and policy resources remain compatibility gates. |
| Ranger Admin StarRocks autocomplete plugin | Omit initially; manually register the versioned StarRocks service definition. | Recommended PoC simplification. Add the optional plugin only if policy autocomplete is required and its artifact is compatible. |
| Human authentication | FreeIPA LDAP/TLS with StarRocks Security Integration and LDAP-backed group lookup as the working direction. | Exact 4.1.6 behavior with Ranger must be proven before deployment. No production FreeIPA connection in this unit. |
| Group synchronization | Ranger UserSync with read-only LDAP access to the isolated FreeIPA test directory. | Required for group-based policies; nested groups, deletion/revocation, and sync timing must be measured. |
| Ranger metadata database | Separate isolated persistent database/schema and credentials for Ranger test state. | Infrastructure design will choose the exact supported database image/version and backup method. Do not reuse or alter the existing HMS or Airflow metadata databases. |
| Ranger audit | Protected local audit files on isolated persistent test storage, with rotation. | No Solr or centralized durable audit system in the initial PoC. Retention is not an SLA. |
| Transport | LDAPS/TLS for FreeIPA and TLS for Ranger API/policy endpoints where supported. | Certificate roots and exact Ranger transport settings are infrastructure/code-generation gates. Kerberos authentication to Ranger is excluded per StarRocks docs. |
| Secrets | Protected Compose secret files or a separately approved secret manager; no secret values in ordinary environment variables or source. | Required security constraint. Do not reuse production credentials for tests. |
| Policy model | Ranger Admin StarRocks service policies map FreeIPA-backed role groups to SQL resource/action scopes. | Exact ServiceDef resource hierarchy and action names must be verified. No JavaScript policy conditions. |
| Native StarRocks grants | Remove or narrow only in isolated test state so native permissions cannot bypass Ranger; retain a protected break-glass administrator. | Existing production grants are not to be modified under this NFR approval. |
| Direct Spark authorization | Retain independent RustFS IAM enforcement with per-user Spark credentials. | Ranger does not replace or participate in this path. |
| Test state | Separate test FreeIPA profile, Ranger DB/state, and disposable StarRocks FE/BE volumes with synthetic data. | Required isolation. No production service/bucket or current named StarRocks volume is a target. |

## Compatibility gates before pinning/build

1. Verify StarRocks 4.1.6 docs/source and FE image contents to identify exactly which Ranger agent integration is bundled and which additional JARs/configurations are required.
2. Select the Ranger release candidate and verify Ranger Admin, UserSync, database drivers, Java runtime, and StarRocks integration compatibility as a complete set.
3. Verify the Ranger StarRocks Service Definition JSON and supported resource/action model for the external Hive catalog, tables, views, and intended DML operations.
4. Verify StarRocks LDAP Security Integration and LDAP Group Provider behavior with Ranger, including matching usernames and group names.
5. Verify policy polling/cache defaults, outage behavior, and audit output. Do not infer fail-closed or revocation guarantees from documentation alone.
6. Pin container image digests and plugin/service-definition checksums after successful exact-stack verification. Avoid floating tags and default credentials.

## Explicitly excluded for this decision

- Ranger Kerberos authentication: StarRocks Ranger integration documentation states it is unsupported.
- JavaScript-evaluated Ranger policy conditions: StarRocks documents these as unsupported and potentially unsafe for policy semantics.
- Hive Ranger plugin as a direct Spark authorization mechanism: the project does not use HiveServer2; direct Spark requests remain governed by RustFS.
- Solr audit infrastructure, HA Ranger, production FreeIPA/RustFS connections, production StarRocks metadata, and production KDC changes.
- Any claim that selecting Ranger 2.9.0 establishes compatibility with StarRocks 4.1.6.

## Source references

- [StarRocks Ranger integration](https://docs.starrocks.io/docs/administration/user_privs/authorization/ranger_plugin/)
- [StarRocks authentication and authorization](https://docs.starrocks.io/docs/best_practices/authentication_authorization/)
- [Apache Ranger downloads](https://ranger.apache.org/download.html)
