# Compose Module Map

## Today
| File | Services | Started by |
|---|---|---|
| `docker-compose.yml` | keycloak-db, keycloak, polaris-db, polaris-schema-init (profile), polaris, polaris-group-reconciler (profile), rustfs, jupyterhub, jenkins. Networks: core, jupyter-user, data-access, rustfs-identity. Volumes: keycloak-db-data, polaris-db-data, rustfs-data, jupyterhub-state, jenkins-home | `lakehouse.sh start` |
| `docker-compose.starrocks.yml` | starrocks-fe, starrocks-be, network `starrocks` | `start`, unless `STARROCKS_ENABLED=false` |
| `docker-compose.airflow.yml` | airflow-postgres, airflow-init, airflow-api-server, airflow-scheduler, airflow-dag-processor, airflow-triggerer, airflow-token-broker. Networks: airflow-internal, airflow-spark | `lakehouse.sh start-airflow` |
| `docker-compose.deferred.yml` | inventory only | none |

## Requested
| Module | Services | Networks and volumes owned |
|---|---|---|
| core | keycloak-db, keycloak, polaris-db, polaris-schema-init, polaris, polaris-group-reconciler, rustfs | networks: core, data-access, rustfs-identity; volumes: keycloak-db-data, polaris-db-data, rustfs-data |
| jupyter | jupyterhub | network: jupyter-user (fixed subnet); volume: jupyterhub-state; also uses core and data-access |
| jenkins | jenkins | volume: jenkins-home; uses core |
| airflow | as today | as today |
| starrocks | as today | as today |

## Impacts
- **Compose filename references**: `docker-compose.yml` is named in 10 places (`lakehouse.sh`, three verifiers, five tests, and the StarRocks file comment), `docker-compose.airflow.yml` in 4, `docker-compose.starrocks.yml` in 5, and `docker-compose.deferred.yml` in 3.
- **Cross-file references**: modules reference networks and volumes defined in core. Compose merges files passed together with `-f`, and every module always runs together with core, so this works.
- **Project and resource names stay the same**: the project stays `lakehouse-local`, and container, volume, and network names do not change. Reset, backups, and running containers are unaffected, and the change applies without a reset.
- **Lifecycle**: `lakehouse.sh` would assemble the file list from enabled modules, in the way StarRocks is handled today.
