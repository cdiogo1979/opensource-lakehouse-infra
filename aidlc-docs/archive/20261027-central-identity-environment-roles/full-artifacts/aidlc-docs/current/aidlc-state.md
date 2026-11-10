# AI-DLC State Tracking

## Project Information
- **Project Type**: Brownfield
- **Start Date**: 2026-10-27
- **Current Stage**: Intent Closure (approved with verification waiver)
- **Intent**: Centralize identity and implement environment-scoped access for developer, analyst, writer, and admin identities using FreeIPA, StarRocks native LDAP roles, and RustFS policies.
- **Intent ID**: `20261027-central-identity-environment-roles`
- **Previous Intent**: Closed and archived at `aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark/`.

## Workspace State
- **Existing Code**: Yes
- **Programming Languages**: Python, Bash, SQL, YAML
- **Build System**: Docker Compose, Python packaging, Jenkins pipeline checks, Docker image builds
- **Project Structure**: Compose lakehouse with Hive Metastore, PostgreSQL, standalone MIT Kerberos KDC, RustFS, Spark, JupyterHub, Airflow, Jenkins, and optional StarRocks.
- **Workspace Root**: `/Users/carlosdiogo/code_repo/opensource-lakehouse-infra-v2`

## Intent Lifecycle
<!-- intent-lifecycle:start -->
```json
{
  "archive": null,
  "current_stage": "CLOSURE_APPROVED",
  "intent_id": "20261027-central-identity-environment-roles",
  "previous_intent": "aidlc-docs/archive/20261026-integrate-airflow-jenkins-spark",
  "status": "COMPACTION",
  "summary": "The user approved intent closure with a verification waiver on 2026-10-28. Unit 5 tests passed on disposable services, but production identity binding, FreeIPA/StarRocks provider deployment, grant migration, identity cutover, RustFS production policy changes, and production verification remain incomplete. See the archive summary and full audit; no production deployment is approved by this closure.",
  "verification_outcome": "waived",
  "verification_waiver": {
    "accepted_by_user": true,
    "date": "2026-10-28",
    "details": "The user explicitly approved closing with a verification waiver. Unit 2 actual FreeIPA-entry membership variants remain unverified (its earlier scoped waiver remains documented). Unit 3 analyst Hive metadata DDL authorization, FreeIPA group-revocation timing, Hive metadata-cache behavior, and Airflow ETL integration remain unestablished. Unit 4 expected pre-spawn authorization denial surfaces as HTTP 500. Unit 5 verification passed only on disposable services. Production LDAP write-service-account to StarRocks write_service_account binding is unresolved; production FreeIPA/StarRocks group provider and native grants were not deployed; production identity migration, RustFS production policy changes, MIT KDC cutover, and post-deployment checks remain incomplete. A production FreeIPA container had reached healthy and identity bootstrap was invoked before all Docker containers were stopped; bootstrap completion/readback was not confirmed. Runtime files were subsequently removed only from the v2 copy. This waiver records incomplete verification and does not authorize or claim production deployment."
  }
}
```
<!-- intent-lifecycle:end -->

## Approved Direction
- Production remains in `lake`; development and UAT use newly provisioned `lake-dev` and `lake-uat` buckets.
- `developer-user` reads all environments and writes only development; `analyst-user` reads production only; `write-service-account` reads and writes all environments; existing `admin` remains an administrator.
- Replace `user_a` and `user_b` only after the new identities pass cutover verification. Preserve production data, the writer's RustFS S3 access key, and the admin privilege mapping.
- Use FreeIPA as the sole Kerberos authority in the existing realm after isolated validation and staged cutover; reissue service keytabs, including the writer's. StarRocks authorization uses native roles mapped to FreeIPA LDAP groups; Ranger is removed from the target design.
- `write-service-account` has an approved StarRocks LDAP SQL login for scoped materialized-view management. It needs an operator-provisioned LDAP password separate from its Kerberos keytab, TLS for the SQL client, and remains denied from JupyterHub interactive login. MVs are scoped to `default_catalog.default_lh`, `default_catalog.default_lhdev`, and `default_catalog.default_lhuat`.

