# Unit 5 Technology Decisions — JupyterHub and Per-User Spark

| Area | Decision | Rationale and limit |
|---|---|---|
| JupyterHub | Retain the existing JupyterHub 5.3.0 baseline from `jupyter-platform/`. | It is the approved starting point. The Hub is local-only and uses DummyAuthenticator only for this PoC. |
| Spawner | Retain DockerSpawner and pin it, plus related Python dependencies, to explicit versions compatible with JupyterHub 5.3.0 before implementation. | The sibling configuration already uses DockerSpawner, but its install currently floats. A repeatable build requires explicit compatible versions; selection/verification is an implementation prerequisite. |
| Spark single-user image | Retain the target PoC's Spark 3.5.5 / Iceberg 1.8.1 image baseline. | This matches the existing target Spark configuration and catalog contract. Runtime compatibility with per-session Kerberos and RustFS credentials remains to be verified. |
| Session topology | Use one isolated notebook container with local Spark per active username; support the three configured sessions concurrently on the existing host. | This satisfies the fixed local capacity without introducing a shared Spark cluster or horizontal scaling. Resource sizing and performance SLAs are out of scope. |
| Authentication | Retain DummyAuthenticator with only the configured `user_a`, `user_b`, and `admin` labels; bind the Hub locally. | DummyAuthenticator does not verify a human identity and is unsuitable for remote exposure. This limitation is explicit and accepted for the local PoC. |
| Credential delivery | Use each user's own read-only Kerberos keytab and distinct RustFS identity, with a private per-session ticket cache. | Keeps component credentials separate and prevents cross-user mounts. No secret values are stored in design artifacts. |
| Workspace storage | Use a distinct persistent work volume per username, with no shared writable notebook directory. | User work survives container recreation without enabling cross-user writable sharing. Automatic backup/restore is not required. |
| Recovery and evidence | Use operator-led recovery of an affected session and keep minimal redacted evidence locally. | Fits the single-host manual-recovery PoC. No monitoring, centralized audit service, formal retention period, or automatic retries are added. |

## Compatibility and Verification Gates

- Resolve and pin exact DockerSpawner/Jupyter Python package versions compatible with JupyterHub 5.3.0 before building the Hub image.
- Verify the retained Spark/Iceberg image can authenticate to the Kerberized Hive Metastore from the notebook container and can use the matching RustFS identity.
- Verify three concurrent sessions fit the available local host resources; no numeric performance commitment is made.
- Demonstrate the `user_a` and `user_b` Spark allow/deny matrix. Hive/RustFS enforcement remains a separate feasibility gate; a failure does not authorize a broader policy or a different user identity.
