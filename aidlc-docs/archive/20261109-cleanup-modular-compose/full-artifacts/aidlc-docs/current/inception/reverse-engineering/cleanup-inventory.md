# Cleanup Inventory

References were found by searching the repository, excluding `aidlc-docs`, `.runtime`, `.agents`, `.claude`, and caches. "Live" means started or called by `scripts/lakehouse.sh`, `bootstrap-default-product.sh`, a Compose file, or a Dockerfile.

## A. Unused by the current solution
| Path | What it is | References | Recommendation |
|---|---|---|---|
| `infra/tpch-generator/` (8 KB) | TPC-H data generator | none | Remove (requested) |
| `infra/tpch-loader/` (52 KB) | TPC-H loader; still references `write-service-account` | none | Remove (requested) |
| `infra/identity-provisioner/` | FreeIPA-era Postgres role provisioning | `tests/rustfs/test_legacy_retirement.py` (asserts that old files inside it are absent) | Remove; keep the retirement test as an absence check |
| `infra/bucket-init/` | Old bucket-init image; its requirements are used only by the one-time reset below | README "One-time catalog path reset" section | Remove together with the one-time reset |
| `infra/polaris/reset-default-product-once.py` | One-time Polaris path-layout reset (intent 20261028), superseded by `lakehouse.sh reset` | README section only | Remove, with its README section |
| `scripts/prepare-ranger-test-secrets.sh` | Ranger test secrets (Ranger never adopted) | none | Remove |
| `docker-compose.deferred.yml` | Inventory only; every listed service is now implemented | README, two tests | Remove; the modular files replace it |
| `Jenkinsfile` (root) | CI pipeline for this repository's tests. Jenkins has no job for this repository ("There is no job for this infrastructure repository") | README mentions | Decide: remove, or keep for a future CI job |
| `infra/jupyter/examples/spark-authz.py` | Notebook example from an earlier unit | none; neither Jupyter Dockerfile copies it | Remove |
| `__pycache__/`, `.pytest_cache/`, `.hypothesis/` | Local caches | git-ignored (`.hypothesis` is not) | Delete the caches and add `.hypothesis/` and `.pytest_cache/` to `.gitignore` |

## B. Still live, but tied to completed legacy work
| Path | What it is | Live use | Recommendation |
|---|---|---|---|
| `scripts/migrate-jenkins-home.py` and `lakehouse.sh remove-legacy-jenkins` | One-time copy of the pre-v2 Jenkins home; guarded removal of the legacy instance | Start runs the migration script, which now only writes a `fresh` marker, because the legacy volume is gone | Decide: simplify (drop the migration and legacy removal) or keep |
| `scripts/bootstrap/smoke-spark.sh`, `infra/spark-bootstrap/`, `scripts/verify/role-matrix.py` (Spark part) | Spark smoke tables and role-matrix data checks | Run by the product bootstrap and verifier, but broken: the image `local/spark-iceberg:3.5.5_1.8.1-krb5` is gone | Decide: repoint to the v2 Spark runtime, or remove the Spark smoke step |

## C. Keep (live)
These are all used by the lifecycle, the bootstrap, the Compose files, or Dockerfiles:
- `infra/{airflow,airflow-token-broker,jenkins,jupyter,keycloak,polaris,rustfs,spark-runtime,spark-token-provider,starrocks}`
- the `scripts/` lifecycle, bootstrap, and verifier scripts, including `verify-keycloak-outage.py`, which is a manual disruptive check
- `scripts/aidlc_intent.py`, the workflow tool
