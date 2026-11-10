# Unit 3 NFR Requirements — Polaris Authorization and RustFS Credential Vending

## Scope and inherited limits

- One local Compose deployment with one Polaris instance and at most two active Jupyter/Spark users.
- Existing Keycloak, Polaris 1.8.0, RustFS 1.0.4, Spark 3.5.5, and Iceberg 1.8.1 pins are retained for this unit unless compatibility review identifies a blocker.
- The approved developer/analyst authorization matrix and Unit 3 functional rules are authoritative. NFR targets do not widen roles, locations, or operations.
- Unit 4 owns complete browser-login-to-RustFS end-to-end acceptance. Unit 3 owns focused authorization, concurrency, credential lifetime/refresh, and redaction verification.
- Live Unit 2 integration/performance and the complete Hub dependency lock remain open and are not considered passed by these requirements.

## Performance and capacity

1. Under normal local conditions, Polaris authorization and metadata operations should complete at p95 <= 1 second, excluding Spark planning, query execution, and RustFS object transfer.
2. Under normal local conditions, a Polaris request that also requires credential vending should complete at p95 <= 5 seconds, excluding subsequent direct RustFS object transfer.
3. The local profile must support at least two distinct users issuing authorized operations concurrently. Authorization requests from one user must not impose a global lock that blocks another user's request.
4. No production-scale throughput, multi-instance, or high-availability claim is made. Polaris and RustFS resource limits remain those of the approved local stack.
5. These are measurable requirements, not demonstrated performance results. Focused and integrated measurements must report the environment, sample size, and result.

## Credential lifetime and refresh

1. Polaris-vended RustFS credentials should be valid for 3600 seconds. Polaris's credential cache target remains 600 seconds, strictly shorter than the credential validity period.
2. The implementation must validate the exact configuration-property names and behavior against the pinned Polaris 1.8.0 image and the RustFS 1.0.4 STS implementation before applying the values.
3. Spark/Iceberg should use the supported REST credential-refresh protocol before expiration when the pinned client supports it. Refresh must remain tied to the original user, role, catalog, and authorized location.
4. If refresh is unavailable, rejected, or cannot establish sufficient remaining validity, fail the affected operation and require a new Spark session when needed. No static RustFS key, root credential, bootstrap credential, or shared writer identity is an acceptable fallback.
5. Vended credentials remain only in the requesting Spark process/client's transient runtime state and are not logged, persisted, or displayed.

## Reliability and failure handling

- Authorization and credential vending fail closed if Polaris, Keycloak validation material, or RustFS credential-vending dependencies are unavailable.
- Permit at most one bounded retry for an idempotent/safe read after a transient transport failure. Do not retry authorization denial as another role or identity.
- Do not automatically replay a mutation when a timeout leaves its result ambiguous. Report a safe “outcome unknown” error and require the caller to inspect/reconcile state before retrying.
- A RustFS error does not trigger a broader credential scope or static-key fallback.
- Invalid/expired JWT, wrong issuer/audience, absent/unapproved role, out-of-scope location, expired credential, refresh failure, or storage denial fails the requested operation.
- Retry and refresh behavior must not change the authenticated principal or role context of a running Spark session.

## Security and privacy

1. Validate JWT signature, canonical issuer, expiry, and explicit `polaris` audience on Polaris operations.
2. Apply role grants to both Polaris catalog actions and the resolved RustFS object location. Developer mutations are dev-only; analysts remain read-only and production-only.
3. Vended credential scope must not exceed the authorized operation and catalog/table location. The 3600-second target is an upper validity duration, not permission to widen scope.
4. User Spark containers receive no RustFS root/bootstrap or persistent writer credentials.
5. Never place access JWTs, RustFS access/secret/session credentials, Keycloak client secrets, or notebook/query contents in logs, metrics labels, notebook output, persistent Spark configuration, or user homes.
6. No automatic retry may substitute an identity, role, catalog, bucket, or location.

## Observability

- Emit structured authorization-decision events containing correlation ID, validated principal, approved role names, resource/environment, operation class, allow/deny decision, latency, and safe failure category.
- Provide aggregate request counts and latency by bounded labels such as outcome, operation class, and environment. Do not use username, subject, token ID, JWT, request ID, table name, query text, or credential values as metric labels.
- Redact authorization headers, all JWTs, temporary access/secret/session credentials, client secrets, and request/query payloads from error paths and logs.
- The audit event must distinguish authentication/claim rejection, policy denial, credential-vending failure, and RustFS access failure without exposing sensitive values.

## Verification requirements

- Measure p95 authorization and credential-vending paths separately; do not mix in query scan/object-transfer time.
- Test two distinct users concurrently and show that one user's request does not globally serialize the other.
- Inspect the vended credential expiration and scope, exercise refresh with the pinned Spark/Iceberg client, and verify expiry/failure has no static-key fallback.
- Verify allowed/denied role-environment-operation cases and that denied requests do not receive credentials.
- Inspect application logs, container logs, Spark configuration/events, and notebook-visible errors for credential leakage.
- Any incompatibility in pinned Polaris/RustFS/Iceberg behavior must be recorded before changing versions or weakening the approved security behavior.
