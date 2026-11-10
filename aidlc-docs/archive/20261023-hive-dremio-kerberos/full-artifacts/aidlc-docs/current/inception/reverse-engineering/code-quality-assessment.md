# Code Quality Assessment

## Test Coverage

- **Automated tests**: None detected for the active PoC.
- **Manual checks**: Spark Nessie helper and documented UI/query procedures.
- **Live integration**: Not run during reverse engineering.

## Configuration Quality

- Compose services and volumes are readable and grouped by purpose.
- Catalog settings and credentials are not fully centralized: Spark properties contain static RustFS credentials while Compose also accepts them from `.env`.
- README is inconsistent with the active Compose file: it describes a direct Hadoop catalog, while Compose and Spark configuration include Nessie and TPCH loading.
- `scripts/start.sh` refers to `spark-init`, which is not a declared Compose service; the actual setup currently has bucket and TPCH one-shot services.
- Kerberos is absent, so identity propagation and impersonation behavior are not currently demonstrated.

## Technical Debt and Risks

- A catalog migration must update all Nessie references, not only the service declaration.
- Kerberos requires a defined realm/KDC, principals, service identity, credential delivery, and explicit scope for Dremio-to-Hive and Spark-to-Hive access.
- Dremio support and configuration for Hive 3 metastore and impersonation need to be verified against the selected Dremio Community build and Hive deployment mode before implementation decisions are finalized.
- Secrets should not be committed; the current local `.env` contains simple development credentials.
