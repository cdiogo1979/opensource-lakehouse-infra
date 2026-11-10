# API and Protocol Inventory

| Interface | Current use | Exposure / client | Replacement consideration |
|---|---|---|---|
| Hive Metastore Thrift, `hive-metastore:9083` | Iceberg catalog metadata | Internal Compose network; Spark and StarRocks | Migrate clients to Polaris Iceberg REST; not protocol-compatible with HMS |
| RustFS S3 API, port 9000 | Iceberg object data | Internal clients; host loopback mapping | Retain bucket/object API; separately design IAM or STS credentials |
| RustFS console, port 9001 | Local object-store administration | Host loopback | Keycloak OIDC may support console login; verify current RustFS release and policy mapping |
| MIT Kerberos, KDC 88 / admin 749 | Principal tickets/keytabs | Internal Compose network | Keycloak is not a KDC replacement; explicit workload migration decision required |
| FreeIPA LDAP/LDAPS and UI | Optional isolated validation and production overlay | Separate network; loopback UI in validation | Remove only after inventorying any active client dependency |
| JupyterHub HTTP, port 8008 | Notebook UI and login | Host loopback | Keycloak OIDC authenticator integration; separate authorization/spawn policy |
| Airflow HTTP, port 8085 | DAG UI/API and orchestration | Host published | Determine whether Keycloak SSO is in scope; job identity remains separate |
| StarRocks FE HTTP 8030 / MySQL protocol 9030 | Optional SQL engine | Host loopback | Configure Iceberg REST catalog with Polaris; confirm version compatibility and auth |
| Jenkins HTTP, port 8098 | CI UI | Host published | Identity integration not part of stated objective unless requirements add it |

This repository does not expose a custom application REST API. Exact host bindings and active profile use should be confirmed during implementation planning.
