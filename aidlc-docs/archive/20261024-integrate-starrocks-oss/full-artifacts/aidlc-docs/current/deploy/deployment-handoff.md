# Deployment Handoff — StarRocks OSS Integration

## Handoff status

Build and Test was closed on 2026-10-25 with the user's approval to accept documented verification limitations. This handoff records the current local PoC state and operating steps. It does not claim production readiness or perform a deployment.

## Current environment

The local Docker Compose stack is running. Hive Metastore, PostgreSQL, Kerberos, RustFS, Spark, and JupyterHub are shared platform services. StarRocks FE/BE are opt-in and were restored to their original unlimited Docker resource settings after the constrained query test. StarRocks FE/BE named volumes were preserved. Credentials were not rotated and no persistent volumes were reset.

Loopback endpoints:

- StarRocks FE UI: <http://127.0.0.1:8030>
- StarRocks MySQL protocol: `127.0.0.1:9030`
- RustFS console: <http://127.0.0.1:9001>
- JupyterHub: <http://127.0.0.1:8008>
- Spark UI: <http://127.0.0.1:8082>

## Operator commands

Start the base platform and provision identities, if needed:

```bash
./scripts/start.sh
./scripts/provision-identities.sh
```

Start StarRocks and inspect health:

```bash
./scripts/start-starrocks.sh
docker compose --profile starrocks ps
```

Stop StarRocks while preserving its volumes:

```bash
docker compose --profile starrocks stop starrocks-be starrocks-fe
```

Start it again through the wrapper so the paired-state preflight and secret-safety canary run:

```bash
./scripts/start-starrocks.sh
```

Do not remove or reset the `starrocks-fe-meta` or `starrocks-be-storage` volumes as a routine recovery action. A failed paired-state preflight is fail-closed; inspect its preserved logs and resolve the discrepancy deliberately.

SQL account/catalog bootstrap must use the documented host MySQL-compatible client flow and canary gate in `README.md`. Passwords and object-store secrets are in ignored `.runtime/credentials/`; never paste their values into chat or commit them. The SQL access matrix and tested setup are documented in the README and Unit 3 artifacts.

## Tested reference profile and limits

For one read-only scale-factor-1 TPC-H Q1 query, FE and BE each passed with 2 CPUs and 2 GiB memory. This is the lowest tested per-node profile, not a proven minimum. The full stack was tested on a Docker allocation of 6 CPUs and 15.6 GiB. The observed StarRocks images occupied about 2.79 GB (FE) and 3.82 GB (BE); measured volume usage was small at the time of inspection. Reserve at least 10 GB incremental Docker storage for the StarRocks images and state as a practical starting allowance, excluding shared images and future warehouse growth. Docker Desktop quota and actual storage growth were not measured.

The tested query was read-only. ETL concurrency, production-scale workloads, backup/restore, high availability, and recovery from host or disk failure are outside the verified scope. Local Compose endpoints bind to loopback and this PoC is not a production security/deployment design.

## Accepted verification limitations

The user approved closing Build and Test with limitations. These checks remain unverified:

- Live FE/BE ticket refresh failure while a valid TGT remains usable, and behavior after TGT expiry. Only the helper's isolated invalid-keytab diagnostic was exercised; live service ticket caches and the KDC were not disrupted.
- Docker Desktop storage quota and storage growth under ETL/concurrency.
- Resource profiles below 2 CPUs/2 GiB per FE/BE.

Do not represent these as passed. Reopen verification before relying on those behaviors or sizing assumptions for a broader workload.

## Handoff evidence

See [Build and Test plan](../construction/plans/build-and-test-plan.md), [README](../../../README.md), and [AI-DLC state](../aidlc-state.md) for test evidence, operating procedures, and the accepted waiver. Deployment execution is pending and requires its own operational decision; this handoff has not changed running services or persistent data.
