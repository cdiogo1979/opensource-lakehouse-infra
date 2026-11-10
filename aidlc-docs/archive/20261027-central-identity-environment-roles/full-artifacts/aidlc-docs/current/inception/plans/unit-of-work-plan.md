# Units Generation Plan — Central Identity and Environment Access

## Purpose and scope

Turn the approved stories and application design into implementation units with clear source ownership, dependencies, acceptance gates, and rollback boundaries. This plan does not authorize code, Compose, identity, bucket, policy, or service changes.

The design contains six logical units. Existing component boundaries remain the default. Runtime compatibility gates, especially direct Hive Metastore authorization against S3A/RustFS and isolation of per-user notebook credentials, must remain visible in unit exit criteria.

## Proposed units and sequence

### Unit 1 — FreeIPA Identity Foundation

Validate FreeIPA in isolation in the existing realm, then replace the MIT KDC through a staged cutover. Establish DNS compatibility, human users and role groups, service principals, LDAP/TLS authentication, and protected keytab operations. Preserve old keytabs/KDC state as rollback material until dependent services pass cutover tests; never treat both KDC databases as co-authoritative.

**Stories**: US-01, US-08, US-11.  
**Depends on**: Brownfield service/principal inventory.  
**Exit gate**: LDAP/TLS and Kerberos paths work under FreeIPA; required service principal names remain compatible, new keytabs work, and rollback material is secured until cutover acceptance.

### Unit 2 — Declarative RustFS Policies and Identity Reconciliation

Define reviewed role-to-bucket/path/action policies in a declarative project file. Extend the provisioner to reconcile FreeIPA memberships to RustFS IAM users/groups, preserve the ETL writer's RustFS S3 access key, create `lake-dev`/`lake-uat` if absent, and verify exact allow/deny behavior.

**Stories**: US-02 through US-07.  
**Depends on**: Unit 1 group and service identity contract.  
**Exit gate**: Role matrix is enforced by actual S3 requests; current `lake` objects and the writer's RustFS S3 key are preserved.

### Unit 3 — Hive Metastore and Direct Spark Authorization

Align Kerberos identity and database locations with the approved bucket layout. Validate metastore authorization for direct Spark clients and object-level RustFS decisions, with explicit deny tests for unauthorized database metadata and cross-environment object access.

**Stories**: US-03 through US-06, US-09.  
**Depends on**: Units 1 and 2.  
**Exit gate**: HMS and S3A/RustFS allow/deny checks work for each role. If HMS storage authorization fails against S3A, block migration and obtain architecture approval before proceeding.

### Unit 4 — JupyterHub Per-User Spark Identity

Authenticate human users through FreeIPA LDAP/TLS; restrict spawning by group; deliver only each user's own Kerberos and RustFS identity material to isolated notebook containers; terminate sessions and destroy ticket caches on revocation.

**Stories**: US-08, US-09.  
**Depends on**: Units 1–3.  
**Exit gate**: No credential crosses user boundaries; notebooks do not receive the ETL writer identity; role-specific Spark tests pass.

### Unit 5 — Ranger and StarRocks Authorization

Connect Ranger UserSync to FreeIPA LDAP, configure StarRocks Ranger integration, and authorize SQL by synchronized role groups. Keep StarRocks service-side HMS/RustFS access separate from end-user query authorization.

**Stories**: US-10.  
**Depends on**: Unit 1 role groups; Unit 2 storage policy baseline; pinned-version compatibility discovery.  
**Exit gate**: StarRocks allow/deny query tests pass for the role matrix; direct Spark still relies on Units 2–4.

### Unit 6 — Staged Cutover and Integrated Verification

Verify replacement users and every enforcement path, then disable `user_a`/`user_b`. Preserve production data, admin privileges, the writer's RustFS S3 key, and user workspaces; include rollback for FreeIPA keytab cutover.

**Stories**: US-02, US-07, US-11.  
**Depends on**: Units 1–5.  
**Exit gate**: All required positive and negative access checks pass before retiring old users; no data or credential loss.

## Dependency and ordering proposal

```text
Unit 1 FreeIPA
    └── Unit 2 RustFS policy/reconciliation
          ├── Unit 3 Hive Metastore and direct Spark
          │     └── Unit 4 JupyterHub per-user Spark identity
          └── Unit 5 Ranger/StarRocks
                    
Units 1–5 ──> Unit 6 staged cutover
```

Use sequential unit review and integration. Some documentation and compatibility research can proceed in parallel, but implementation must not cross an unresolved identity or authorization contract. Unit 6 begins only after all preceding exit gates pass.

## Source ownership map

| Unit | Candidate source areas |
|---|---|
| 1 | `docker-compose.yml`, `infra/freeipa/` (new), `infra/kerberos/`, identity provisioning and protected credential workflows |
| 2 | `infra/identity-provisioner/`, `scripts/provision-identities.sh`, RustFS bucket/bootstrap policy configuration |
| 3 | `infra/hive/`, `infra/spark/`, metastore configuration/rendering, database initialization and access probes |
| 4 | `infra/jupyter/hub/`, `infra/jupyter/singleuser/`, JupyterHub spawner/authentication and per-user runtime credential handling |
| 5 | `infra/ranger/` (new), `infra/starrocks/`, Ranger UserSync and policy bootstrap/configuration |
| 6 | `scripts/`, operational documentation, integration verification, cutover/rollback procedures |

Exact package paths are candidates and must be reconciled with the current tree during unit functional design. Do not put live secrets under version control.

## Cross-unit contracts

- Role names and exact scopes come from the approved requirements; role policy changes are reviewed in Git, membership changes originate in FreeIPA.
- Every human Spark session uses its own Kerberos and RustFS identity; ETL continues to use the existing writer identity.
- RustFS decides object access; HMS authorization decides metadata access; Ranger/StarRocks decide StarRocks query access.
- Services fail closed if identity lookup, group sync, policy reconciliation, or authorization verification fails.
- Do not replace the MIT KDC until FreeIPA can serve all existing required principals and services.
- No bucket deletion, volume reset, object migration, or implicit fallback to production is allowed.

## Review questions

1. Approve the six-unit decomposition and sequential dependency order, or specify desired changes.
2. Keep Unit 3’s S3A/HMS authorization check as a hard blocker before Jupyter cutover and old-user retirement?
3. Use isolated FreeIPA validation followed by staged MIT-KDC replacement in the existing realm, preserving the old KDC only as rollback material? **Resolved: Yes, option B selected by the user on 2026-10-27.**

## Approval

Approved by the user on 2026-10-27 with the proposed six-unit sequence and direct HMS/S3A authorization blocker. The user later selected FreeIPA replacement of the MIT KDC in the same realm, with service keytab reissuance and preservation of the writer's RustFS S3 key. Generated `application-design/unit-of-work-dependency.md` and `application-design/unit-of-work-story-map.md`. No implementation or runtime changes were made.

## Review gate

Review the unit definitions, dependency matrix, and story map before per-unit Construction planning. No implementation or runtime changes occur in Units Generation planning.
