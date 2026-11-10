# Unit 1 Build and Test Plan — Core Runtime

## Objective

Verify the generated Keycloak, Polaris, PostgreSQL, and RustFS local runtime against the approved U1 infrastructure and NFR designs. Use only the new `lakehouse-local` Compose project and its project-scoped volumes. Do not start or alter legacy services, volumes, or object stores.

## Approved image policy

- Verify the immutable Keycloak, Polaris, and PostgreSQL references against the registry and host architecture.
- Use `rustfs/rustfs:1.0.4` as the user-approved tag-pinned reference. Record the resolved digest and platform from the registry/pull for evidence; do not rewrite the accepted Compose tag as part of verification.
- Do not use `latest` tags or substitute unverified/older digests.

## Sequential verification steps

### Step 1 — Static Compose and local command review

- [x] Validate Compose syntax and interpolation without creating containers.
- [x] Confirm the primary graph contains only Keycloak, its PostgreSQL database, Polaris, its PostgreSQL database, RustFS, and the explicit schema-init helper.
- [x] Confirm host ports are loopback-only; database and private management ports are not published.
- [x] Confirm no FreeIPA, Hive Metastore, or Kerberos service/configuration is active in the supported startup path.
- [x] Inspect scripts for safe secret handling, bounded readiness, redacted status, and volume-preserving stop semantics.

### Step 2 — Image and platform verification

- [x] Confirm the local Docker architecture and registry availability (`linux/arm64`).
- [x] Pull and verify the Keycloak, Polaris, and PostgreSQL immutable references for the local platform.
- [x] Pull RustFS 1.0.4 by the accepted version tag and record the actual registry digest and platform (`linux/arm64`); do not expose credentials.

### Step 3 — Fresh runtime startup and health

- [x] Start only the new core Compose project using the documented operator command.
- [x] Verify readiness for both databases, Keycloak, Polaris, and RustFS within the configured startup deadline.
- [x] Verify the schema helper creates only `polaris_schema` and completes idempotently.
- [x] Verify the configured endpoints respond on loopback and no private endpoint is host-published.
- [x] Inspect diagnostics for useful failure context and absence of credential values.

### Step 4 — Persistence and safe stop

- [x] Verify source credential/config files are mode `0600` under a `0700` directory; per-service mount copies are mode `0644` under their own `0700` host directory and are mounted read-only; keep Polaris `pgpass` mode `0600`. Do not print file contents.
- [x] Verify Keycloak and RustFS service users can read their assigned mounted files; Polaris starts healthy with its mounted configuration. Credential values are absent from all five containers' environment metadata and from core logs.
- [x] Verify PostgreSQL data and Polaris schema survive a normal stop/restart; schema initializer confirms the schema already exists.
- [x] Verify RustFS health and its new named volume survive a normal stop/restart. No buckets or objects were created, per the plan boundary.
- [x] Confirm stop does not remove volumes and does not target legacy or unrelated containers.

## Safety boundaries

- Do not run `docker compose down -v`, prune Docker resources, or remove any volume.
- Do not connect to or modify the old project or any previously running Compose project.
- Do not create data-product catalogs, namespaces, buckets, policies, roles, or test tables; those belong to later units.
- Never include secret values in logs, screenshots, test output, or the evidence report.
- If registry access is unavailable, report the exact blocked check; do not silently substitute image references.

## Evidence and completion criteria

Record command outcomes, service health, architecture/digest evidence, port bindings, schema state, protected file modes, and persistence results in a Build and Test report. Mark U1 Build and Test complete only when all applicable checks pass or a clearly scoped verification waiver is explicitly accepted by the user. No production deployment is part of this unit.

## Approval gate

The user approved this plan on 2026-10-28. All U1 checks completed successfully. Initial startup exposed a bind-mount permission issue and a missing `curl` in Keycloak; the host-private staging-copy fix and Bash-based HTTP readiness probe passed on subsequent startup and persistence restart. See `aidlc-docs/current/construction/unit-1/build-test-report.md`.
