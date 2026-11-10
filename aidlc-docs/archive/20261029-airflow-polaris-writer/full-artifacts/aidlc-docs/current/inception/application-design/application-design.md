# Application Design — Airflow Polaris Writer Identity

## Decision summary

Airflow's production and UAT workloads use the existing `write-service-account`, authorized in Polaris as `role-default-writer`. The writer client secret remains inside the Airflow boundary. An Airflow-owned HTTPS broker manages per-run renewal state. Spark receives only the initial access token and a high-entropy DAG-run capability, and renews through the broker without restarting the application.

Jupyter Spark and Airflow Spark use a common pinned Spark runtime definition and common Spark-side token provider. They retain separate identity adapters and broker paths: Jupyter continues as the authenticated human user through the existing JupyterHub broker; Airflow uses the writer service identity through the Airflow broker. No identity fallback is allowed.

The selected Q5 design upgrades the shared Iceberg runtime to a compatible release exposing the public auth-provider extension approach. The exact tested Spark/Iceberg patch versions and provider SPI signatures are finalized during Functional Design and implementation compatibility checks. The initial token handoff remains in place; the custom provider handles refresh through its selected adapter.

## Runtime topology

- Airflow control plane and writer token broker run within the v2 Airflow Compose boundary.
- Airflow creates one ephemeral Spark container per DAG run on a private network shared with the broker and Polaris.
- JupyterHub keeps its existing user broker; Jupyter single-user containers consume the same pinned Spark runtime/provider package.
- Keycloak issues both service and human tokens. Polaris validates each token and the corresponding role/group authorization.
- Polaris vends scoped RustFS credentials; Spark uses those credentials for object storage I/O.

## Identity separation

| Runtime | Initial identity | Renewal adapter | Authorization |
|---|---|---|---|
| Airflow Spark | Keycloak `write-service-account` access token | Airflow broker with this DAG run's capability | Existing Polaris `role-default-writer` |
| Jupyter Spark | Current authenticated user's access token | JupyterHub broker with that active server's Hub API token | Existing user/group role mapping |

The shared provider manages bearer expiry, refresh scheduling, atomic token replacement, safe errors, and Spark/Iceberg integration. It does not select or elevate the identity.

## Required controls

- Writer client secret is readable only by the trusted Airflow token-broker path.
- Run capability is random, per-DAG-run, time-bounded to the configured run maximum, and revoked on all completion paths.
- Broker endpoints use private Docker networking and verified TLS; renewal requests are authenticated and scoped to the registered run.
- Tokens, secrets, capabilities, authorization headers, and sensitive response bodies are redacted from logs and exceptions.
- Airflow cleanup removes the Spark container and revokes broker state after success, failure, cancellation, or timeout.
- Jupyter user tokens are not exposed to Airflow; Airflow writer tokens and capabilities are not exposed to Jupyter.
- Polaris remains the policy decision point and RustFS credential vending point. No policy broadening or root-key handoff is part of this design.

## Preserved behavior and verification scope

The Bundle contract is unchanged: `lakehouse-main` tracks `main` and `lakehouse-uat` tracks `uat`. Only the main/production `main-init_environment` path receives runtime end-to-end testing, including its configured sample-table overwrite. UAT identity/configuration is source-checked only. Concurrent-workload and resilience tests remain deferred. JupyterHub's human authentication and Keycloak token policy remain unchanged; Spark renewal occurs within the running application.

## Requirement traceability

| Requirement | Design coverage |
|---|---|
| FR-1, FR-2 | Airflow topology and preserved Bundle selection contract. |
| FR-3 | Writer adapter, Keycloak service token, existing Polaris writer role. |
| FR-4, FR-5 | Airflow broker, initial token handoff, bounded run capability, shared provider refresh. |
| FR-6 | Iceberg REST bearer provider, Polaris authorization, separate vended S3 credential lifecycle. |
| FR-7, FR-8 | Main workflow test boundary and sibling source release visibility. |
| NFR-1, NFR-2 | Credential boundaries, redaction, run scoping, and unchanged grants. |
| NFR-3, NFR-4 | Shared pinned runtime with separate identity behavior; main-only evidence and explicit gaps. |

## Open items for Functional Design

1. Pin an exact Spark/Iceberg combination compatible with Spark 3.5 and the selected public auth-provider API; confirm the extension integration points.
2. Define broker request/response schemas, endpoint paths, registration idempotency, concurrency control, rate limits, and expiry validation.
3. Select the protected per-run handoff mechanism for the initial token and capability while accounting for the Docker daemon and host visibility boundary.
4. Define whether Airflow's broker is a separate service or a narrowly scoped API process, with explicit network and secret-store ownership.
5. Specify behavior for Polaris OAuth expiry separately from Polaris-vended RustFS credential expiry.
6. Confirm repository ownership/build process for one pinned Spark runtime artifact consumed by both images without changing Bundle setup.

## Stage gate

Application Design artifacts were approved on 2026-10-29. Implementation must wait for the remaining construction stages; if review finds any approved requirement needs to change, update and re-approve requirements before proceeding.
