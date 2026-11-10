# Unit 1 Build and Test Report

**Date:** 2026-10-28  
**Project:** `opensource-lakehouse-infra-v2`  
**Compose project:** `lakehouse-local`  
**Docker platform:** `linux/arm64`

## Result

**PASS** for the Unit 1 local provider runtime on the tested Docker platform. This does not verify the later Keycloak identity, Polaris catalog authorization, bucket/policy, or Spark data-product journeys owned by Units 2–4.

## Image verification

The approved Keycloak, Polaris, and PostgreSQL immutable references were pulled successfully and their local repo digests matched the configured references. RustFS 1.0.4 was pulled using the user-approved version tag and resolved locally to `sha256:ed9210d6411d77ffceb70d94b964a3cb7d225983368bc25bebe01e995293dcc2` on arm64. The tag-only policy for RustFS was accepted by the user. See `code/image-compatibility.md` for the full matrix.

## Checks completed

- `docker compose config --quiet` passed.
- `bash -n` passed for the lifecycle and Polaris schema scripts; Python AST parsing passed for the runtime file generator.
- The primary Compose graph contains only Keycloak, its PostgreSQL database, Polaris, its PostgreSQL database, RustFS, and the explicitly invoked schema initializer. The supported startup path has no FreeIPA, Hive, or Kerberos services.
- Docker inspection confirmed Keycloak (`8080`), Polaris (`8181`), RustFS S3 (`9000`), and RustFS console (`9001`) publish only on `127.0.0.1`. Neither PostgreSQL container publishes a host port.
- After the mount fix, `scripts/lakehouse.sh start` reached healthy status for both PostgreSQL services, Keycloak, Polaris, and RustFS.
- Keycloak root returned HTTP 200. Polaris's `/api/catalog/v1/config` returned HTTP 401 without credentials, confirming the API endpoint responded and required authentication; `/` and the unauthenticated catalog root returned 404. RustFS `/health/ready` returned HTTP 200. RustFS console root returned HTTP 403 without a session; the container healthcheck was healthy.
- Polaris schema initialization succeeded on initial startup and again on rerun (`polaris_schema` already exists). It remained available after stop/restart.
- Authoritative files are mode `0600` in `.runtime/credentials/` (`0700`). Service-readable staging copies are mode `0644` in `.runtime/container-mounts/` (`0700`) and mounted read-only. Polaris `pgpass` remains mode `0600`.
- Keycloak and RustFS service users successfully read their assigned mounted files; Polaris started healthy using its mounted config. Credential values were absent from environment metadata for all five provider containers and absent from captured core logs. No credential values were emitted.
- The documented `stop` command stopped only the `lakehouse-local` services. All three named volumes remained present, and the subsequent start returned all five services to healthy status.

## Issues found and fixed

1. **Host-owned `0600` bind mounts were unreadable by non-root images.** RustFS initially exited because it could not read the mounted access-key source file. The generator now preserves authoritative source files at `0600` and stages service-specific `0644` copies under a separate host `0700` directory. Compose mounts those copies read-only. The second startup verified the fix.
2. **Keycloak image has no `curl`.** Its original HTTP healthcheck failed with `curl: command not found`. The healthcheck now uses the image's Bash `/dev/tcp` support to check the readiness endpoint's HTTP status. Keycloak reached healthy status after the probe change.

## Scope limits

- No buckets, objects, Polaris realms/catalogs/namespaces, product roles, or test tables were created; those belong to later units.
- No legacy project containers, volumes, or RustFS objects were touched.
- No image builds were needed. No destructive volume command was used.
- The stack is currently running and healthy after the persistence restart.
