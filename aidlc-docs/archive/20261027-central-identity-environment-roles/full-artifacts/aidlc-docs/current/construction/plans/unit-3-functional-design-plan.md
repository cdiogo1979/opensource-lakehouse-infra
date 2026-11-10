# Unit 3 Functional Design Plan — Hive Metastore and Direct Spark Authorization

## Unit Context

Unit 3 determines whether direct Spark clients can enforce FreeIPA role membership against Hive Metastore metadata and RustFS-backed Iceberg data. The approved matrix is in `inception/requirements/requirements.md`: developers read all three environments and write only development; analysts read production only and cannot write; `write-service-account` reads and writes all three environments; `admin` keeps its existing administrator mapping. RustFS is the object authorization layer. Ranger is for supported StarRocks query authorization and does not govern direct Spark-to-S3 access.

The approved execution sequence places Hive Metastore and direct Spark authorization before JupyterHub rollout. Unit 2 Build and Test has closed with a user-accepted waiver: actual FreeIPA-entry membership variants were not tested. Unit 1 FreeIPA validation is isolated; the MIT KDC remains authoritative until the later staged cutover. Design must preserve that separation and cannot assume that production services already use FreeIPA principals or keytabs.

Current source inspection found `infra/hive/hive-site.xml.in` enables Kerberos SASL, `hive.metastore.execute.setugi=true`, `AuthorizationPreEventListener`, and `StorageBasedAuthorizationProvider`; the Hive warehouse root is `s3a://lake/warehouse/`. `infra/spark/spark-defaults.conf` configures an Iceberg HiveCatalog at `thrift://hive-metastore:9083`, with the same production warehouse and RustFS S3 endpoint. The requirement maps `lhdev*` databases to `lake-dev`, UAT databases to `lake-uat`, and production databases to `lake`. These configured properties do not by themselves prove that HMS and Spark enforce the requested authorization with S3A/RustFS.

## Functional Design Checklist

- [ ] Trace Unit 3 requirements and stories to identity mapping, database metadata operations, table/partition operations, object access, failure behavior, and acceptance probes.
- [ ] Inspect the full HMS and Spark configuration, pinned service images/dependencies, initialization scripts, and existing database/table location conventions without changing runtime state.
- [ ] Determine precisely which client identity HMS sees for each Spark metastore operation and whether `execute.setugi`, SASL, and the configured authenticator preserve the intended principal.
- [ ] Establish how `StorageBasedAuthorizationProvider` evaluates permissions for S3A/RustFS paths and whether required list/status/permission checks are supported by the pinned stack.
- [ ] Separate Hive Metastore metadata authorization from RustFS object authorization and identify any operations that bypass either layer.
- [ ] Define explicit environment-to-database-to-bucket location rules, including default database behavior, `lhdev*`, UAT naming, production databases, and existing-location conflict handling.
- [ ] Define exact developer, analyst, writer, and admin allow/deny behavior for database, table, partition, read, create/write, overwrite, and delete operations.
- [ ] Define how user and service identities, groups, Kerberos tickets, S3 credentials, and the writer identity are supplied without shared human-user credentials.
- [ ] Define behavior for unknown principals, unavailable FreeIPA/KDC/HMS/RustFS, stale credentials, unsafe locations, and conflicting metadata; default to denial without silent fallback.
- [ ] Generate the Unit 3 Functional Design artifacts for review before Unit 3 NFR Requirements.

## Design Questions to Resolve

1. **HMS authorization mechanism:** Verify what `StorageBasedAuthorizationProvider` actually enforces for Hive 3.1.3 when warehouse locations use S3A and the RustFS S3 API. Identify whether filesystem permissions are exposed and checked as expected. Do not infer enforcement from the XML settings alone.
2. **Caller identity propagation:** Determine whether the direct Spark HiveCatalog client presents the end-user Kerberos principal to HMS and whether HMS performs storage operations as the user, the metastore service, or a configured proxy identity. Clarify what `hive.metastore.execute.setugi` means in this exact deployment.
3. **S3A credential identity:** Resolve how S3A obtains per-user credentials for direct Spark jobs and how they correspond to the RustFS policies from Unit 2. Keep the writer service credentials restricted to ETL/service use; never mount them into human sessions as a fallback.
4. **Database and table locations:** Define default and explicit locations for production, `lhdev*`, and UAT databases. Determine whether table-specific locations may override database roots and how cross-bucket or arbitrary external locations are rejected.
5. **Metadata operation matrix:** Specify which HMS operations must succeed or fail for each role, including database discovery, table/partition listing, metadata reads, create/alter/drop, and ownership-sensitive operations.
6. **S3 object operation matrix:** Specify representative reads, writes, overwrites, deletes, and multipart behavior and distinguish failures from metadata authorization failures. Probes must use disposable data only.
7. **Group-to-user mapping:** Determine whether HMS/Spark consumes canonical FreeIPA groups directly or whether it requires local group resolution/mapping. Preserve the current MIT KDC until staged cutover is separately approved.
8. **Authorization gaps:** If the configured HMS provider cannot enforce the requirements on S3A/RustFS, identify viable options (for example a supported authorization plugin, a metadata service boundary, or another approved mechanism) and stop for architecture approval instead of relying on UI hiding or Ranger claims.
9. **Preservation and transition:** Define how the existing production database locations and data remain intact, how new development/UAT databases are initialized, and how failures are rolled back without deleting buckets, objects, databases, or user workspaces.

## Expected Functional Design Artifacts

- `construction/unit-3/functional-design/business-logic-model.md`
- `construction/unit-3/functional-design/business-rules.md`
- `construction/unit-3/functional-design/domain-entities.md`
- Update `construction/unit-3/functional-design-clarification.md` only if pinned-stack evidence leaves a material requirement or enforcement decision unresolved; otherwise record decisions and evidence in the design artifacts.

## Safety and Scope Boundaries

- This plan is for design only. Do not modify Hive/Spark configuration, database grants, warehouse locations, FreeIPA groups, Kerberos principals/keytabs, RustFS policies, buckets, objects, or production data.
- Do not change the active MIT KDC, make FreeIPA a production authority, or perform the Unit 6 staged cutover.
- Use read-only source/config inspection and authoritative documentation for the design. Any runtime experiments or test data creation require a later approved Unit 3 Build and Test plan and must use disposable databases/tables/objects and identities.
- Preserve `lake` and all existing production objects. Do not migrate or delete existing Hive databases or tables during design.
- The user later accepted cross-environment metadata visibility. Verify actual per-user RustFS object authorization through Spark; return for architecture review if that object matrix fails. Analyst HMS metadata DDL restrictions are not guaranteed.

## Approval Gate

Unit 2 Build and Test was completed with a user-accepted verification waiver on 2026-10-27. The user approved this Unit 3 Functional Design Plan on 2026-10-27, and approved the generated Functional Design on 2026-10-27. The next gate is completion and review of Unit 3 NFR Requirements; runtime changes remain outside this stage.

## Design finding

Primary Apache Hive and Hadoop documentation establishes that the configured storage-based authorization model relies on filesystem permissions, while S3A reports stub permissions and does not enforce them. The user accepts cross-environment metadata visibility. Direct Spark data reads/writes must instead be enforced by RustFS using the caller's own credentials. Analyst HMS metadata DDL restrictions are not guaranteed and remain a separate architecture decision if required.
