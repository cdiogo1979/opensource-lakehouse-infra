# Technology Stack

- **StarRocks**: the legacy image tag is 4.1.6 (`local/starrocks-fe:4.1.6-kerberos`), and the base image is upstream `starrocks/fe-ubuntu` and `be-ubuntu`. The version for v2 is to be decided.
- **Platform services**: Polaris 1.8.0 (Iceberg REST), Keycloak 26.8.1, RustFS 1.0.4, Iceberg 1.10.2 / Spark 3.5.5 for writers.
- **Host tooling**: Docker Compose V2 on Rancher Desktop (`linux/arm64`) and Python 3. The upstream StarRocks images must support arm64.
