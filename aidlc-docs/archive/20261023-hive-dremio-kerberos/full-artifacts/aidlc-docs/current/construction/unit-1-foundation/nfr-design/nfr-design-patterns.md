# Unit 1 NFR Design Patterns

## Scope

These patterns translate the approved Unit 1 NFRs into logical implementation guidance for the local Docker Compose foundation. They do not select concrete image tags, healthcheck commands, ports, mounts, environment variables, or Compose syntax; those belong to Infrastructure Design. They do not prove Hive Metastore storage-based authorization over RustFS or effective-user propagation through Dremio and Spark.

## Availability, Readiness, and Dependency Gating

- Model service health separately from overall platform readiness. A container being running is not sufficient evidence that it can safely serve dependent initialization.
- Long-running dependencies expose a readiness signal appropriate to their role: KDC authentication, PostgreSQL accepting connections and serving the Hive schema, RustFS API availability, and Hive Metastore serving catalog requests after its schema and authentication prerequisites are satisfied.
- Order dependents on the readiness of the prerequisites they actually consume. Hive Metastore depends on PostgreSQL schema readiness, KDC service identity availability, and configured storage prerequisites. Bucket setup depends on RustFS readiness. Later identity provisioning and ETL must wait for the relevant foundation and authorization steps to succeed.
- Treat one-shot initialization as a successful-completion dependency, not as a healthcheck on a long-running process. A failed initializer blocks its dependents and leaves the overall foundation not ready.
- Report per-component and per-initialization-step outcomes so an operator can distinguish available diagnostic services from a foundation that is ready for downstream use.

## Retry and Failure Pattern

- Use bounded retries only around operations that are explicitly safe to repeat, such as waiting for a dependency, ensure-only bucket creation, and idempotent identity/schema setup.
- Do not retry permanent configuration, authentication, authorization, or incompatible persisted-state failures as if they were transient. Surface the failed component/step and stop the dependent chain.
- Do not restart the entire stack in a loop or add a recovery supervisor. Compose health/restart behavior must not conceal a failed one-shot initialization or declare downstream readiness prematurely.
- Preserve named volumes and partial state after failure for diagnosis. Recovery is operator initiated; startup does not remove or replace metadata or object data.
- Keep stop-only and destructive full-reset operations distinct. Full reset is an explicit operator action and is never an automatic retry or error-recovery path.

## Local Credential and Secret Delivery Pattern

- Generate or provision development credentials and keytabs into a local runtime directory that is ignored by version control and restricted to the host operator.
- Mount only the credential files required by each consuming service, read-only where supported. Do not copy secrets into tracked configuration, container images, logs, or general diagnostic output.
- Keep Kerberos credentials, RustFS access keys, PostgreSQL passwords, and Dremio credentials separate; identity reuse across these systems is not implied.
- Runtime logs may show principal/account names and step outcomes, but never secret values, keytab contents, or credential-bearing command arguments.
- This is a local PoC credential pattern, not a production secrets-management design.

## Network Exposure Pattern

- Bind developer-facing host-published service ports to loopback. Container-to-container traffic uses the Compose network and service names.
- Do not publish services to a LAN interface or add a reverse proxy/load balancer in this unit. Any future non-local access requirement changes the security boundary and requires a reviewed design update.
- Show useful local URLs in operator status output while identifying services that are not ready.

## Performance and Scaling Pattern

- Use one instance per service on one Compose host. Do not add replicas, a load balancer, distributed coordination, or horizontal scaling mechanisms.
- Keep resource defaults appropriate for the small TPCH demonstration and prioritize deterministic initialization and correct authorization behavior.
- Do not add caches, queues, or benchmarking infrastructure absent a measured need and an approved target. Resource constraints that prevent local startup should be documented during Infrastructure Design.

## Observability and Operator Recovery

- Compose health/status and concise actionable service/initializer logs are sufficient for this local environment. No metrics, alerting, monitoring stack, or custom administration UI is added.
- Initialization reports component, operation, and outcome (created, already present, ready, or failed), without disclosing secrets.
- On a required failure, present the failed step and relevant diagnostic route; do not label the overall platform ready while downstream prerequisites are unknown or failed.
- Document prerequisites, startup order, readiness interpretation, stop-only behavior, explicit destructive reset, persistence, and safe recovery commands during Infrastructure Design.

## Feasibility Boundary

Hive storage-based authorization over RustFS and effective-user results for both Dremio and Spark remain unresolved feasibility gates. Health checks and successful startup do not constitute evidence that per-database allow/deny outcomes are enforced. Preserve the Functional Design rule to report unsupported outcomes as blocked and request review of any architecture change rather than weakening the authorization criterion.

## NFR Traceability

| Design concern | Approved requirements |
|---|---|
| Single host, no scaling or SLA | U1-NFR-01 to U1-NFR-05 |
| Persistent state, operator-managed recovery | U1-NFR-06 to U1-NFR-08, U1-NFR-20 |
| Loopback-only exposure and secret handling | U1-NFR-09 to U1-NFR-14 |
| Version and authorization feasibility gates | U1-NFR-15 to U1-NFR-17 |
| Readiness, fail-closed initialization, and safe retries | U1-NFR-18 to U1-NFR-22 |
| Maintainable local operation and status | U1-NFR-23 to U1-NFR-26 |

## Extension Applicability

- Security Baseline extension: disabled; the applicable approved NFR security constraints above remain in force.
- Property-Based Testing extension: partial; not applicable to this design-only artifact stage.
- Resiliency Baseline extension: disabled; functional failure and recovery requirements above remain in force.