## Stage Progress
- [x] Brownfield discovery — current KDC, local JupyterHub accounts, RustFS IAM policies, Hive warehouse, and StarRocks SQL grants inspected.
- [x] Requirement verification — three-bucket layout and requested access matrix confirmed by the user.
- [x] Requirements approved by user on 2026-10-27.
- [x] Story generation plan approved by user on 2026-10-27; personas and stories generated.
- [x] User stories approved by user on 2026-10-27.
- [x] Application Design Plan approved by user on 2026-10-27; detailed design and units generated using recorded working decisions.
- [x] Application design and unit decomposition approved by user on 2026-10-27.
- [x] Units Generation Plan approved by user on 2026-10-27 with proposed defaults.
- [x] Unit dependency matrix and story map approved by user on 2026-10-27.
- [x] Execution plan approved by user on 2026-10-27.
- [x] Unit 1 Functional Design Plan updated for option B and approved by user on 2026-10-27.
- [x] Unit 1 Functional Design artifacts approved by user on 2026-10-27.
- [x] Unit 1 NFR Requirements answers completed: A/A/A/A/A/A/A/A.
- [x] Unit 1 NFR Requirements and tech-stack decision artifacts approved by user on 2026-10-27.
- [x] Unit 1 NFR Design artifacts approved by user on 2026-10-27.
- [x] Unit 1 Infrastructure Design answers completed: A/A/A/A/A/A/A/A.
- [x] Unit 1 Infrastructure Design artifacts approved by user on 2026-10-27.
- [x] Unit 1 Code Generation Plan approved by user on 2026-10-27.
- [x] Unit 1 Code Generation implementation drafted and statically reviewed on 2026-10-27. No services started and active MIT identity state remains unchanged.
- [x] Unit 1 isolated Build and Test completed on 2026-10-27: FreeIPA startup/readiness, identities, scoped role membership, service keytabs, TLS/Kerberos/DNS, persistence, volatile journaling, and protected backup/isolated restore passed. Downstream consumer integration and MIT cutover are deferred; see `construction/plans/unit-1-build-and-test-plan.md`.
- [x] Unit 2 Functional Design Plan — RustFS role policies and reconciliation; approved by the user on 2026-10-27.
- [x] Unit 2 Functional Design artifacts generated and approved by the user on 2026-10-27.
- [x] Unit 2 NFR Requirements answers completed: A/A/A/A/A/A/A/A.
- [x] Unit 2 NFR Requirements and tech-stack decision artifacts approved by the user on 2026-10-27.
- [x] Unit 2 NFR Design Plan approved by the user on 2026-10-27.
- [x] Unit 2 NFR Design artifacts generated and approved by the user on 2026-10-27.
- [x] Unit 2 Infrastructure Design Plan completed with recommended answers A/A/A/A/A/A/A/A after user requested continuation.
- [x] Unit 2 Infrastructure Design artifacts generated and approved by the user on 2026-10-27.
- [x] Unit 2 Code Generation Plan approved by the user on 2026-10-27.
- [x] Unit 2 Code Generation implemented and recorded on 2026-10-27. The reconciler is restricted to the isolated `rustfs-iam-test:9000` target, test-only secrets, test status storage, and isolated test/validation networks. No live RustFS state changed during Code Generation.
- [x] Unit 2 Build and Test Plan approved by the user on 2026-10-27.
- [x] Unit 2 Build and Test — completed with a user-accepted verification waiver on 2026-10-27. Actual FreeIPA-entry membership variants remain unverified; all recorded evidence and limitations are in `construction/plans/unit-2-build-and-test-plan.md`.
- [x] Production StarRocks grant migration preflight on 2026-10-28: FE 4.1.6, iceberg catalog, target tables, and current writer grants match the approved draft; no LDAP group providers exist, so no SQL was applied. The user chose a dedicated production FreeIPA integration; deployment defaults and safety gates are recorded in `construction/plans/remaining-work-and-production-cutover-plan.md`.
- [x] Unit 3 Functional Design Plan approved by the user on 2026-10-27; artifacts generated.
- [x] Unit 3 Functional Design artifacts approved by the user on 2026-10-27; cross-environment metadata visibility later accepted by user.
- [x] Unit 3 NFR Requirements Plan prepared for answers.
- [x] Unit 3 NFR Requirements answered A/A/A/A/A/A/A/A using recommended options; artifacts generated.
- [x] Unit 3 NFR Requirements artifacts approved by the user on 2026-10-27; object-level RustFS authorization is the required direct Spark boundary.
- [x] Unit 3 NFR Design Plan prepared for review.
- [x] Unit 3 NFR Design Plan approved by the user on 2026-10-27; artifacts generated.
- [x] Unit 3 NFR Design artifacts approved by the user on 2026-10-27; object-level RustFS authorization is the required direct Spark boundary.
- [x] Unit 3 Infrastructure Design Plan prepared for answers and review.
- [x] Unit 3 Infrastructure Design Plan answered A/A/A/A/A/A/A/A using recommended options; artifacts generated.
- [x] Unit 3 Infrastructure Design artifacts approved by the user on 2026-10-27; Unit 3 Code Generation Plan prepared for review.
- [x] Unit 3 Code Generation Plan approved by the user on 2026-10-27.
- [x] Unit 3 Code Generation implemented for explicit TPC-H ETL environment/database locations and documented; manual source review only, no tests added or run.
- [x] Unit 3 Build and Test Plan prepared for review; metadata visibility later accepted by user.
- [x] Unit 3 Build and Test Plan approved by the user on 2026-10-27.
- [x] Unit 3 Build and Test — direct Spark/RustFS role and mutation matrices, 24 ETL helper checks, fail-closed and outage probes, admin and multipart/list/head coverage, unsafe-location checks, expired-ticket failure after six minutes, RustFS policy revocation through both a persistent S3 client (first denial 0.006 sec after detach) and Spark's Iceberg `S3FileIO`, and exact before/after bucket inventory comparison are recorded. Pass with documented limits: no FreeIPA group-membership timing, Hive metadata DDL authorization/cache behavior, Airflow ETL integration, or JupyterHub login/spawner mapping. See `construction/plans/unit-3-build-and-test-plan.md`.
- [x] Prepared `construction/plans/unit-4-functional-design-plan.md` for FreeIPA-backed JupyterHub authentication and per-user Spark identity. At this point Unit 3 was still in Build and Test; Unit 4 design/runtime work did not imply Unit 3 acceptance.
- [x] Unit 4 Functional Design generated and approved by the user on 2026-10-27: FreeIPA LDAPS authentication and role mapping, explicit admin treatment, per-user credential registry/mounts, MIT-KDC transition boundary, notebook ticket cache, revocation, and workspace persistence. Validation items are listed in `construction/unit-4/functional-design-clarification.md`. No runtime configuration or identity state changed.
- [x] Prepared `construction/plans/unit-4-nfr-requirements-plan.md` for scale, latency, availability, revocation, credential security, audit, workspace persistence, and compatibility decisions. At that point Unit 3 remained in Build and Test; this plan did not close its residual gaps.
- [x] Unit 4 NFR Requirements answered A/A/A/A/A/A/A/A; generated `construction/unit-4/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md` for review. No SLA, backup/RPO, HA, or retention commitment was added; no runtime changes or tests were performed.
- [x] Unit 4 NFR Requirements artifacts approved by the user on 2026-10-27; prepared `construction/plans/unit-4-nfr-design-plan.md`. At that point Unit 3 residual verification gaps remained open and were not waived by this design work.
- [x] Unit 4 NFR Design Plan approved and artifacts generated: `construction/unit-4/nfr-design/nfr-design-patterns.md` and `logical-components.md`. At that point Unit 3 remained in Build and Test; Unit 4 implementation was still gated.
- [x] Unit 4 NFR Design artifacts approved by the user on 2026-10-27; prepared `construction/plans/unit-4-infrastructure-design-plan.md`. Runtime and network remain unchanged.
- [x] Unit 4 Infrastructure Design Plan approved by the user on 2026-10-27; generated `construction/unit-4/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`, with `infrastructure-design-clarification.md` recording the reserved FreeIPA `admin` identity conflict. Documentation only; no runtime changes or tests.
- [x] Unit 4 Code Generation Plan approved by the user on 2026-10-27. LDAPAuthenticator 2.0.2 is the reviewed candidate: published minimums are Python 3.9, JupyterHub 4.1.6, and ldap3 2.9.1. Read-only inspection confirmed the running Hub uses Python 3.10.12 and JupyterHub 5.3.0, meeting those declared minimums. FreeIPA schema/TLS behavior remains a Build and Test gate.
- [x] Prepared `construction/unit-4/code-generation-clarifications.md` with recommendations for the `administrator` identity mapping, legacy JupyterHub access, and authenticator choice. The user approved the recommendations on 2026-10-27.
- [x] User approved the recommended administrator mapping, disabling legacy `user_a`/`user_b` logins while preserving their data, and LDAPAuthenticator 2.0.2 subject to compatibility gates.
- [x] Unit 4 Code Generation implemented: FreeIPA LDAPS/network config, strict login and pre-spawn role checks, explicit per-user credential/workspace registry, protected auth-state key, and notebook tmpfs credential staging before dropping to UID/GID 10001. Python 3.10.12/JupyterHub 5.3.0 were read from the running Hub and satisfy published candidate minimums. No tests, image build, FreeIPA identity changes, deployment, or service restart were performed.
- [x] Unit 4 Build and Test completed on 2026-10-27. Hub/single-user builds, FreeIPA login and role denials, notebook spawns, identity mounts, UID/GID 10001, ticket setup, notebook S3 role matrix, LDAP outage denial, temporary membership revocation/restoration, Spark SQL role checks after explicit Hadoop UGI keytab login, administrator API stop, one-use token revocation, fresh pre-spawn denial after role removal, and missing-CA startup failure passed. A stale authenticated session's denied pre-spawn currently returns HTTP 500, with no notebook created. See `construction/plans/unit-4-build-and-test-plan.md`.
- [x] User chose to keep the intent open and prepare remaining work/cutover planning on 2026-10-27. On 2026-10-27, the user directed that the plan include actual production changes; the revised production plan was approved by the user on 2026-10-27. It sequences Unit 4 denial-response polish, Unit 5 Ranger/StarRocks design and validation, disposition of Unit 2/3 limits, production FreeIPA deployment, RustFS policy rollout, consumer migration, MIT KDC authority transition, verification, and rollback. This remains planning only; no production deployment or identity mutation has been authorized or performed.
- [x] Unit 5 Functional Design Plan prepared on 2026-10-27 after approval of the production-change plan. The plan covers StarRocks 4.1.6, Ranger service/plugin and UserSync, FreeIPA LDAP/group integration, role policies, outage/revocation behavior, audit, and isolated test boundaries. No services or runtime state changed.
- [x] Unit 5 Functional Design artifacts generated on 2026-10-27: `construction/unit-5/functional-design/business-logic-model.md`, `business-rules.md`, `domain-entities.md`, and `functional-design-clarification.md`. Updated the canonical application design. Exact StarRocks/Ranger compatibility, LDAP group propagation, resource/action mapping, policy cache/outage behavior, and writer DDL need verification in later approved stages. No services, grants, identities, production data, or runtime state changed.
- [x] Unit 5 Functional Design artifacts approved by the user on 2026-10-27. Prepared `construction/plans/unit-5-nfr-requirements-plan.md` to set scale, performance, outage, revocation, security, audit, recovery, compatibility, and test-isolation requirements. No runtime changes or tests performed.
- [x] Unit 5 NFR Requirements completed with recommended answers A/A/A/A/A/A/A/A/A on 2026-10-27. Generated `construction/unit-5/nfr-requirements/nfr-requirements.md` and `tech-stack-decisions.md`. Ranger 2.9.0 is an evaluation candidate only; exact StarRocks 4.1.6 compatibility remains unverified. No runtime changes or tests performed.
- [x] Unit 5 NFR Requirements and technology decisions approved by the user on 2026-10-27. Prepared `construction/plans/unit-5-nfr-design-plan.md` for principal binding, layered authorization, bounded/fail-closed dependency behavior, policy cache and revocation, audit, preservation, and compatibility design. No runtime changes or tests performed.
- [x] Unit 5 NFR Design Plan approved by the user on 2026-10-27. Generated `construction/unit-5/nfr-design/nfr-design-patterns.md` and `logical-components.md`. Exact Ranger/StarRocks compatibility, LDAP group propagation, outage/cache behavior, and revocation timing remain Build and Test gates. No runtime changes or tests performed.
- [x] Unit 5 NFR Design artifacts approved by the user on 2026-10-27; prepared `construction/plans/unit-5-infrastructure-design-plan.md` for isolated Ranger/StarRocks topology, secret/network/storage boundaries, and disposable catalog dependencies. No runtime changes or tests performed.
- [x] Unit 5 Infrastructure Design answers set to recommended A/A/A/A/A/A/A/A/A/A by explicit user approval. Generated `construction/unit-5/infrastructure-design/infrastructure-design.md` and `deployment-architecture.md`; corrected the external Hive catalog Ranger boundary according to the StarRocks guide.
- [x] Unit 5 Code Generation and Build and Test authorized by the user's explicit request; prepared `construction/plans/unit-5-code-generation-plan.md` and `unit-5-build-and-test-plan.md`. Isolated implementation is underway; production changes remain prohibited.
- [x] Unit 5 Code Generation and Build and Test completed on 2026-10-28 on disposable StarRocks 4.1.6/FreeIPA and isolated Hive Metastore/RustFS services. TLS LDAP role mapping, source/MV role matrices, cache revocation, no-group/unknown users, negative DDL, direct writer-role exception, external Hive/Iceberg 15-case matrix, and external-source manual MV refresh passed. See `construction/plans/unit-5-build-and-test-plan.md`; operational limits and direct-role lifecycle are documented in the handoff. No production FE grants or identities were changed.
- [x] Performed the approved read-only production StarRocks metadata inventory on 2026-10-28. Recorded users, roles, catalogs, databases, direct grants, and writer table-level DML in `construction/plans/remaining-work-and-production-cutover-plan.md`. No production mutation was issued.
- [x] User chose to preserve existing writer INSERT/UPDATE/DELETE grants. On an isolated StarRocks 4.1.6 Iceberg catalog, INSERT and DELETE succeeded; UPDATE was rejected as unsupported. Read-only `CURRENT_ROLE()` checks confirmed active roles for the current production accounts: `user_a`, `user_b`, and `write_service_account` have NONE; `admin` has its four assigned admin roles; `root` has root.
- [x] Prepared the additive writer-role grant migration and rollback draft in `construction/plans/remaining-work-and-production-cutover-plan.md`, preserving the inventoried table scope and recording that Iceberg UPDATE is not executable on StarRocks 4.1.6.
- [x] User approved the additive writer-role grants and preservation of existing DML. The 2026-10-28 preflight found no StarRocks LDAP Group Provider, so no SQL was applied.
- [x] User chose a dedicated production FreeIPA integration rather than promoting the isolated validation service. Recommended deployment boundaries and prerequisites are recorded in `construction/plans/remaining-work-and-production-cutover-plan.md`.
- [x] Prepared the optional production FreeIPA/StarRocks LDAP and SQL TLS configuration in `docker-compose.freeipa-production.yml`, `infra/starrocks/fe/entrypoint.sh`, `infra/freeipa/patch-httpd-redirects.py`, and protected-input helpers under `scripts/`.
- [x] Added `scripts/bootstrap-starrocks-production-group-provider.py` as a separate production-only provider preflight/apply tool. It requires the exact production FE/container identity, both approved networks, TLS settings/material, and protected credentials; apply creates only the named missing provider, not users/roles/grants.
- [ ] Resolve the production identity binding between LDAP `write-service-account` and existing StarRocks `write_service_account`; the new reconciler reports both account-presence checks and performs no grant transfer.
- [ ] Review the configuration, subnet, secret ownership, and backup/restore path before provisioning. No service was started/restarted and no production SQL or identity changes were made.
- [ ] Configure and verify the production LDAP Group Provider and authentication integration; then apply the additive writer-role grants and perform positive/negative authorization probes.
- [ ] Production grant deployment, identity cutover, and post-deployment verification.
- [x] Deployment handoff reviewed; the user approved closure with a verification waiver on 2026-10-28. Production deployment and identity/KDC cutover remain incomplete.

