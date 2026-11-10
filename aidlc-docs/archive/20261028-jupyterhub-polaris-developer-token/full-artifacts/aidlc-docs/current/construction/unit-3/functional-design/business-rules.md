# Unit 3 Business Rules — Polaris Authorization and RustFS Credential Vending

## Identity and role rules

1. Polaris accepts a user JWT only when signature, canonical issuer, expiry, and explicit `polaris` audience validation succeed.
2. Resolve the Polaris principal from the verified `preferred_username` claim, matching the pre-provisioned principal. Do not accept caller-supplied identity fields as authority.
3. Extract only explicitly allow-listed values from `resource_access/polaris/roles`: `role-default-developer` and `role-default-analyst` for these journeys. Missing, malformed, or unrecognized roles do not grant access.
4. A user with both approved roles receives the union of their grants, consistent with Unit 1 admission. Effective access remains bounded by the combined matrix below.
5. Never substitute `write-service-account`, a Polaris bootstrap principal, or another user's identity for a human user's failed or missing authorization.

## Environment and operation rules

| Role | Read prod (`lakehouse`) | Read UAT (`lakehouse_uat`) | Read dev (`lakehouse_dev`) | Mutate prod | Mutate UAT | Mutate dev |
|---|---:|---:|---:|---:|---:|---:|
| Developer | Allow | Allow | Allow | Deny | Deny | Allow |
| Analyst | Allow | Deny | Deny | Deny | Deny | Deny |
| Both | Allow | Allow | Allow | Deny | Deny | Allow |

1. “Read” covers authorized catalog/namespace/table discovery, metadata reads, and data reads.
2. Catalog and namespace discovery must not disclose resources outside the principal's read scope. Developers may discover all three approved environments; analysts may discover production only.
3. “Mutate” covers all supported data-changing or resource-changing operations, including namespace/table create, alter, and drop, append, overwrite, delete, and equivalent Polaris-authorized changes.
4. Developers may mutate only within approved dev catalog/bucket locations. Analysts cannot mutate any environment. No user mutation may affect production or UAT.
5. Authorization is evaluated for both the Polaris catalog operation and the resolved object-store location. A permitted catalog operation does not authorize a path outside the applicable environment.
6. Reject malformed, ambiguous, or out-of-scope locations. Do not infer an environment from a user-supplied path fragment or silently redirect a request.

## Credential-vending rules

1. Polaris may vend RustFS credentials only after the identity, role, operation, catalog, and storage location are authorized.
2. Each vended credential set must be temporary and scoped to the authorized location/operation as supported by the configured Polaris and RustFS integration.
3. Spark uses vended credentials for direct RustFS object access. User containers must not receive RustFS root, bootstrap, or shared writer storage credentials.
4. Use the supported Iceberg/Polaris refresh path for later object requests when available. If refresh is unsupported, expires, or is denied, fail the affected operation and require a new Spark session when necessary.
5. Never extend access by falling back to static keys, a different principal, or a broader location scope.
6. Keep temporary access keys, secret keys, session tokens, and bearer JWTs out of logs, notebook output, persistent Spark configuration, home volumes, and shared files.

## Failure, revocation, and diagnostics

- Invalid, expired, wrong-issuer, wrong-audience, or unverifiable JWTs are denied.
- Missing/ambiguous principal or absent/unapproved roles are denied; no default role is applied.
- A denied catalog operation or location is rejected before storage credentials are vended.
- Credential-vending failure and RustFS denial fail the requested operation; neither permits a different identity or static credential fallback.
- Keycloak, Polaris, or RustFS availability failure does not broaden access. Reauthentication or a new Spark session may be required after token/credential expiry.
- Effective role grants apply for the identity and claims validated on each Polaris request. Unit 3 does not promise instant Keycloak group-revocation propagation for already-issued JWTs; revocation/expiry behavior must be verified in Unit 4.
- Safe diagnostics may include correlation ID, validated principal, resource/environment, operation class, decision, and failure category. Secret values and notebook data are prohibited.

## Scope

These rules preserve the existing catalog/bucket layout and grant matrix. They define desired behavior and do not authorize changing unrelated Polaris grants, Keycloak users/groups, buckets, or runtime data. Version-specific filtering, operation names, and refresh behavior must be validated during NFR/infrastructure/code design before implementation claims compatibility.
