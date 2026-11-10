# Proposed PR: Remove Dremio and organize retained lakehouse tooling

## Problem

Dremio and its JDBC integration are no longer part of the desired local lakehouse. Its service, identity/configuration, workload code, credentials, and old examples add unnecessary project and runtime state. The remaining Hive/RustFS/Spark/Jupyter platform and its data must be preserved.

## Solution

Remove Dremio from the active Compose and workload configuration, retain the Hive-backed Spark ETL, and make the legacy runtime cleanup narrowly confirmation-gated. Organize Spark, TPCH loader, and generator assets under `infra/`. Preserve existing Hive/RustFS/Kerberos/Jupyter data and the ignored runtime TPCH files.

## Main changes

- Removed Dremio and `tpch-jdbc` Compose integration, Dremio identity/proxy setup, JDBC code, and Dremio-only active examples/configuration.
- Kept the TPCH Spark ETL as `write-service-account` and retained the Hive/RustFS-backed databases and table behavior.
- Moved Spark configuration to `infra/spark/`, the TPCH loader to `infra/tpch-loader/`, and the generator to `infra/tpch-generator/`; updated Compose paths.
- Removed unused standalone Iceberg seed/Dremio SQL examples and duplicate root TPCH files after byte-comparing them with the retained `.runtime/workload/tpch-data/` copies.
- Added/retained a confirmation-gated cleanup operation that targets only legacy Dremio runtime resources.

## Verification

- **Passed:** Compose model validation; shell syntax checks; Python syntax parsing; relocated-path assertions; active-source Dremio reference review; Docker Compose builds for default and enabled-profile images.
- **Not run:** Live service health/integration, Spark-to-Hive/RustFS ETL, and the Dremio runtime cleanup. No containers were started/stopped, and no Hive, RustFS, KDC, Jupyter, or runtime credential state was changed.
- **Waiver:** None accepted. Verification is incomplete and this proposal does not claim runtime behavior or cleanup success.

## Deployment

Ordered local operational steps are required. See [`deploy_instructions.md`](deploy_instructions.md). This is a proposed handoff only; no deployment or cleanup has been executed.

## Risks and limitations

- Running `scripts/clean.sh` irreversibly deletes the Dremio data volume, `dremio` principal, and Dremio-only local credentials/keytab after confirmation. Back up any Dremio-only state that must be retained before running it.
- Cleanup fails closed unless it can prove the current Compose project, working directory, Dremio container/volume, and running KDC identity. If the existing Dremio or KDC resources were created from another project path/name, stop and resolve ownership rather than bypassing its checks.
- The optional TPCH workload removes and regenerates `.runtime/workload/tpch-data/*.tbl`, then may write Hive metadata and RustFS objects. It was not run; protect any local modifications before using it as an integration test.
- No Git metadata is present in this project directory, so the handoff is not backed by a repository diff or branch.
- This remains a local proof of concept; no production release is implied.