## Unit 5 architecture update — 2026-10-28

The user directed that Ranger be removed from the Unit 5 target. The replacement is StarRocks native RBAC mapped to FreeIPA LDAP groups. Current design/code artifacts and `unit-5-build-and-test-plan.md` were updated to supersede Ranger work. Added `infra/starrocks/ldap-access/bootstrap_roles.py` and `scripts/bootstrap-starrocks-ldap-roles.sh` for a disposable StarRocks test FE only. The utility enforces explicit disjoint database lists, LDAP users/groups/roles, least-privilege grants, protected test secret locations, and Docker project/service/loopback-port identity checks. StarRocks 4.1.6 uses explicit registered LDAP users bound to DNs because its virtual-user security integration path is not the selected native authorization route. No live StarRocks FE, Ranger, FreeIPA, RustFS, HMS, KDC, user, group, secret, volume, grant, or data was changed by this design/code pivot. Static compile and shell syntax checks passed. Runtime integration remains open because the dedicated `starrocks-ldap-test-fe` service and test-only credential files are not yet provisioned. Existing Ranger test state/progress remains historical and preserved.

## Current Gate
Unit 1 isolated FreeIPA Build and Test is complete. Its pinned image, readiness, role bootstrap, scoped grants/denials, keytabs, TLS/Kerberos/DNS, persistence, and protected backup/isolated restore passed. The active MIT KDC remains authoritative and unchanged. FreeIPA remains isolated; do not attach production clients, assign the active `kdc` alias, or perform authority cutover.

