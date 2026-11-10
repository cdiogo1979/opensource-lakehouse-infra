# Application Design Plan — Airflow Polaris Writer Identity

## Context

The approved requirements add a writer-token lifecycle across the v2 Airflow deployment and the sibling workload repository. The writer client secret stays in the Airflow trust boundary; Spark receives access tokens and must renew them during a long-running application. The current JupyterHub broker is a reference for authenticated token mediation, but it refreshes user OIDC tokens and cannot be reused as the writer client broker without changing its identity and authorization semantics.

The design will retain the `lakehouse-main`/`main` and `lakehouse-uat`/`uat` Bundles. Implementation and runtime verification remain limited to the main/production Bundle.

The user also asked whether Jupyter Spark and Airflow Spark can share a requirements/runtime setup. The current Jupyter image copies Spark 3.5.5 with Iceberg 1.8.1 from the Tabulario image and has a Jupyter-only Python requirements file; the workload repository has development requirements but no shared Spark runtime lock. Jupyter's Spark builder obtains user tokens from its Hub broker, so a shared runtime must preserve separate user and writer identity providers. The user approved the recommended shared-runtime/provider option and the compatible Iceberg auth-provider upgrade option.

## Design Scope

- Airflow control plane and protected writer credential ownership.
- Airflow-owned private token-renewal interface and the lifecycle of a per-DAG-run renewal capability.
- DAG factory to ephemeral Spark container orchestration.
- Spark token-provider integration with Polaris REST, including replacement-token behavior.
- Keycloak writer-only one-hour access-token policy and Polaris-vended RustFS access.
- Compose networking, service interfaces, failure boundaries, and source ownership across the two repositories.
- Potentially shared Spark base image, pinned runtime/dependency definition, and common Polaris auth interface for Jupyter and Airflow; identity-specific broker adapters remain separate.

## Plan and Progress

- [x] Review approved requirements, reverse-engineering findings, execution plan, and current canonical infrastructure design.
- [x] Resolve Q1–Q3: dedicated broker service, run-scoped capability, and HTTPS transport.
- [x] Resolve Q4–Q5: shared Spark runtime scope and Iceberg token-renewal integration.
- [x] Generate `components.md` with component definitions, responsibilities, and interfaces.
- [x] Generate `component-methods.md` with high-level method signatures and inputs/outputs.
- [x] Generate `services.md` with service responsibilities and orchestration.
- [x] Generate `component-dependency.md` with dependency relationships, communication patterns, and data flow.
- [x] Generate consolidated `application-design.md`.
- [x] Validate design completeness, requirement traceability, and consistency with the preserved Bundle contract.

## Questions

Please answer each question by filling the `[Answer]:` tag. If a recommendation is acceptable, enter its option letter.

### Question 1 — Token broker ownership

Where should the writer token-renewal endpoint run?

A) A dedicated internal `airflow-token-broker` service in the Airflow Compose trust boundary. It owns the Keycloak client secret; Airflow registers per-run renewal state; Spark reaches it only over the internal service network. This separates token issuance from DAG task code while keeping the secret within the Airflow boundary (recommended).

B) Extend an Airflow web/API process with a custom token endpoint and keep the secret in that process. This avoids a new container but couples token issuance to Airflow internals.

C) Put the renewal endpoint in Spark and mount the Keycloak client secret into Spark. This conflicts with the approved secret boundary and is not recommended.

X) Other (please describe after the `[Answer]:` tag below)

[Answer]:A

### Question 2 — Spark authorization to renew

How should Spark prove that it may renew the writer token for its active DAG run?

A) Airflow creates a cryptographically random, run-scoped renewal capability limited to that DAG run's configured maximum duration, sends it only to that run's Spark container, and revokes it when the DAG run ends. The broker accepts it only for the registered run and never returns the client secret (recommended).

B) Use one shared long-lived broker credential for every Spark run. This is simpler but broadens the impact of a leaked Spark container credential.

C) Use the writer access token itself to authorize renewal. This may fail precisely when the token has expired and does not independently bind renewal to a run.

X) Other (please describe after the `[Answer]:` tag below)

[Answer]:A

### Question 3 — Renewal transport

How should Spark communicate with the broker inside Docker?

A) HTTPS on a private Docker network, with Spark verifying an internal CA certificate and presenting its run-scoped renewal capability. This protects tokens in transit and authenticates the caller (recommended).

B) HTTP on a private, isolated Docker network, authenticated by the run-scoped renewal capability. This reduces certificate setup but leaves tokens readable to any workload able to observe that network.

X) Other (please describe after the `[Answer]:` tag below)

[Answer]:A

### Question 4 — Shared Spark runtime setup

Should this intent consolidate the Spark runtime/dependency setup for Jupyter Spark and Airflow Spark?

A) Create one pinned shared Spark base/runtime definition and common Polaris token-renewal engine/configuration used by both containers, with separate Jupyter-user and Airflow-writer broker adapters. Make the minimum Jupyter image/config changes needed to consume it (recommended for consistent runtime versions and less configuration drift).

B) Define shared auth/config code for Airflow only and leave the existing Jupyter Spark image and dependency file unchanged. Defer container/dependency consolidation to a later intent (smaller current change).

X) Other (please describe after the `[Answer]:` tag below)

[Answer]:A

### Question 5 — Iceberg 1.8.1 token renewal compatibility

The current Spark runtime pins Iceberg 1.8.1. That version supports REST OAuth client credentials and token exchange, but it predates the later public `AuthManager` extension API. How should Spark integrate with the Airflow token broker while keeping the writer secret out of Spark?

A) Keep Iceberg 1.8.1 and expose an OAuth2-compatible token endpoint in the broker. Airflow registers a run-scoped capability; Spark's native Iceberg OAuth client obtains and renews tokens through the broker. This keeps runtime versions stable, but means Spark obtains its initial access token from the broker instead of Airflow directly injecting it; the requirements would need to be updated and re-approved.

B) Upgrade the shared Spark runtime to an Iceberg version with the public `AuthManager` extension API, implement one broker-backed auth provider that accepts the initial Airflow token or Jupyter user token and renews through the corresponding broker, and use it from both images. This preserves the approved initial-token handoff model but expands the dependency and Jupyter runtime change.

X) Other (please describe after the `[Answer]:` tag below)

[Answer]:B

## Design Artifacts to Produce After Answers

1. `components.md`
2. `component-methods.md`
3. `services.md`
4. `component-dependency.md`
5. `application-design.md`

The design will use the approved choices where they are unambiguous, and it will identify unresolved implementation details for Functional Design rather than inventing business rules.

If Question 5 selects option A, update `requirements.md` to reflect the initial Spark-to-broker token exchange and obtain requirements re-approval before finalizing application design.
