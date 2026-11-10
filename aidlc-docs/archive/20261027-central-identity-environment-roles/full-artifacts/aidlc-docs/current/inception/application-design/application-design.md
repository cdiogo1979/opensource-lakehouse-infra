# Application Design — Central Identity and Environment Access

## Overview

The design uses FreeIPA as the source for users, groups, and Kerberos identities; a version-controlled policy document plus identity provisioner maps those groups to RustFS IAM; JupyterHub authenticates human users through FreeIPA LDAP and starts isolated notebook sessions; Spark uses the user’s own Kerberos and RustFS identity; StarRocks native roles mapped to FreeIPA LDAP groups authorize StarRocks queries. The existing Hive Metastore remains the Spark catalog, and its authorization behavior against S3A/RustFS is a mandatory verification gate. The current design does not add HiveServer2 or Ranger.

## Role-to-enforcement mapping

| Principal/group | FreeIPA | RustFS | Hive/Spark | JupyterHub | StarRocks |
|---|---|---|---|---|---|
| `lakehouse-developers` / `developer-user` | Canonical human account and group | Read all buckets; write only `lake-dev` | Own Kerberos principal; HMS and S3A denial/allow checks | LDAP login; own isolated runtime identity | Read all; write dev only |
| `lakehouse-analysts` / `analyst-user` | Canonical human account and group | Read `lake` only; no writes | Own Kerberos principal; HMS and S3A denial/allow checks | LDAP login; own isolated runtime identity | Read production only; no writes |
| `lakehouse-writers` / `write-service-account` | Non-interactive service identity | Read/write all three buckets; preserve RustFS S3 key | Airflow ETL identity; Kerberos keytab reissued by FreeIPA | Denied interactive login | LDAP SQL login over TLS; read/write Iceberg environments and create/manage MVs in scoped internal databases |
| `admin` | Separate platform-admin identity | Retain platform admin capability | Administrative access | Authorized administrator login | StarRocks administrator separately provisioned |

## Policy lifecycle

Role policy documents live in a declarative, version-controlled policy file beside `infra/identity-provisioner`. Changes to what a role can access go through Git review and are applied by the reconciler. Routine grants and revocations change FreeIPA group membership and trigger reconciliation; they do not require editing the policy document. The reconciler manages per-user RustFS IAM identities and maps them to role groups. It compares actual and desired policies, verifies allow/deny probes, and fails closed on unexpected broad access.

RustFS evaluates actual S3 requests. Removing role membership must remove the RustFS group grant or disable the affected identity. Revocation also terminates that user’s active notebook/Spark sessions and destroys the private Kerberos cache. StarRocks LDAP group resolution and native role grants govern the SQL path independently.

## Human notebook security flow

JupyterHub validates the user through FreeIPA LDAP over TLS. LDAP login does not itself issue Kerberos credentials. Each user's isolated runtime receives only that user's protected Kerberos credential material and individual RustFS IAM credentials. The user's Spark client authenticates to HMS as that user and signs S3 requests with their scoped RustFS identity. The ETL writer keytab and S3 key are never mounted into human notebook containers.

The selected proof-of-concept direction is a per-user RustFS IAM identity/key managed by the provisioner, with protected, per-user delivery to the isolated notebook. Credential paths, ownership, mount construction, and key revocation are detailed in construction design and must be validated before enabling user access. If this isolation cannot be guaranteed by the local Docker/Jupyter setup, implementation must stop and revisit the credential broker option.

## Hive Metastore and direct Spark

Spark connects directly to the Kerberized Hive Metastore. The current storage-based metastore authorization is retained provisionally because there is no HiveServer2. Hive storage authorization historically uses underlying filesystem permissions; its behavior with this S3A/RustFS setup must be verified for database and table metadata calls, including denied users. RustFS IAM is authoritative for object reads/writes. If the metastore cannot enforce metadata boundaries with S3A/RustFS, the architecture requires a reviewed change; Ranger UI rules or hiding databases are not acceptable substitutes.

## StarRocks LDAP groups and native roles

FreeIPA remains the source of login passwords and role-group membership. The Unit 5 design uses registered StarRocks LDAP users bound to their FreeIPA DNs, the LDAP Group Provider, and native StarRocks roles granted to external groups. StarRocks stores usernames/DNs and SQL grants; FreeIPA keeps passwords and group memberships. Developer reads all configured environments and inserts only in dev; analyst reads prod only; writer reads/inserts all configured environments. The approved `write-service-account` also logs in to StarRocks for materialized-view management. A separately protected FreeIPA LDAP password is required in addition to its Kerberos keytab, and SQL clients must use TLS. MVs live in internal `default_catalog` databases `default_lh`, `default_lhdev`, and `default_lhuat`; developer reads all three, analyst reads prod only, and writer creates/manages MVs in all three. These database lists are explicit and never wildcarded. General schema/security DDL remains denied.

StarRocks uses its own service identity for HMS/RustFS reads after native SQL authorization. LDAP authentication clients must use TLS for the SQL connection because the MySQL LDAP plugin sends the password using the cleartext authentication plugin. Role groups must be mutually exclusive because native RBAC unions mapped roles. Exact 4.1.6 authentication, group lookup, catalog grants, cache/revocation behavior, and allow/deny boundaries must pass on a disposable FE before production rollout. StarRocks roles do not govern direct Spark-to-RustFS requests. See `construction/unit-5/functional-design/` and `construction/unit-5/infrastructure-design/` for current behavior.

## Environment data placement

- Production: `s3a://lake/warehouse/`
- Development: `s3a://lake-dev/warehouse/`
- UAT: `s3a://lake-uat/warehouse/`

Provisioning creates the new buckets only if absent, preserves existing contents, and stops on conflicting database locations. No automatic migration of production data is planned.

## Boundaries and operational failure behavior

- FreeIPA owns identity and membership; policy documents own RustFS role scope; RustFS enforces object access; HMS enforces metadata access; StarRocks native roles enforce SQL query access.
- Failure of identity lookup or reconciliation must not result in broader fallback access.
- `write-service-account` remains a dedicated non-interactive workload identity, is separately registered as a StarRocks LDAP SQL login for scoped MV management, and is never a notebook user's substitute identity.
- Preserve the `admin` privilege mapping, the writer's RustFS S3 key, production objects, and user workspace data. Reissue service Kerberos keytabs under FreeIPA.
- Old accounts are disabled only after new-account positive and negative checks pass.
- The design is for a local proof of concept. FreeIPA operation on Docker Desktop and StarRocks LDAP/RBAC compatibility are not production-readiness claims.

## Related design artifacts

- Component ownership: `components.md`
- Logical interfaces: `component-methods.md`
- Service contracts: `services.md`
- Flows and dependencies: `component-dependency.md`
- Implementation decomposition: `unit-of-work.md`