Unit 2 Build and Test completed with a user-accepted verification waiver on 2026-10-27. The pinned image and direct package inventory passed. A separate disposable RustFS test service received the approved IAM baseline, and the reconciler created `lake-dev`/`lake-uat`, role users/groups/policies, and bindings. Exact membership/policy readback and S3 role probes passed, as did multipart checks, probe cleanup, and protected snapshot restore into a second disposable RustFS instance. Target guard, lock contention, tested LDAP/RustFS authentication and transport failures, managed-policy drift, malformed responses, 12 injected fail-closed preflight cases, actual validation-reader write denial, snapshot-write recovery, and failure injection after successful user creation, policy creation, membership removal, and group-policy binding passed. Reviewed recovery runs converged; a final run returned protected `no-change` with readback and role probes passed. Synthetic LDAP response fixtures exercised exact, empty/missing, locked, missing-user, extra-member, and cross-role-conflict parsing. Actual FreeIPA-entry membership variants were waived and remain unverified. Compose inspection confirms only the two intended test networks, six test-only secret targets, and three read-only bind mounts. Docker inspection confirmed the disposable test instance has no published ports and only `identity_test_net`; normal `object-store` remains only on `iceberg-poc-net`. Do not attach the reconciler to production `iceberg_net` or touch `object-store`.

