# Intent Summary: Central Identity and Environment-Scoped Lakehouse Access

## Intent
Central Identity and Environment-Scoped Lakehouse Access (`20261027-central-identity-environment-roles`)

## Objective
Define and implement the local infrastructure path for centralized FreeIPA identities, environment-scoped RustFS/Spark access, JupyterHub authentication, and StarRocks native LDAP-group roles.

## Date
2026-10-28

## Scope
Units 1-5 design, isolated implementation and verification, production integration preparation, and an explicitly waived production cutover. The original project directory remains as a reference. Runtime files were removed from the v2 copy at user request.

## Units / workstreams
Unit 1: FreeIPA identity foundation, Unit 2: RustFS role policy reconciliation, Unit 3: Spark and RustFS environment authorization, Unit 4: JupyterHub authentication and per-user access, Unit 5: StarRocks native LDAP-group roles and production migration planning

## Major requirements
- Use FreeIPA as the central identity and group source while preserving existing production data and service credentials during any future cutover.
- Scope developer, analyst, writer, and admin access across production lake, lake-dev, lake-uat, Spark/JupyterHub, and StarRocks.
- Keep direct Spark/RustFS object authorization independent from StarRocks SQL authorization.
- Use StarRocks native LDAP group roles instead of Ranger for the approved target.

## Architecture and design decisions
- Environment buckets are lake, lake-dev, and lake-uat.
- Developer reads all environments and writes development; analyst reads production only; writer reads/writes all; preserve admin.
- StarRocks native roles map to FreeIPA LDAP groups; a direct writer-role exception is retained for materialized-view refresh.
- The MIT KDC remains authoritative until a separately planned and verified cutover.

## Implementation decisions
- Isolated FreeIPA, RustFS, JupyterHub, Spark, and StarRocks tests are retained as evidence in the archive.
- Optional production FreeIPA/StarRocks integration and guarded bootstrap helpers were prepared, but production grants/provider/cutover were not completed.
- The v2 .runtime directory was removed at the user's request; the original project folder remains unchanged as reference.

## Deviations
- Closure was approved with a verification waiver while production integration and cutover remained incomplete.
- A production FreeIPA identity bootstrap was initiated but its result was not confirmed before containers were stopped.

## Verification
The user approved closure with a verification waiver on 2026-10-28. Unit 2 actual FreeIPA membership variants remain unverified under its earlier scoped waiver. Unit 3 Hive metadata DDL authorization, FreeIPA group-revocation timing, Hive metadata-cache behavior, and Airflow ETL integration remain unestablished. Unit 4 expected pre-spawn denial is surfaced as HTTP 500. Unit 5 passed on disposable services only. Production write-service-account identity binding is unresolved; the production FreeIPA/StarRocks LDAP provider and grants were not applied; production identity and RustFS policy migration, MIT KDC cutover, and post-deployment checks remain incomplete. A production FreeIPA container became healthy and its identity bootstrap was invoked, but completion/readback was not confirmed before all Docker containers were stopped. This waiver records incomplete work and is not a production pass or deployment authorization.

## Canonical documents updated
- aidlc-docs/knowledge/hive-dremio-rustfs/application-design.md
- aidlc-docs/knowledge/hive-dremio-rustfs/functional-design/lakehouse-workload-and-access.md

## Superseded decisions
- The earlier Ranger-based Unit 5 design was superseded by StarRocks native RBAC mapped to FreeIPA LDAP groups.
- The earlier user_a/user_b access target was superseded by developer-user and analyst-user; production identity migration remains pending.

## Archived artifacts
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/aidlc-docs/current/inception
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/aidlc-docs/current/construction
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/aidlc-docs/current/deploy
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/aidlc-docs/current/compaction/20261027-central-identity-environment-roles/manifest.json
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/README.md
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/.env.example
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/docker-compose.yml
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/docker-compose.freeipa-production.yml
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/docker-compose.ranger-test.yml
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/docker-compose.starrocks-ldap-test.yml
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/infra
- aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/scripts

## Archive
- Full artifacts and audit snapshot: `aidlc-docs/archive/20261027-central-identity-environment-roles/full-artifacts/`
