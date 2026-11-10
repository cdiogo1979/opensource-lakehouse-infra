# Unit 1 Code Generation Summary

## Implemented

- Replaced `docker-compose.yml`; added the inventory-only `docker-compose.deferred.yml` and a new `.env.example`.
- Added `scripts/lakehouse.sh`, `scripts/prepare-lakehouse-runtime.py`, and `infra/polaris/init-polaris-schema.sh`.
- Replaced the legacy `README.md`; added `image-compatibility.md` and this code summary.
- Removed the old root compose overlays for FreeIPA production, Ranger testing, and StarRocks LDAP testing, along with obsolete legacy operator entry scripts.
- Replaced the default Compose graph with Keycloak 26.8.1, dedicated Keycloak PostgreSQL, Apache Polaris 1.8.0, dedicated Polaris PostgreSQL, RustFS 1.0.4, and an explicitly profiled Polaris schema helper.
- Bound published provider ports to loopback and defined new project-scoped named volumes. No old volume or object-store mount is referenced.
- Added protected, create-once credential/config generation and `scripts/lakehouse.sh start|status|stop` with bounded provider readiness and volume-preserving stop behavior.
- Runtime testing showed that host-owned `0600` source files cannot be read by non-root images through local Compose bind-mounted secrets. The generator now keeps authoritative files `0600` in a `0700` directory and stages service-specific `0644` read-only mount copies inside a separate host `0700` directory. Polaris `pgpass` stays `0600`.
- Added the idempotent `polaris_schema` initializer and rewrote operator documentation for the new runtime boundary.
- Removed the old root compose overlays and obsolete operator entry scripts for the previous FreeIPA/Hive/Kerberos setup.
- Added a deferred integration inventory for Airflow, JupyterHub, Jenkins, and StarRocks; it intentionally contains no runnable services and is not used by the core lifecycle script.
- Following the user's explicit approval on 2026-10-28, removed exactly `infra/freeipa`, `infra/hive`, and `infra/kerberos`. No other legacy directories, runtime volumes, RustFS objects, credentials, or running containers were touched.

## Traceability

Implementation follows U1 Infrastructure Design and Deployment Architecture. It creates only the local providers and Polaris metadata schema. Keycloak realm/groups, Polaris realm/catalog/database bootstrap, product buckets/policies, and smoke tables remain later-unit work.

## Open acceptance items

- RustFS 1.0.4 remains pinned by version tag only, as explicitly accepted by the user on 2026-10-28. Build and Test will record the digest/platform actually pulled; immutable digest pinning is waived for RustFS.
- Keycloak, Polaris, and PostgreSQL digests are provisionally recorded in `image-compatibility.md`; confirm the selected registry manifests and target architecture in Build and Test.
- Other legacy/deferred directories remain in this project copy and were outside the approved deletion scope. The default Compose and lifecycle entry points do not activate them.
- Deferred integrations are inventory metadata only, not a functional overlay. This was chosen after inspection confirmed the old definitions depend on retired services and config.

## Build and Test activity so far

- Compose syntax, shell syntax, and Python AST checks passed. Docker reports `linux/arm64`.
- The Keycloak, Polaris, PostgreSQL, and RustFS images were pulled. RustFS 1.0.4 resolved to `sha256:ed9210d6411d77ffceb70d94b964a3cb7d225983368bc25bebe01e995293dcc2` for `linux/arm64`.
- The first start created only the three new project-scoped volumes and the `lakehouse-local_core` network. PostgreSQL became healthy; RustFS exited because its non-root image could not read the host-owned `0600` source file through a local Compose bind mount.
- The approved stop command stopped the new project's running services without removing volumes. No legacy project containers, volumes, or RustFS objects were modified.
- Runtime credentials and config were generated locally and were not printed. The mount permission fix is implemented but has not yet passed a second startup.

## Build and Test handoff

After the staged-mount permission fix passes, verify Keycloak and Polaris health, the Polaris schema initializer, loopback endpoints, service-specific readable mounts, PostgreSQL and RustFS persistence across restart, and safe stop behavior. Record final outcomes in `aidlc-docs/current/construction/unit-1/build-test-report.md`.