Unit 3 Build and Test completed with documented limits. Direct Spark/Iceberg access passed the tested role matrix: analyst reads prod only and cannot write; developer reads all and writes dev only; writer and unchanged admin mappings read/write all three. Append/overwrite/delete, 24 ETL config/location helper checks plus external-host location rejection, raw RustFS bucket/list/head/multipart checks, invalid-credential/no-fallback, missing-keytab, expired-TGT, HMS/RustFS outages, and temporary RustFS policy revocation through a persistent S3 client and the platform's Spark `S3FileIO` are recorded in the Unit 3 plan. The Spark client denied its first read after policy detach; direct S3 denial was measured at 0.006 seconds. All temporary users, policies, and object prefixes were removed. Final bucket counts/hashes match the before snapshot exactly; the observed counts were 23 objects in `lake` and 1 each in `lake-dev` and `lake-uat`, so the buckets were not empty at inventory time. The three empty namespaces from the earlier Unit 3 run remain; no old table data was used as test input. Analyst Hive metadata-DDL authorization, FreeIPA group-membership revocation timing, Hive catalog metadata-cache behavior, and Airflow ETL integration remain unestablished. Do not migrate the MIT KDC.

Unit 4 Build and Test is complete. All three allowed identities authenticated and spawned isolated notebooks; role denials, per-user mounts, S3 authorization, and Spark SQL authorization passed. LDAP outage denied login with HTTP 403. Hadoop access required explicit `UserGroupInformation.loginUserFromKeytab`; the tested synthetic Iceberg table and all its probe objects were removed. The JupyterHub admin API stopped the administrator notebook with HTTP 204. Temporary CLI tokens were revoked, verified as unauthorized (HTTP 403), and the Hub database has zero remaining `command-line generated` token records. With developer membership removed and a notebook stopped, the existing session's fresh spawn was denied before creating a container (HTTP 500 from the pre-spawn hook); membership was restored. A missing-CA Compose start failed before container creation. No temporary notebook containers remain and the developer, analyst, and administrator work volumes remain. Keep the MIT KDC authoritative and unchanged. The only noted polish item is converting expected pre-spawn authorization failures from HTTP 500 to a user-facing denial response.

