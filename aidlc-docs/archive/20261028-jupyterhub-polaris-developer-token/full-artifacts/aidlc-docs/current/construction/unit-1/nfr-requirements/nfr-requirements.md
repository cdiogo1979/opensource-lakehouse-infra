# Unit 1 NFR Requirements — JupyterHub Foundation and OIDC Admission

## Scope

These quality requirements apply to the local single-node Compose profile, Hub OIDC login/admission, user server startup, encrypted Hub state, and per-user persistent homes. They do not assert a production SLA or broaden the explicitly approved security scope.

## Scalability

- The initial profile shall support two simultaneous single-user servers: one developer and one analyst.
- The profile does not need autoscaling, multi-host scheduling, or shared Spark capacity. More than two simultaneous users requires capacity review and a revised profile.
- Each user server remains isolated in its own container with its own named home volume.

## Performance

- After Keycloak returns the OIDC callback to Hub, Hub processing to a completed login response shall take no more than 5 seconds on the supported local host. This excludes user interaction with Keycloak and time before the callback arrives.
- A requested, admitted single-user server shall report ready within 120 seconds on the supported local host.
- Report callback processing and server startup durations using timestamps and safe correlation metadata. Do not include tokens or secrets in measurements or logs.
- Construction verification shall state the local host/image conditions used for timing; these are local acceptance targets, not guarantees on other machines.

## Availability, recovery, and durability

- The local profile has no uptime SLA, high availability, failover, or disaster-recovery target. Container or host restart may interrupt active sessions.
- Normal service restarts shall preserve Hub persistent state and per-user named home volumes.
- Automated backup and restore is outside this unit. The operator is responsible for separately backing up protected Hub state, encryption keys, and user homes if needed.
- Removal of named volumes, local disk loss, or unavailability of Keycloak are outside the persistence guarantee. New login/admission fails closed when Keycloak is unavailable.

## Security and privacy

- Retain the approved Authorization Code flow, OIDC state/nonce validation, approved-group admission, and failure-closed behavior.
- Encrypt Hub auth state at rest, including OAuth tokens. Keep client secrets and refresh tokens in Hub-controlled protected storage; never mount them into user home volumes.
- Do not log access tokens, refresh tokens, client secrets, or user data. Logs may include validated identity, request correlation, lifecycle event, timing, and safe failure category.
- Do not give single-user containers the Docker socket, Hub database credentials, or Keycloak confidential-client secret.
- Keep each server and persistent home isolated to the owning Hub identity. Clean partial containers on spawn failure without deleting that user's home.
- Local HTTP callback and issuer behavior apply only to the local development profile. Any later shared/production deployment requires a separately approved TLS and public endpoint design.
- Do not add compliance certifications or controls from the declined broader Security Baseline; retain the security properties necessary for the approved OIDC/token flow.

## Reliability and maintainability

- Invalid OIDC response, unresolved group membership, auth-state persistence failure, or spawn failure shall not result in an authenticated or running unauthorized server.
- Failed partial spawns shall be cleaned before an operator/user retry. A retry shall reuse the same user's persistent home.
- Pin exact Python package versions and immutable container image digests after compatibility validation. Hub and single-user image JupyterHub versions must match.
- Keep configuration and image build inputs in the existing `infra/jupyter/hub/` and `infra/jupyter/singleuser/` areas; configuration checks must be repeatable.

## Usability and operations

- Use the standard JupyterHub login, callback, spawn, and stop user experience; no custom frontend is required.
- Operators shall be able to distinguish OIDC authentication failure, group-admission denial, auth-state failure, and spawn failure without retrieving credentials.
- If membership is removed during a running server, stop it at the next Hub admission/auth-state revalidation; where no automatic trigger exists, an operator must stop it. No instantaneous revocation guarantee is made between checks.

## Acceptance measurements

1. Start developer and analyst servers concurrently without cross-user access; verify the stated two-server capacity.
2. Measure from Hub callback receipt to login response and verify ≤5 seconds under the recorded local conditions.
3. Measure from admitted spawn request to ready server and verify ≤120 seconds under the recorded local conditions.
4. Restart services without deleting volumes; verify Hub state and both user homes remain present.
5. Confirm logs and user home volumes contain no access token, refresh token, or client secret.
6. Confirm user containers have no Docker socket or Hub/provider administrative credential mounts.

These are requirements for later verification; tests are not run as part of this document-generation step.
