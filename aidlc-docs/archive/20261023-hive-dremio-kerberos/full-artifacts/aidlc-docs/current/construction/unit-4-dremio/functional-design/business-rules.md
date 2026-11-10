# Unit 4 Business Rules — Dremio Query Authorization

1. Each scenario uses a distinct Dremio local account matching the intended Hive username.
2. Dremio's Hive service identity is used only to authenticate to the metastore; it must not replace the query user's effective identity for authorization.
3. Username mapping is case-preserving/as-is for `user_a` and `user_b`.
4. Proxy-user configuration remains limited to the four approved principals and the existing Compose subnet.
5. VDS-based Access Delegation remains disabled for the authorization demonstration so the query user is impersonated when querying views.
6. `user_a` must be allowed to query `databaseA` and denied access to `databaseB`.
7. `user_b` must be allowed to query both `databaseA` and `databaseB`.
8. Direct Hive source queries are the primary authorization check; Dremio Space/view checks are supplemental and their permission boundary is identified separately.
9. The existing Hive source's RustFS S3A credentials are preserved. They are shared source credentials and cannot be used as evidence that RustFS itself authorizes each Dremio query user.
10. Successful service health, metadata discovery, or a query as `admin`/`write-service-account` does not satisfy the per-user acceptance matrix.
11. A failed access attempt counts as a policy denial only when evidence identifies the intended effective user and the authorization decision point; connection, login, missing object, Dremio Space, and S3 credential failures are separate outcomes.
12. If the matrix cannot be enforced by the approved Hive Metastore/RustFS path, do not broaden proxy settings, grant administrator privileges, rotate credentials, or change architecture in-place. Record evidence and request review of the smallest proposed adjustment.
