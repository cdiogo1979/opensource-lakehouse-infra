# Build and Test Summary — Cleanup and Modular Compose

Run on 2026-11-09 against the live local stack. **The result passed**, with two existing defects found and fixed, and one known failure recorded.

| Check | Result |
|---|---|
| Contract suite | 217 passed, 1 skipped, plus 2 earlier Airflow drift failures. Broker tests: 10 passed |
| Product bootstrap end to end | Pass (exit 0), the first full run since the legacy Spark image disappeared: start through the modules; realm, users, Polaris, buckets, catalogs, and grants; the writer check; Spark smoke tables in prod, UAT, and dev; StarRocks catalogs (`equal`), roles, smoke reads, and users |
| Repeat `start` | No container recreated, after the attestation fix (below) |
| Opt-outs | Core-only `status` lists core only. Core-only `start` prints three notices, leaves the module containers unchanged, and shows no orphan warnings |
| Stop and start | Everything stopped, then everything healthy with the same container IDs |
| Verifiers | RustFS OIDC 7/7; RustFS STS; Polaris negative cases; Polaris writer check; role matrix fully passing, including the Spark data part (four roles across three environments, cleanup restored the smoke tables); StarRocks login as peter-analyst (analyst role); Airflow production and UAT DAGs registered (run with the Airflow environment from `lakehouse.sh`, as `start-airflow` does) |
| Jenkins verifier | 8/9. "Workload CI job is missing" is the known follow-up |

## Defects found and fixed
1. **Containers recreated on every start.** This predates this intent. With the containerd image store, BuildKit adds a timestamped provenance attestation, so a fully cached build got a new image ID and Compose recreated Jenkins, JupyterHub, and the reconciler on every start and bootstrap. Fixed by exporting `BUILDX_NO_DEFAULT_ATTESTATIONS=1` in both entry scripts, which was verified: identical image IDs and no recreation.
2. **Misleading orphan warnings.** Commands that pass only some module files made Compose suggest `--remove-orphans`, which would delete the other modules. Fixed with `COMPOSE_IGNORE_ORPHANS=true` in both entry scripts and a README warning.

## Notes
- `scripts/verify/airflow-dags.sh` needs the Airflow variables set by `lakehouse.sh`, so it is meant to be called from `start-airflow`. Run on its own, it times out. Behavior unchanged.
- Local images were pruned outside this session earlier today. The Spark runtime image was rebuilt from its Dockerfile.
- DBeaver: the user verified that the StarRocks connection type needs only `idTokenFile`. The README was updated, and its test passes.
