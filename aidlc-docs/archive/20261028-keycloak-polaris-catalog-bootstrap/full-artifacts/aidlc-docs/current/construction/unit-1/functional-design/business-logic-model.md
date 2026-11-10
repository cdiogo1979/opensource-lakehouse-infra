# U1 Business Logic Model — Runtime Composition and Legacy Removal

## Purpose

U1 defines how the local runtime reaches and reports a usable state for the `default` data-product journey. It establishes service readiness and state ownership, retires FreeIPA, Hive Metastore, and MIT Kerberos/KDC from the active journey, and preserves deferred integrations as explicitly unsupported opt-in contexts until they are migrated.

## Runtime lifecycle

Each runtime service follows this logical lifecycle:

1. **Configured** — its role, required providers, and state owner are known.
2. **Starting** — initialization is in progress; dependent work waits.
3. **Ready** — its own readiness condition is satisfied and it may serve dependent work.
4. **Unavailable** — it failed to start or lost readiness; the failure and affected dependents are reported.
5. **Stopped** — it was explicitly stopped or the runtime was shut down.

`Unavailable` is scoped to the affected service and its dependents. A failure does not automatically stop healthy providers, remove persistent state, or erase object data. A dependent operation is held until its required providers are ready; if they cannot become ready, the operation ends with an actionable dependency error.

## Deployment contexts

| Context | Intended behavior |
|---|---|
| Default runtime | Starts only the long-running providers required by the platform-admin bootstrap journey. Each provider reports readiness independently. |
| On-demand operation | The host bootstrap CLI and one-shot Spark smoke workload run only when invoked and only after their required providers are ready. They do not become default long-running services. |
| Deferred integration | Airflow, JupyterHub, Jenkins, and StarRocks remain outside the supported default journey. If retained in the project, they require an explicit opt-in context and are not considered operational until separately migrated from retired dependencies. |
| Legacy cleanup | A separate, explicitly invoked transition operation may remove only identified retired FreeIPA, Hive/metastore, and MIT KDC volumes. It is not part of startup or product bootstrap. |

## Dependency and failure flow

The runtime foundation supplies readiness to later bootstrap stages. Keycloak, Polaris and its metadata state, and RustFS are independent providers in the core runtime; cross-provider bootstrap work may begin only when each provider it needs is ready. U1 owns the readiness contract, not the provider-specific setup or bootstrap logic owned by later units.

When a provider is unavailable, the runtime records the failed provider and the dependent work that cannot proceed. Healthy services remain available. Recovery retries or restarts the affected provider or dependent operation without an implicit cleanup of persistent state.

## Legacy retirement flow

Active runtime dependencies on FreeIPA, Hive Metastore, and MIT Kerberos/KDC are removed after references are checked. The new runtime owns fresh, separate state; it does not import legacy identity, catalog metadata, or KDC state. Historical AI-DLC archive material remains immutable reference material and is not an active runtime dependency.

Before any legacy-volume cleanup, an operator identifies and reviews the exact volume names and confirms that each belongs only to a retired FreeIPA, Hive/metastore, or MIT KDC service. Cleanup then targets those confirmed volumes alone. RustFS object data and unrelated service state are outside this cleanup boundary. Ordinary startup and bootstrap never invoke it.

## U1 completion outcome

U1 is functionally complete when the default runtime context contains only journey-required providers, readiness is reported per provider, dependent work waits or fails clearly, healthy state survives partial failure, and no active default dependency requires FreeIPA, Hive, or Kerberos. Infrastructure Design will define concrete service names, health checks, profiles, and volume names.
