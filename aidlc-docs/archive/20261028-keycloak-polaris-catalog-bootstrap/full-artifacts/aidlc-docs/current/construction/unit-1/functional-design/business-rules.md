# U1 Business Rules — Runtime Composition and Legacy Removal

1. **Core runtime boundary:** The default context includes only long-running services required by the approved platform-admin journey. Provider-specific startup configuration is defined in Infrastructure Design.
2. **On-demand work:** The bootstrap CLI and Spark smoke workload are invoked on demand. They may not proceed until their required providers report ready.
3. **Readiness is per service:** A service is ready only when its own readiness condition is satisfied. The readiness of one service does not imply that another is ready.
4. **Fail closed on dependencies:** If a required provider is unavailable, dependent work does not proceed and reports which dependency is unavailable.
5. **Preserve healthy state:** A partial startup or service failure does not automatically stop healthy providers, delete persistent state, or delete RustFS objects.
6. **Fresh platform state:** Keycloak, Polaris, and other new journey providers use their own fresh state. FreeIPA identity state, Hive Metastore metadata, and Kerberos/KDC state are not imported.
7. **Retire active legacy dependencies:** After reference checks, the active default deployment and its clients/configuration must not depend on FreeIPA, Hive Metastore, MIT Kerberos, or KDC services.
8. **Deferred services are unsupported until migrated:** Airflow, JupyterHub, Jenkins, and StarRocks remain outside the default journey. Any retained opt-in configuration must not start by default and must be clearly marked unsupported where it still relies on retired services.
9. **Historical records remain historical:** Immutable AI-DLC archive/history may retain legacy names and designs, but that material is not used as active runtime configuration.
10. **Legacy cleanup is explicit and narrow:** A separate cleanup operation may remove only exact, reviewed volume names confirmed to belong to retired FreeIPA, Hive/metastore, and MIT KDC services. If ownership is ambiguous, cleanup must stop without deleting anything.
11. **Never clean unrelated or object storage state:** Legacy cleanup must preserve RustFS volumes and objects and all unrelated service volumes. It must not be called by normal Compose startup or data-product bootstrap.
12. **No implicit rollback by deletion:** Recovery from startup failure may retry or restart affected services, but it does not roll back by deleting persistent resources.
