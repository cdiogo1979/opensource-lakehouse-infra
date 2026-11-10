# Unit 3 Business Rules — SQL Bootstrap and Catalog Access

## Catalog and Service Identity

1. **Iceberg catalog type:** Register the lake as a StarRocks Iceberg external catalog backed by the existing Hive Metastore, not as a Hive-format catalog. (FR-2)
2. **Existing endpoints:** Use the in-network Hive Metastore Thrift endpoint and RustFS S3-compatible endpoint, warehouse/bucket, region, and path-style configuration already established by the project. Preserve existing paths and metadata. (FR-2, FR-7)
3. **Dedicated service credentials:** StarRocks accesses HMS using the Unit 1 StarRocks Kerberos principal/keytab and RustFS using its dedicated scoped account. SQL user passwords are separate and must not be substituted for service credentials. (FR-4, FR-5, US-04)
4. **No end-user delegation:** StarRocks SQL authorization is independent of Kerberos and RustFS identity. SQL grants govern queries through StarRocks and do not change direct Spark, Hive, or RustFS authorization. (FR-6)

## SQL Access

5. **`user_a`:** May read `databaseA`; must be denied reads and writes in `databaseB`; cannot write or administer StarRocks. (FR-6, US-01, US-03)
6. **`user_b`:** May read both `databaseA` and `databaseB`; cannot write or administer StarRocks. (FR-6, US-01, US-03)
7. **Writer:** `write_service_account` may read and perform DML writes to existing Iceberg tables in both databases. It may not create, alter, or drop databases/tables and may not manage users, roles, catalogs, or global configuration. (FR-3, FR-6, US-02)
8. **Administrator:** `admin` has full StarRocks administration and data access, with a password distinct from the built-in `root` password. (FR-6)
9. **Default deny:** No target identity receives permissions beyond its matrix entry. Validate effective access, including inherited role grants, before reporting bootstrap success. (FR-6)

## Credentials and Idempotency

10. **Separate root and admin credentials:** Maintain separately protected password files for built-in `root` and requested `admin`. Establish the `root` password on initial bootstrap and use the stored value for subsequent runs. Never leave root passwordless after successful bootstrap. (Q1 A, FR-6, NFR-1)
11. **Create-on-absence:** Generate a protected password file for each SQL identity only when absent. Never print, commit, rotate, or overwrite an existing password file implicitly. (Q3 A, NFR-1, NFR-2)
12. **Drift fails closed:** If a target account exists but authentication using its protected password file fails, stop and preserve both states. Do not reset the account password or rewrite the file automatically. (Q3 A, NFR-2)
13. **No secret diagnostics:** Logs and errors may name the affected account or configuration key, but must not contain passwords, keytabs, tokens, or RustFS secrets. (NFR-1)
14. **Safe rerun:** Reconcile only known-safe missing catalog settings, users, roles, and intended grants. Preserve unrelated grants and all existing catalog/data objects. (Q4 A, NFR-2, FR-7)
15. **Conflict handling:** If existing state grants broader access or conflicts with the desired catalog/access configuration, fail with a redacted diagnostic. Do not revoke or rewrite existing state automatically. (Q4 A)
16. **Partial progress:** Completed additive changes may remain after a later operation fails; rerunning after correction must converge without credential rotation or data loss. (NFR-2)

## Verification Boundary

17. **Connectivity before authorization:** A failed query is an authorization denial only after FE, HMS, Kerberos, RustFS, and catalog health are confirmed. (US-01, US-03)
18. **Writer verification:** Verify writes only against a designated disposable table or explicitly reversible data. Never overwrite or drop existing sample tables. (US-02)
19. **No implementation claim:** Design approval does not establish that grants, Iceberg write compatibility, or security behavior have passed; those require Build and Test evidence. (FR-3, acceptance criteria)
