# Unit 1 NFR Design Plan — JupyterHub Foundation and OIDC Admission

## Purpose

Translate approved Unit 1 NFR requirements into local resilience, capacity, performance, security, and persistence patterns. Design remains for the local single-node Compose profile with at most two user servers and no SLA/HA commitment.

## Inputs

- `aidlc-docs/current/construction/unit-1/nfr-requirements/nfr-requirements.md`
- `aidlc-docs/current/construction/unit-1/nfr-requirements/tech-stack-decisions.md`
- `aidlc-docs/current/construction/unit-1/functional-design/`
- `aidlc-docs/current/inception/application-design/`
- Existing local runtime conventions in `docker-compose.yml`, `infra/jupyter/`, and `.runtime/credentials/`.

## NFR design work plan

- [x] Design Hub state, encrypted auth-state key, and per-user home persistence boundaries.
- [x] Choose the Hub database and restart/recovery behavior for a single Hub process.
- [x] Define spawn performance and image-availability patterns to meet the 120-second readiness target.
- [x] Define resource isolation and capacity controls for two concurrent user servers.
- [x] Define fail-closed recovery/cleanup and operator-visible lifecycle diagnostics.
- [x] Carry forward approved secret, network, token, and logging boundaries without expanding the security baseline.
- [x] Generate `nfr-design-patterns.md` and `logical-components.md` after answers are resolved.
- [x] Validate patterns against the approved NFR targets and functional lifecycle rules.

## Clarification questions

### Q1 — Hub state database

Which database pattern should persist JupyterHub state, including encrypted auth-state records?

A) Use SQLite stored on a dedicated persistent Hub state volume for this single Hub/local profile (Recommended; simplest and consistent with no HA/SLA).

B) Add a dedicated JupyterHub PostgreSQL database on the existing PostgreSQL service for a relational shared-service pattern.

X) Other (please describe).

[Answer]: A — Persist Hub state and encrypted auth state in SQLite on a dedicated persistent Hub volume; keep the crypt key outside that volume in protected runtime credentials.

### Q2 — Image readiness and per-user resource controls

The user server must become ready within 120 seconds for two concurrent users. Which resource/image pattern should the design use?

A) Build/pull the pinned matching Hub/single-user images before users spawn; configure per-server CPU/memory limits as host-tunable settings, then validate the two-server target on the supported machine (Recommended).

B) Pull/build images on first spawn and do not set per-server resource limits.

X) Other (please describe).

[Answer]: A — Pre-build/pull pinned matching Hub and single-user images before spawn; set host-tunable per-server CPU and memory limits and verify both servers can meet the target.

### Q3 — Spawn failure recovery

When DockerSpawner fails after creating some user resources, how should the recovery pattern behave?

A) Clean partial server/container resources, preserve the user's home, report a safe failure category, and require a deliberate user/operator retry (Recommended; avoids duplicate or uncontrolled retry loops).

B) Automatically retry once after cleanup, then report failure.

X) Other (please describe).

[Answer]: A — Clean partial server/container resources, preserve the home, report a safe failure category, and require a deliberate user/operator retry; do not auto-retry.

## Category assessment

- **Resilience:** Local single-node, no SLA. Q3 resolves automatic retry vs controlled retry; Keycloak outage and auth failures remain fail-closed.
- **Scalability:** Two simultaneous servers only; no horizontal or automatic scaling. Q2 defines per-server resource controls.
- **Performance:** Login callback ≤5 seconds and server-ready ≤120 seconds. Q2 resolves prebuilding/pulling images and how to apply limits.
- **Security:** Inherit Authorization Code flow, state/nonce validation, group admission, encrypted Hub auth state, protected runtime credentials, no secrets in user homes/logs, no Docker socket in user containers, and local-only HTTP. No additional compliance scope.
- **Logical components:** Q1 resolves the Hub state database. Other logical components are Hub, OIDC authenticator, DockerSpawner, Hub crypt key, user home volumes, and safe lifecycle logs.

## Next gate

All three answers select clear, compatible recommendations. Generated the NFR pattern and logical-component artifacts for review. No application code or runtime configuration was changed.

**Approval prompt recorded 2026-10-28T18:51:05Z:** “Review Unit 1 NFR Design at `aidlc-docs/current/construction/unit-1/nfr-design/`: `nfr-design-patterns.md` and `logical-components.md`. They apply persistent SQLite Hub state with a separate protected crypt key, preloaded pinned images and configurable per-user resource limits, bounded capacity, and cleanup with deliberate retry after spawn failure. Approve to continue to Infrastructure Design, or request changes.”
