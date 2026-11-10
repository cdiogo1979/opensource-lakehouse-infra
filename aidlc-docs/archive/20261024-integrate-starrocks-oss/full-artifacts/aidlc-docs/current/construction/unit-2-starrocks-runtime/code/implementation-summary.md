# Unit 2 StarRocks Runtime — Code Generation Summary

## Implemented scope

Implemented US-05 runtime support for one StarRocks FE and one BE behind the opt-in Compose profile `starrocks`. The default Compose startup remains unchanged. No Hive catalog SQL, SQL users/roles/grants, sample databases, or sample tables are created in this unit.

## Changed application paths

- `docker-compose.yml` — adds the opt-in FE, BE, and one-shot state preflight services; FE/BE named volumes; health checks; loopback FE UI/SQL endpoints; read-only credential/config inputs; and isolated TGT tmpfs mounts.
- `infra/starrocks/fe/Dockerfile`, `infra/starrocks/be/Dockerfile` — derive from StarRocks 4.1.6 FE/BE images pinned by multi-platform digest and install pinned Ubuntu Kerberos and cron package versions. Their build context is restricted to `infra/starrocks/`, excluding local runtime credentials.
- `infra/starrocks/fe/entrypoint.sh`, `infra/starrocks/be/entrypoint.sh` — validate inputs, acquire initial tickets, set the documented Java Kerberos option, start ticket refresh, and start FE/BE in foreground. Host-side startup handles backend registration using the protected root credential after bootstrap.
- `infra/starrocks/conf/core-site.xml`, `infra/starrocks/conf/hive-site.xml` — minimal credential-free Hadoop Kerberos and Hive Metastore SASL settings mounted read-only into FE/BE; the full Hive configuration is not shared with StarRocks.
- `infra/starrocks/kerberos/refresh-ticket.sh`, `infra/starrocks/kerberos/starrocks-ticket-refresh` — refresh the node's TGT hourly and emit only fixed, redacted status text.
- `infra/starrocks/preflight/Dockerfile`, `infra/starrocks/preflight/check-paired-state.sh` — inspect only the FE and BE named volumes through read-only mounts and fail closed for unknown or one-sided state.
- `scripts/start-starrocks.sh` — build the local runtime images, require the already-running KDC to be healthy, run a fresh preflight, start FE/BE, then register and verify the BE through host-side SQL credentials.
- `README.md` — documents startup, endpoints, readiness limits, ticket refresh, logs, persistence, and safe recovery.

## Identity and storage contract

FE and BE consume `.runtime/credentials/keytabs/starrocks.keytab`, `infra/kerberos/krb5.conf`, and the file-backed `rustfs-starrocks-secret-key` secret. Keytab and config mounts are read-only. The Kerberos principal is `starrocks@${KERBEROS_REALM}` and the RustFS access-key ID is `starrocks`; secret values are not written into tracked files or emitted by scripts. Each node has its own `/run/krb5` memory-backed cache.

FE state persists in named volume `iceberg-poc-starrocks-fe-meta` at `/opt/starrocks/fe/meta`; BE state persists in `iceberg-poc-starrocks-be-storage` at `/opt/starrocks/be/storage`. The preflight performs no writes and does not mount any shared platform state.

## Image pins and verification status

- FE base: `starrocks/fe-ubuntu:4.1.6@sha256:d07aa750be77625a09866a76dbfe0ee032baeb5e48fe0e952d30cb525329dc31`.
- BE base: `starrocks/be-ubuntu:4.1.6@sha256:bf0f5ca7fd9fc4e568d4d0e593e362f229b376976b513a5a549b1b922d9ec23b`.
- Preflight base: `debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171`.
- FE and BE images built successfully and both services reached healthy state during Build and Test.
- Runtime verification confirmed StarRocks FE can authenticate to the secured Hive Metastore and discover the two sample databases after mounting the minimal configs.
- Build and Test still needs to verify positive writer DML/readback, Spark interoperability, controlled restart persistence, notebook workspace preservation, and resource needs.

## Traceability

| Story/requirement | Implementation |
|---|---|
| US-05 / FR-1 | Pinned FE/BE runtime images, opt-in Compose profile, health checks, operator startup wrapper |
| FR-5 / NFR-1 | Per-node keytab use, private TGT cache, hourly refresh, secret-free diagnostics |
| FR-7 / NFR-3 | Paired-volume read-only preflight and fail-closed startup behavior |
| NFR-4 | Fixed FE/BE topology and image/package pins; measurement is deferred to Build and Test |
| NFR-5 / NFR-6 | Compose log workflow and documented persistence/recovery boundary |
