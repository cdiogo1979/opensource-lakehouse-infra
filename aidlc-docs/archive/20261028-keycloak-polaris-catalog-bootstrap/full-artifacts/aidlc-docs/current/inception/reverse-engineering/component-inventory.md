# Component Inventory

| Component | Current status / role | Persistence | New-intent disposition candidate |
|---|---|---|---|
| RustFS | S3-compatible object store | `object-store-data` volume | Retain; create requested environment buckets and IAM policy |
| Hive Metastore | Active Iceberg catalog (Thrift) | Metadata in PostgreSQL | Remove/replace with Polaris after clients migrate |
| Metastore PostgreSQL | Hive metadata backend | `metastore-db-data` | Remove Hive-specific DB only after migration; Polaris needs its own persistence |
| MIT KDC | Active Kerberos service | `kerberos-kdc-data` | Decision required; Keycloak cannot replace KDC protocol |
| FreeIPA validation | Optional, isolated validation | `freeipa-validation-data` | Remove old setup as requested after dependency and data review |
| Identity provisioner/reconciler | Identity, RustFS, PostgreSQL setup | Runtime credentials/state | Refactor for Keycloak, Polaris, and RustFS bootstrap |
| Spark | Iceberg compute and Airflow jobs | Mostly ephemeral; config/image | Retain; replace HMS catalog config and auth |
| JupyterHub | User notebook service | Hub and workspace volumes | Retain; replace LDAP authentication with Keycloak OIDC |
| Airflow | DAG orchestration | Airflow PostgreSQL and bundle files | Retain unless new requirements say otherwise; update Spark/catalog auth |
| Jenkins | CI | Jenkins home volume | Retain unless separately scoped |
| StarRocks | Optional analytical SQL | FE/BE volumes | Likely retain; replace HMS external catalog with Polaris REST |
| TPCH generator/loader | Optional sample workload profile | Runtime input/output | Reassess after core catalog bootstrap requirements |
| Ranger test stack | Isolated authorization experiment | Test-only | Likely remove if confirmed obsolete; separate from default stack |

Compose declares these services: `freeipa-validation`, `kdc`, `identity-provisioner`, `identity-reconciler`, `metastore-db`, `hive-schema-init`, `object-store`, `create-bucket`, `hive-metastore`, `spark`, `jupyterhub`, `jupyter-singleuser-build`, `tpch-generator`, `tpch-loader`, `airflow-postgres`, `airflow-init`, `airflow-api-server`, `airflow-scheduler`, `airflow-dag-processor`, `airflow-triggerer`, `jenkins`, `starrocks-preflight`, `starrocks-fe`, and `starrocks-be`. Several are profile-gated.
