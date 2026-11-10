# U1 Domain Entities — Runtime Composition and Legacy Removal

These are logical entities for lifecycle reasoning, not implementation classes or Compose object names.

## Entities

### Runtime Service

Represents one independently managed provider or on-demand workload.

- **Identity:** Stable logical service name and service category.
- **Category:** Core provider, on-demand workload, or deferred integration.
- **Lifecycle state:** Configured, Starting, Ready, Unavailable, or Stopped.
- **State owner:** The service responsible for its own persistent state and recovery.
- **Dependencies:** Zero or more required services.

### Deployment Context

Describes which services may participate in a runtime invocation.

- **Identity:** Context name.
- **Kind:** Default, on-demand, deferred opt-in, or explicit cleanup.
- **Included services:** Services allowed to start or execute in the context.
- **Support status:** Supported, unsupported pending migration, or transition-only.

The default context is distinct from explicit opt-in and cleanup contexts. A service marked deferred cannot become part of default startup merely because it exists in the repository.

### Service Dependency

Records a prerequisite relationship between a dependent service/operation and a provider.

- **Provider:** Required Runtime Service.
- **Dependent:** Runtime Service or operation that consumes it.
- **Readiness requirement:** Provider state required before dependent work proceeds.
- **Failure effect:** The dependent work waits or reports unavailable; healthy providers remain intact.

### Readiness Observation

Records the latest readiness state for a Runtime Service.

- **Service:** Observed Runtime Service.
- **State:** Starting, Ready, Unavailable, or Stopped.
- **Observed time:** Time of observation.
- **Reason:** Redacted, actionable status or failure reason.

Readiness is service-scoped and does not assert that the entire platform is ready unless all providers required by a particular operation are ready.

### Persistent State Store

Represents state owned by a service across restarts.

- **Owner:** Exactly one Runtime Service.
- **Purpose:** Identity, catalog metadata, object data, or other service state.
- **Lifecycle:** Created for the new platform, preserved during ordinary recovery, and removed only by an explicitly authorized operation within its service boundary.
- **Legacy relationship:** New platform state is separate from legacy state and is not populated by implicit import.

### Legacy Component

Represents a retired component whose active runtime setup and dependencies are removed.

- **Identity:** FreeIPA, Hive Metastore, MIT Kerberos, or KDC.
- **Retirement status:** Planned, reference-checked, or retired from active runtime.
- **Historical references:** May remain in immutable AI-DLC archive/history.
- **Associated state:** Zero or more Legacy State Stores.

### Legacy State Store

Represents a persistent volume associated with a retired component.

- **Owning legacy component:** The component that created/used it.
- **Exact resource name:** Must be identified and reviewed before cleanup.
- **Ownership confidence:** Confirmed or ambiguous.
- **Cleanup eligibility:** Eligible only if ownership is confirmed and the store is not RustFS or otherwise unrelated.

### Legacy Cleanup Request

Represents a separate, explicit operator request to remove retired service state.

- **Requested stores:** Exact Legacy State Stores selected for removal.
- **Confirmation:** Explicit operator invocation after reviewing resource names and ownership.
- **Validation outcome:** Approved for execution or rejected as ambiguous/out of scope.
- **Result:** Removed stores and any preserved/rejected stores, without touching RustFS object data or unrelated service state.

## Relationships and invariants

- A Deployment Context includes Runtime Services; the default context excludes deferred and cleanup-only services.
- A Service Dependency links one provider to one dependent operation/service. A dependent may proceed only when all required providers are Ready.
- A Runtime Service owns its Persistent State Stores; ordinary failure or restart does not delete them.
- A Legacy Component may have Legacy State Stores, but a Legacy Cleanup Request may include only stores with confirmed ownership by a retired component.
- RustFS object storage and unrelated Persistent State Stores are never eligible for legacy cleanup.
- Cleanup is an explicit transition action and has no relationship that causes it to run during ordinary startup or bootstrap.
