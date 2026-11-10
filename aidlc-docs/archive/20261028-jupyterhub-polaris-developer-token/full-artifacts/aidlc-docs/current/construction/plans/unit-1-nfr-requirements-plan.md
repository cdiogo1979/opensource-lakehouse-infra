# Unit 1 NFR Requirements Plan — JupyterHub Foundation and OIDC Admission

## Purpose

Set measurable quality requirements and technology constraints for the Unit 1 Hub, OIDC admission, isolated single-user runtime, auth-state persistence, and user home lifecycle. Scope remains the approved local Compose journey; it does not add production HA or broaden the declined security baseline.

## Inputs

- Unit 1 functional design: `aidlc-docs/current/construction/unit-1/functional-design/`.
- Unit definition and ownership: `aidlc-docs/current/inception/application-design/unit-of-work.md`.
- Approved requirements: `aidlc-docs/current/inception/requirements/requirements.md`.
- Current application stack: local Docker Compose with Keycloak, Polaris, RustFS, and PostgreSQL; JupyterHub is currently deferred.
- Existing OIDC callback: `http://jupyterhub.localhost:8000/hub/oauth_callback` for the local profile.
- Non-negotiable inherited controls: Authorization Code flow, state/nonce validation, approved-group admission, encrypted Hub auth state, no tokens in logs or user homes, per-user isolation, and no Docker socket in user containers.

## NFR assessment work plan

- [x] Set initial concurrency and measurable Hub login/server startup targets.
- [x] Define local availability, persistence, recovery, and backup expectations.
- [x] Select supported JupyterHub/OIDC authenticator/DockerSpawner and matching single-user image version policy.
- [x] Confirm security and privacy requirements inherited from the approved functional and application design.
- [x] Define observability and operator support requirements for admission and server lifecycle.
- [x] Generate `nfr-requirements.md` and `tech-stack-decisions.md` after answers are resolved.
- [x] Validate every choice against Unit 1 scope and record NFR requirements for later NFR Design.

## Clarification questions

### Q1 — Initial capacity and performance targets

What should Unit 1 support on the local developer machine, and what startup targets should we use?

A) Two simultaneous user servers (one developer and one analyst); after Keycloak returns the OIDC callback, Hub processing completes within 5 seconds, and an admitted server becomes ready within 120 seconds on the supported local host (Recommended starting target).

B) Specify a different concurrent-user count and callback/server-ready targets.

X) Other (please describe).

[Answer]: A — Support two simultaneous user servers; Hub callback processing ≤5 seconds after Keycloak returns the callback, and admitted user server ready ≤120 seconds on the supported local host.

### Q2 — Availability, persistence, and backups

Which resilience expectation applies to this local single-node journey?

A) No uptime SLA or HA; service/container restart may interrupt sessions. Persist Hub state and per-user named homes across normal restarts. Backups are out of scope and must be handled separately by the operator (Recommended).

B) Add a stated recovery target and an automated backup/restore requirement for Hub state and user homes.

X) Other (please describe).

[Answer]: A — Local single-node only, no uptime SLA/HA; persist Hub state and named homes across normal service restarts; no automated backup/restore requirement, operator handles backup separately.

### Q3 — JupyterHub and image version policy

The official JupyterHub changelog lists 6.1.1 as the latest release on 2026-10-28 and reports a 6.1.0 security-fix release; DockerSpawner requires the single-user image's JupyterHub version to match the Hub. Which version policy should guide Unit 1?

A) Start with JupyterHub 6.1.1, Python 3.10 or later, and a custom Spark-enabled single-user image using the matching JupyterHub version; pin exact package versions and image digests after compatibility validation (Recommended for a new local install).

B) Use the latest compatible 5.5.x maintenance release instead; pin exact versions/digests after validation.

X) Other version or image policy (please describe).

[Answer]: A — JupyterHub 6.1.1, Python 3.10 or later, custom Spark-enabled single-user image with matching JupyterHub version; pin package versions and image digests after compatibility validation.

## Category analysis

- **Scalability:** Local Compose and per-user containers are approved; initial simultaneous-user capacity is not specified. Q1 resolves it.
- **Performance:** No measurable login or spawn target exists. Q1 proposes callback processing and server-ready targets.
- **Availability:** Single-node local operation is approved, but SLA, restart, and recovery expectations need an explicit boundary. Q2 resolves it.
- **Security:** Inherit only the controls already approved for this flow. These include OIDC state/nonce, group admission, encrypted Hub token state, secret isolation, no user-container Docker socket, and no token logging/persistence. No new compliance scope is proposed.
- **Technology stack:** Version compatibility and immutable pin policy are open for the new Hub. Q3 resolves the major-version/image direction; exact compatible dependencies and digests are validated in later design/build stages.
- **Reliability:** Fail closed on Keycloak outage, invalid auth state, admission failure, or spawn failure; clean partial server resources and preserve user home. Q2 clarifies restart/backup boundaries.
- **Maintainability:** Keep config and image ownership under existing `infra/jupyter/` paths; pin versions and add repeatable configuration checks in the relevant implementation plans.
- **Usability:** Keep standard JupyterHub login and server feedback; no custom frontend. The callback/spawn targets are defined in Q1.

## References

- [JupyterHub 6.1.1 changelog and supported maintenance releases](https://jupyterhub.readthedocs.io/en/stable/reference/changelog.html)
- [JupyterHub quickstart prerequisites](https://jupyterhub.readthedocs.io/en/stable/tutorial/quickstart.html)
- [DockerSpawner image version compatibility](https://jupyterhub-dockerspawner.readthedocs.io/en/latest/docker-image.html)
- [OAuthenticator OIDC and group admission configuration](https://oauthenticator.readthedocs.io/en/latest/reference/api/gen/oauthenticator.generic.html)

## Next gate

The three answers are specific and consistent with the local-only scope. NFR requirements and technology decisions have been generated below and await review. No code or runtime configuration was changed.

**Approval prompt recorded 2026-10-28T18:49:01Z:** “Review Unit 1 NFR Requirements in `aidlc-docs/current/construction/unit-1/nfr-requirements/`: `nfr-requirements.md` and `tech-stack-decisions.md`. They record two concurrent servers, callback processing ≤5 seconds, server-ready ≤120 seconds, single-node/no-SLA operation with persistent volumes and operator-managed backups, and the selected JupyterHub 6.1.1 matching-image policy. Approve to continue to Unit 1 NFR Design, or request changes.”
