# Unit 2 Identity and Permission Provisioning — Business Rules

## Identity Ownership

1. The disposable Kerberos realm contains distinct `admin`, `write-service-account`, `user_a`, and `user_b` principals. The existing `hive/hive-metastore` service principal is preserved.
2. Each principal has its own keytab. Test-user keytabs are never shared; keytab bytes and Kerberos password material are never logged or committed.
3. Kerberos credentials, Dremio local credentials, RustFS access keys, and PostgreSQL credentials are separate. Native credentials are independently generated for different components; one component's administrator credential is never reused in another component.
4. `admin` and `write-service-account` are separate identities. The writer is not a component administrator and cannot use the metastore PostgreSQL service credential.
5. Component ownership remains explicit: KDC owns Kerberos principals; RustFS owns S3 users and policies; PostgreSQL owns its database roles; Dremio owns local accounts and Space permissions; Hive/Hadoop owns Hive-side authorization behavior.
6. Spark has no independent local identity directory in this design. It consumes the caller's Kerberos identity and RustFS credentials. JupyterHub's admin-user mapping and isolated sessions are completed in Unit 5.

## Administrator Mapping

7. `admin` receives the component-specific administrator role/account required for the local PoC in each component that supports such an account. Each native admin secret is separately generated and stored.
8. Where a component has no user-account model, the design records an operator access procedure and does not claim a fictitious native account was created.
9. Dremio admin account creation is part of Unit 2 after the initial Dremio setup is complete. Dremio source setup and query-user mapping remain Unit 4 responsibilities.
10. PostgreSQL administrator access is a separate native role/credential. The existing `hive` database role remains a service identity; `write-service-account` is not granted direct PostgreSQL login.

## Writer and Reader Permissions

11. `write-service-account` receives a distinct RustFS access key and the narrowest supported policy for the `lake` warehouse paths required by `databaseA` and `databaseB`. Bucket setup retains a separate setup/admin credential.
12. `write-service-account` receives only the Hive operations needed to create and populate those databases/tables, subject to the selected Hive-owned authorization mechanism. If the standalone Metastore cannot express this permission boundary, provisioning fails closed and returns the feasibility gap; it must not use `admin` as a workaround.
13. Unit 2 provisions identities and initial writer capability. It does not create `databaseA`, `databaseB`, or sample tables; Unit 3 creates them as `write-service-account`.
14. Reader grants are applied only after the databases exist, through a repeatable post-ETL grant operation: `user_a` may read `databaseA`; `user_b` may read both databases.
15. Granting a read permission does not itself prove enforcement. Hive/RustFS effective-user behavior must be verified for Spark and Dremio, and unsupported results are reported as blocked.
16. User-specific RustFS credentials are distinct for `user_a` and `user_b`; their policies must align with the selected database read profiles. Direct RustFS access is not an acceptance demonstration.

## Dremio Accounts

17. Unit 2 creates separate Dremio local accounts for `admin` and `write-service-account`, using distinct component-native credentials.
18. The writer receives no platform-admin privilege. Creation of the requested object in an existing Dremio Space over JDBC is verified in Unit 4; if Community cannot grant it, report the blocker rather than elevating the writer.
19. Dremio query users and their Hive effective-user mappings are completed in Unit 4. Unit 2 does not claim identity propagation.

## Repeatability and Secrets

20. Initial identity provisioning is an explicit one-shot step after required services are ready. It creates missing identities and reports existing ones without changing their credential values.
21. Existing keytabs, passwords, access keys, policies, and component accounts are preserved on safe reruns. Rotation is explicit and coordinated with all consumers.
22. Credential files reside only in the ignored, host-restricted runtime directory. Mount only required credentials to their consumer and read-only where supported.
23. Logs and summaries may include principal/account names, component names, action status, and redacted errors. They must never contain password values, RustFS secret keys, keytab contents, or ticket-cache contents.

## Failure Handling

24. Verify service health and required setup state before provisioning; do not mutate identities if a required dependency is unavailable.
25. A failed required account or permission operation stops the run. Preserve previous successful actions and persistent data, and make rerun safe.
26. Report the failing component and operation with a safe diagnostic. Never report complete when a required identity or permission remains missing.
27. No automatic cleanup or rollback removes a principal, account, keytab, object, volume, or database state after partial failure.
28. A component limitation is a feasibility blocker. Present evidence and the smallest proposed adjustment for review before broadening permissions or changing the approved architecture.
