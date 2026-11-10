# Reverse Engineering — Code Quality and Cleanup Risks

- Dremio concerns are spread across service definitions, identity lifecycle scripts, bootstrap credentials, workload code, and operator documentation; deleting only the service would leave broken references.
- The TPCH loader belongs with its container and runner under `infra/tpch-loader/`; Dremio JDBC/Space/view behavior has been removed.
- The TPCH loader Dockerfile obtains a JDBC driver from a Dremio image. Removing the Dremio service but retaining this stage would continue pulling and building Dremio artifacts.
- `.runtime/` contains both Dremio-specific and shared credentials/data. Whole-directory cleanup is unsafe without explicit approval and would break retained services.
- Compose named volumes are externally persisted. Removing the Dremio service does not necessarily remove the named `dremio-data` volume; removing all volumes would also erase Hive metadata, RustFS data, KDC state, and notebook workspaces.
- This workspace has no `.git` metadata; changes need explicit file inventory and post-change search/Compose checks rather than a Git diff.
- Prior intent archive must remain intact; only current project source/docs and explicitly approved runtime state are candidates for cleanup.