Unit 5 isolated Code Generation and Build and Test are complete. See the 2026-10-28 verification addenda in `construction/plans/unit-5-build-and-test-plan.md`. The disposable FE/BE and isolated test FreeIPA remain available; temporary Hive/RustFS test services, volumes, and test credentials were removed. No production StarRocks grants/catalogs, FreeIPA identities, RustFS policy, Hive metadata, MIT KDC, or data were changed.

The current gate is production readiness planning: inventory and review existing StarRocks FE users/default grants before reconciling native roles, specify how the direct `write-service-account` role is disabled/revoked and active sessions are closed, and prepare an operator-reviewed migration/rollback. Disable FreeIPA authentication alone does not terminate an already-open StarRocks SQL session. Production deployment, user migration, and MIT KDC cutover have not occurred.

## Audit
Prior intent histories remain preserved in their archives. Events for this intent are recorded in `aidlc-docs/current/audit.md`.

## Unit 5 native RBAC clarification and cleanup — 2026-10-28

The user confirmed `write-service-account` must authenticate to StarRocks SQL to create and manage materialized views, and approved the recommendation to use internal `default_catalog` databases `default_lh`, `default_lhdev`, and `default_lhuat`. The isolated bootstrap creates those namespaces and grants writer-only MV creation/management, with developer read access across environments and analyst read access to production only. General DDL/security administration remains denied. The writer needs a separate protected FreeIPA LDAP password in addition to its Kerberos keytab and SQL client TLS; it remains excluded from JupyterHub interactive login.

The user also authorized cleanup of unneeded running containers. Ranger Admin, Ranger PostgreSQL, Ranger UserSync, obsolete RustFS IAM test containers, and a duplicate test container were stopped/removed where present. The isolated `ranger-test-ipa` container is retained as an isolated FreeIPA dependency despite its legacy name. The later 2026-10-28 native-role test addenda supersede the earlier pending-verification status: external Hive/Iceberg authorization and MV refresh passed on isolated services; production FE remains unchanged.
