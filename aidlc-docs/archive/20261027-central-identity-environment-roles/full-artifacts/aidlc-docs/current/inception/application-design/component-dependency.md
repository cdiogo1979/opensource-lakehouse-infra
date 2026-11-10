# Component Dependency and Access Flows

## Component dependency matrix

| Component | Depends on | Provides |
|---|---|---|
| FreeIPA | PostgreSQL/LDAP/Kerberos state and DNS/network readiness | User/group directory, LDAP authentication, Kerberos identities/tickets |
| Identity provisioner | FreeIPA LDAP, RustFS Admin API, reviewed policy document, protected admin secrets | Reconciled RustFS identities/groups/policies and verification reports |
| JupyterHub | FreeIPA LDAP, Docker runtime, per-user protected identity material | Authenticated isolated notebook sessions |
| Notebook Spark | Per-user Kerberos credential, HMS, RustFS | User-attributed metadata and object access |
| Hive Metastore | Kerberos, PostgreSQL metadata DB, RustFS storage permission checks | Authenticated catalog metadata API |
| StarRocks | FreeIPA LDAP/group provider, native roles/grants, HMS, RustFS, dedicated service identity | SQL query service with StarRocks-native authorization |
| Airflow Spark workload | Airflow bundle, Spark runtime, HMS, RustFS writer identity | Non-interactive ETL using `write-service-account` |

## Grant flow

1. Administrator creates/updates a FreeIPA user and adds it to the approved role group.
2. Reconciler reads the authoritative membership and attaches the matching RustFS group policy to that user’s RustFS identity.
3. StarRocks LDAP Group Provider resolves the user's FreeIPA group; a native StarRocks role mapped to that external group supplies SQL permissions.
4. User authenticates to JupyterHub through LDAP. The spawner provides only the user’s own Kerberos and RustFS identity material.
5. Spark’s HMS metadata request is authenticated as that user. S3 requests are evaluated by RustFS against current role policies.

## Revoke flow

1. Administrator removes the user from the FreeIPA role group or disables the account.
2. Reconciler removes corresponding RustFS group membership or deactivates credentials for a disabled account, then verifies denied S3 probes.
3. StarRocks resolves updated LDAP group membership for subsequent authentication/group lookups; the measured group-cache and session behavior determines when query access changes.
4. The operator terminates the affected user’s active Jupyter/Spark sessions and destroys private Kerberos caches.
5. The operation is complete only after new S3 and HMS requests and applicable StarRocks queries are denied. Existing data is retained.

## Runtime access flows

### Human notebook

`User → JupyterHub LDAP/TLS → FreeIPA` authenticates the user. `JupyterHub spawner → isolated notebook` supplies that user’s protected runtime identity. `Spark → Hive Metastore/Kerberos` retrieves metadata; `Spark → RustFS/S3 IAM` reads or writes objects. StarRocks roles do not govern this direct path.

### StarRocks query

`User → StarRocks SQL endpoint → LDAP authentication/group provider → native StarRocks role grants` evaluates the query as the end user and resolved FreeIPA groups. On allow, `StarRocks service identity → Hive Metastore/RustFS` retrieves catalog metadata and data. Denied query authorization must stop access before reading protected objects.

### Airflow ETL

`Airflow → per-run Spark workload → HMS and RustFS` uses the non-interactive `write-service-account`. This identity is broad by requirement and is not a human role credential.

## Failure and safety rules

- If FreeIPA, policy reconciliation, or LDAP group resolution is unavailable, do not silently grant a broader fallback role.
- Do not spawn a human notebook with shared writer credentials.
- Do not complete old-user cutover until positive and negative access checks pass for replacement users.
- Do not delete or migrate production objects during policy updates or rollback.
- A policy change is not verified merely because the directory group or UI visibility changed; enforce at RustFS/HMS/StarRocks and check denied operations.
