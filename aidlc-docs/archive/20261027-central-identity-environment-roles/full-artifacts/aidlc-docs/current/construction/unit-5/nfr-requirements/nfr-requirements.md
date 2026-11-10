# Unit 5 NFR Requirements — Ranger and StarRocks Authorization

> **Superseded direction (2026-10-28):** The Ranger requirements below are retained as history, not current acceptance criteria. The user chose StarRocks native roles/grants mapped to FreeIPA LDAP groups without Ranger. Current NFR design and verification requirements are in `../nfr-design/` and `../../plans/unit-5-build-and-test-plan.md`. Direct Spark/RustFS, secret protection, test isolation, and preservation requirements still apply.

## Scope and quality profile

These requirements apply to the local proof of concept for Ranger-backed SQL authorization through StarRocks 4.1.6. They supplement the functional rules in `../functional-design/`. They do not define production availability, scale, latency SLA, audit-retention SLA, or recovery-point/recovery-time objectives.

The verification boundary is isolated FreeIPA/Ranger test state, disposable StarRocks FE/BE state, and synthetic tables/objects. Existing StarRocks metadata/volumes, HMS state, RustFS buckets and objects, credentials, workspaces, and KDC routing are preserved.

## Non-functional requirements

### Scale and performance

- Support the current local PoC identity profiles, environment databases, and small manually managed extensions only. No throughput, concurrent-session, or growth commitment is established.
- Authorization correctness takes precedence over latency. No end-to-end query or policy-decision latency SLA is established.
- LDAP, Ranger API/policy, and UserSync network operations must use finite timeouts and bounded retry behavior where configurable. Avoid unbounded retry loops and retry storms.
- Record sanitized timing for authentication, group synchronization, policy refresh, and authorization probes so future targets can be based on observed behavior.

### Availability, outage, and recovery

- The PoC is single-host/best-effort and has no HA, RTO, or RPO commitment.
- Failure of LDAP authentication/group resolution must not produce an authenticated role fallback.
- A new or uncached authorization must not be presumed allowed if Ranger is unavailable. Exact StarRocks FE behavior for last-known-good cached policies during Ranger Admin outage must be tested and documented; this specification does not claim all outage paths fail closed until evidence confirms it.
- Ranger, UserSync, LDAP, and StarRocks recovery is operator-led. Recovery must preserve policy state and existing data. No automatic policy broadening or fallback to native grants is allowed.
- Ranger service definitions and policies must be exported/protected before isolated test mutations, with restore demonstrated against isolated Ranger state.

### Revocation and consistency

- Do not claim immediate revocation or a fixed propagation SLA.
- Measure from FreeIPA membership removal through UserSync synchronization, Ranger policy state, FE policy polling/cache, and the first denied request.
- Measure both fresh authentication and an already-open SQL session. Record whether subsequent statements in active sessions are denied and whether a reconnect is required.
- Configure finite UserSync and FE policy-poll intervals where supported. Document the tested configuration and observed worst-case delay; no numeric maximum has been approved.
- Tests must show that stale directory or policy state does not grant a new role or broaden access beyond the last approved role matrix.

### Security and identity protection

- Use LDAPS/TLS with certificate validation for FreeIPA. Use TLS for Ranger API/policy endpoints where supported by the selected OSS components.
- Ranger UserSync LDAP bind access is read-only and scoped to required users/groups.
- Ranger, UserSync, and StarRocks service credentials must be protected as secret files or through an approved secret manager. Do not place secret values in source, ordinary Compose environment literals, command arguments, SQL output, generated documentation, or logs.
- Do not use Kerberos authentication between StarRocks Ranger integration and Ranger because StarRocks documentation says this is unsupported. Select a supported protected mechanism during infrastructure design.
- Preserve separation between the SQL user's identity evaluated by Ranger and the StarRocks FE/BE service identity used for HMS/RustFS access.
- Unknown users, unresolved/conflicting groups, and unrecognized resources/actions default to denial. No broad native grant may bypass the Ranger matrix.
- Do not use JavaScript-evaluated Ranger policy conditions with StarRocks.

### Auditability and logging

- Record sanitized principal, group context where available, resource, action, allow/deny outcome, policy/service identifier, timestamp, and bounded reason for StarRocks Ranger decisions.
- Audit must provide both allow and deny examples for each role during Build and Test.
- Use protected local audit files with rotation for the isolated PoC. No centralized audit service, immutable retention, or production retention duration is required by this intent at this stage.
- Logs must not contain passwords, bind credentials, S3 keys, Kerberos tickets/keytabs, object contents, unrestricted request bodies, or sensitive SQL literals.
- Distinguish authentication, group lookup/UserSync, Ranger policy, HMS, and RustFS failures in test evidence.

### Preservation and verification safety

- Unit 5 tests must not use existing production objects or mutate existing StarRocks/HMS state. Use uniquely named synthetic tables/objects and disposable state only.
- Before test policy changes, export the Ranger service definition and policy state and verify a restore into isolated state.
- Preserve existing StarRocks FE/BE named volumes, HMS metadata, RustFS bucket/object inventory, user workspaces, and current credentials. Clean up only resources uniquely created by a test run.
- Before/after snapshots must demonstrate that protected baseline state did not change.

### Compatibility and change control

- Keep StarRocks FE/BE pinned at 4.1.6 unless a documented compatibility failure is reviewed and an explicit architecture approval is obtained.
- Apache Ranger 2.9.0 is an evaluation candidate only. The exact Ranger release, Ranger Admin/UserSync images, StarRocks FE integration, service-definition JSON, and optional Ranger Admin autocomplete plugin must be pinned and integrity-checked only after exact-stack compatibility evidence.
- The documented StarRocks Ranger minimum is not proof that a later Ranger release works with this exact StarRocks pin.
- Any version change, gateway, new authorization component, Ranger service/plugin architecture change, production connection, or broad native-grant change requires explicit approval before implementation.

## Verification evidence required

Unit 5 Build and Test evidence must include:

1. Identity and group propagation for each approved role, including verifying `write-service-account` cannot log in interactively to JupyterHub while its separate, TLS-protected LDAP SQL login succeeds.
2. Allow/deny SQL matrix across production, development, and UAT through the actual Hive external catalog.
3. Supported write-action probes; prove narrowly scoped `write-service-account` materialized-view create/manage permissions and developer/analyst MV read scope, while unrelated database/table DDL and security-administration remain denied. Assert denied operations did not mutate metadata or objects.
4. Ranger Admin outage tests for cached and uncached policies, plugin restart/recovery, and no fallback to broader native grants.
5. Membership-removal propagation measurement for fresh and active sessions.
6. Audit evidence for allow and deny decisions with sensitive-data checks.
7. TLS trust validation and negative tests for invalid CA/endpoint configuration.
8. Isolated Ranger state backup/restore and before/after StarRocks/HMS/RustFS inventory comparison.
9. Separate direct Spark-to-RustFS allow/deny probes demonstrating that Ranger does not control direct Spark requests.

## Accepted limitations

- No concurrency, throughput, response-time, availability, revocation-latency, audit-retention, RPO, or RTO service level is established.
- Cached-policy behavior during Ranger outage and exact revocation latency remain unknown until measured.
- Exact Ranger/StarRocks 4.1.6 compatibility and LDAP group visibility remain hard verification gates.
- This local proof of concept is not a production-readiness claim.
